"""Project original command target tags onto observed stock Dragon Shire startup ranks."""

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing
from hashlib import file_digest, sha256
import json
from pathlib import Path

from heroprotocol.versions import protocol41810, protocol96477
from migrate_replay import decode_events, encode_events
from mpq_reader import MPQArchive
from repair_unit_tags import components, pack, tracker_pairs

SOURCE = "e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824"
ANCHORS = "4bd6c35a1550a9fbdf90c31f25170faefdd4d170e3f49dfb737089495fccdd46"
ROSTER = "fc6dbc312dac9143bfe450d661f8033a04c2ce4eec51878618e2a517f8faf609"
MAP = {
    41810: "e0a58745837b3b5351015c933560dbffb178d747009d2d57b4153ef425cf7250",
    98348: "f557190f8aaab160789272ce086b8b69d6a8037b152de150332603dae3dc098f",
}
TRANSITIONS = {
    "SUnitBornEvent",
    "SUnitInitEvent",
    "SUnitTypeChangeEvent",
    "SUnitDiedEvent",
    "SUnitRevivedEvent",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pinned(path, expected):
    raw = path.read_bytes()
    # Both full-file digests are known for the two JSON manifests when Git converts LF/CRLF.
    # Archives and game inputs always require the sole raw-file digest.
    newline_variants = {
        ANCHORS: "98dcdbdb03d3282caada47b18071d6a1eab8d59d64429a32fafa5aa91777e072",
        ROSTER: "c32a4a1ac9649c8a2b01637794743fd28996ba5dde8f199d73032b89fab2a172",
    }
    require(
        sha256(raw).hexdigest() in (expected, newline_variants.get(expected)),
        "Unexpected SHA-256: " + path.name,
    )
    return raw


def members(path, expected, build):
    protocol = protocol41810 if build == 41810 else protocol96477
    with closing(MPQArchive(path)) as arc:
        arc.file.seek(0)
        require(file_digest(arc.file, "sha256").hexdigest() == expected, "Replay SHA-256")
        head = protocol.decode_replay_header(arc.header["user_data_header"]["content"])
        require(
            (head["m_version"]["m_build"], head["m_version"]["m_baseBuild"]) == (build, build), "build"
        )
        deps = protocol.decode_replay_details(arc.read_file("replay.details"))["m_cacheHandles"]
        require(deps[-1][8:].hex() == MAP[build], "map dependency")
        game = arc.read_file("replay.game.events")
        tracker = list(protocol.decode_replay_tracker_events(arc.read_file("replay.tracker.events")))
        arc.file.seek(0)
        require(file_digest(arc.file, "sha256").hexdigest() == expected, "Replay changed during read")
    return game, tracker


def field(event):
    if event["_event"] == "NNet.Game.SCmdEvent":
        return event["m_data"].get("TargetUnit")
    if event["_event"] == "NNet.Game.SCmdUpdateTargetUnitEvent":
        return event["m_target"]
    return None


def command_checks(events, tracker, rows, identities, shift):
    counted = Counter()
    by_xy = defaultdict(list)
    for row, identity in zip(rows, identities):
        by_xy[row["x"] * 4096, row["y"] * 4096].append(identity)
    ends = lifetime_ends(tracker, identities)
    anchor_set = set(identities)
    predictions = Counter()
    for event in events:
        target = field(event)
        if target is None:
            continue
        loop = event["_gameloop"]
        point = target["m_snapshotPoint"]
        candidates = by_xy.get((point["x"], point["y"]), ())
        predicted = None
        if len(candidates) == 1 and eligible(candidates[0], loop, anchor_set, ends):
            predicted = pack(*candidates[0], shift)
        # Neither candidate selection nor lifetime uses the command's held-out tag.
        recorded = target["m_tag"]
        if recorded not in (0, 0xFFFFFFFF):
            counted[recorded] += 1
        actual_anchor = eligible(components(recorded, shift), loop, anchor_set, ends)
        if actual_anchor:
            predictions["recorded_initial_anchor_targets"] += 1
        if predicted is not None:
            predictions["xy_predictions"] += 1
            predictions["tag_equal" if predicted == recorded else "tag_different"] += 1
    pairs = tracker_pairs(tracker)
    scores = {
        shift: sum(count for tag, count in counted.items() if components(tag, shift) in pairs)
        for shift in range(1, 32)
    }
    compatible = [s for s in scores if scores[s] == counted.total()]
    require(counted and compatible, "No fully compatible command target layout")
    return dict(
        compatible_shifts=compatible,
        distinct_tags=len(counted),
        fields=counted.total(),
        unique_live_anchor_xy_test={
            k: predictions[k]
            for k in ("recorded_initial_anchor_targets", "xy_predictions", "tag_equal", "tag_different")
        },
    )


def startup(tracker, rows, column):
    births = defaultdict(list)
    for event in tracker:
        if event["_gameloop"] == 0 and event["_event"].endswith(".SUnitBornEvent"):
            key = (event["m_unitTypeName"].decode("ascii"), event["m_x"], event["m_y"])
            births[key].append((event["m_unitTagIndex"], event["m_unitTagRecycle"]))
    observed = []
    for row in rows:
        key = row["type"], row["x"], row["y"]
        (identity,) = births[key]
        require(identity[0] == row[column], "Rank differs from startup identity")
        observed.append(identity)
    require(len(set(observed)) == len(rows), "Duplicate startup identity")
    return observed


def control(args):
    path, replay_sha, rows = args
    game, tracker = members(path, replay_sha, 98348)
    observed = startup(tracker, rows, "target_index")
    shift = command_checks(protocol96477.decode_replay_game_events(game), tracker, rows, observed, 22)
    return (
        dict(
            replay_sha256=replay_sha,
            common_births=len(observed),
            observed_recycles=sorted({r for _, r in observed}),
            **shift
        ),
        observed,
    )


def lifetime_ends(tracker, source_ids):
    by_index = {i: r for i, r in source_ids}
    anchor_set = set(source_ids)
    ends = {}
    for event in tracker:
        loop = event["_gameloop"]
        kind = event["_event"].rsplit(".", 1)[-1]
        if kind not in TRANSITIONS:
            continue
        idx, recycle = event["m_unitTagIndex"], event["m_unitTagRecycle"]
        if idx not in by_index:
            continue
        key = idx, by_index[idx]
        if loop == 0 and kind == "SUnitBornEvent" and (idx, recycle) == key:
            continue
        if (idx, recycle) in anchor_set or kind in {
            "SUnitBornEvent",
            "SUnitInitEvent",
            "SUnitRevivedEvent",
        }:
            ends.setdefault(key, loop)
    return ends


def eligible(identity, loop, ranks, ends):
    return identity in ranks and 0 < loop < ends.get(identity, float("inf"))


def project(game, tracker, rows, target_ids):
    events = list(decode_events(game, protocol41810, "game"))
    source_ids = startup(tracker, rows, "source_index")
    source_shift = command_checks(events, tracker, rows, source_ids, 18)
    require(source_shift["compatible_shifts"] == [18], "Ambiguous original command target shift")
    mapping = dict(zip(source_ids, zip(rows, target_ids)))
    inverse = dict(zip(target_ids, source_ids))
    require(len(mapping) == len(inverse) == len(rows), "Non-bijective anchor subset")
    ends = lifetime_ends(tracker, source_ids)
    scoped, excluded, table = [], Counter(), Counter()
    total = 0
    identities = set()
    for ordinal, event in enumerate(events):
        target = field(event)
        if target is None:
            continue
        total += 1
        old_tag = target["m_tag"]
        source_key = components(old_tag, 18)
        if source_key not in mapping:
            excluded["outside_common_startup_identity"] += 1
            continue
        loop = event["_gameloop"]
        if not eligible(source_key, loop, mapping, ends):
            excluded["outside_initial_source_lifetime_or_boundary"] += 1
            continue
        row, dest_key = mapping[source_key]
        point = target["m_snapshotPoint"]
        require(
            (point["x"], point["y"]) == (row["x"] * 4096, row["y"] * 4096),
            "Projected source identity has different snapshot X/Y",
        )
        projected_tag = pack(*dest_key, 22)
        require(projected_tag not in (0, 0xFFFFFFFF), "Sentinel in projected tag")
        target["m_tag"] = projected_tag
        kind = event["_event"].rsplit(".", 1)[-1]
        table[row["type"], kind] += 1
        identities.add(source_key)
        scoped.append(
            dict(
                ordinal=ordinal,
                loop=loop,
                event=kind,
                unit_type=row["type"],
                source_index=source_key[0],
                target_index=dest_key[0],
                source_tag=old_tag,
                projected_tag=projected_tag,
            )
        )
    require(len(scoped) + excluded.total() == total, "Command target partition")
    projected_raw = encode_events(events, protocol41810, "game")
    check = list(decode_events(projected_raw, protocol41810, "game"))
    for row in scoped:
        target = field(check[row["ordinal"]])
        require(target is not None and target["m_tag"] == row["projected_tag"], "Projected ordinal")
        original_key = inverse[components(target["m_tag"], 22)]
        target["m_tag"] = pack(*original_key, 18)
        require(target["m_tag"] == row["source_tag"], "Source inverse tag")
    recovered = encode_events(check, protocol41810, "game")
    require(recovered == game, "Original game member was not fully recovered")
    changed_rank = [r for r in scoped if r["source_index"] != r["target_index"]]
    tested_initial_ends = [key for key in identities if key in ends]
    require(
        all(not eligible(key, ends[key], mapping, ends) for key in tested_initial_ends),
        "Lifetime boundary",
    )
    wrong_recycle = [(i, r + 1) for i, r in identities]
    require(all(not eligible(key, 1, mapping, ends) for key in wrong_recycle), "Wrong recycle")
    wrong_same_rank = sum(
        pack(r["source_index"], components(r["source_tag"], 18)[1], 22) != r["projected_tag"]
        for r in scoped
    )
    require(wrong_same_rank == len(changed_rank), "Same-rank negative")
    report = dict(
        source_replay_sha256=SOURCE,
        source_game_bytes=len(game),
        source_game_sha256=sha256(game).hexdigest(),
        command_targets=total,
        qualifying_fields=len(scoped),
        distinct_qualifying_anchors=len(identities),
        changed_rank_fields=len(changed_rank),
        same_rank_fields=len(scoped) - len(changed_rank),
        changed_packed_tag_fields=sum(r["source_tag"] != r["projected_tag"] for r in scoped),
        source_shift_evidence=source_shift,
        excluded=dict(excluded),
        exact_source_snapshot_xy_multiplication=4096,
        matched_source_snapshot_xy=len(scoped),
        by_event=dict(sorted(Counter(r["event"] for r in scoped).items())),
        by_type_and_event=[dict(unit_type=t, event=k, count=v) for (t, k), v in sorted(table.items())],
        negative_controls=dict(
            retaining_source_rank_wrong_fields=wrong_same_rank,
            rejected_wrong_recycles=len(wrong_recycle),
            rejected_source_end_boundary_identities=len(tested_initial_ends),
        ),
        projected_in_memory_41810_game_sha256=sha256(projected_raw).hexdigest(),
        inverse_game_byte_equal=True,
    )
    return scoped, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "anchors", "roster", "control-root", "output-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    rows = json.loads(pinned(args.anchors, ANCHORS))
    require(
        len({(r["type"], r["x"], r["y"]) for r in rows}) == len(rows)
        and all(type(r["x"]) is type(r["y"]) is int for r in rows),
        "unique integer anchors",
    )
    refs = json.loads(pinned(args.roster, ROSTER))["references"]
    require(len({r["replay_sha256"] for r in refs}) == len(refs) == 12, "control roster")
    tasks = [(args.control_root / r["replay_file"], r["replay_sha256"], rows) for r in refs]
    with ProcessPoolExecutor(max_workers=3) as pool:
        result = list(pool.map(control, tasks))
    controls, id_lists = zip(*result)
    require(
        all(ids == id_lists[0] for ids in id_lists), "Target controls disagree on initial identities"
    )
    compatible = set.intersection(*(set(c["compatible_shifts"]) for c in controls))
    require(compatible == {22}, "Ambiguous target shift")
    game, tracker = members(args.source, SOURCE, 41810)
    scoped, report = project(game, tracker, rows, id_lists[0])
    report.update(
        anchor_table_sha256=ANCHORS,
        control_manifest_sha256=ROSTER,
        total_common_anchors=len(rows),
        target_shift_across_controls=sorted(compatible),
        controls=controls,
        scope="Zero-based game event ordinals. Projected fields are initial stock-layout target tags only. "
        "Current command-time lifetime, snapshot fields, playback and simulation are unverified.",
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, value in [("command-ordinals.json", scoped), ("projection.json", report)]:
        path = args.output_dir / name
        encoded = (json.dumps(value, indent=2) + "\n").encode("utf-8")
        if path.exists():
            require(
                path.read_bytes() in (encoded, encoded.replace(b"\n", b"\r\n")),
                "Existing output differs",
            )
        else:
            with path.open("xb") as output:
                output.write(encoded)
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "command_targets",
                    "qualifying_fields",
                    "changed_rank_fields",
                    "same_rank_fields",
                    "distinct_qualifying_anchors",
                    "excluded",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
