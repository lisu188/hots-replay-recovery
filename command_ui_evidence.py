"""Test whether same-user clicks, selection or trigger UI actions recover the missing creator."""

import argparse
from bisect import bisect_left
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from hashlib import sha256
import json
from pathlib import Path

from encoders import encode_game_events
from predict_camp_captures import SOURCE
from symbolic_command_starts import FAMILY, members, references as pinned_references

UI={28,29,39,40,55,58,59,61,62,66}
NEW=("7fb7b9bcd16df2c19d64f720731b3a937b5931a83582e67c45347368a563fb60",
     "f4e315a3b7044401359e73969172a442a96e7529432f64c183b9f09e7387f04c",
     "96f31eb4ca6c71ba094646442e95090c65226be63301dfd40e6e9fcea728a14c")


def target_tag(e):
    return e["m_data"].get("TargetUnit",{}).get("m_tag")


def measure(args):
    path, digest, build=args
    p,raw,_=members(path,digest,build)
    ui=defaultdict(list)
    issues=defaultdict(list)
    first={}
    first_update={}
    pending={}
    paired=set()
    complete=Counter()
    offset=prior=0
    # Retain byte slices only for the small auxiliary UI, not every game event.
    for n,e in enumerate(p.decode_replay_game_events(raw)):
        kind,t,u=e["_eventid"],e["_gameloop"],e["_userid"]["m_userId"]
        size,rem=divmod(e["_bits"],8)
        if rem or not size or offset+size>len(raw) or t<prior:
            raise ValueError("Invalid game frame boundary")
        if kind in UI:
            if kind==39: info=e["m_unitTag"]
            elif kind==28: info=tuple(e["m_delta"]["m_addUnitTags"])
            else: info=None
            ui[u,kind].append((n,t,info))
            complete[kind]+=1
            physical=raw[offset:offset+size]
            if encode_game_events([{**e,"_gameloop":t-prior}],p)!=physical:
                raise ValueError("Supplemental UI frame differs on re-encoding")
        if kind in FAMILY:
            seq=e.get("m_sequence");key=u,seq
            if kind==27:
                issues[key].append((n,e))
            if kind in (103,104,105) and seq is not None:
                first.setdefault(key,n)
                if kind in (104,105):
                    first_update.setdefault(key,(n,e))
                elif e["m_state"]==2 and pending.get(u)==(first.get(key),t,key):
                    paired.add(key)
            pending[u]=(n,t,key) if kind in (104,105) else None
        prior=t
        offset+=size
    if offset!=len(raw):
        raise ValueError("Incomplete game stream")
    stats=defaultdict(Counter)
    stratified=defaultdict(Counter)
    for key,(n,update) in first_update.items():
        u,seq=key
        tick=update["_gameloop"];kind=update["_eventid"]
        matches=issues.get(key,())
        if key in paired and first[key]==n and not matches:
            group="historical_missing"
        elif key in paired and first[key]==n and len(matches)==1:
            group="state2_recorded_later" if matches[0][0]>n else "state2_recorded_earlier"
        elif build==98348 and len(matches)==1 and matches[0][0]<n and matches[0][1]["m_cmdFlags"]&(1<<19):
            group="target_unique_bit19_creator"
        else:
            continue
        count=stats[group];count["rows"]+=1
        creator=matches[0][1] if matches else None
        if creator:
            count["explicit_ability"]+=creator["m_abil"] is not None
            for name in ("m_otherUnit","m_unitGroup","m_vector"):
                if name in creator:
                    count[name+"_tested"]+=1
                    count[name+"_present"]+=creator[name] is not None
        for event_id in sorted(UI):
            events=ui[u,event_id]
            i=bisect_left(events,n,key=lambda item:item[0])
            if i<len(events) and events[i][1]==tick:
                count[f"following_same_tick_{event_id}"]+=1
            if i==0: continue
            ordinal,t,value=events[i-1]
            lag=tick-t
            if lag>4: continue
            count[f"prior_0_4_{event_id}"]+=1
            if lag==0: count[f"prior_same_tick_{event_id}"]+=1
            if event_id not in (39,28): continue
            if event_id==28:
                if len(value)!=1: continue
                value,=value
            # Evaluate the candidate unit from UI at update time against an independently recorded issue.
            same_update=kind==105 and update["m_target"]["m_tag"]==value
            form="unit_same" if same_update else ("unit_different" if kind==105 else "point")
            band="same_tick" if not lag else "prior_1_4"
            bucket=stratified[f"{group}/{event_id}/{band}/{form}"]
            bucket["rows"]+=1
            if creator:
                bucket["creator_targets_ui_unit"]+=target_tag(creator)==value
                bucket["creator_targets_other_unit"]+=target_tag(creator) is not None and target_tag(creator)!=value
                bucket["creator_not_unit_targeted"]+=target_tag(creator) is None
                bucket["creator_is_implicit"]+=creator["m_abil"] is None
                bucket["ui_observation_precedes_creator"]+=ordinal<matches[0][0]
    return dict(replay_sha256=digest,build=build,all_auxiliary_frames=dict(complete),groups=dict(stats),by_ui=dict(stratified))


def run(source, references, public_folder, jobs):
    paths=json.loads(references.read_bytes())
    inputs=[row for row in pinned_references(paths) if row[2] in (41810,98348)]
    for path in public_folder.glob("*98348.private.StormReplay"):
        h=sha256(path.read_bytes()).hexdigest()
        if h in NEW: inputs.append((path,h,98348))
    if len(inputs)!=50 or len({d for _,d,_ in inputs})!=50 or not set(NEW)<={d for _,d,_ in inputs}:
        raise ValueError("Expected the 23 old and 24 target held-out recordings plus the three new public controls")
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        rows=list(pool.map(measure,[(source,SOURCE,41810),*sorted(inputs,key=lambda r:r[1])]))
    summary={}
    for name,part in (("ten",rows[:1]),("old_holdouts",[r for r in rows[1:] if r["build"]==41810]),
                      ("target_controls",[r for r in rows if r["build"]==98348 and r["replay_sha256"] not in NEW]),
                      ("new_public_target",[r for r in rows if r["replay_sha256"] in NEW])):
        groups=defaultdict(Counter);by_ui=defaultdict(Counter)
        for row in part:
            for key,value in row["groups"].items(): groups[key].update(value)
            for key,value in row["by_ui"].items(): by_ui[key].update(value)
        summary[name]=dict(recordings=len(part),groups=groups,by_ui=by_ui)
    if summary["ten"]["groups"]["historical_missing"]["rows"]!=13984:
        raise ValueError("Original missing cohort changed")
    return dict(summary=summary,case_sha256_build=[[r["replay_sha256"],r["build"]] for r in rows],
                emitted_creators=0)


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    for key in ("source","references","public_folder"):
        cli.add_argument(key,type=Path)
    cli.add_argument("--jobs",type=int,default=4)
    print(json.dumps(run(**vars(cli.parse_args())),indent=2))
