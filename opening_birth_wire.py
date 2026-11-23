"""Emit Dragon Shire opening birth frames from map placements, lobby roles and the 98348 slot pool."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from camp_owner_wire import read_tracker, TARGET_SCHEMA_SHA
from dragon_startup_births import BIRTH, predict
from encoders import encode_tracker_events
from hero_camera_lifetimes import lobby_predictions
from hero_revive_wire import starts, team_slots
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from predict_camp_captures import SOURCE
from protocol_loader import load_protocol
from unit_slot_pool import UnitSlotPool


FIELDS = ("m_unitTagIndex", "m_unitTagRecycle", "m_unitTypeName", "m_controlPlayerId",
          "m_upkeepPlayerId", "m_x", "m_y")
END_LOOP = 82


def target_protocol():
    target = load_protocol(96477)
    tid, kind = target.tracker_event_types[1]
    if (kind != BIRTH or target.recovery_schema_sha256 != TARGET_SCHEMA_SHA or
            tuple(f[0] for f in target.typeinfos[tid][1][0]) != FIELDS):
        raise ValueError("Unexpected target birth schema")
    return target


def model(replay, build, source_protocol, map_file, mechanics):
    """No tracker data enters the model. Both tag fields come only from allocate()."""
    points, map_sha = starts(map_file, build)
    with closing(MPQArchive(map_file)) as archive:
        parts = [read_member(archive, k) for k in ("Objects", "Regions", "MapScript.galaxy")]
    map_units, _ = predict(*parts, mechanics.read_bytes())
    slots = team_slots(replay, source_protocol)
    pool = UnitSlotPool()

    def birth(loop, unit, controller, upkeep, x, y):
        tag = pool.allocate()
        if tag is None:
            raise ValueError("Opening exceeds unit-pool capacity")
        return dict(_eventid=1, _event=BIRTH, _gameloop=loop,
                    **dict(zip(FIELDS, (*tag, unit, controller, upkeep, x, y))))

    placed = [birth(0, *(u[k] for k in FIELDS[2:])) for u in map_units]
    heroes = [birth(tick, unit, owner, upkeep, *points[slots[owner]])
              for tick, _, _, owner, upkeep, unit in lobby_predictions(replay, build)] if slots else []
    return placed, heroes, map_sha


def opening_observations(raw, protocol):
    """Keep physical frame bounds and the preceding event's tick, including non-births."""
    startup, heroes, retirements = [], [], []
    offset, prior = 0, 0
    for event in protocol.decode_replay_tracker_events(raw):
        tick = event["_gameloop"]
        if tick > END_LOOP:
            return startup, heroes, retirements
        length, partial = divmod(event["_bits"], 8)
        if partial or not length or offset + length > len(raw) or tick < prior:
            raise ValueError("Invalid opening frame extent")
        kind = event["_eventid"]
        if kind in (1, 6):
            dest = startup if tick == 0 else heroes
            dest.append((event, prior, offset, length))
        if kind == 2:
            retirements.append(tick)
        prior, offset = tick, offset + length
    raise ValueError("Tracker exhausted before the opening boundary")


def compare(predicted, observed, raw, target):
    """Return all-or-nothing group admission and private per-frame witnesses."""
    mismatches = Counter()
    if len(observed) != len(predicted):
        mismatches["count"] += 1
    evidence = []
    for row, (native, prior, offset, size) in zip(predicted, observed):
        different = [k for k in ("_eventid", "_gameloop", *FIELDS) if row[k] != native.get(k)]
        if different:
            mismatches.update(different)
            continue
        frame = encode_tracker_events([{**row, "_gameloop": row["_gameloop"] - prior}], target)
        if frame != raw[offset:offset + size]:
            mismatches["physical_bytes"] += 1
            continue
        evidence.append(dict(loop=row["_gameloop"], slot=row["m_unitTagIndex"],
                             unit=row["m_unitTypeName"].decode("ascii"),
                             previous_physical_loop=prior, physical_offset=offset, bytes=size,
                             physical_sha256=sha256(frame).hexdigest()))
    return dict(predicted=len(predicted), observed=len(observed), ordered_exact_frames=len(evidence),
                physical_exact_bytes=sum(e["bytes"] for e in evidence),
                mismatch_counts=dict(mismatches)), evidence


def sparse_stream(rows, evidence, target):
    sparse = encode_tracker_events(rows, target)
    decoded = list(target.decode_replay_tracker_events(sparse))
    if len(rows) != len(decoded) or len(rows) != len(evidence):
        raise ValueError("Sparse count mismatch")
    offset = 0
    for row, wire_row, witness in zip(rows, decoded, evidence):
        n, rem = divmod(wire_row["_bits"], 8)
        if rem or {k: v for k, v in wire_row.items() if k != "_bits"} != row:
            raise ValueError("Sparse target frame mismatch")
        witness.update(sparse_offset=offset, sparse_bytes=n,
                       sparse_sha256=sha256(sparse[offset:offset+n]).hexdigest())
        offset += n
    if offset != len(sparse):
        raise ValueError("Sparse stream has trailing bytes")
    return sparse


def analyze(replay, digest, build, map_file, mechanics):
    if sha256(replay.read_bytes()).hexdigest() != digest:
        raise ValueError("Replay digest mismatch")
    source_protocol, raw, horizon = read_tracker(replay, build)
    if horizon <= END_LOOP:
        raise ValueError("Incomplete opening")
    placed, heroes, map_sha = model(replay, build, source_protocol, map_file, mechanics)
    native_map, native_heroes, deaths = opening_observations(raw, source_protocol)
    target = target_protocol()
    startup, start_witness = compare(placed, native_map, raw, target)
    hero, hero_witness = compare(heroes, native_heroes, raw, target)
    startup["admitted"] = bool(placed) and not startup["mismatch_counts"] and 0 not in deaths
    hero["admitted"] = startup["admitted"] and len(heroes) == 10 and not deaths and not hero["mismatch_counts"]
    rows, witness = [], []
    if startup["admitted"]:
        rows.extend(placed)
        witness.extend(start_witness)
    if hero["admitted"]:
        rows.extend(heroes)
        witness.extend(hero_witness)
    sparse = sparse_stream(rows, witness, target)
    data = dict(build=build, replay_sha256=digest, map_sha256=map_sha, map_births=startup,
                hero_births=hero, observed_early_unit_deaths=len(deaths),
                admitted_hero_types=sorted({r["m_unitTypeName"].decode("ascii") for r in heroes}
                                           if hero["admitted"] else []),
                observed_hero_epoch_units=sorted({e["m_unitTypeName"].decode("ascii")
                                                  for e, *_ in native_heroes}),
                private_stream_frames=len(rows), sparse_bytes=len(sparse),
                sparse_sha256=sha256(sparse).hexdigest())
    return data, sparse, witness


def crossmap_hero_roles(replay, digest):
    """Cross-map witnesses for lobby type, owners, loop and birth order only."""
    if sha256(replay.read_bytes()).hexdigest() != digest:
        raise ValueError("Unexpected cross-map replay")
    protocol = target_protocol()
    with closing(MPQArchive(replay)) as archive:
        header = protocol.decode_replay_header(archive.header["user_data_header"]["content"])
        v = header["m_version"]
        if (v["m_build"], v["m_baseBuild"], header["m_dataBuildNum"]) != (98348,) * 3:
            raise ValueError("Unexpected cross-map build")
        raw = archive.read_file("replay.tracker.events")
    roster = lobby_predictions(replay, 98348)
    _, physical, deaths = opening_observations(raw, protocol)
    # Other maps can create neutral beacons and remove setup units before heroes.
    # No cross-map allocation or coordinates are being inferred from this window.
    physical = [row for row in physical if row[0]["_gameloop"] >= 50
                or row[0]["m_controlPlayerId"] in range(1, 11)]
    if not roster or len(roster) != len(physical) or any(t >= 50 for t in deaths):
        return []
    roles = []
    for (tick, _, _, owner, upkeep, unit), (e, prior, offset, size) in zip(roster, physical):
        if (e["_eventid"], e["_gameloop"], e["m_unitTypeName"], e["m_controlPlayerId"],
                e["m_upkeepPlayerId"]) != (1, tick, unit, owner, upkeep):
            return []
        # Coordinates and tag are observed on this other map, not independently scored.
        frame = encode_tracker_events([{**e, "_gameloop": tick-prior}], protocol)
        if frame != raw[offset:offset+size]:
            raise ValueError("Cross-map native frame mismatch")
        roles.append(unit.decode("ascii"))
    return roles


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("replay", type=Path)
    parser.add_argument("map", type=Path)
    parser.add_argument("mechanics", type=Path)
    parser.add_argument("--build", type=int, choices=(41810, 98348), required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--out", type=Path, help="Write the qualified private TEN sparse stream")
    args = parser.parse_args()
    report, sparse, _ = analyze(args.replay, args.sha256, args.build, args.map, args.mechanics)
    if args.out:
        if args.build != 41810 or args.sha256 != SOURCE or not report["hero_births"]["admitted"]:
            raise ValueError("Output requires complete TEN opening")
        with args.out.open("xb") as output:
            output.write(sparse)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
