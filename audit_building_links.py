"""Re-derive original building catalog links and verify target witnesses across disjoint recordings."""

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from hashlib import sha256
import json
from pathlib import Path

from catalog_diagnostics import UnitTimeline, link_fields
from command_authored_xy import BUILDINGS, fixed
from map_startup_identity import match_startup
from plan_authored_targets import layout, write_once
from project_rank_targets import (
    MAP,
    ROSTER,
    SOURCE,
    components,
    field,
    lifetime_ends,
    members,
    pinned,
    protocol41810,
    protocol96477,
    require,
)

RUNTIME = "8371d65c0c680ad8aaf9fa283f489f76c8dd6660595a566d438cbf62a003f73e"
ROW_DIGEST = "9cfa8a1dbe50fed97167485590661060982a5aed5d2db586563910492050eccd"


def inspect(task):
    path, digest, build, map_path, wanted = task
    game, tracker = members(path, digest, build)
    protocol, shift = (protocol41810, 18) if build == 41810 else (protocol96477, 22)
    game = list(protocol.decode_replay_game_events(game))
    timeline = UnitTimeline(tracker)
    mapping = defaultdict(set)
    unclassified = 0
    for f in link_fields(game):
        names = [timeline.lookup(tag, f.gameloop, shift)[0] for tag in f.tags]
        unclassified += int(None in names)
        # A known second type vetoes a link, even in a partially classified subgroup.
        for name in set(names) - {None}:
            mapping[name].add(f.link)
    placements, _, _ = layout(map_path, build)
    anchors, evidence = match_startup(placements, tracker)
    require(evidence["verified"] == len(placements), "Incomplete authored startup")
    by_key = {(a.index, a.recycle): a for a in anchors}
    ends = lifetime_ends(tracker, by_key)
    witnesses = Counter()
    source_rows = []
    for ordinal, event in enumerate(game):
        target = field(event)
        if target is None:
            continue
        key = components(target["m_tag"], shift)
        anchor = by_key.get(key)
        loop = event["_gameloop"]
        if (
            anchor is None
            or anchor.unit_type not in BUILDINGS
            or not 0 < loop < ends.get(key, float("inf"))
        ):
            continue
        xy = fixed(anchor.authored_x), fixed(anchor.authored_y)
        point = target["m_snapshotPoint"]
        if xy != (point["x"], point["y"]):
            continue
        name, link = anchor.unit_type, target["m_snapshotUnitLink"]
        require(
            timeline.lookup(target["m_tag"], loop, shift) == (name, "known_alive"),
            "Source/target live type",
        )
        shape = target["m_targetUnitFlags"], target["m_timer"]
        witnesses[name, link, *shape] += 1
        if build == 41810:
            require(
                wanted.get(ordinal) == [loop, anchor.object_id, *xy], "Original ordinal/loop/object/XY"
            )
            eid = event["_eventid"]
            require(eid in (27, 105), "Unexpected building command event id")
            sequence_state = (
                ("absent" if event["m_sequence"] is None else "present")
                if eid == 105
                else "not_applicable"
            )
            source_rows.append((ordinal, name, link, *shape, eid, sequence_state))
    if build == 41810:
        require(len(source_rows) == len(wanted) == 2179, "Complete historical ordinal set")
    return dict(
        digest=digest,
        mapping=mapping,
        witnesses=witnesses,
        unknown_fields=unclassified,
        rows=source_rows,
    )


def combine(data):
    forward = defaultdict(set)
    reverse = defaultdict(set)
    for r in data:
        for name, links in r["mapping"].items():
            for link in links:
                forward[name].add(link)
                reverse[link].add(name)
    return forward, reverse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "source",
        "source-map",
        "current-map",
        "rows",
        "roster",
        "runtime-anchors",
        "control-root",
        "external-manifest",
        "external-root",
        "output-dir",
    ):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--private-ordinals", type=Path, help="Optional local-only per-event ledger.")
    args = parser.parse_args()
    roster = json.loads(pinned(args.roster, ROSTER))
    runtime = json.loads(pinned(args.runtime_anchors, RUNTIME))
    old = json.loads(args.rows.read_bytes())
    encoded = json.dumps(old["rows"], separators=(",", ":")).encode()
    require(
        old["source_sha256"] == SOURCE
        and old["original_map_sha256"] == MAP[41810]
        and sha256(encoded).hexdigest() == old["compact_rows_json_sha256"] == ROW_DIGEST,
        "Original rows pin",
    )
    wanted = {row[0]: row[1:] for row in old["rows"]}
    ext = json.loads(args.external_manifest.read_bytes())["cases"]
    expected_external = (
        "bc16af7f68496cddc4698f70b3853402a0f30aa37951aec3a6b555ed703879e8",
        "a956b186a0459a47d9b0fdd8af4ccb65c437f11926186471c434e543e218b2d7",
    )
    require(
        tuple(r["replay_sha256"] for r in ext) == expected_external, "Unexpected independent controls"
    )
    refs = roster["references"]
    tasks = [
        (args.control_root / r["replay_file"], r["replay_sha256"], 98348, args.current_map, None)
        for r in refs
    ]
    tasks.extend(
        (
            args.external_root / (r["replay_sha256"] + ".StormReplay"),
            r["replay_sha256"],
            98348,
            args.current_map,
            None,
        )
        for r in ext
    )
    require(
        len(refs) == 12 and len(ext) == 2 and len({t[1] for t in tasks}) == 14,
        "Disjoint stock controls",
    )
    with ProcessPoolExecutor(max_workers=3) as pool:
        controls = list(pool.map(inspect, tasks))
    original = inspect((args.source, SOURCE, 41810, args.source_map, wanted))
    source_names, source_reverse = combine([original])
    target_names, target_reverse = combine(controls)
    leads = {r["unit_type"]: r["after"] for r in roster["proposed_unit_mapping"]["observed_pairs"]}
    require(
        len(leads) == 33
        and roster["source"]["build"] == 98285
        and roster["source"]["replay_sha256"] != SOURCE,
        "Expected R8 lead manifest",
    )
    external_alias = {int(x) for x in runtime["excluded_reverse_aliases"]}
    source_type_count = Counter(r[1] for r in original["rows"])
    groups = {}
    counters = Counter()
    tier = Counter()
    qualified = []
    events_by_tier = defaultdict(Counter)
    for name, source_count in sorted(source_type_count.items()):
        before, after = source_names[name], target_names[name]
        source_collision = sorted({n for l in before for n in source_reverse[l] if n != name})
        target_collision = sorted({n for l in after for n in target_reverse[l] if n != name})
        reasons = []
        if name not in leads:
            reasons.append("outside_33_target_leads")
        if len(before) != 1 or source_collision:
            reasons.append("ambiguous_original_link")
        if len(after) != 1 or target_collision or external_alias.intersection(after):
            reasons.append("target_alias_or_no_unique_link")
        if name in leads and after != {leads[name]}:
            reasons.append("target_lead_not_confirmed")
        current_candidate = runtime["all_unambiguous_current_candidates"].get(name)
        if current_candidate is not None and after != {current_candidate}:
            reasons.append("other_current_observation_conflicts")
        shapes = Counter()
        for (n, l, flags, timer), cnt in original["witnesses"].items():
            if n == name:
                shapes[flags, timer] += cnt
        if shapes != {(111, 0): source_count}:
            reasons.append("original_shape_disagreement")
        witnesses = []
        live_all = []
        target_shape = Counter()
        for record in controls:
            c = record["witnesses"]
            matched = 0
            observed = 0
            for (n, l, flags, timer), cnt in c.items():
                if n == name:
                    target_shape[(flags, timer)] += cnt
                    observed += cnt
                    if l == leads.get(name) and (flags, timer) == (111, 0):
                        matched += cnt
            witnesses.append(matched)
            live_all.append(observed)
        if any(s != (111, 0) for s in target_shape):
            reasons.append("target_live_building_shape_disagreement")
        if not sum(live_all[:12]):
            reasons.append("no_twelve_live_building_witness")
        elif name in leads and not sum(witnesses[:12]):
            reasons.append("no_twelve_witness_for_lead_and_shape")
        if not reasons:
            support = sum(bool(n) for n in witnesses[12:])
            tier[support] += source_count
            counters["source_rows_with_twelve_support"] += source_count
            if support:
                counters["source_rows_with_external_support"] += source_count
            if support == 2:
                counters["source_rows_with_both_externals"] += source_count
        groups[name] = dict(
            source_commands=source_count,
            original_links=sorted(before),
            target_lead=leads.get(name),
            current_observed_links=sorted(after),
            original_aliases=source_collision,
            current_aliases=target_collision,
            current_broader_alias_veto=bool(external_alias.intersection(after)),
            live_building_witnesses_any_link_in_twelve=sum(live_all[:12]),
            live_building_witnesses_any_link_in_two=live_all[12:],
            source_shape_counts={f"{f}/{t}": n for (f, t), n in shapes.items()},
            target_live_shape_counts={f"{f}/{t}": n for (f, t), n in sorted(target_shape.items())},
            live_matching_witnesses_in_twelve=sum(witnesses[:12]),
            twelve_files_with_live_witnesses=sum(bool(c) for c in witnesses[:12]),
            live_matching_witnesses_in_two=witnesses[12:],
            blocks=reasons,
        )
    for ordinal, name, oldlink, flags, timer, event_id, sequence_state in original["rows"]:
        group = groups[name]
        if group["blocks"]:
            continue
        support = sum(bool(x) for x in group["live_matching_witnesses_in_two"])
        events_by_tier[support][f"event_{event_id}_sequence_{sequence_state}"] += 1
        qualified.append(
            [ordinal, oldlink, leads[name], flags, timer, support, event_id, sequence_state]
        )
    args.output_dir.mkdir(exist_ok=True, parents=True)
    private = dict(
        columns=[
            "source_ordinal",
            "actual_41810_link",
            "stock_98348_link",
            "flags",
            "timer",
            "external_files",
            "event_id",
            "source_sequence_state",
        ],
        rows=qualified,
    )
    table = sha256((json.dumps(private, indent=2) + "\n").encode("utf-8")).hexdigest()
    if args.private_ordinals:
        require(write_once(args.private_ordinals, private) == table, "Private ledger digest mismatch")
    report = dict(
        source_sha256=SOURCE,
        historical_rows_sha256=ROW_DIGEST,
        twelve_manifest_sha256=ROSTER,
        earlier_manifest_source_build=roster["source"]["build"],
        earlier_manifest_source_sha256=roster["source"]["replay_sha256"],
        historical_commands=len(original["rows"]),
        groups=groups,
        counts=dict(counters),
        historical_building_source_flags_and_timer={
            "flags_111_timer_0": sum(r[3:5] == (111, 0) for r in original["rows"])
        },
        number_of_eligible_types=sum(not bool(g["blocks"]) for g in groups.values()),
        excluded_source_commands=len(original["rows"]) - len(qualified),
        event_sequence_by_external_support={k: dict(v) for k, v in sorted(events_by_tier.items())},
        external_files_support_for_eligible_source_rows=dict(sorted(tier.items())),
        qualified_ordinal_table_sha256=table,
        source_unclassified_or_partly_classified_catalog_fields=original["unknown_fields"],
        controls=[
            dict(
                replay_sha256=c["digest"],
                unclassified_or_partly_classified_catalog_fields=c["unknown_fields"],
            )
            for c in controls
        ],
        scope="Known aliases checked across recorded command and selection links. "
        "Target IDs are conditional on the stock 98348 Dragon Shire catalog and dependency order. "
        "Unknown identities, complete runtime catalog, and custom historical package numeric links are unverified.",
    )
    write_once(args.output_dir / "building-link-receipt.json", report)
    print(
        json.dumps(
            dict(
                counts=dict(counters),
                tiers=dict(tier),
                blocked=[
                    (n, g["source_commands"], g["blocks"]) for n, g in groups.items() if g["blocks"]
                ],
            )
        )
    )


if __name__ == "__main__":
    main()
