"""Predict ordinary lane and capture births on the two verified Dragon Shire layouts."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from hashlib import sha256
import json
from math import floor, hypot
from pathlib import Path
import re
from xml.etree import ElementTree

from camp_owner_wire import read_tracker, STOCK
from convert_historical_pings import PING, pinned
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from predict_camp_captures import MAP, number, SOURCE
from repair_unit_tags import components

PROFILES = {41810: (MAP, 81, 481), 98348: (STOCK, 2, 480)}
TEMPLATES = {
    41810: "7efa1c335816eebe802747ae4b16252ed22fcd8387b09d24b115b2917542b52a",
    98348: "4732077e899f6894c29586795a01e2a27fba622dbf22b5d29c7b30d57e3ce4fc",
}
GROUPS = (("FootmanMinion", 3), ("WizardMinion", 1), ("RangedMinion", 3))
REGULAR = {name for name, _ in GROUPS}
CAPTURES = {"Knights": ["MercLanerMeleeKnight"] * 3 + ["MercLanerRangedMage"],
            "SiegeGiants": ["MercLanerSiegeGiant"] * 2}


def layouts(path, build):
    pinned(path, PROFILES[build][0])
    with closing(MPQArchive(path)) as archive:
        objects = ElementTree.fromstring(read_member(archive, "Objects"))
        script = read_member(archive, "MapScript.galaxy").decode("utf-8-sig")
    points = {}
    lanes = defaultdict(dict)
    for e in objects.findall("ObjectPoint"):
        x, y, _ = map(float, e.get("Position").split(","))
        points[int(e.get("Id"))] = floor(x), floor(y)
        name = re.fullmatch(r"Lane (\d+) - Waypoint (\d+)(?: \((?:Order|Chaos) Spawn\))?", e.get("Name",""))
        if name:
            lane, waypoint = map(int, name.groups())
            if waypoint in lanes[lane]:
                raise ValueError("Repeated lane waypoint")
            lanes[lane][waypoint] = x, y
    camps = {}
    for cid, block in enumerate(script.split("lv_junglecamp += 1;")[1:],1):
        kind, = re.findall(r"lv_mapDataCampDefenderType = libMapM_ge_JungleCampDefenderTypes_(\w+);", block)
        slots = re.findall(r"lv_mapDataDefenderSpawnPoints\[(\d+)\] = PointFromId\((\d+)\);", block)
        if [int(i) for i, _ in slots] != list(range(1, len(CAPTURES[kind])+1)):
            raise ValueError("Unsupported camp slot assignment")
        camps[cid] = [(name, *points[int(pid)]) for name, (_,pid) in zip(CAPTURES[kind], slots)]
    if set(lanes) != {1,2,3} or set(camps) != set(range(1,6)):
        raise ValueError("Incomplete map")
    return lanes, camps


def load(path, digest, build):
    pinned(path, digest)
    proto, raw, horizon = read_tracker(path, build)
    events = list(proto.decode_replay_tracker_events(raw))
    if sum(e["_bits"] for e in events) != len(raw)*8:
        raise ValueError("Incomplete tracker")
    gates, = [e["_gameloop"] for e in events if e.get("m_eventName")==b"GatesOpen"]
    cores = {tag(e) for e in events if e.get("m_unitTypeName")==b"KingsCore" and e["_gameloop"]==0}
    core_deaths = [e["_gameloop"] for e in events if e["_eventid"]==2 and tag(e) in cores]
    if len(cores)!=2 or len(core_deaths)>1:
        raise ValueError("Core selection")
    return proto, events, gates, next(iter(core_deaths),horizon), horizon


def tag(e):
    return e["m_unitTagIndex"], e["m_unitTagRecycle"]


def physical(e):
    return (e["m_unitTypeName"].decode(), e["m_controlPlayerId"], e["m_upkeepPlayerId"],e["m_x"],e["m_y"])


def template_reference(path, build, lanes):
    _, events, gates, _, _ = load(path,TEMPLATES[build],build)
    first = gates + PROFILES[build][1]
    units = defaultdict(list)
    for e in events:
        if e["_eventid"]==1 and e["m_unitTypeName"].decode() in REGULAR:
            units[e["_gameloop"]].append(physical(e))
    template = []
    anchor_stats = Counter()
    for lane in (1,2,3):
        for group, (name, count) in enumerate(GROUPS):
            delta = (lane-1)*3+group
            rows = units[first+delta]
            if [(n,o,u) for n,o,u,x,y in rows] != [(name,o,o) for o in (12,11) for _ in range(count)]:
                raise ValueError("Unexpected first-wave formation")
            for owner in (12,11):
                lane_points=lanes[lane]
                start=max(lane_points) if owner==12 else 0
                nxt=start-1 if owner==12 else 1
                bx,by=lane_points[start]
                dx,dy=lane_points[nxt][0]-bx,lane_points[nxt][1]-by
                dist=hypot(dx,dy)
                nominal=(floor(bx+dx/dist*(3-group)*1.875),floor(by+dy/dist*(3-group)*1.875))
                group_rows=[r for r in rows if r[1]==owner]
                anchor_stats["groups"] += 1
                anchor_stats["lead_at_floored_map_projection"] += nominal==group_rows[0][3:]
                if max(abs(a-b) for a,b in zip(nominal,group_rows[0][3:]))>1:
                    raise ValueError("Group lead too far from authored spawn")
                for rank,row in enumerate(group_rows,1):
                    template.append((delta,lane,rank,row))
    return template, dict(anchor_stats)


def rebind_role(role, tick, births_by_tag, deaths, horizon):
    """Resolve one producer/slot in an independently supplied historic-layout trace."""
    if not role["born"] < tick <= horizon:
        raise ValueError("Ping is outside the supplied trace")
    hits = [key for key, evidence in births_by_tag.items() if role == evidence]
    if len(hits) != 1 or tick >= deaths.get(hits[0], horizon + 1):
        raise ValueError("Missing, ambiguous, or expired target generation")
    return hits[0]


def compare(path,digest,build,template,camps):
    p,tracker,gates,end,horizon = load(path,digest,build)
    _,delay,stride=PROFILES[build]
    first=gates+delay
    observed = defaultdict(list)
    mercs = defaultdict(list)
    stats = []
    deaths={}
    for e in tracker:
        t=e["_gameloop"]
        if e["_eventid"]==1:
            item=physical(e)
            if item[0] in REGULAR:
                observed[t].append((item,tag(e)))
            if item[0] in CAPTURES["Knights"]+CAPTURES["SiegeGiants"]:
                mercs[t].append((item,tag(e)))
        elif e["_eventid"]==2:
            deaths[tag(e)]=t
        elif e.get("m_eventName")==b"JungleCampCapture":
            team=number(e,"m_fixedData","TeamID")
            if team not in (4096,8192):raise ValueError("Unexpected team")
            stats.append((t,number(e,"m_intData","CampID"),10+team//4096))
    target_keys = {}
    all_predictions=defaultdict(list)
    for wave,tick in enumerate(range(first,end+1,stride),1):
        for delta,lane,slot,signature in template:
            if tick+delta <= end:
                all_predictions[tick+delta].append((signature,wave,lane,slot))
    exact=structural=missing=extra=0
    for t in sorted(all_predictions.keys()|observed.keys()):
        expected=all_predictions[t]
        actual=observed[t]
        missing+=max(0,len(expected)-len(actual))
        extra+=max(0,len(actual)-len(expected))
        for (sig,wave,lane,slot),(seen,key) in zip(expected,actual):
            structural += sig[:3]==seen[:3]
            if seen==sig:
                exact+=1
                target_keys[key] = dict(kind=sig[0],owner=sig[1],wave=wave,lane=lane,slot=slot,born=t,xy=list(sig[3:]))
    capture_rows=matched_captures=complete_groups=wrong_clock=0
    for t,cid,owner in stats:
        expected=[(n,owner,owner,x,y) for n,x,y in camps[cid]]
        # Qualify by matching each predicted spatial slot; the current map may create mercs in another order.
        actual=mercs.get(t,[])
        capture_rows+=len(expected)
        for slot,sig in enumerate(expected,1):
            hits=[key for seen,key in actual if seen==sig]
            if len(hits)==1:
                matched_captures+=1
                target_keys[hits[0]]=dict(kind=sig[0],owner=owner,camp=cid,slot=slot,born=t,xy=list(sig[3:]))
        complete_groups += [x for x,_ in actual]==expected
        wrong_clock += len(expected) if not actual else 0
    with closing(MPQArchive(path)) as a:
        wire=a.read_file("replay.game.events")
    references=[]
    size=0
    ping_ordinal=0
    for e in p.decode_replay_game_events(wire):
        size+=e["_bits"]
        if e["_eventid"]!=PING:continue
        key=components(e["m_unit"],18 if build==41810 else 22) if e["m_unit"] else None
        if key in target_keys:
            r=target_keys[key]
            if r["born"]<e["_gameloop"]<deaths.get(key,horizon+1):
                references.append(dict(ping_ordinal=ping_ordinal,ping_loop=e["_gameloop"],**r))
                if rebind_role(r, e["_gameloop"], target_keys, deaths, horizon) != key:
                    raise ValueError("Producer-slot lookup failed")
        ping_ordinal+=1
    if size != len(wire)*8:raise ValueError("Incomplete game events")
    true_starts=sorted(t for t, group in observed.items() if group and group[0][0][:3]==("FootmanMinion",12,12)
                       and (t-1 not in observed or not observed[t-1]))
    # Ignore earlier indexing of missing rows when computing the clock.
    if not true_starts: raise ValueError("No regular lane waves")
    return dict(build=build,sha256=digest,gates_loop=gates,core_cutoff=end,header_end=horizon,
                first_delay=true_starts[0]-gates,observed_wave_starts=len(true_starts),
                start_intervals=dict(Counter(b-a for a,b in zip(true_starts,true_starts[1:]))),
                last_start=true_starts[-1],predicted_normal_births=sum(map(len,all_predictions.values())),
                observed_normal_births=sum(map(len,observed.values())),matched_tick_type_owners_ordinal=structural,
                exact_birth_xy_and_order=exact,missing_births=missing,extra_births=extra,captures=len(stats),
                expected_mercs=capture_rows,same_loop_position_type_team_slots=matched_captures,
                exact_ordered_camps=complete_groups,mercs_missing_at_capture_loop=wrong_clock,
                qualified_pings=references if digest==SOURCE else len(references))


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--build",type=int,choices=PROFILES,required=True)
    cli.add_argument("--map",type=Path,required=True)
    cli.add_argument("--template-replay",type=Path,required=True)
    cli.add_argument("--case",nargs=2,action="append",required=True)
    a=cli.parse_args()
    lanes,camps=layouts(a.map,a.build)
    template, geometry=template_reference(a.template_replay,a.build,lanes)
    if len({d for _,d in a.case})!=len(a.case):raise ValueError("Duplicate case")
    print(json.dumps(dict(template_sha256=TEMPLATES[a.build],geometry=geometry,
                          cases=[compare(Path(path),d,a.build,template,camps) for path,d in a.case]),indent=2))
