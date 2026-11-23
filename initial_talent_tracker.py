"""Project initial Greymane and Kael'thas awards from translated inputs and 98348 catalog columns."""

from argparse import ArgumentParser
from collections import Counter
from contextlib import closing
from hashlib import sha256
from pathlib import Path
from xml.etree import ElementTree as ET
import json

from build_gate_order_map import definition
from encoders import encode_tracker_events
from first_sound_timing import verify_manifest
from first_sync_game import game
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE
from source_talent_path_41810 import _tracker_history

SIGNED = "150bdcea5435021263c84648d892c2c3dcc26bff8c72d1be5198c31a4bb09791"
MERC = "54e1a8fbe7e42f00b7b52cde420ed259105228fcdf165097ef52ecd0f5c4125a"
GAME = "a6384749fbe8f676cbd6ccb9ec1aeac004815d37a8e1c2f8f9f8f176b2bfca09"
STREAM = "d5722b8a4e8e794d6321abe49a7d4cdf825b793fc259e3b9c94fbf2d9c814cfd"
LEDGER = "8493263af8a2292db62fdec6e8f956534c60727c3f0e0caceea3a302c8355671"
PREFIX = "1073a5bdbffca7d6c50fd4ffe7dcedfe150ea4d2ba4152b4db7b04b357259d86"
HEROES = {"HeroGreymane":"78a564ee1334eeaee26c4b6c57a7dd5d5b3c048cba63a9b7131440d778b98cff",
          "HeroKaelthas":"39cf6954288e32edd73dfed13f82e45ab5f944a54f9f3fa9adaf2aacc7ffc13b"}
CHOICE = b"TalentChosen"
TAG = "talent_index_requires_target_award_state"


def require(value,why):
    if not value: raise ValueError(why)


def pinned(path,h):
    raw=path.read_bytes()
    require(sha256(raw).hexdigest()==h,"Wrong "+path.name)
    return raw


def read_trees(grey,kael,script,package):
    libs=pinned(script,GAME).decode("utf-8-sig").replace("\r\n","\n")
    choose=definition(libs,"void","libGame_gf_TalentsChooseTalentForPlayer")
    place=choose.index('StatEventCreate("TalentChosen");')
    emitted=choose[place:choose.index("    PlayerAddTalent(",place)].strip().splitlines()
    require(len(emitted)==4 and '"PlayerID", lp_player)' in emitted[1] and '"PurchaseName"' in emitted[2]
            and "lv_talentData[lp_buttonIndex].lv_talentCatalogLink" in emitted[2] and "StatEventSend(" in emitted[3],"Stat emitter changed")
    choose_event=definition(libs,"bool","libGame_gt_TalentsChoiceSelected_Func")
    require("libGame_gv_talents_ActiveChoiceTierForPlayer[EventPlayer()]" in choose_event and
            "TalentTreeGetSelectedHeroTalentTreeColumn(EventPlayer()" in choose_event,"Choice callback differs")
    trees={}
    for hero,path in (("HeroGreymane",grey),("HeroKaelthas",kael)):
        xml=ET.fromstring(pinned(path,HEROES[hero]))
        unit,=xml.findall("CHero[@id='"+hero[4:]+"']")
        choices=unit.findall("TalentTreeArray")
        tier={i:n.get("Talent") for i,n in enumerate(choices) if n.get("Tier")=="1"}
        require(set(tier)==set(range(3)) and len(set(tier.values()))==3,"Unexpected opening tier")
        for i,name in tier.items():
            require(choices[i].get("Column")==str(i+1) and set(choices[i].attrib)=={"Tier","Column","Talent"} and
                    list(choices[i])==[] and xml.find("CTalent[@id='"+name+"']") is not None,"Choice has additional requirements")
        trees[hero]=tier
    package_hash=sha256(package.read_bytes()).hexdigest()
    require(package_hash in (SIGNED,MERC),"Unknown opening talent map")
    with closing(MPQArchive(package)) as a:
        for n in read_member(a,"(listfile)").decode().splitlines():
            if not n.lower().endswith(".xml") or not n.lower().startswith("base.stormdata\\gamedata\\"):
                continue
            doc=ET.fromstring(read_member(a,n))
            require(not any(node.tag=="CHero" and (node.get("default") or ("Hero"+str(node.get("id"))) in trees)
                            for node in doc),"Map overrides the two tree layouts")
            for elem in doc.findall("CTalent"):
                if any(elem.get("id") in t.values() for t in trees.values()):
                    require(elem.get("id")=="KaelthasManaAddict" and len(elem)==1 and
                            elem[0].tag=="QuestData" and elem[0].attrib=={"TargetCount":"25"},"Changed opening talent override")
    return trees,package_hash


def stat(loop,player,name):
    return dict(_eventid=10,_event="NNet.Replay.Tracker.SStatGameEvent",_gameloop=loop,m_eventName=CHOICE,
                m_stringData=[dict(m_key=b"PurchaseName",m_value=name.encode("ascii"))],
                m_intData=[dict(m_key=b"PlayerID",m_value=player)],m_fixedData=None)


def history(events):
    # Only identity and levels enter the predictor. All purchase names remain held out.
    return _tracker_history(r for r in events if r["_eventid"]==9 or r.get("m_eventName") in (b"PlayerSpawned",b"LevelUp"))[:3]


def compare(rows,tracker,raw,protocol):
    wanted={(r["_gameloop"],r["m_intData"][0]["m_value"]):r for r in rows}
    require(len(wanted)==len(rows),"Repeated expected player/tick")
    ordinals={}
    offset=before=0
    for ordinal,event in enumerate(tracker):
        size,tail=divmod(event["_bits"],8)
        require(tail==0,"Non-byte-aligned tracker frame")
        if event.get("m_eventName")==CHOICE:
            player,=[r["m_value"] for r in event["m_intData"] if r["m_key"]==b"PlayerID"]
            key=(event["_gameloop"],player)
            if key in wanted:
                expected=wanted[key]
                require(key not in ordinals and expected=={k:v for k,v in event.items() if k!="_bits"},"Wrong observed award")
                physical={**expected,"_gameloop":expected["_gameloop"]-before}
                require(encode_tracker_events([physical],protocol)==raw[offset:offset+size],"Award frame bytes differ")
                ordinals[key]=ordinal
        before=event["_gameloop"]
        offset+=size
    require(offset==len(raw) and wanted.keys()==ordinals.keys(),"Missing physical award")
    return [ordinals[(r["_gameloop"],r["m_intData"][0]["m_value"])] for r in rows]


def load_case(path,h,b):
    protocol,raw=game(path,h,b)
    with closing(MPQArchive(path)) as a:
        data=a.read_file("replay.tracker.events")
    return protocol,raw,data,list(protocol.decode_replay_tracker_events(data))


def first_inputs(protocol,raw,setup,heroes,levels,trees):
    first={}
    for i,e in enumerate(protocol.decode_replay_game_events(raw)):
        if e["_eventid"]!=110:continue
        uid=e["_userid"]["m_userId"]
        if uid not in setup: continue
        _,player=setup[uid]
        if player in first or player not in heroes:continue
        spawn,hero=heroes[player]
        if hero not in trees:continue
        loop=e["_gameloop"]
        require(spawn<loop and any(t<loop and level>=1 for t,level in levels[player]),"No prior spawn/level")
        first[player]=(i,loop,uid,hero,e["m_index"])
    return first


def generate(cases,grey,kael,gamelib,signed,game_dir,prefix,output=None):
    trees, map_hash=read_trees(grey,kael,gamelib,signed)
    target=target_protocol()
    decoded_prefix=list(target.decode_replay_tracker_events(pinned(prefix,PREFIX)))
    projected_setup,projected_heroes,projected_levels=history(decoded_prefix)
    stream=pinned(game_dir/"game-inputs.private.bin",STREAM)
    ledger=json.loads(pinned(game_dir/"ordinals.private.json",LEDGER))
    inputs={}
    for rec,e in zip(ledger,target.decode_replay_game_events(stream),strict=True):
        ordinal,tick,kind,labels=rec
        require((tick,kind)==(e["_gameloop"],e["_eventid"]),"Input ledger differs")
        if TAG in labels:
            require(kind==110,"Unexpected admitted input");inputs[ordinal]=e
    controls=[]
    controls_seen=Counter()
    ten=None
    for file,h,b in verify_manifest(cases):
        if b==41810 and h!=SOURCE:continue
        p,raw,data,all_rows=load_case(Path(file),h,b)
        setup,heroes,levels=history(all_rows)
        first=first_inputs(p,raw,setup,heroes,levels,trees)
        physical=[]
        stats=[]
        for player,(ordinal,tick,uid,hero,original_index) in sorted(first.items(),key=lambda v:v[1][0]):
            if b==98348:
                ix=original_index
            elif ordinal in inputs:
                input_row=inputs[ordinal]
                require(input_row["_gameloop"]==tick and input_row["_userid"]["m_userId"]==uid,"Wrong input player/clock")
                require(projected_setup[uid][1]==player and projected_heroes[player][1]==hero and
                        any(t<tick and level>=1 for t,level in projected_levels[player]),"Signed opening identity or level differs")
                ix=input_row["m_index"]
            else: continue
            require(ix in trees[hero],"First selector outside verified tier")
            name=trees[hero][ix]
            stats.append(stat(tick+1,player,name))
            physical.append(dict(source_game_ordinal=ordinal,selection_loop=tick,player_id=player,hero=hero,
                                 original_index=original_index,projected_index=ix,computed_identifier=name))
            if b==98348:controls_seen[hero,ix]+=1
        ords=compare(stats,all_rows,data,target)
        for record,ordinal in zip(physical,ords):record["recorded_tracker_ordinal"]=ordinal
        if b==41810:
            require({r["source_game_ordinal"] for r in physical}==set(inputs) and len(stats)==3,"Unsupported or missing TEN row")
            ten=(stats,physical)
        else: controls.append(dict(sha256=h,awards=physical))
    stats,physical=ten
    for r in physical:
        require(controls_seen[r["hero"],r["projected_index"]]>0,"No independent native witness")
    wire=encode_tracker_events(stats,target)
    require([{k:v for k,v in r.items() if k!="_bits"} for r in target.decode_replay_tracker_events(wire)]==stats,"Roundtrip")
    if output:
        with output.open("xb") as f:f.write(wire)
    return dict(source_sha256=SOURCE,map_sha256=map_hash,ten=physical,target_count=len(stats),wire_bytes=len(wire),
                wire_sha256=sha256(wire).hexdigest(),checked_native_archives=len(controls),checked_native_awards=sum(controls_seen.values()),
                native_exact_hero_selectors={hero+":"+str(ix):v for (hero,ix),v in sorted(controls_seen.items())},
                approximate_or_missing_awards_admitted=0,target_runtime_verified=False,controls=sorted(controls,key=lambda r:r["sha256"]))


if __name__=="__main__":
    cli=ArgumentParser(description=__doc__)
    for name in ("manifest","grey","kael","gamelib","signed","game_dir","prefix"):
        cli.add_argument(name,type=Path)
    cli.add_argument("--output",type=Path)
    args=vars(cli.parse_args())
    print(json.dumps(generate(json.loads(args.pop("manifest").read_bytes()),**args),indent=2))
