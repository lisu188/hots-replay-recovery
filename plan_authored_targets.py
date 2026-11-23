"""Derive a TEN_GREYMANE command-target transfer plan from its tracker and the two stock maps."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from xml.etree import ElementTree

from map_startup_identity import match_startup, parse_objects
from project_rank_targets import MAP, SOURCE, MPQArchive, components, field, lifetime_ends, members
from project_rank_targets import decode_events, encode_events, pack, pinned, protocol41810, require


def layout(path, build):
    pinned(path, MAP[build])
    with closing(MPQArchive(path)) as archive:
        xml = archive.read_file("Objects")
    nodes = ElementTree.fromstring(xml).findall("ObjectUnit")
    players = {int(n.attrib["Id"]): int(n.get("Player", 0)) for n in nodes}
    placements = parse_objects(xml)
    require(len(players) == len(nodes) == len(placements), "Duplicate or missing object IDs")
    return placements, players, sha256(xml).hexdigest()


def spatial_key(row):
    return row.unit_type, row.x, row.y


def join_layouts(source_rows, target_rows):
    counts = [Counter(spatial_key(r) for r in side) for side in (source_rows, target_rows)]
    target_by_id = {r.object_id: (i, r) for i, r in enumerate(target_rows)}
    links = {}
    for source_index, source in enumerate(source_rows):
        pair = target_by_id.get(source.object_id)
        if pair is None:
            continue
        target_index, target = pair
        key = spatial_key(source)
        if spatial_key(target) == key and all(c[key] == 1 for c in counts):
            links[source_index] = target_index
    require(len(links) == len(set(links.values())), "Non-injective object correspondence")
    return links


def owner_policy(loop, first_change, snapshot_pair, authored_player):
    if first_change is not None and loop >= first_change:
        return "withhold_after_or_at_source_owner_transition"
    if snapshot_pair != (authored_player, authored_player):
        return "withhold_source_snapshot_disagrees_with_authored_player"
    return "project_authored_player"


def transfer_plan(game, tracker, source_layout, target_layout):
    old_rows, old_owner, old_xml_sha = source_layout
    new_rows, new_owner, new_xml_sha = target_layout
    cross = join_layouts(old_rows, new_rows)
    verified, evidence = match_startup(old_rows, tracker)
    require(evidence["verified"] == len(old_rows), "Incomplete verified source placements")
    source_ids = [(a.index, a.recycle) for a in verified]
    initial_end = lifetime_ends(tracker, source_ids)
    first_owner_change = {}
    for e in tracker:
        if e["_event"].endswith(".SUnitOwnerChangeEvent"):
            first_owner_change.setdefault((e["m_unitTagIndex"], e["m_unitTagRecycle"]), e["_gameloop"])
    for a in verified:
        born = tracker[a.event_offset]
        require(
            (born["m_controlPlayerId"], born["m_upkeepPlayerId"]) == (old_owner[a.object_id],) * 2,
            "Source XML owner disagrees with tracker startup",
        )
    by_key = {(a.index, a.recycle): a for a in verified}
    all_refs = qualifying = 0
    rows, excluded, counts = [], Counter(), Counter()
    events = list(decode_events(game, protocol41810, "game"))
    for ordinal, e in enumerate(events):
        target = field(e)
        if target is None:
            continue
        all_refs += 1
        tag = target["m_tag"]
        key = components(tag, 18)
        a = by_key.get(key)
        if a is None or a.index not in cross:
            excluded["outside_unique_common_startup_objects"] += 1
            continue
        loop = e["_gameloop"]
        if not 0 < loop < initial_end.get(key, float("inf")):
            excluded["outside_first_source_lifetime"] += 1
            continue
        dest = cross[a.index]
        predicted = pack(dest, 1, 22)
        source = old_rows[a.index]
        point = target["m_snapshotPoint"]
        xy_agree = (point["x"], point["y"]) == (source.x * 4096, source.y * 4096)
        if not xy_agree:
            excluded["source_snapshot_differs_from_exact_authored_xy"] += 1
            continue
        qualifying += 1
        counts["source_snapshot_exact_xy"] += 1
        counts["changed_rank" if a.index != dest else "same_rank"] += 1
        counts["changed_packed_tag" if predicted != tag else "same_packed_tag"] += 1
        if source.x == int(source.x) and source.y == int(source.y):
            counts["integer_xy"] += 1
        else:
            counts["fractional_xy"] += 1
        old = old_owner[a.object_id]
        new = new_owner[new_rows[dest].object_id]
        src_pair = (target["m_snapshotControlPlayerId"], target["m_snapshotUpkeepPlayerId"])
        ownership = owner_policy(loop, first_owner_change.get(key), src_pair, old)
        counts[ownership] += 1
        output = dict(
            ordinal=ordinal,
            loop=loop,
            object_id=a.object_id,
            unit_type=a.unit_type,
            source_tag=tag,
            projected_tag=predicted,
            authored_owner_policy=ownership,
        )
        if ownership == "project_authored_player":
            output.update(projected_control_player_id=new, projected_upkeep_player_id=new)
            counts[
                (
                    "projected_owner_pair_differs_from_source"
                    if old != new
                    else "projected_owner_pair_matches_source"
                )
            ] += 1
        rows.append(output)
        target["m_tag"] = predicted
    require(all_refs == qualifying + excluded.total(), "Command accounting")
    wire = encode_events(events, protocol41810, "game")
    inverse = {dest: source for source, dest in cross.items()}
    recovered = list(decode_events(wire, protocol41810, "game"))
    for r in rows:
        target = field(recovered[r["ordinal"]])
        idx, recycle = components(target["m_tag"], 22)
        require(recycle == 1, "Projected initial recycle changed")
        target["m_tag"] = pack(inverse[idx], 1, 18)
    recovered_wire = encode_events(recovered, protocol41810, "game")
    require(recovered_wire == game, "Authored inverse did not restore exact source game member")
    receipt = dict(
        source_replay_sha256=SOURCE,
        source_objects_sha256=old_xml_sha,
        target_objects_sha256=new_xml_sha,
        source_placements=len(old_rows),
        target_placements=len(new_rows),
        common_authored_objects=len(cross),
        source_verified_startup_placements=len(source_ids),
        target_inputs="stock map Objects only",
        target_initial_recycle_rule=1,
        original_command_targets=all_refs,
        qualifying_fields=qualifying,
        counts=dict(sorted(counts.items())),
        excluded=dict(sorted(excluded.items())),
        original_game_bytes=len(game),
        original_game_sha256=sha256(game).hexdigest(),
        projected_in_memory_41810_game_sha256=sha256(wire).hexdigest(),
        inverse_game_byte_equal=True,
        scope="The plan projects initial target tags and authored owner pairs for qualifying source events. "
        "Command-time state for the historical match on the target build is unverified.",
    )
    return rows, receipt


def write_once(path, value):
    data = (json.dumps(value, indent=2) + "\n").encode("utf-8")
    if path.exists():
        require(path.read_bytes() == data, "Existing output differs")
    else:
        with path.open("xb") as stream:
            stream.write(data)
    return sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "source-map", "target-map", "output-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--compare-prior", type=Path)
    args = parser.parse_args()
    layouts = layout(args.source_map, 41810), layout(args.target_map, 98348)
    game, tracker = members(args.source, SOURCE, 41810)
    rows, report = transfer_plan(game, tracker, *layouts)
    if args.compare_prior:
        old = json.loads(args.compare_prior.read_bytes())
        new = {r["ordinal"]: (r["source_tag"], r["projected_tag"]) for r in rows}
        prior = {r["ordinal"]: (r["source_tag"], r["projected_tag"]) for r in old}
        require(
            len(prior) == len(old) and all(new.get(i) == v for i, v in prior.items()),
            "Prior projection mismatch",
        )
        report["prior_comparison"] = dict(
            prior_fields=len(prior), agreeing_fields=len(prior), additional_fields=len(new) - len(prior)
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report["ordinal_table_sha256"] = write_once(args.output_dir / "authored-targets.json", rows)
    write_once(args.output_dir / "authored-plan.json", report)
    print(json.dumps(report))


if __name__ == "__main__":
    main()
