"""Verify the conditional Unfurling Spray selector and tracker award against original and stock controls."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from build_extended_spikes_map import one,pinned,require
from build_gate_order_map import definition
from build_unfurling_spray import BRIGHT,HERO,TALENTS,VALIDATORS,EFFECTS,GATE,SEARCH,HEAL,FLARE,OLD
from encoders import encode_game_events,encode_tracker_events
from initial_talent_tracker import GAME,PREFIX,first_inputs,history,load_case,stat
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE
from warpaint_control import frame

MAP="bdf99d5bd9610774fe1758855f5c1f7981d9ef126e906cf06fd94177e1d3e72e"
COMBINED="13493e67e36594f908239dd0cce37fda0c0b386bbef385dcef22a83848f589d1"
OTHER="036e05a19255d42930ee561b3bfd07234d8d6e15fb87dd893798ff64d252acce"
STOCK="db40f495edb70b2127b97cae4f479de19e18e61b2a5a0e0413052b571e1dbf7e"


def check(source,other,stock,candidate,hero_xml,gamelib,prefix,output=None):
    map_hash=sha256(candidate.read_bytes()).hexdigest()
    require(map_hash in (MAP,COMBINED),"Unknown Brightwing package")
    tree=one(ET.fromstring(pinned(hero_xml,BRIGHT)),"CHero[@id='FaerieDragon']").findall("TalentTreeArray")
    with closing(MPQArchive(candidate)) as arc:
        data={k:ET.fromstring(read_member(arc,k)) for k in (HERO,TALENTS,EFFECTS,VALIDATORS)}
    change=one(data[HERO],"CHero[@id='FaerieDragon']/TalentTreeArray")
    require(change.attrib==dict(index="0",Talent=OLD) and set(tree[0].attrib)=={"Talent","Tier","Column"} and
            (tree[0].get("Tier"),tree[0].get("Column"))==("1","1"),"Opening override changed")
    name=change.get("Talent")
    talent=one(data[TALENTS],"CTalent[@id='"+name+"']")
    expected={("Effect",SEARCH),("Validator",GATE)}
    mods=talent.findall("AbilityModificationArray/Modifications")
    require(len(mods)==2 and {(one(m,"Catalog").get("value"),one(m,"Entry").get("value")) for m in mods}==expected and
            all(one(m,"Field").get("value")=="AreaArray[0].Radius" and one(m,"Value").get("value")=="2"
                and one(m,"Type").get("value")=="FlatModification" for m in mods),"Talent radius field references differ")
    require(one(data[VALIDATORS],"CValidatorLocationEnumArea[@id='"+GATE+"']/AreaArray[@index='0']/Radius").get("value")=="6"
            and one(data[EFFECTS],"CEffectEnumArea[@id='"+SEARCH+"']/AreaArray[@index='0']/Radius").get("value")=="6"
            and one(data[EFFECTS],"CEffectCreateHealer[@id='"+HEAL+"']/RechargeVitalRate").get("value")=="96"
            and one(data[EFFECTS],"CEffectSet[@id='"+FLARE+"']/EffectArray").attrib==dict(index="1",removed="1"),
            "Candidate numerical profile or Q edge changed")
    lib=pinned(gamelib,GAME).decode("utf-8-sig").replace("\r\n","\n")
    bind=definition(lib,"void","libGame_gf_TalentsSetupTalentChoicesFromHeroDataForPlayer")
    choose=definition(lib,"void","libGame_gf_TalentsChooseTalentForPlayer")
    apply=definition(lib,"void","libGame_gf_ApplyAbilityModificationsForPlayerAtTalent")
    require("lv_talentData[lv_column].lv_talentCatalogLink = (lv_talentID);" in bind and
            any('"PurchaseName"' in s and "lv_talentData[lp_buttonIndex].lv_talentCatalogLink" in s for s in choose.splitlines())
            and "CatalogFieldValueSetFixed(lv_catalog, lv_entry, lv_field, lp_player, lv_newValue);" in apply,
            "Unexpected native choice binding")
    target=target_protocol()
    pre=history(target.decode_replay_tracker_events(pinned(prefix,PREFIX)))
    cases=[]
    for path,h,b in ((source,SOURCE,41810),(other,OTHER,41810),(stock,STOCK,98348)):
        p,gm,tm,tr=load_case(path,h,b)
        setup,heroes,levels=history(tr)
        found=first_inputs(p,gm,setup,heroes,levels,{"HeroFaerieDragon":{}})
        (pid,(i,t,uid,_,ix)),=[x for x in found.items() if x[1][-1]==0]
        row=dict(_event="NNet.Game.SHeroTalentTreeSelectedEvent",_eventid=110,_gameloop=t,_userid={"m_userId":uid},m_index=ix)
        award=stat(t+1,pid,name if b==41810 else tree[ix].get("Talent"))
        j,=(j for j,r in enumerate(tr) if r.get("m_eventName")==b"TalentChosen" and r["_gameloop"]==t+1 and
            {"m_key":b"PlayerID","m_value":pid} in r["m_intData"])
        gs=list(p.decode_replay_game_events(gm))
        gcheck=frame(gs,gm,i,row,encode_game_events,target)
        tcheck=frame(tr,tm,j,award,encode_tracker_events,target)
        cases.append(dict(sha256=h,build=b,player=pid,user=uid,m_index=ix,game=gcheck,tracker=tcheck,
                          award=award["m_stringData"][0]["m_value"].decode(),
                          explicit_ability_inputs=sum(r["_userid"]["m_userId"]==uid and r["_eventid"]==27 and
                                                      r["m_abil"] is not None for r in gs),
                          named_mist_or_heal_stats=sorted({r["m_eventName"].decode() for r in tr if r.get("m_eventName")
                                and any(s in r["m_eventName"].lower() for s in (b"heal",b"mist"))})))
        if h==SOURCE:
            require((i,j,t)==(914,246,148) and pre[0][uid][1]==pid and pre[1][pid][1]=="HeroFaerieDragon" and
                    any(loop<t and lv==1 for loop,lv in pre[2][pid]),"Different original award or startup")
            g=encode_game_events([row],target)
            s=encode_tracker_events([award],target)
            for blob,decoder,wanted in ((g,target.decode_replay_game_events,row),(s,target.decode_replay_tracker_events,award)):
                decoded,=decoder(blob)
                require(decoded.pop("_bits")==len(blob)*8 and decoded==wanted,"Target round trip differs")
    if output:
        output.mkdir()
        (output/"choice.game.private.bin").write_bytes(g)
        (output/"award.tracker.private.bin").write_bytes(s)
    return dict(map_sha256=map_hash,opening_prefix_sha256=PREFIX,cases=cases,game_bytes=len(g),game_sha256=sha256(g).hexdigest(),
                tracker_bytes=len(s),tracker_sha256=sha256(s).hexdigest(),historical_base_radius_proven=False,
                exact_source_recipient_state_verified=False,effective_target_simulation_verified=False)


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ("source","other","stock","candidate","hero_xml","gamelib","prefix"):
        cli.add_argument(name,type=Path)
    cli.add_argument("--output",type=Path)
    print(json.dumps(check(**vars(cli.parse_args())),indent=2))
