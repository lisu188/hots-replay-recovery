"""Rebuild Dragon Shire's opening gate-removal records from the layout and GatesOpen."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
import math
from pathlib import Path

from camp_owner_wire import read_tracker, STOCK, STOCK_PACKAGE
from convert_historical_pings import placements
from dragonshire_packages import HISTORICAL_PACKAGES
from encoders import encode_tracker_events
from predict_camp_captures import MAP
from protocol_loader import load_protocol
from smartcam_tags import DST_SCHEMA

BLOCKERS = ("StormGameStartPathingBlocker", "StormGameStartPathingBlockerDiagonal")
DIED = "NNet.Replay.Tracker.SUnitDiedEvent"
FIELDS = ("m_unitTagIndex", "m_unitTagRecycle", "m_killerPlayerId", "m_x", "m_y",
          "m_killerUnitTagIndex", "m_killerUnitTagRecycle")
GAME = "a6384749fbe8f676cbd6ccb9ec1aeac004815d37a8e1c2f8f9f8f176b2bfca09"


def verify_trigger(path):
    raw = path.read_bytes()
    if len(raw) != 1179642 or sha256(raw).hexdigest() != GAME:
        raise ValueError("Unexpected GameLib")
    text = raw.decode("utf-8-sig")
    begin = text.index('auto157DB87C_g = UnitGroup("' + BLOCKERS[0] + '"')
    end = text.index("if ((libCore_gv_sYSDataMining", begin)
    segment = text[begin:end]
    cursor = 0
    for unit, var in zip(BLOCKERS, ("auto157DB87C", "auto4CAD3EA8")):
        for marker in (f'{var}_g = UnitGroup("{unit}",', f"UnitGroupCount({var}_g,",
                       f"UnitGroupUnitFromEnd({var}_g,", "UnitRemove(lv_itBlocker);"):
            cursor = segment.index(marker, cursor) + len(marker)


def audit(replay, digest, build, package, library):
    if sha256(replay.read_bytes()).hexdigest() != digest:
        raise ValueError("Unexpected replay")
    verify_trigger(library)
    map_sha = sha256(package.read_bytes()).hexdigest()
    if map_sha not in ({MAP, *HISTORICAL_PACKAGES} if build == 41810 else {STOCK, STOCK_PACKAGE}):
        raise ValueError("Unexpected map")
    layout = placements(package, map_sha)
    objects = {i: row for i, row in enumerate(layout) if row.unit_type in BLOCKERS}
    if Counter(row.unit_type for row in objects.values()) != dict(zip(BLOCKERS, (30, 24))):
        raise ValueError("Unexpected gate geometry")
    p, stream, _ = read_tracker(replay, build)
    t = load_protocol(96477)
    tid, name = t.tracker_event_types[2]
    if t.recovery_schema_sha256 != DST_SCHEMA or name != DIED or tuple(f[0] for f in t.typeinfos[tid][1][0]) != FIELDS:
        raise ValueError("Unexpected target death graph")
    events = list(p.decode_replay_tracker_events(stream))
    tick, = [e["_gameloop"] for e in events if e.get("m_eventName") == b"GatesOpen"]
    initial = {e["m_unitTagIndex"]: e for e in events if e["_eventid"] == 1 and
               e["_gameloop"] == 0 and e["m_unitTypeName"].decode() in BLOCKERS}
    if set(initial) != set(objects):
        raise ValueError("Unexpected initial blockers")
    for i,row in objects.items():
        old = initial[i]
        if (old["m_unitTypeName"].decode(), old["m_unitTagRecycle"], old["m_x"], old["m_y"]) != (
                row.unit_type, 1, math.floor(row.x), math.floor(row.y)):
            raise ValueError("Startup slot, generation or position differs from map")
    rows = []
    physical = offset = prev = 0
    for e in events:
        size, rem = divmod(e["_bits"], 8)
        if rem: raise ValueError("Unaligned tracker event")
        i = e.get("m_unitTagIndex")
        if e["_eventid"] == 2 and i in objects and e["m_unitTagRecycle"] == 1:
            row = objects[i]
            event = dict(_eventid=2, _event=DIED, _gameloop=tick, m_unitTagIndex=i, m_unitTagRecycle=1,
                         m_killerPlayerId=0, m_x=math.floor(row.x), m_y=math.floor(row.y),
                         m_killerUnitTagIndex=None, m_killerUnitTagRecycle=None)
            expected = event if build == 98348 else {**event, "m_killerPlayerId": None}
            if any(e[k] != v for k,v in expected.items()):
                raise ValueError("Recorded removal differs from projection")
            if build == 98348:
                frame = encode_tracker_events([{**event, "_gameloop": tick - prev}], t)
                if frame != stream[offset:offset + size]:
                    raise ValueError("Native event bytes differ")
                physical += size
            rows.append(event)
        prev = e["_gameloop"]
        offset += size
    ordered = [e["m_unitTagIndex"] for e in rows]
    if offset != len(stream) or len(ordered) != len(objects) or set(ordered) != set(objects):
        raise ValueError("Incomplete blocker or tracker coverage")
    if [objects[i].unit_type for i in ordered] != [BLOCKERS[0]] * 30 + [BLOCKERS[1]] * 24:
        raise ValueError("Removal type-group order differs")
    sparse = encode_tracker_events(rows, t)
    decoded = list(t.decode_replay_tracker_events(sparse))
    decoded_rows = [{k: e[k] for k in ("_eventid", "_event", "_gameloop", *FIELDS)} for e in decoded]
    if decoded_rows != rows or sum(e["_bits"] for e in decoded) != len(sparse) * 8:
        raise ValueError("Sparse blocker stream differs")
    return sparse, dict(build=build, sha256=digest, map_sha256=map_sha, gate_loop=tick,
                        deaths=len(rows), input_killer_player=None if build==41810 else 0,
                        target_killer_player=0, complete_native_frame_bytes=physical,
                        order_sha256=sha256(bytes(ordered)).hexdigest(), sparse_bytes=len(sparse),
                        sparse_sha256=sha256(sparse).hexdigest())


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--case", required=True, nargs=3, metavar=("REPLAY","SHA256","BUILD"))
    cli.add_argument("--map", type=Path, required=True)
    cli.add_argument("--library", type=Path, required=True)
    cli.add_argument("--output", type=Path)
    args = cli.parse_args()
    p,h,b = args.case
    raw, report = audit(Path(p),h,int(b),args.map,args.library)
    if args.output:
        with args.output.open("xb") as out:
            out.write(raw)
    print(json.dumps(report,indent=2))
