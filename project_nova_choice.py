"""Project TEN's first Nova selection and award for the opt-in intended-rule map."""
import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from build_gate_order_map import definition
from build_nova_intended_map import NOVA, PREFIX, RULE, need, pinned
from encoders import encode_game_events, encode_tracker_events
from initial_talent_tracker import GAME, compare, first_inputs, history, load_case, stat
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE
from symbolic_command_starts import references

CANDIDATE="8b0cdec389be8a7cc52b438e9798af5903158a59a426d9ab3e08f166e791fd8f"
COMBINED="13493e67e36594f908239dd0cce37fda0c0b386bbef385dcef22a83848f589d1"


def catalog(candidate, nova, gamelib):
    map_digest=sha256(candidate.read_bytes()).hexdigest()
    need(map_digest in (CANDIDATE,COMBINED),"Unexpected map")
    stock=ET.fromstring(pinned(nova,NOVA))
    with closing(MPQArchive(candidate)) as mpq:
        hero=ET.fromstring(read_member(mpq,r"Base.StormData\GameData\HeroData.xml"))
        talent=ET.fromstring(read_member(mpq,r"Base.StormData\GameData\TalentData.xml"))
    base=[r.attrib for r in stock.findall("CHero[@id='Nova']/TalentTreeArray")]
    after=base.copy()
    for row in hero.findall("CHero[@id='Nova']/TalentTreeArray"):
        value=dict(row.attrib)
        i=int(value.pop("index"))
        if i == len(after):
            after.append(value)
        else:
            after[i]=value
    need(after[:3] == base[:3] and after[3] == dict(Talent=RULE,Tier="1",Column="4")
         and after[4:] == base[3:], "Effective Nova indices")
    choice,=talent.findall(f"CTalent[@id='{RULE}']")
    need(choice.find("Face").get("value")==PREFIX+"Button" and choice.find("RankArray") is not None,"Talent record")
    g=pinned(gamelib,GAME).decode("utf-8-sig").replace("\r\n","\n")
    setup=definition(g,"void","libGame_gf_TalentsSetupTalentChoicesFromHeroDataForPlayer")
    for field in ("Tier","Talent","Column"):
        need('"TalentTreeArray[" + IntToString((lv_itTalent - 1)) + "].'+field+'"' in setup,"Field read")
    choose=definition(g,"void","libGame_gf_TalentsChooseTalentForPlayer")
    need('StatEventCreate("TalentChosen")' in choose and any('"PurchaseName"' in line and
         "lv_talentData[lp_buttonIndex].lv_talentCatalogLink" in line for line in choose.splitlines()),"Award emitter")
    return base,after,map_digest


def first_choice(path,digest,build,tree,target):
    p,game,tracker,rows=load_case(path,digest,build)
    setup,heroes,levels=history(rows)
    first=first_inputs(p,game,setup,heroes,levels,{"HeroNova":tree})
    results=[]
    for player,(ordinal,tick,user,_,index) in first.items():
        cell=tree[index]
        need(cell["Tier"]=="1","First Nova selection fell outside the first tier")
        if build==41810 and cell["Talent"]!=RULE:
            continue
        want=dict(_event="NNet.Game.SHeroTalentTreeSelectedEvent",_eventid=110,_userid={"m_userId":user},_gameloop=tick,m_index=index)
        before=offset=0
        for i,e in enumerate(p.decode_replay_game_events(game)):
            size,rem=divmod(e["_bits"],8)
            need(not rem and size>0,"Input alignment")
            if i==ordinal:
                need(want=={k:v for k,v in e.items() if k!="_bits"},"Unexpected selection frame")
                row={**want,"_gameloop":tick-before}
                need(encode_game_events([row],target)==game[offset:offset+size],"Physical issue bytes")
                break
            before=e["_gameloop"]
            offset+=size
        award=stat(tick+1,player,cell["Talent"])
        tracker_ordinal,=compare([award],rows,tracker,target)
        results.append((want,award,dict(digest=digest,build=build,selection_ordinal=ordinal,
            selection_loop=tick,award_ordinal=tracker_ordinal,award_loop=tick+1,selector=index,
            tier=1,column=int(cell["Column"]),talent=cell["Talent"])))
    return results


def run(source,candidate,nova,gamelib,refs,output=None):
    base,modified,map_digest=catalog(candidate,nova,gamelib)
    target=target_protocol()
    (game,award,detail),=first_choice(source,SOURCE,41810,modified,target)
    need((detail["selection_ordinal"],detail["award_ordinal"],detail["selection_loop"],detail["award_loop"])==
         (844,245,133,134),"Unexpected original selection/award pair")
    g=encode_game_events([game],target)
    a=encode_tracker_events([award],target)
    witnesses=[]
    for path,digest,build in references(json.loads(refs.read_bytes())):
        if build in (41810,98348):
            tree=modified if build==41810 else base
            for _,_,rec in first_choice(path,digest,build,tree,target):
                witnesses.append(rec)
    need(any(w["build"]==41810 and w["talent"]==RULE for w in witnesses),"Missing independent old award")
    need(any(w["build"]==98348 for w in witnesses),"Missing genuine retail Nova award")
    if output:
        output.mkdir()
        (output/"nova.game.private.bin").write_bytes(g)
        (output/"nova.tracker.private.bin").write_bytes(a)
    return dict(candidate_sha256=map_digest,ten=detail,witnesses=witnesses,
        standalone_input=dict(bytes=len(g),sha256=sha256(g).hexdigest()),
        standalone_award=dict(bytes=len(a),sha256=sha256(a).hexdigest()),
        native_delivery_verified=False,exact_41810_rules_verified=False,scope="conditional_intended_rule")


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ("source","candidate","nova","gamelib","refs"):
        cli.add_argument(name,type=Path)
    cli.add_argument("--output",type=Path)
    print(json.dumps(run(**vars(cli.parse_args())),indent=2))
