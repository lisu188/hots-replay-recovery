"""Test a tracker-order-independent historical gate projection against held-out recordings."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path

from blocker_death_wire import BLOCKERS, DIED, MAP, STOCK, STOCK_PACKAGE, verify_trigger
from camp_owner_wire import read_tracker
from convert_historical_pings import placements
from dragonshire_packages import HISTORICAL_PACKAGES
from encoders import encode_tracker_events
from protocol_loader import load_protocol


def predict(layout, tick):
    """Derive tag, within-type position in the sequence and coordinates from authored placement."""
    blockers = [(BLOCKERS.index(row.unit_type), row.y, row.x, i) for i, row in enumerate(layout)
                if row.unit_type in BLOCKERS]
    if Counter(k for k,_,_,_ in blockers) != {0: 30, 1: 24}:
        raise ValueError("Unexpected gate layout")
    if len({(k,y,x) for k,y,x,_ in blockers}) != len(blockers):
        raise ValueError("Ambiguous authored coordinates in one group")
    return [dict(_eventid=2, _event=DIED, _gameloop=tick, m_unitTagIndex=i, m_unitTagRecycle=1,
                 m_killerPlayerId=0, m_x=int(x), m_y=int(y), m_killerUnitTagIndex=None, m_killerUnitTagRecycle=None)
            for _,y,x,i in sorted(blockers)]


def check(path, digest, build, package, library):
    verify_trigger(library)
    if sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("Wrong replay")
    map_sha = sha256(package.read_bytes()).hexdigest()
    if map_sha not in ({MAP, *HISTORICAL_PACKAGES} if build == 41810 else {STOCK, STOCK_PACKAGE}):
        raise ValueError("Wrong map")
    layout = placements(package, map_sha)
    protocol, wire, _ = read_tracker(path, build)
    tr = list(protocol.decode_replay_tracker_events(wire))
    if sum(e["_bits"] for e in tr) != 8 * len(wire):
        raise ValueError("Incomplete tracker")
    tick, = [e["_gameloop"] for e in tr if e.get("m_eventName") == b"GatesOpen"]
    projected = predict(layout, tick)
    by_idx = {e["m_unitTagIndex"]:e for e in projected}
    groups = defaultdict(list)
    hits = 0
    for e in tr:
        i = e.get("m_unitTagIndex")
        if e["_eventid"] != 2 or i not in by_idx or e["m_unitTagRecycle"] != 1:
            continue
        expected = by_idx[i]
        for k,v in expected.items():
            if e[k] != (None if build == 41810 and k=="m_killerPlayerId" else v):
                raise ValueError("Gate removal payload mismatch")
        hits += i == projected[sum(map(len,groups.values()))]["m_unitTagIndex"]
        groups[layout[i].unit_type].append(i)
    if len(set(groups[BLOCKERS[0]])) != 30 or len(set(groups[BLOCKERS[1]])) != 24:
        raise ValueError("Incomplete removal set")
    return (dict(build=build, sha256=digest, package_sha256=map_sha, tick=tick,
                 exact_order_positions=hits),groups,encode_tracker_events(projected,load_protocol(96477)))


def summarize(results):
    summary={"cases": sorted((r for r,_,_ in results),key=lambda r:r["sha256"]), "profiles":{}}
    if len({r["sha256"] for r,_,_ in results}) != len(results):
        raise ValueError("Duplicate replay")
    for b in sorted({r["build"] for r,_,_ in results}):
        cohort=[(r,g) for r,g,_ in results if r["build"]==b]
        pair_counts={}
        for t in BLOCKERS:
            preceding = [set(combinations(g[t],2)) for _,g in cohort]
            if any({i for pair in s for i in pair} != set(cohort[0][1][t]) for s in preceding):
                raise ValueError("Mixed geometries")
            pair_counts[t]=dict(comparable_pairs=len(preceding[0]),same_precedence_all_cases=len(set.intersection(*preceding)))
        summary["profiles"][str(b)]=dict(replays=len(cohort),exact_position_matches=sum(r["exact_order_positions"] for r,g in cohort),
                                         complete_order_matches=sum(r["exact_order_positions"]==54 for r,g in cohort),
                                         within_group_precedence=pair_counts)
    return summary


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--case",nargs=4,action="append",required=True,metavar=("REPLAY","SHA256","BUILD","MAP"))
    cli.add_argument("--library",type=Path,required=True)
    cli.add_argument("--historical-output",type=Path)
    a=cli.parse_args()
    results=[check(Path(p),h,int(b),Path(m),a.library) for p,h,b,m in a.case]
    if a.historical_output:
        if len(results)!=1 or results[0][0]["build"]!=41810 or results[0][0]["exact_order_positions"]!=54:
            raise ValueError("One fully matched historical layout required for emission")
        with a.historical_output.open("xb") as out:
            out.write(results[0][2])
    print(json.dumps(summarize(results),indent=2))
