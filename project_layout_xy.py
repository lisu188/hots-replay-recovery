"""Project eligible TEN_GREYMANE command X/Y onto the stock 98348 Dragon Shire layout."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from command_authored_xy import analyze, get_target
from migrate_replay import decode_events, encode_events
from mpq_reader import MPQArchive
from protocol_loader import load_protocol

SOURCE = "e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824"
MAPS = {
    41810: "e0a58745837b3b5351015c933560dbffb178d747009d2d57b4153ef425cf7250",
    98348: "f557190f8aaab160789272ce086b8b69d6a8037b152de150332603dae3dc098f",
}


def checked(report, build):
    if (
        report["build"] != build
        or report["map_sha256"] != MAPS[build]
        or not report["full_game_byte_equal"]
        or report["counts"].get("mismatches", 0)
    ):
        raise ValueError("Unverified layout, coordinate, or game member")


def structure_signature(record):
    return (
        record["type"],
        tuple(record["startup_owners"]),
        record["index"],
        record["recycle"],
        tuple(record["xy"]),
    )


def correspondence(source, controls):
    """Compare independently identified editor placements and target command-position witnesses."""
    checked(source, 41810)
    if source["replay_sha256"] != SOURCE:
        raise ValueError("Expected TEN_GREYMANE source")
    if not controls or len({c["replay_sha256"] for c in controls}) != len(controls):
        raise ValueError("Expected distinct target replay controls")
    for c in controls:
        checked(c, 98348)
    old = {p["object_id"]: p for p in source["structure_positions"]}
    current = {p["object_id"]: p for p in controls[0]["structure_positions"]}
    reference = {k: structure_signature(p) for k, p in current.items()}
    witnesses = Counter()
    for c in controls:
        values = {p["object_id"]: structure_signature(p) for p in c["structure_positions"]}
        if values != reference:
            raise ValueError("Independent controls disagree on target map startup identities")
        witnesses.update(p["object_id"] for p in c["structure_positions"] if p["matching_commands"] > 0)
    counts = Counter()
    candidates = []
    for event in source["projected_rows"]:
        ident = event["object_id"]
        src = old[ident]
        if list(event["xy"]) != list(src["xy"]) or event["type"] != src["type"]:
            raise ValueError("Source command and declared placement differ")
        target = current.get(ident)
        if target is None:
            counts["no_same_id_target_structure"] += 1
            continue
        if src["type"] != target["type"] or src["startup_owners"] != target["startup_owners"]:
            counts["same_id_but_type_or_team_differs"] += 1
            continue
        if not witnesses[ident]:
            counts["same_id_type_team_without_target_command_witness"] += 1
            continue
        changed = list(src["xy"]) != list(target["xy"])
        counts["xy_changes" if changed else "xy_equal"] += 1
        candidates.append(
            dict(
                ordinal=event["ordinal"],
                loop=event["loop"],
                object_id=ident,
                type=src["type"],
                source_xy=src["xy"],
                target_xy=target["xy"],
                source_index=src["index"],
                target_index=target["index"],
                independent_controls_targeting_object=witnesses[ident],
            )
        )
    return counts, candidates


def project(source, controls, source_path):
    counts, rows = correspondence(source, controls)
    if sha256(source_path.read_bytes()).hexdigest() != SOURCE:
        raise ValueError("Physical source replay changed")
    with closing(MPQArchive(source_path)) as archive:
        raw = archive.read_file("replay.game.events")
    protocol = load_protocol(41810)
    events = list(decode_events(raw, protocol, "game"))
    for row in rows:
        event = events[row["ordinal"]]
        point = get_target(event)["m_snapshotPoint"]
        if event["_gameloop"] != row["loop"] or [point["x"], point["y"]] != list(row["source_xy"]):
            raise ValueError("Source evidence no longer matches recorded command")
        point["x"], point["y"] = row["target_xy"]
    intermediate = encode_events(events, protocol, "game")
    inverse = list(decode_events(intermediate, protocol, "game"))
    for row in rows:
        point = get_target(inverse[row["ordinal"]])["m_snapshotPoint"]
        if [point["x"], point["y"]] != list(row["target_xy"]):
            raise ValueError("Projected coordinates failed codec verification")
        point["x"], point["y"] = row["source_xy"]
    if encode_events(inverse, protocol, "game") != raw:
        raise ValueError("Inverting the 41810 field projection did not recover the complete source")
    changed = [r for r in rows if r["source_xy"] != r["target_xy"]]
    return dict(
        format="dragon-shire-command-xy-layout-projection-v1",
        source_sha256=SOURCE,
        source_map=MAPS[41810],
        target_map=MAPS[98348],
        control_hashes=[c["replay_sha256"] for c in controls],
        source_commands_examined=len(source["projected_rows"]),
        counts=dict(counts),
        projected_commands=len(rows),
        distinct_objects=len({r["object_id"] for r in rows}),
        distinct_moved_objects=len({r["object_id"] for r in changed}),
        inverse_source_game_byte_equal=True,
        source_game_bytes=len(raw),
        source_game_sha256=sha256(raw).hexdigest(),
        projected_game_bytes_41810=len(intermediate),
        projected_game_sha256_41810=sha256(intermediate).hexdigest(),
        converted_match_target_lifetimes_verified=False,
        xy_only=True,
        rows=rows,
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("source-map", "source-replay", "target-map"):
        cli.add_argument("--" + name, type=Path, required=True)
    cli.add_argument(
        "--target-replay",
        type=Path,
        required=True,
        action="append",
        help="Genuine replay that references the stock target map. Repeat for additional witnesses.",
    )
    cli.add_argument(
        "--rows", action="store_true", help="Include all zero-based event ordinals and projected fields."
    )
    args = cli.parse_args()
    old = analyze(args.source_map, args.source_replay, 41810, observations=True)
    controls = [analyze(args.target_map, replay, 98348) for replay in args.target_replay]
    result = project(old, controls, args.source_replay)
    if not args.rows:
        del result["rows"]
    print(json.dumps(result, indent=2))
