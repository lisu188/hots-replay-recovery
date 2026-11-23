"""Check Nova's unit-targeted source ability links in independent build 41810 recordings."""

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing
import json
from math import hypot
from pathlib import Path

from mpq_reader import MPQArchive
from predict_camp_captures import SOURCE
from symbolic_command_starts import members, references


def check(item):
    digest, path = item
    p, raw, _ = members(path, digest, 41810)
    with closing(MPQArchive(path)) as mpq:
        tracker = mpq.read_file("replay.tracker.events")
    setup = {}
    nova_births = []
    gates = []
    picks = {}
    first_pick_tick = {}
    heroic = {}
    potential_hero_births = []
    for e in p.decode_replay_tracker_events(tracker):
        if e["_event"].endswith(".SPlayerSetupEvent"):
            setup[e["m_playerId"]] = e["m_userId"]
        if e.get("m_unitTypeName") == b"HeroNova":
            nova_births.append((e["_gameloop"],e["m_controlPlayerId"]))
        if (e.get("m_unitTypeName", b"").startswith(b"Hero") and e["_event"].endswith(".SUnitBornEvent")
                and 1 <= e["m_controlPlayerId"] <= 10):
            potential_hero_births.append((e["_gameloop"],p.unit_tag(e["m_unitTagIndex"],e["m_unitTagRecycle"])))
        if e.get("m_eventName") == b"GatesOpen":
            gates.append(e["_gameloop"])
        if e.get("m_eventName") == b"TalentChosen":
            texts = {x["m_value"] for x in e["m_stringData"]}
            ints = {x["m_key"]: x["m_value"] for x in e["m_intData"]}
            player = ints[b"PlayerID"]
            for choice in texts:
                if choice.startswith(b"Nova"):
                    picks.setdefault(player,choice)
                    first_pick_tick.setdefault(player,e["_gameloop"])
                if choice in (b"NovaHeroicAbilityTripleTap",b"NovaHeroicAbilityPrecisionStrike"):
                    heroic[player] = (choice,e["_gameloop"])
    if len(gates) != 1:
        raise ValueError("Ambiguous opening gate phase")
    players = {pid for t,pid in nova_births if t < gates[0]}
    hero_tags = {tag for t,tag in potential_hero_births if t < gates[0]}
    if players != set(picks):
        raise ValueError("Opening Nova actor and purchased Nova talents disagree")
    before = Counter()
    all_unit = Counter()
    other = Counter()
    shots = []
    snapshots = defaultdict(lambda: defaultdict(set))
    owned = {setup[player]: player for player in players}
    for e in p.decode_replay_game_events(raw):
        tick, user = e["_gameloop"], e["_userid"]["m_userId"]
        target = e["m_target"] if e["_eventid"] == 105 else e.get("m_data",{}).get("TargetUnit") if e["_eventid"]==27 else None
        if target and players and target["m_tag"] in hero_tags:
            point=target["m_snapshotPoint"]
            snapshots[target["m_tag"],user][tick].add((point["x"],point["y"]))
        if e["_eventid"] != 27 or e["m_abil"] is None:
            continue
        link = e["m_abil"]["m_abilLink"]
        form = next(iter(e["m_data"]))
        user = e["_userid"]["m_userId"]
        if user in owned:
            player = owned[user]
            if form == "TargetUnit":
                all_unit[link] += 1
                if e["_gameloop"] < heroic.get(player, (None, 1 << 32))[1]:
                    before[link] += 1
                if link==378 and target["m_tag"] in hero_tags:
                    choice = picks[player].decode() if tick >= first_pick_tick[player] else "no_first_pick_at_issue"
                    shots.append((choice,tick,target["m_tag"]))
        elif link == 378:
            other[form] += 1
    by_pick = defaultdict(Counter)
    for purchase,t,tag in shots:
        measures=by_pick[purchase]
        measures["hero_target_issues"] += 1
        chord=set()
        for (actor, _), ticks in snapshots.items():
            if actor != tag:
                continue
            for a in range(t+1,t+36):
                if len(ticks.get(a,()))!=1 or len(ticks.get(a+1,()))!=1:
                    continue
                (x,y), = ticks[a]
                (u,v), = ticks[a+1]
                chord.add((a,u-x,v-y))
        rates=[hypot(x,y)/256 for _,x,y in chord]
        measures["issues_with_any_chord"]+=bool(rates)
        measures["one_loop_chords"]+=len(rates)
        for name, center in (("near_1_76",1.76),("near_2_64",2.64),("near_4_4",4.4)):
            matches=sum(abs(rate-center)<=0.02 for rate in rates)
            measures[name+"_chords"]+=matches
            measures[name+"_issues"]+=matches>0
        for slow in range(40,61,2):
            center=4.4*(100-slow)/100
            # Three consecutive displacements at the same displayed speed reduce the influence
            # of occasional curved or stopping paths. Each run must use one physical observer.
            seen_run=False
            for (actor, _), ticks in snapshots.items():
                if actor!=tag:
                    continue
                longest=0
                for a in range(t+1,t+36):
                    if len(ticks.get(a,()))==len(ticks.get(a+1,()))==1:
                        (x,y),=ticks[a]
                        (u,v),=ticks[a+1]
                        if abs(hypot(u-x,v-y)/256-center)<=0.02:
                            longest+=1
                            if longest>=3:
                                seen_run=True
                                break
                            continue
                    longest=0
                if seen_run:
                    break
            measures[f"three_adjacent_at_{slow}_percent_issues"]+=seen_run
    return dict(digest=digest, nova_players=len(players), first_picks=[picks.get(p,b"-").decode() for p in sorted(players)],
        heroics=[heroic.get(p,(b"-",None))[0].decode() for p in sorted(players)],
        all_nova_unit_links=all_unit, before_heroic_nova_unit_links=before, non_nova_378=other,
        post_378_hero_motion_by_first_talent=by_pick)


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("references",type=Path)
    cli.add_argument("--source",type=Path)
    args=cli.parse_args()
    refs=json.loads(args.references.read_bytes())
    items=[(d,path) for path,d,build in references(refs) if build==41810]
    if len(items)!=23:
        raise ValueError("Expected the original independent historical cohort")
    if args.source:
        items.append((SOURCE,args.source))
    with ProcessPoolExecutor(max_workers=4) as pool:
        print(json.dumps(list(pool.map(check,items)),indent=2))
