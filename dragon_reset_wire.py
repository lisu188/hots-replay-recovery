"""Write shrine resets and opening flag transfers using map-derived tags and activation clocks."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from camp_owner_wire import FIELDS, OWNER, STOCK, encode_sparse, frame_bytes, read_tracker, target_protocol
from dragon_startup_births import predict
from first_camp_event_order import layout
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from predict_camp_captures import SOURCE

DERIVATIVE = "4fc0c3bf21a2b96eda9d8d03f3a309256bf6aacf4715c1a1fc71700ae8edb2c8"
SHARED = "2d5cba9c5fd8276ae62468533fae558222730d55b146d41b7ebb7d30532e70b7"
HISTORICAL_MAPS = {DERIVATIVE, SHARED,
                   '786f04a19c4222d5e81faefd7363c5422c16b49216732c28a773c74d853e10a9',
                   '150bdcea5435021263c84648d892c2c3dcc26bff8c72d1be5198c31a4bb09791'}
COHORT = "1b571c891d5b5646c21d39e6552af48b1b98926d4b0b948c556ae19408600a94"
SHRINES = (b"DragonShireShrineSun", b"DragonShireShrineMoon")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unit_tag(row):
    return row["m_unitTagIndex"], row["m_unitTagRecycle"]


def position(row):
    return row["m_x"], row["m_y"]


def actors(package, mechanics, digest):
    require(sha256(package.read_bytes()).hexdigest() == digest and digest in HISTORICAL_MAPS | {STOCK},
            "Unexpected map for this timeline")
    with closing(MPQArchive(package)) as archive:
        inputs = [read_member(archive, key) for key in ("Objects", "Regions", "MapScript.galaxy")]
    births, _ = predict(*inputs, mechanics.read_bytes())
    shrine_rows = [next(row for row in births if row["m_unitTypeName"] == kind) for kind in SHRINES]
    shrine_tags = [unit_tag(row) for row in shrine_rows]
    beacons = [row for row in births if row["m_unitTypeName"] == b"DragonballCaptureBeacon"]
    require(len(beacons)==2 and len({position(row) for row in beacons})==2, "Expected two unique beacons")
    beacon_by_position = {position(row):unit_tag(row) for row in beacons}
    beacon_tags = [beacon_by_position[position(row)] for row in shrine_rows]
    flags = []
    if digest in HISTORICAL_MAPS:
        available = {position(row):unit_tag(row) for row in births if row["m_unitTypeName"] == b"CampOwnershipFlag"}
        flags = [available[flag[1]] for _, flag, _ in layout(package)]
        require(len(set(flags)) == len(available) == 5, "Expected five distinct authored flags")
    return shrine_tags, beacon_tags, flags


def owner(tick, tag, who):
    return dict(_event=OWNER, _eventid=3, _gameloop=tick, m_unitTagIndex=tag[0],
                m_unitTagRecycle=tag[1], m_controlPlayerId=who, m_upkeepPlayerId=who)


def project(gate, activations, tags, delay, digest):
    shrines, beacons, flags = tags
    require(activations == sorted(set(activations)) and all(t > gate for t in activations),
            "Invalid activation clocks")
    require(all(b-a>delay for a,b in zip(activations, activations[1:])), "Overlapping reset windows")
    clocks = defaultdict(list)
    for tick in activations:
        clocks[tick].extend(owner(tick, tag, 0) for tag in shrines)
        clocks[tick+delay].extend(owner(tick+delay, tag, 0) for tag in reversed(beacons))
    opening = gate+120*16
    collision = bool(flags and opening in clocks)
    if collision:
        # A single cross-callback tie in this cohort is bound to its recording.
        require(digest==SOURCE and opening==2530 and 2514 in activations and delay==16,
                "Unverified cross-callback ordering")
    if flags:
        clocks[opening].extend(owner(opening, tag, 15) for tag in flags)
    return [row for tick in sorted(clocks) for row in clocks[tick]], collision


def verify_case(path, digest, build, tags):
    require(sha256(path.read_bytes()).hexdigest()==digest, "Unexpected recording")
    p, wire, _ = read_tracker(path,build)
    events=list(p.decode_replay_tracker_events(wire))
    gate, = [event["_gameloop"] for event in events if event.get("m_eventName")==b"GatesOpen"]
    activations=[event["_gameloop"] for event in events if event.get("m_eventName")==b"DragonKnightActivated"]
    delay=16 if build==41810 else 48
    predictions,collision=project(gate,activations,tags,delay,digest)
    sparse,_=encode_sparse(predictions)
    lookup={(row["_gameloop"],unit_tag(row)):row for row in predictions}
    require(len(lookup)==len(predictions), "Unresolved tracker tie")
    permanent=set(tags[0]+tags[1])
    protected_tags=permanent|set(tags[2])
    permanent_slots={tag[0] for tag in permanent}
    protected={tag[0] for tag in protected_tags}
    last_owner={}
    actual=[]
    offset=prev=0
    for row in events:
        tick=row["_gameloop"]
        event_id=row["_eventid"]
        require(row["_bits"]%8==0, "Tracker frame alignment")
        size=row["_bits"]//8
        tag=(row.get("m_unitTagIndex"),row.get("m_unitTagRecycle"))
        if tag[0] in protected and event_id in (1,2,4) and tick and (
                tag[0] in permanent_slots or tick<=gate+1920):
            raise ValueError("Unexpected generation change before the projected transfer")
        if tag in protected_tags and event_id in (1,3):
            state=(row["m_controlPlayerId"],row["m_upkeepPlayerId"])
            if (tick,tag) in lookup and event_id==3:
                expected=lookup[tick,tag]
                require(all(expected[k]==row[k] for k in FIELDS), "Owner transition differs")
                if tag in permanent:
                    require(last_owner[tag] in ((11,11),(12,12)), "Expected prior team ownership")
                require(frame_bytes(expected, prev, target_protocol())==wire[offset:offset+size],
                        "Predicted frame differs from physical tracker")
                actual.append((tick,tag))
            last_owner[tag]=state
        offset+=size
        prev=tick
    require(actual==list(lookup) and offset==len(wire), "Projected physical ordering differs")
    return sparse,dict(build=build,replay_sha256=digest,activations=len(activations),
                       verified_frames=len(actual),checked_cross_callback_tie=collision)


def run(legacy, target, derivative, stock, library, evidence, write_to=None):
    report=json.loads(evidence.read_bytes())
    canonical=json.dumps(report,sort_keys=True,separators=(",",":")).encode()
    require(sha256(canonical).hexdigest()==COHORT, "Unexpected independent timing cohort")
    src=json.loads(legacy.read_bytes())
    dst=json.loads(target.read_bytes())
    cases=[]
    ten=None
    derivative_sha=sha256(derivative.read_bytes()).hexdigest()
    require(derivative_sha in HISTORICAL_MAPS, 'Unrecognized historical map derivative')
    for build, field, paths, package, key in (
        (41810,"old_replays",src,derivative,derivative_sha),(98348,"target_controls",dst,stock,STOCK)
    ):
        tags=actors(package,library,key)
        for row in report[field]:
            digest=row["sha256"]
            sparse, case=verify_case(Path(paths[digest]),digest,build,tags)
            cases.append(case)
            if digest==SOURCE:
                ten=sparse
    require(ten is not None and Counter(c["build"] for c in cases)=={41810:5,98348:15}, "Incomplete cohort")
    require(sum(c['activations'] for c in cases)==67 and sum(c['verified_frames'] for c in cases)==293,
            'Incomplete physical comparison')
    if write_to:
        with write_to.open("xb") as output:
            output.write(ten)
    return dict(target_map_sha256=derivative_sha,ten_sparse_bytes=len(ten),ten_sparse_sha256=sha256(ten).hexdigest(),
                ten_records=next(c["verified_frames"] for c in cases if c["replay_sha256"]==SOURCE),
                checked_frames=sum(c["verified_frames"] for c in cases),cases=cases,
                uses_recorded_activation_loops=True,derivative_dispatch_order_verified_natively=False)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("legacy","target","derivative","stock","library","evidence"):
        parser.add_argument(name,type=Path)
    parser.add_argument("--write-to",type=Path)
    print(json.dumps(run(**vars(parser.parse_args())),indent=2))
