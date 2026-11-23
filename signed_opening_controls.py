"""Check the complete 1–84 opening and individual modeled hero frames against physical Dragon Shire recordings."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from assemble_signed_tracker import opening_heroes
from camp_owner_wire import STOCK, read_tracker
from dragon_reset_wire import COHORT
from dragonshire_packages import MERC_CAPTURE
from encoders import encode_tracker_events
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE


def label(e):
    return (e.get("m_eventName") or e["_event"].rsplit(".",1)[-1].encode()).decode()


def window(raw, protocol):
    result = []
    at = before = 0
    for event in protocol.decode_replay_tracker_events(raw):
        loop = event["_gameloop"]
        if loop > 84:
            break
        size, partial = divmod(event.pop("_bits"), 8)
        if partial or size<=0 or at+size>len(raw) or loop<before:
            raise ValueError("Invalid original tracker frame")
        if loop:
            result.append((event,before,raw[at:at+size]))
        at += size
        before=loop
    return result


def compare(path, digest, build, package, scripts):
    if sha256(path.read_bytes()).hexdigest()!=digest:
        raise ValueError("Replay digest mismatch")
    original, raw, _ = read_tracker(path,build)
    actual = window(raw,original)
    result = dict(replay_sha256=digest, build=build, observed_frames=len(actual))
    try:
        model = opening_heroes(path,build,original,package,scripts)
    except ValueError as exc:
        if str(exc) not in {"Incomplete hero roster","Unmodeled hero startup schedule","Incomplete hero pair"}:
            raise
        return {**result,"complete":False,"reason":str(exc),"joined_frames":0}
    target=target_protocol()
    joined=Counter()
    failures=[]
    matched=set()
    for ordinal, pred in enumerate(model):
        hits=[i for i,(e,_,_) in enumerate(actual) if e==pred]
        if len(hits)!=1:
            failures.append(label(pred))
            continue
        i,=hits
        matched.add(i)
        _,prev,physical=actual[i]
        encoded=encode_tracker_events([{**pred,"_gameloop":pred["_gameloop"]-prev}],target)
        if encoded!=physical:
            raise ValueError("Semantic match differed from the physical frame")
        joined[label(pred)]+=1
    complete=len(actual)==len(model) and all(e==p for (e,_,_),p in zip(actual,model))
    if complete:
        if failures or sum(joined.values())!=len(actual):
            raise ValueError("Complete opening failed physical join")
        # All observed frames are consecutive from the final loop-zero frame.
        if encode_tracker_events(model,target)!=b"".join(b for _,_,b in actual):
            raise ValueError("Complete window differs in raw bytes")
    if complete:
        reason=None
    elif failures:
        reason="model rows differ or are missing"
    elif len(actual)!=len(model):
        reason="additional physical events in window"
    else:
        reason="physical event order differs"
    return {**result, "predicted_frames":len(model), "joined_frames":joined.total(), "joined_by_kind":dict(joined),
            "complete":complete,"reason":reason,"failed_by_kind":dict(Counter(failures)),
            "unmatched_physical_by_kind":dict(Counter(label(e) for i,(e,_,_) in enumerate(actual) if i not in matched)),
            "complete_bytes":sum(len(row[2]) for row in actual) if complete else 0}


def audit(manifest, cohort, historical_map, retail_map, scripts):
    cases=json.loads(cohort.read_bytes())
    if sha256(json.dumps(cases,sort_keys=True,separators=(",",":")).encode()).hexdigest()!=COHORT:
        raise ValueError("Unexpected Dragon Shire cohort")
    data=json.loads(manifest.read_bytes())
    paths={(build,sha):Path(p) for p,sha,build in data}
    if len(paths)!=len(data) or [sha256(p.read_bytes()).hexdigest() for p in (historical_map,retail_map)]!=[MERC_CAPTURE,STOCK]:
        raise ValueError("Duplicate case or wrong map")
    rows=[]
    totals={}
    for build,key,package in ((41810,"old_replays",historical_map),(98348,"target_controls",retail_map)):
        group=[compare(paths[build,e["sha256"]],e["sha256"],build,package,scripts) for e in cases[key]]
        rows.extend(group)
        totals[str(build)]=dict(recordings=len(group),complete=sum(r["complete"] for r in group),
                                withheld=sum(not r["complete"] for r in group),
                                complete_physical_bytes=sum(r.get("complete_bytes",0) for r in group),
                                physically_matched_individual_rows=sum(r["joined_frames"] for r in group))
    if len(rows)!=20 or len({r["replay_sha256"] for r in rows})!=20 or not next(r["complete"] for r in rows if r["replay_sha256"]==SOURCE):
        raise ValueError("Unexpected cohort or original TEN opening")
    return dict(loops=[1,84],historical_target_map=MERC_CAPTURE,retail_map=STOCK,totals=totals,cases=rows,
                inferred_target_native_playback=False)


if __name__=="__main__":
    args=argparse.ArgumentParser(description=__doc__)
    for name in ("manifest","cohort","historical_map","retail_map","scripts"):
        args.add_argument(name,type=Path)
    print(json.dumps(audit(**vars(args.parse_args())),indent=2))
