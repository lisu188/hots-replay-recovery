"""Verify Sonya's native level-one War Paint choice and award in a pinned public 98348 replay."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from encoders import encode_game_events, encode_tracker_events
from initial_talent_tracker import first_inputs, history, load_case, pinned, require, stat
from mpq_reader import MPQArchive

ARCHIVE = "6987fe1729e6cc3afc272d1089c74d7ef001f5e340b60ac37610132586fb9939"
XML = "1e4bc827d905d70772f6e3cd06707b147fa2e8349e94ae9c659b6aa91a79444f"
URL = ("https://s3.amazonaws.com/ngs-replay-storage/"
       "ngs_10-15-2026_Bork_Side_of_the_Moon_vs_NO_CC_NO_PROBLEM_Infernal_Shrines.stormReplay")


def frame(events, raw, ordinal, expected, encoder, protocol):
    require(ordinal > 0 and all(r["_bits"] % 8 == 0 for r in events), "Invalid physical framing")
    before = events[ordinal-1]["_gameloop"]
    row = events[ordinal]
    offset = sum(r["_bits"]//8 for r in events[:ordinal])
    data = raw[offset:offset+row["_bits"]//8]
    delta = expected["_gameloop"]-before
    require({k:v for k,v in row.items() if k!="_bits"} == expected and
            data == encoder([{**expected,"_gameloop":delta}],protocol), "Physical row differs")
    return dict(ordinal=ordinal,tick=row["_gameloop"],previous_tick=before,delta=delta,offset=offset,
                bytes=len(data),sha256=sha256(data).hexdigest())


def check(replay, hero_xml):
    xml = ET.fromstring(pinned(hero_xml,XML))
    tree, = xml.findall("CHero[@id='Barbarian']")
    choices = tree.findall("TalentTreeArray")
    p, gm, tm, tr = load_case(replay,ARCHIVE,98348)
    with closing(MPQArchive(replay)) as a:
        head=p.decode_replay_header(a.header["user_data_header"]["content"])
        root=head["m_ngdpRootKey"]["m_data"].hex()
    require(root=="c3b3c8bc82e3a5a62e550fdde9a40c28", "Unexpected data root")
    setup, heroes, levels = history(tr)
    first = first_inputs(p,gm,setup,heroes,levels,{"HeroBarbarian":{}})
    (pid,(index,tick,uid,hero,selector)), = first.items()
    choice = choices[selector]
    name = choice.get("Talent")
    require((selector,choice.get("Tier"),choice.get("Column"),name)==(1,"1","2","BarbarianWarPaint") and
            xml.find(f"CTalent[@id='{name}']") is not None,"Selector does not identify War Paint")
    require(setup[uid][1]==pid and any(t<tick and v==1 for t,v in levels[pid]),"Different setup or level")
    selection = dict(_event="NNet.Game.SHeroTalentTreeSelectedEvent",_eventid=110,
                     _userid={"m_userId":uid},_gameloop=tick,m_index=selector)
    ga = list(p.decode_replay_game_events(gm))
    g=frame(ga,gm,index,selection,encode_game_events,p)
    expected = stat(tick+1,pid,name)
    ordinal, = (i for i,r in enumerate(tr) if r.get("m_eventName")==b"TalentChosen" and
                r["_gameloop"]==tick+1 and {"m_key":b"PlayerID","m_value":pid} in r["m_intData"])
    t=frame(tr,tm,ordinal,expected,encode_tracker_events,p)
    require((index,tick,uid,pid,ordinal)==(6098,973,9,10,483), "Unexpected native case")
    return dict(source_url=URL,replay_sha256=ARCHIVE,replay_bytes=replay.stat().st_size,build=98348,
        data_root=root,hero_xml_sha256=XML,hero=hero,user=uid,tracker_player=pid,selector=selector,tier=1,
        column=2,purchase=name,game_member_sha256=sha256(gm).hexdigest(),game=g,
        tracker_member_sha256=sha256(tm).hexdigest(),tracker=t,independently_encoded_frames=2,
        transfer_to_historical_replay_tested=False)


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("replay",type=Path)
    cli.add_argument("hero_xml",type=Path)
    a=cli.parse_args()
    print(json.dumps(check(a.replay,a.hero_xml),indent=2))
