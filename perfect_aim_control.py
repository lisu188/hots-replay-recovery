"""Check the first Perfect Aim choice and award in the native 98348 NGS control."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from encoders import encode_game_events, encode_tracker_events
from initial_talent_tracker import HEROES, first_inputs, history, load_case, pinned, require, stat
from mpq_reader import MPQArchive
from warpaint_control import frame

CONTROL = "9faf99e38dae70f27fd2278318d851d57801df034764f7e408c7f363705abc3b"
NAME = "GreymaneGilneanCocktailPerfectAim"
URL = ("https://s3.amazonaws.com/ngs-replay-storage/"
       "ngs_11-7-2026_Roll1Esports_vs_COSMOS_Infernal_Shrines.stormReplay")


def check(replay, catalog):
    hero = "HeroGreymane"
    doc = ET.fromstring(pinned(catalog,HEROES[hero]))
    tree, = doc.findall("CHero[@id='Greymane']")
    first = {i:n for i,n in enumerate(tree.findall("TalentTreeArray")) if n.get("Tier")=="1"}
    p,gm,tm,tr = load_case(replay,CONTROL,98348)
    with closing(MPQArchive(replay)) as arc:
        head=p.decode_replay_header(arc.header["user_data_header"]["content"])
        root=head["m_ngdpRootKey"]["m_data"].hex()
    require(root=="c3b3c8bc82e3a5a62e550fdde9a40c28","Different build root")
    setup,heroes,levels=history(tr)
    picks=first_inputs(p,gm,setup,heroes,levels,{hero:first})
    qualifying=[(pid,data) for pid,data in picks.items() if first[data[-1]].get("Talent")==NAME]
    (pid,(ordinal,tick,uid,_,idx)), = qualifying
    node=first[idx]
    require(node.attrib==dict(Talent=NAME,Tier="1",Column="2") and idx==1 and not len(node)
            and doc.find("CTalent[@id='"+NAME+"']/Abil").get("value")=="GreymaneGilneanCocktail",
            "Unexpected target catalog mapping")
    selection=dict(_event="NNet.Game.SHeroTalentTreeSelectedEvent",_eventid=110,_userid={"m_userId":uid},
                   _gameloop=tick,m_index=idx)
    g=frame(list(p.decode_replay_game_events(gm)),gm,ordinal,selection,encode_game_events,p)
    expected=stat(tick+1,pid,node.get("Talent"))
    k,=(i for i,r in enumerate(tr) if r.get("m_eventName")==b"TalentChosen" and r["_gameloop"]==tick+1 and
         {"m_key":b"PlayerID","m_value":pid} in r["m_intData"])
    a=frame(tr,tm,k,expected,encode_tracker_events,p)
    return dict(replay_sha256=CONTROL,replay_bytes=replay.stat().st_size,source_url=URL,data_root=root,build=98348,
                hero=hero,hero_xml_sha256=HEROES[hero],user=uid,player=pid,selector=idx,tier=1,column=2,
                award=NAME,input=g,tracker=a,game_member_sha256=sha256(gm).hexdigest(),
                tracker_member_sha256=sha256(tm).hexdigest(),independently_encoded_frames=2)


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("replay",type=Path)
    cli.add_argument("catalog",type=Path)
    args=cli.parse_args()
    print(json.dumps(check(args.replay,args.catalog),indent=2))
