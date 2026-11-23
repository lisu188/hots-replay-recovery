"""Apply numeric links independently witnessed in original 98285 matches to a private R8 archive."""
import argparse
from collections import Counter, defaultdict
from contextlib import closing
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from command_snapshot_owners import OwnerHistory
from hero_camera_lifetimes import recorded_histories
from implicit_hero_issues import generate as hero_candidates
from implicit_point_issues import check_schema, native
from integrate_r8_camera_pings import GAME, SYNC, inventory
from match_selections import groups
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from native_game_events import encode_game_events as native_encode
from opening_birth_wire import target_protocol
from point_ability_births import generate as cast_candidates
from portable_sync_98348 import decode_sync, encode_sync
from predict_camp_captures import SOURCE
from protocol_loader import load_protocol
from repair_r8_command_sequences import DONORS, digest, encode_physical, identity, iter_frames, modern_header
from repair_unit_tags import components
from runtime_catalog_probe import Storm

PARENT = "50328fad2a8e7808b978ace43e30a49ba175515998c83887a93305ca63e5af8d"
GAME_HASH = "e783f0ac96bcd57901e18eee6cbc026411b688b2b2d24d3ac8dc7099e9c902c3"
HEROES = {"HeroAnubarak","HeroBarbarian","HeroGreymane","HeroKaelthas","HeroTyrande"}
SUMMONS = {"Abathur":"AbathurToxicNest","Nova":"NovaHoloClone"}


def control(path):
    h = digest(path.read_bytes())
    if h not in DONORS:
        raise ValueError("Unexpected control")
    p = target_protocol()
    tid = check_schema(p,98348)
    with closing(MPQArchive(path)) as arc:
        modern_header(p,arc.header["user_data_header"]["content"])
        raw = read_member(arc,GAME)
        tracker = list(p.decode_replay_tracker_events(read_member(arc,"replay.tracker.events")))
        slots = p.decode_replay_initdata(read_member(arc,"replay.initData"))["m_syncLobbyState"]["m_lobbyState"]["m_slots"]
    users = {s["m_userId"]:(i,s["m_hero"].decode()) for i,s in enumerate(slots,1)
             if s.get("m_hero") and s["m_control"]==2 and not s["m_observe"] and s.get("m_userId") is not None}
    actors = {i:hero for i,hero in users.values() if hero in SUMMONS}
    births = defaultdict(list)
    for e in tracker:
        slot = e.get("m_controlPlayerId")
        if (e["_eventid"] == 1 and slot in actors and e["m_upkeepPlayerId"] == slot
                and e["m_unitTypeName"].decode() == SUMMONS[actors[slot]]):
            births[slot,e["_gameloop"],e["m_x"],e["m_y"]].append(SUMMONS[actors[slot]])
    hits, selections = defaultdict(list),defaultdict(set)
    heroes = recorded_histories(tracker)
    owners = OwnerHistory(tracker)
    commands = defaultdict(Counter)
    bytes_hero, bytes_summon = 0,0
    for e,prev,frame in iter_frames(p,raw):
        tick,user,kind,_ = identity(e)
        if kind == 28:
            for g,tag in groups(e["m_delta"]):
                k = components(tag,22)
                if k in heroes and heroes[k][0] == users.get(user,(None,None))[0]:
                    selections[heroes[k][1].decode()].add(g["m_unitLink"])
        if kind not in (27,104):
            continue
        point = e["m_data"].get("TargetPoint") if kind == 27 else e["m_target"]
        if user in users and point:
            k = (users[user][0],tick,point["x"]//4096,point["y"]//4096)
            if k in births:
                hits[k].append((e,prev,frame))
        if kind != 27 or e["m_abil"] is not None or set(e["m_data"]) != {"TargetUnit"}:
            continue
        target = e["m_data"]["TargetUnit"]
        k = components(target["m_tag"],22)
        if k not in heroes or heroes[k][1].decode() not in HEROES:
            continue
        slot, unit, _ = heroes[k]
        pair,why = owners.lookup(target["m_tag"],tick,22)
        if why not in ("alive","revived") or pair != (slot,slot):
            continue
        shape = (e["m_cmdFlags"],target["m_targetUnitFlags"],target["m_timer"],
                 e["m_otherUnit"],e["m_unitGroup"],e["m_vector"],
                 target["m_snapshotControlPlayerId"],target["m_snapshotUpkeepPlayerId"])
        if shape != (0x80108,111,0,None,None,None,slot,slot):
            continue
        if native_encode([native(e,tick-prev,p,tid)]) != frame:
            raise ValueError("Native hero issue does not reproduce")
        commands[unit.decode()][target["m_snapshotUnitLink"]] += 1
        bytes_hero += len(frame)
    ability = defaultdict(Counter)
    for k, units in births.items():
        if len(hits[k]) != 1 or len(units) != 1:
            continue
        (e,prev,frame), = hits[k]
        ab = e.get("m_abil")
        if (e["_eventid"] != 27 or not ab or ab["m_abilCmdIndex"] != 0 or ab["m_abilCmdData"] is not None
                or any(e[n] is not None for n in ("m_otherUnit","m_unitGroup","m_vector"))):
            continue
        if native_encode([native(e,e["_gameloop"]-prev,p,tid)]) != frame:
            raise ValueError("Native exact-build spawn witness does not reproduce")
        ability[units[0]][ab["m_abilLink"],e["m_cmdFlags"]] += 1
        bytes_summon += len(frame)
    return (h, commands, selections, ability,
            dict(replay_sha256=h,spawn_frames=sum(c.total() for c in ability.values()),spawn_bytes=bytes_summon,
                 verified_hero_frames=sum(c.total() for c in commands.values()),hero_bytes=bytes_hero))


def qualifications(results):
    if len(results) != 2 or {x[0] for x in results} != DONORS:
        raise ValueError("Need both original controls")
    commands, selections, abilities = defaultdict(Counter),defaultdict(set),defaultdict(Counter)
    for _, c, s, a, _ in results:
        for k,v in c.items():
            commands[k].update(v)
        for k,v in s.items():
            selections[k].update(v)
        for k,v in a.items():
            abilities[k].update(v)
    hero_links = {}
    for unit in HEROES:
        matches = commands[unit]
        if len(matches)==1 and set(matches)==selections[unit]:
            link, = matches
            if not any(n!=unit and link in v for n,v in selections.items()):
                hero_links[unit] = link
    cast = {n:next(iter(v)) for n,v in abilities.items() if len(v)==1}
    witnesses = dict(hero={k:{"link":v,"frames":commands[k][v]} for k,v in sorted(hero_links.items())},
                     cast={k:{"link":v[0],"flag":v[1],"frames":abilities[k][v]} for k,v in sorted(cast.items())})
    return hero_links,cast,witnesses


def equal_except(actual, proposed, field):
    changed = deepcopy(actual)
    holder = changed["m_abil"] if field == "m_abilLink" else changed["m_data"]["TargetUnit"]
    expected_holder = proposed["m_abil"] if field == "m_abilLink" else proposed["m_data"]["TargetUnit"]
    holder[field] = expected_holder[field]
    if {k:v for k,v in changed.items() if k!="_bits"} != {k:v for k,v in proposed.items() if k!="_bits"}:
        raise ValueError("Unexplained intervening draft or proposed payload")
    return changed


def patch(source, raw, hero_rows, cast_rows, hero_links, abilities):
    old,p = load_protocol(41810),target_protocol()
    tid = check_schema(p,98348)
    with closing(MPQArchive(source)) as arc:
        original = read_member(arc,GAME)
        tracker = list(old.decode_replay_tracker_events(read_member(arc,"replay.tracker.events")))
    original_heroes = recorded_histories(tracker)
    edited, ledger, rejected = bytearray(), [], Counter()
    accepted = {}
    affected = Counter()
    for i, ((old_e,pa,_),(e,pb,frame)) in enumerate(zip(iter_frames(old,original),iter_frames(p,raw),strict=True)):
        if identity(e) != identity(old_e) or pa != pb:
            raise ValueError("Original/draft ordinal mapping mismatch")
        if i not in hero_rows and i not in cast_rows:
            edited.extend(frame)
            continue
        if i in hero_rows:
            held = hero_rows[i]
            target = e["m_data"]["TargetUnit"]
            key = components(old_e["m_data"]["TargetUnit"]["m_tag"],18)
            unit = original_heroes[key][1].decode()
            link = hero_links.get(unit)
            if link is None:
                rejected[unit] += 1
                edited.extend(frame)
                continue
            if (e["m_cmdFlags"]!=0x80108 or components(target["m_tag"],22)!=key or
                    old_e["m_data"]["TargetUnit"]["m_snapshotUnitLink"]!=target["m_snapshotUnitLink"] or
                    held["m_data"]["TargetUnit"]["m_snapshotUnitLink"]!=link):
                raise ValueError("Unexpected source or draft hero link context")
            field = "m_snapshotUnitLink"
            row = equal_except(e,held,field)
        else:
            projection = cast_rows[i]
            old_link = old_e["m_abil"]["m_abilLink"]
            unit = {173:"AbathurToxicNest",244:"NovaHoloClone"}[old_link]
            if unit not in abilities:
                rejected[unit] += 1
                edited.extend(frame)
                continue
            link,flag = abilities[unit]
            if old_e["m_cmdFlags"]!=flag or e["m_cmdFlags"]!=flag or e["m_abil"]["m_abilLink"]!=old_link:
                raise ValueError("Original and exact-build witness cast flag/context differ")
            # The 98348 flag does not describe the authentic 98285 shape. Both numeric
            # fields below come from the 98285 same-owner, same-loop spawn witness.
            desired = {**projection,"m_cmdFlags":flag,"m_abil":{**projection["m_abil"],"m_abilLink":link}}
            field = "m_abilLink"
            row = equal_except(e,desired,field)
        result = encode_physical(p,row,pb)
        if (e["_eventid"]!=27 or encode_physical(p,e,pb)!=frame or len(result)!=len(frame)
                or native_encode([native(row,e["_gameloop"]-pb,p,tid)])!=result or result==frame):
            raise ValueError("Unexpected physical frame")
        accepted[i] = (field,row)
        ledger.append([i,e["_gameloop"],field,link])
        affected[unit] += 1
        edited.extend(result)
    data = bytes(edited)
    total = 0
    for i,((a,prior,fa),(b,after,fb)) in enumerate(zip(iter_frames(p,raw),iter_frames(p,data),strict=True)):
        if i in accepted:
            field,expected = accepted[i]
            if expected!=b or equal_except(a,b,field)!=b or prior!=after:
                raise ValueError("Different record beyond verified numeric link")
        elif fa!=fb:
            raise ValueError("Unexpected changed physical record")
        total += 1
    if total!=104257 or len(ledger)+rejected.total()!=68:
        raise ValueError("Incomplete enumeration of 68 candidate records")
    return data,dict(full_game_events=total,considered=68,changed=len(ledger),
                     changed_by_unit=dict(sorted(affected.items())),withheld_by_unit=dict(sorted(rejected.items())),
                     physical_differing_bytes=sum(a!=b for a,b in zip(raw,data,strict=True)),
                     edit_ledger_sha256=digest(json.dumps(ledger,separators=(",",":")).encode()))


def integrate(source,parent,controls,gate_map,mechanics,curve,selection,broader,abathur,nova,stormlib,output):
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    if digest(parent.read_bytes()) != PARENT or digest(source.read_bytes()) != SOURCE:
        raise ValueError("Unexpected input archive")
    scores = [control(path) for path in controls]
    hero_links,abilities,physical = qualifications(scores)
    hero_rows,_,heroes = hero_candidates(source,gate_map,mechanics,curve,selection,broader)
    cast_rows,_,casts = cast_candidates(source,abathur,nova)
    if (len(hero_rows),len(cast_rows),len(hero_rows.keys()&cast_rows.keys())) != (17,51,0):
        raise ValueError("Unexpected candidate sets")
    storm = Storm(stormlib)
    p = target_protocol()
    header,before,v4 = inventory(parent,storm)
    modern_header(p,header)
    with closing(MPQArchive(source)) as arc:
        sync = read_member(arc,SYNC)
        if before["replay.tracker.events"] != read_member(arc,"replay.tracker.events"):
            raise ValueError("Historical tracker mismatch")
    records = decode_sync(sync)
    if digest(before[GAME])!=GAME_HASH or before[SYNC]!=sync or encode_sync(records)!=sync or len(records)!=308:
        raise ValueError("Unexpected parent game or source syncs")
    data,notes = patch(source,before[GAME],hero_rows,cast_rows,hero_links,abilities)
    with TemporaryDirectory(dir=output.parent) as tmp:
        dest=Path(tmp)/"candidate.StormReplay"
        dest.write_bytes(parent.read_bytes())
        storm.replace(dest,{GAME:data})
        h,after,v2=inventory(dest,storm)
        different=sorted(k for k in before if before[k]!=after[k])
        if (header!=h or before.keys()!=after.keys() or different!=["(attributes)",GAME] or after[GAME]!=data
                or after[SYNC]!=sync or v4["raw_chunk_size"]!=v2["raw_chunk_size"]):
            raise ValueError("Archive member verification failed")
        image=digest(dest.read_bytes())
        if digest(parent.read_bytes())!=PARENT or digest(source.read_bytes())!=SOURCE:
            raise ValueError("Protected input changed")
        os.link(dest,output)
    return dict(source_sha256=SOURCE,parent_sha256=PARENT,output_sha256=image,output_bytes=output.stat().st_size,
                declared_build=98285,sync_records=len(records),sync_sha256=digest(sync),unchanged_members=12,
                changed_members=different,game_bytes=len(data),game_sha256=digest(data),
                source_hero_fragment=heroes["sha256"],source_cast_fragment=casts["sparse_sha256"],
                exact_build_witnesses=physical,exact_build_controls=sorted((r[-1] for r in scores),key=lambda r:r["replay_sha256"]),
                independent_mpq_readers_agree=True,target_simulation_verified=False,**notes)


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    for arg in ("source","parent","gate_map","mechanics","curve","selection","broader","abathur","nova","output"):
        cli.add_argument(arg,type=Path)
    cli.add_argument("--control",action="append",dest="controls",type=Path,required=True)
    cli.add_argument("--stormlib",required=True)
    print(json.dumps(integrate(**vars(cli.parse_args())),indent=2))
