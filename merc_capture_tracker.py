"""Project TEN mercenary beacon and historical-flag owner changes using the MercCapture map."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from camp_owner_wire import OWNER, capture_stats, frame_bytes, read_tracker, target_protocol
from dragon_startup_births import predict
from encoders import encode_tracker_events
from first_camp_event_order import layout
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from predict_camp_captures import SOURCE

MERC = "54e1a8fbe7e42f00b7b52cde420ed259105228fcdf165097ef52ecd0f5c4125a"


def generate(source, target_map, mechanics):
    if sha256(source.read_bytes()).hexdigest() != SOURCE or sha256(target_map.read_bytes()).hexdigest() != MERC:
        raise ValueError("Expected TEN and the actual MercCapture package")
    with closing(MPQArchive(target_map)) as archive:
        parts = [read_member(archive, name) for name in ("Objects", "Regions", "MapScript.galaxy")]
    opening, _ = predict(*parts, mechanics.read_bytes())
    tags = {}
    for camp, (captain, flag, _) in enumerate(layout(target_map), 1):
        for role, kind, point in (("beacon", b"TownMercCampCaptureBeacon", captain),
                                  ("flag", b"CampOwnershipFlag", flag[1])):
            row, = [r for r in opening if r["m_unitTypeName"] == kind and (r["m_x"], r["m_y"]) == point]
            tags[camp, role] = row["m_unitTagIndex"], row["m_unitTagRecycle"]
    if len(set(tags.values())) != 10:
        raise ValueError("Opening placements do not identify ten distinct camp units")
    protocol, raw, horizon = read_tracker(source, 41810)
    original = list(protocol.decode_replay_tracker_events(raw))
    projected = {}
    stats = list(capture_stats(original))
    if len(stats) != 13:
        raise ValueError("Unexpected TEN capture cohort")
    for loop, camp, team in stats:
        for role, when, owner in (("beacon", loop-1, 10+team), ("flag", loop, 10+team), ("beacon", loop+16, 0)):
            index, generation = tags[camp, role]
            key = (when, index, generation, owner, owner)
            if key in projected or not 0 < when <= horizon:
                raise ValueError("Duplicate or censored capture projection")
            projected[key] = (role, dict(_gameloop=when, _eventid=3, _event=OWNER, m_unitTagIndex=index,
                                         m_unitTagRecycle=generation, m_controlPlayerId=owner, m_upkeepPlayerId=owner))
    target = target_protocol()
    index_by_ordinal = {}
    observations = Counter()
    offset = previous = physical_size = 0
    for ordinal, event in enumerate(original):
        size, partial = divmod(event["_bits"], 8)
        if partial or size <= 0 or offset + size > len(raw):
            raise ValueError("Invalid original tracker frame boundaries")
        tick = event["_gameloop"]
        if event["_eventid"] == 3:
            key = (tick, event["m_unitTagIndex"], event["m_unitTagRecycle"], event["m_controlPlayerId"], event["m_upkeepPlayerId"])
            if key in projected:
                role, row = projected[key]
                observations[key] += 1
                if (row != {k:v for k,v in event.items() if k != "_bits"} or
                        frame_bytes(row, previous, target) != raw[offset:offset+size]):
                    raise ValueError("Target fields or physical frame disagree with original")
                index_by_ordinal[ordinal] = (role,row)
                physical_size += size
        offset += size
        previous = tick
    if offset != len(raw) or observations != Counter(projected.keys()):
        raise ValueError("Incomplete or ambiguous source coverage")
    rows = [item[1] for item in index_by_ordinal.values()]
    wire = encode_tracker_events(rows, target)
    replayed = list(target.decode_replay_tracker_events(wire))
    if rows != [{k:v for k,v in r.items() if k != "_bits"} for r in replayed] or sum(r["_bits"] for r in replayed) != len(wire)*8:
        raise ValueError("Sparse target readback disagrees")
    report = dict(source_sha256=SOURCE, target_map_sha256=MERC, capture_statistics=len(stats),
                  beacon_team=13, beacon_neutral=13, historical_flag_team=13, dynamic_icons=0,
                  joined_source_ordinals=len(rows), physical_source_bytes=physical_size,
                  ordinal_list_sha256=sha256(json.dumps(list(index_by_ordinal),separators=(",",":")).encode()).hexdigest(),
                  sparse_bytes=len(wire), sparse_sha256=sha256(wire).hexdigest(), native_execution_verified=False)
    return index_by_ordinal, wire, report


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "target_map", "mechanics"):
        cli.add_argument(name, type=Path)
    cli.add_argument("--private-dir", type=Path)
    a = cli.parse_args()
    items, wire, report = generate(a.source, a.target_map, a.mechanics)
    if a.private_dir:
        a.private_dir.mkdir(exist_ok=False)
        (a.private_dir/"owners.private.bin").write_bytes(wire)
        (a.private_dir/"rows.private.json").write_text(json.dumps([[n,*v] for n,v in items.items()], separators=(",",":")),encoding="utf-8")
    print(json.dumps(report, indent=2))
