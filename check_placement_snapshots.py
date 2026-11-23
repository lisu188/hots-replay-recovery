"""Compare inexact, independently identified map placements with physical command snapshots."""

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing
import json
from pathlib import Path

import first_sync_game
from command_authored_xy import get_target
from first_sync_game import game
from mpq_reader import MPQArchive
from predict_camp_captures import SOURCE
from project_rank_targets import lifetime_ends
from repair_unit_tags import components
from placement_xy import object_rows


def check_case(args):
    replay, digest, build, cache = args
    proto, raw = game(replay, digest, build)
    with closing(MPQArchive(replay)) as ar:
        handle = proto.decode_replay_details(ar.read_file("replay.details"))["m_cacheHandles"][-1][8:].hex()
        tracker = list(proto.decode_replay_tracker_events(ar.read_file("replay.tracker.events")))
    path = cache / handle[:2] / handle[2:4] / (handle + ".s2ma")
    rows = object_rows(path, handle)
    mapped = defaultdict(list)
    for r in rows.values():
        mapped[r["unit"],r["x"]//4096,r["y"]//4096].append(r)
    born = defaultdict(list)
    for e in tracker:
        if e["_eventid"] == 1 and e["_gameloop"] == 0:
            born[e["m_unitTypeName"].decode(),e["m_x"],e["m_y"]].append((e["m_unitTagIndex"],e["m_unitTagRecycle"]))
    tags = {born[k][0]:v[0] for k,v in mapped.items() if len(v)==len(born[k])==1}
    ends = lifetime_ends(tracker,tags)
    counts = Counter()
    objects = defaultdict(Counter)
    for e in proto.decode_replay_game_events(raw):
        t = get_target(e)
        if not t:
            continue
        key = components(t["m_tag"],18 if build==41810 else 22)
        r = tags.get(key)
        if r is None or not 0 < e["_gameloop"] < ends.get(key,float("inf")):
            continue
        if not (r["inexact_x"] or r["inexact_y"]):
            continue
        pt=t["m_snapshotPoint"]
        same = (pt["x"],pt["y"]) == (r["x"],r["y"])
        objects[(r["unit"],r["object_id"]) ]["match" if same else "different"] += 1
        counts["match" if same else "different"] += 1
    return dict(build=build,map=handle,counts=dict(counts),
                units=[dict(unit=k[0],id=k[1],**c) for k,c in sorted(objects.items())])


def verify(source, manifest, cache, jobs):
    pins={r["replay_sha256"] for r in json.loads((Path(first_sync_game.__file__).parent /
        "observations/first-sync-game.json").read_bytes())["references"]}
    cases=json.loads(manifest.read_bytes())
    if not pins.issubset(cases) or len(pins)!=24:
        raise ValueError("Unexpected target cohort")
    inputs = [(source,SOURCE,41810,cache)]
    for sha in sorted(pins):
        value = cases[sha]
        inputs.append((Path(value["path"] if isinstance(value,dict) else value),sha,98348,cache))
    with ProcessPoolExecutor(jobs) as pool:
        results = list(pool.map(check_case,inputs))
    by_unit = defaultdict(Counter)
    for result in results[1:]:
        for unit in result["units"]:
            for k in ("match","different"):
                by_unit[unit["unit"]][k] += unit.get(k,0)
    measured = dict(original_inexact_comparisons=sum(results[0]["counts"].values()),
                    native_recordings=len(results)-1,
                    native_distinct_maps=len({r["map"] for r in results[1:]}),
                    native_inexact_snapshots_by_unit=dict(sorted(by_unit.items())))
    if (measured["original_inexact_comparisons"] != 0 or measured["native_distinct_maps"] != 9
            or by_unit != {"WaygateEntrance":{"match":16,"different":0},
                           "VehicleDragon":{"match":79,"different":710}}):
        raise ValueError("Placement snapshot evidence differs for the pinned cohort")
    return measured


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for k in ("source","manifest","cache"):
        parser.add_argument(k,type=Path)
    parser.add_argument("--jobs",type=int,default=3)
    args=parser.parse_args()
    print(json.dumps(verify(args.source,args.manifest,args.cache,args.jobs),indent=2))
