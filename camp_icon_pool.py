"""Measure the shared-pool information missing before the five historical Dragon camp icon births."""

import argparse
from collections import defaultdict
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from camp_owner_wire import STOCK, read_tracker
from dragon_reset_wire import COHORT
from dragon_startup_births import predict
from dragonshire_packages import MERC_CAPTURE
from first_camp_event_order import layout
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from pool_generation_bounds import single_slot_witness
from predict_camp_captures import SOURCE
from unit_slot_pool import GENERATION_MASK, SLOT_LIMIT

ICON=b"JungleCampIconUnitTeamColor"


def need(condition, message):
    if not condition:
        raise ValueError(message)


def openings(package, mechanics, map_sha):
    need(sha256(package.read_bytes()).hexdigest()==map_sha,"Wrong map")
    points={center:camp for camp,(center,_,_) in enumerate(layout(package),1)}
    with closing(MPQArchive(package)) as a:
        parts=[read_member(a,k) for k in ("Objects","Regions","MapScript.galaxy")]
    birth,_=predict(*parts,mechanics.read_bytes())
    return points,{points[r["m_x"],r["m_y"]]:(r["m_unitTagIndex"],r["m_unitTagRecycle"]) for r in birth if r["m_unitTypeName"]==ICON}


def observe(path, digest, build, points, modeled):
    need(sha256(path.read_bytes()).hexdigest()==digest,"Recording digest differs")
    protocol,raw,_=read_tracker(path,build)
    seen=defaultdict(dict)
    deaths={}
    icons={}
    first_gap=None
    first_icon=None
    for i,e in enumerate(protocol.decode_replay_tracker_events(raw)):
        tick=e["_gameloop"]
        if first_icon is not None and tick>first_icon:
            break
        kind=e["_eventid"]
        if kind not in (1,2,6):
            continue
        slot,gen=e["m_unitTagIndex"],e["m_unitTagRecycle"]
        need(0<=slot<SLOT_LIMIT and 0<gen<GENERATION_MASK,"Tag outside ordinary pool")
        if kind==2:
            deaths[slot,gen]=tick
            continue
        prior=max(seen[slot],default=0)
        need(gen>=prior,"Nonmonotonic tracker generation")
        if gen==prior:
            continue
        name=e["m_unitTypeName"]
        if gen>prior+1 and first_gap is None:
            first_gap=dict(loop=tick,source_ordinal=i,slot=slot,previous=prior,current=gen)
        if name==ICON:
            if first_icon is None:
                first_icon=tick
            camp=points[e["m_x"],e["m_y"]]
            need(tick==first_icon and camp not in icons,"Ambiguous first visible icon")
            if prior:
                missing=single_slot_witness(slot,prior,gen)
            else:
                missing=gen-1
            icons[camp]=dict(source_ordinal=i,slot=slot,generation=gen,previous_generation=prior,
                             previous_birth_loop=seen[slot].get(prior),previous_death_loop=deaths.get((slot,prior)),
                             intervening_unreported_birth_generations=missing)
        seen[slot][gen]=tick
    need(len(icons)==5,"Incomplete physical icon set")
    if build==98348:
        need(first_icon==0 and {c:(r["slot"],r["generation"]) for c,r in icons.items()}==modeled,
             "Retail opening icon tags differ from map prediction")
    else:
        need(first_icon>0 and not modeled,"Expected dynamically allocated legacy icons")
    lower=sum(max(events)-len(events) for events in seen.values() if events)
    return dict(replay_sha256=digest,build=build,icon_loop=first_icon,icons=icons,
                minimum_unreported_generations_to_match_visible_slots_through_icon_loop=lower,
                first_tracker_generation_gap=first_gap)


def audit(manifest, cohort, merc_map, stock_map, mechanics):
    group=json.loads(cohort.read_bytes())
    need(sha256(json.dumps(group,sort_keys=True,separators=(",",":")).encode()).hexdigest()==COHORT,"Changed cohort")
    records=json.loads(manifest.read_bytes())
    paths={(build,sha):Path(p) for p,sha,build in records}
    need(len(records)==len(paths),"Duplicate recording")
    all_cases=[]
    for build,key,pkg,map_hash in ((41810,"old_replays",merc_map,MERC_CAPTURE),(98348,"target_controls",stock_map,STOCK)):
        points,opening= openings(pkg,mechanics,map_hash)
        all_cases.extend(observe(paths[build,r["sha256"]],r["sha256"],build,points,opening) for r in group[key])
    old=[r for r in all_cases if r["build"]==41810]
    retail=[r for r in all_cases if r["build"]==98348]
    ten,=[r for r in old if r["replay_sha256"]==SOURCE]
    need((len(old),len(retail))==(5,15),"Incomplete cohort")
    return dict(merc_capture_sha256=MERC_CAPTURE,stock_sha256=STOCK,
                ten=ten,minimum_unreported_intervening_birth_generations_at_ten_icon_slots=sum(
                    r["intervening_unreported_birth_generations"] for r in ten["icons"].values()),
                distinct_41810_tags_per_camp={c:len({(r["icons"][c]["slot"],r["icons"][c]["generation"]) for r in old}) for c in range(1,6)},
                held_out_historical=[r for r in old if r is not ten],retail_control_sha256=[r["replay_sha256"] for r in retail],
                retail_loop_zero_icon_tags_matched=5*len(retail),projected_merc_capture_icon_tags=0,
                condition="Historical bounds count intervening allocations required to reproduce observed source generations under the ordinary 98348 unit pool.")


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ("manifest","cohort","merc_map","stock_map","mechanics"):
        cli.add_argument(name,type=Path)
    print(json.dumps(audit(**vars(cli.parse_args())),indent=2))
