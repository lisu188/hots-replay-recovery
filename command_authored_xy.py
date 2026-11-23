"""Check map-authored fixed-point XY against unit-target command snapshots."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path

from map_startup_identity import SCHEMAS, inspect_replay
from migrate_replay import decode_events, encode_events
from mpq_reader import MPQArchive
from protocol_loader import load_protocol
from repair_unit_tags import components

BUILDINGS = frozenset(
    {
        "KingsCore",
        "TownMoonwellL2",
        "TownMoonwellL3",
        "TownTownHallL2",
        "TownTownHallL3",
        "TownCannonTowerL2",
        "TownCannonTowerL3",
        "TownCannonTowerL2Standalone",
        "TownCannonTowerL3Standalone",
        "TownGateL215BLUR",
        "TownGateL215BRUL",
        "TownGateL3BLURBRVisionBlocked",
        "TownGateL3BLURTLVisionBlocked",
        "TownGateL3BRULBLVisionBlocked",
        "TownGateL3BRULTRVisionBlocked",
        "TownGateL3VerticalLeftVisionBlocked",
        "TownGateL3VerticalRightVisionBlocked",
        "TownWallRadial18L2",
        "TownWallRadial19L2",
        "TownWallRadial4L2",
        "TownWallRadial5L2",
        *(f"TownWallRadial{i}L3" for i in (2, 3, 5, 6, 8, 9, 14, 15, 17, 18, 20, 21)),
    }
)
TRANSITIONS = {
    "SUnitBornEvent",
    "SUnitInitEvent",
    "SUnitTypeChangeEvent",
    "SUnitRevivedEvent",
    "SUnitDiedEvent",
}


def fixed(text):
    """Return exactly representable nonnegative positions; XML printing can lose precision."""
    value = Decimal(text)
    if not value.is_finite() or value < 0:
        return None
    numerator, denominator = value.as_integer_ratio()
    wire, remainder = divmod(numerator * 4096, denominator)
    return wire if remainder == 0 else None


def get_target(event):
    if event["_event"] == "NNet.Game.SCmdEvent":
        return event["m_data"].get("TargetUnit")
    if event["_event"] == "NNet.Game.SCmdUpdateTargetUnitEvent":
        return event["m_target"]
    return None


def lifetime_ends(tracker, anchors):
    by_index = {a.index: a for a in anchors}
    ends = {}
    for event in tracker:
        kind = event["_event"].rsplit(".", 1)[-1]
        if kind not in TRANSITIONS:
            continue
        idx = event["m_unitTagIndex"]
        anchor = by_index.get(idx)
        if anchor is None:
            continue
        loop = event["_gameloop"]
        recycle = event["m_unitTagRecycle"]
        if kind == "SUnitBornEvent" and loop == 0 and recycle == anchor.recycle:
            continue
        if recycle == anchor.recycle or kind in ("SUnitBornEvent", "SUnitInitEvent", "SUnitRevivedEvent"):
            ends.setdefault(idx, loop)
    return ends


def analyze(map_path, replay_path, build, observations=False):
    anchors, startup = inspect_replay(map_path, replay_path, build)
    protocol = load_protocol(SCHEMAS[build])
    shift = {41810: 18, 98348: 22}[build]
    with closing(MPQArchive(replay_path)) as arc:
        game = arc.read_file("replay.game.events")
        tracker = list(protocol.decode_replay_tracker_events(arc.read_file("replay.tracker.events")))
    by_key = {(a.index, a.recycle): a for a in anchors}
    ends = lifetime_ends(tracker, anchors)
    # Have a separate diagnostic for the common but incorrect generalization to mobile
    # post-start heroes. Cut off on any subsequent lifecycle change, including slot reuse.
    active = {}
    spawns = {}
    for event in tracker:
        kind = event["_event"].rsplit(".", 1)[-1]
        if kind not in TRANSITIONS:
            continue
        idx, rec = event["m_unitTagIndex"], event["m_unitTagRecycle"]
        loop = event["_gameloop"]
        old = active.pop(idx, None)
        if old is not None:
            old["end"] = loop
        if kind == "SUnitBornEvent" and loop > 0:
            name = event["m_unitTypeName"].decode()
            if name.startswith("Hero") and (idx, rec) not in spawns:
                life = dict(start=loop, end=float("inf"), birth=(event["m_x"], event["m_y"]), type=name)
                spawns[idx, rec] = active[idx] = life
    result = Counter()
    per_type = defaultdict(Counter)
    examples = []
    errors = []
    excluded_offsite = []
    mobile_sample = []
    source_rows = []
    unique = set()
    witnesses = Counter()
    event_counts = Counter()
    events = list(decode_events(game, protocol, "game"))
    for ordinal, event in enumerate(events):
        target = get_target(event)
        if target is None:
            continue
        result["target_commands"] += 1
        tag = target["m_tag"]
        key = components(tag, shift)
        loop = event["_gameloop"]
        point = target["m_snapshotPoint"]
        observed = (point["x"], point["y"])
        life = spawns.get(key)
        if tag not in (0, 0xFFFFFFFF) and life and life["start"] < loop < life["end"]:
            result["post_start_hero_spawn_snapshot_commands"] += 1
            if any(abs(v // 4096 - b) > 1 for v, b in zip(observed, life["birth"])):
                result["post_start_hero_position_over_one_cell_from_birth"] += 1
                if len(mobile_sample) < 4:
                    mobile_sample.append(
                        dict(
                            unit_type=life["type"],
                            birth=life["birth"],
                            birth_loop=life["start"],
                            command_loop=loop,
                            ordinal=ordinal,
                            observed_xy=observed,
                        )
                    )
        a = by_key.get(key)
        if not a or tag in (0, 0xFFFFFFFF):
            result["outside_verified_startup_tags"] += 1
            continue
        if not 0 < loop < ends.get(a.index, float("inf")):
            result["outside_initial_lifetime"] += 1
            continue
        predicted = fixed(a.authored_x), fixed(a.authored_y)
        if a.unit_type not in BUILDINGS or None in predicted:
            result["outside_building_or_inexact"] += 1
            if None not in predicted and observed != predicted:
                result["other_authored_type_xy_differences"] += 1
                if len(excluded_offsite) < 4:
                    excluded_offsite.append(
                        dict(
                            type=a.unit_type,
                            ordinal=ordinal,
                            loop=loop,
                            object_id=a.object_id,
                            predicted=predicted,
                            observed=observed,
                        )
                    )
            continue
        counter = per_type[a.unit_type]
        result["eligible"] += 1
        counter["eligible"] += 1
        unique.add(a.object_id)
        event_counts[event["_event"].rsplit(".", 1)[-1]] += 1
        fractional = any(v % 4096 for v in predicted)
        result["fractional"] += fractional
        counter["fractional"] += fractional
        if predicted != observed:
            result["mismatches"] += 1
            counter["mismatches"] += 1
            if len(errors) < 8:
                errors.append(
                    dict(
                        ordinal=ordinal,
                        loop=loop,
                        object_id=a.object_id,
                        type=a.unit_type,
                        xy_authored=[a.authored_x, a.authored_y],
                        predicted=predicted,
                        observed=observed,
                    )
                )
        else:
            witnesses[a.object_id] += 1
        if fractional and len(examples) < 3:
            examples.append(
                dict(
                    ordinal=ordinal,
                    loop=loop,
                    type=a.unit_type,
                    object_id=a.object_id,
                    xy_authored=[a.authored_x, a.authored_y],
                    predicted=predicted,
                    observed=observed,
                )
            )
        point["x"], point["y"] = predicted
        if observations:
            source_rows.append(
                dict(ordinal=ordinal, loop=loop, object_id=a.object_id, type=a.unit_type, xy=predicted)
            )
    reconstructed = encode_events(events, protocol, "game")
    report = dict(
        build=build,
        replay_sha256=startup["replay_sha256"],
        map_sha256=startup["map_sha256"],
        objects_sha256=startup["objects_sha256"],
        startup=startup["verified"],
        counts=dict(result),
        distinct_targeted_structures=len(unique),
        by_event=dict(event_counts),
        by_type=dict(per_type),
        fractional_examples=examples,
        disagreements=errors,
        other_authored_disagreements=excluded_offsite,
        mobile_spawn_counterexamples=mobile_sample,
        full_input_game_bytes=len(game),
        input_game_sha256=sha256(game).hexdigest(),
        reconstructed_game_sha256=sha256(reconstructed).hexdigest(),
        full_game_byte_equal=game == reconstructed,
        structure_positions=[
            dict(
                object_id=a.object_id,
                type=a.unit_type,
                index=a.index,
                recycle=a.recycle,
                xy=[fixed(a.authored_x), fixed(a.authored_y)],
                startup_owners=[
                    tracker[a.event_offset]["m_controlPlayerId"],
                    tracker[a.event_offset]["m_upkeepPlayerId"],
                ],
                matching_commands=witnesses[a.object_id],
            )
            for a in anchors
            if a.unit_type in BUILDINGS and None not in (fixed(a.authored_x), fixed(a.authored_y))
        ],
    )
    if observations:
        report["projected_rows"] = source_rows
    return report


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("map", type=Path)
    cli.add_argument("replay", type=Path)
    cli.add_argument("--build", choices=SCHEMAS, type=int, required=True)
    cli.add_argument("--observations", action="store_true")
    a = cli.parse_args()
    report = analyze(a.map, a.replay, a.build, a.observations)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["full_game_byte_equal"] and not report["counts"].get("mismatches") else 1)
