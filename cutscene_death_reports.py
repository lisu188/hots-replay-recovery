"""Compare physical EndSceneFired reports with tracker deaths in the pinned replay cohort."""

from argparse import ArgumentParser
from bisect import bisect_right
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing
import json
from pathlib import Path

from first_sound_timing import verify_manifest
from first_sync_game import game
from mpq_reader import MPQArchive
from predict_camp_captures import SOURCE


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sample(case):
    path,digest,build = case
    source,raw = game(Path(path),digest,build)
    with closing(MPQArchive(Path(path))) as archive:
        tracker = list(source.decode_replay_tracker_events(archive.read_file('replay.tracker.events')))
        details = source.decode_replay_details(archive.read_file('replay.details'))
    users = {r['m_userId']:r['m_playerId'] for r in tracker if r['_eventid']==9 and r['m_userId'] is not None}
    need(len(set(users.values()))==len(users),'Player setup has duplicate player IDs')
    times = defaultdict(list)
    for r in tracker:
        name = r.get('m_eventName')
        if name not in (b'PlayerDeath',b'RegenGlobePickedUp',b'TalentChosen'):
            continue
        for kv in r.get('m_intData') or []:
            if kv['m_key']==b'PlayerID':
                times[(kv['m_value'],name)].append(r['_gameloop'])
            elif kv['m_key']==b'KillingPlayer' and name==b'PlayerDeath':
                times[(kv['m_value'],b'KillerOrAssist')].append(r['_gameloop'])
    handles = Counter()
    lags = Counter()
    signals = Counter()
    dialogs = set()
    deaths = set()
    for r in source.decode_replay_game_events(raw):
        if r['_eventid']==55:
            dialogs.add(r['m_controlId'])
        if r['_eventid']!=98:
            continue
        tick = r['_gameloop']
        user = users.get(r['_userid']['m_userId'])
        handle = r['m_cutsceneId']
        handles[handle]+=1
        for name in (b'PlayerDeath',b'KillerOrAssist',b'RegenGlobePickedUp',b'TalentChosen'):
            timeline = times[(user,name)]
            pos = bisect_right(timeline,tick)
            if not pos:
                continue
            lag = tick-timeline[pos-1]
            if lag<=96:
                signals[name.decode()]+=1
            if name==b'PlayerDeath':
                lags[lag]+=1
                if lag<=96:
                    deaths.add((user,timeline[pos-1]))
    return dict(sha256=digest,build=build,map=details['m_cacheHandles'][-1][8:].hex(),
                reports=sum(handles.values()),handles=dict(sorted(handles.items())),
                victim_deaths=sum(len(v) for (_,name),v in times.items() if name==b'PlayerDeath'),
                distinct_reported_deaths_in_96=len(deaths),
                own_death_lag_counts_to_96={k:v for k,v in sorted(lags.items()) if k<=96},
                after_own_death_1_to_3=sum(lags[i] for i in range(1,4)),
                after_own_death_88_to_94=sum(lags[i] for i in range(88,95)),
                within_96=dict(sorted(signals.items())),unlabeled_dialog_event_ids_below_160=sorted(i for i in dialogs if i<160))


def summarize(samples):
    target = [r for r in samples if r['build']==98348]
    map_counts = Counter(r['map'] for r in target)
    dragon_map, = [m for m,count in map_counts.items() if count==15]
    need(dragon_map.startswith('f557190'),'Pinned Dragon Shire map differs')
    stock = [r for r in target if r['map']==dragon_map]
    ten, = [r for r in samples if r['sha256']==SOURCE]
    need(len(samples)==29 and len(target)==24 and len(stock)==15,'Incomplete replay cohort')
    counts = Counter()
    for r in stock:
        counts.update(r['handles'])
    need(ten['handles']=={131196:121} and counts=={131187:209},'Physical report cohort differs')
    return dict(cases=len(samples),legacy_cases=5,target_cases=len(target),target_dragon_cases=len(stock),TEN=ten,
                target_dragon=dict(reports=sum(counts.values()),handles=dict(counts),
                    victim_deaths=sum(r['victim_deaths'] for r in stock),
                    own_1_to_3=sum(r['after_own_death_1_to_3'] for r in stock),
                    own_88_to_94=sum(r['after_own_death_88_to_94'] for r in stock),
                    own_in_96=sum(r['within_96'].get('PlayerDeath',0) for r in stock),
                    distinct_reported_deaths_in_96=sum(r['distinct_reported_deaths_in_96'] for r in stock),
                    unlabeled_dialog_event_ids_below_160=sorted({i for r in stock for i in r['unlabeled_dialog_event_ids_below_160']})),
                other_41810=[r for r in sorted(samples,key=lambda x:x['sha256']) if r['build']==41810 and r!=ten],
                target_reports_admitted=0)


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--workers',type=int,choices=range(1,5),default=1)
    args=parser.parse_args()
    cases=verify_manifest(json.loads(args.manifest.read_bytes()))
    if args.workers==1:
        records=list(map(sample,cases))
    else:
        with ProcessPoolExecutor(args.workers) as workers:
            records=list(workers.map(sample,cases))
    print(json.dumps(summarize(records),indent=2))
