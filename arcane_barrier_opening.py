"""Project the first Arcane Barrier purchase using the 98348 ability-behavior representation."""

import argparse
from contextlib import closing
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from build_extended_spikes_map import one, pinned, require
from combined_first_purchases import MAP
from encoders import encode_tracker_events
from initial_talent_tracker import HEROES, compare, first_inputs, history, load_case, stat
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE
from signed_game_input_map import digest
from verify_signed_tracker import frames

PREFIX = "ede0650626ad85cc22cddde0c08b93d3a88c2d8f3bb7abec80c779f0d58b8cfa"
CONTROLS = {
    "a3c97e9a669e73e4c2b19a8f6c5e2de0315cbc5725be82cf1e887ed6319a01c4",
    "afcf49a656068f343173fc79afff2d2ebf15066f531cb192382cdba9d1ea3272",
    "96d960545dca6a4ef027c41d8734cce36bc7bc14f9391352acc130e511eb1fef",
    "9faf99e38dae70f27fd2278318d851d57801df034764f7e408c7f363705abc3b",
}
ITEM = b"KaelthasArcaneBarrierItem"
TALENT = "KaelthasManaAddict"
ABILITY = "KaelthasArcaneBarrier"


def catalog(package,kael):
    pinned(package,MAP)
    xml=ET.fromstring(pinned(kael,HEROES["HeroKaelthas"]))
    talent=one(xml,f"CTalent[@id='{TALENT}']")
    require([r.attrib["value"] for r in one(talent,"RankArray")] ==
            ["KaelthasManaAddictQuestToken","KaelthasManaAddictManaRegen",ABILITY+"Ability"],
            "Unexpected rank grant")
    grant=one(xml,f"CBehaviorAbility[@id='{ABILITY}Ability']")
    require(one(grant,"Buttons").attrib==dict(Face=ABILITY,Type="AbilCmd",AbilCmd=ABILITY+",Execute"),
            "Different ability command")
    require(one(xml,f"CAbilEffectInstant[@id='{ABILITY}']/Cost/Cooldown").get("TimeUse")=="45",
            "Different cooldown")
    require(one(xml,"CAccumulatorToken[@id='KaelthasManaAddictAccumulator']/Scale").get("value")=="15",
            "Different mana per globe")
    cond=one(xml,"CBehaviorTokenCounter[@id='KaelthasManaAddictQuestToken']/ConditionalEvents")
    require(cond.get("Compare")=="GE" and cond.get("CompareValue")=="20" and
            one(cond,"Event").attrib==dict(EventId="QuestComplete",Effect=ABILITY+"ApplyUnlockingCarry"),
            "Different token reward")
    protected={TALENT,ABILITY,ABILITY+"Ability","KaelthasManaAddictQuestToken","HeroKaelthas","Kaelthas",
               ABILITY+"Item",ABILITY+"ApplyUnlockingCarry"}
    with closing(MPQArchive(package)) as arc:
        patches=[]
        for name in read_member(arc,"(listfile)").decode().splitlines():
            if not name.lower().startswith("base.stormdata"+chr(92)+"gamedata"+chr(92)) or not name.lower().endswith(".xml"):
                continue
            patches.extend(n for n in ET.fromstring(read_member(arc,name)) if n.get("id") in protected)
    require(len(patches)==2,"Unexpected map override of the ability or its owning hero")
    overrides={n.get("id"):n for n in patches}
    require(one(overrides[TALENT],"QuestData").attrib=={"TargetCount":"25"} and
            one(overrides["KaelthasManaAddictQuestToken"],"ConditionalEvents").attrib=={"index":"0","CompareValue":"25"},
            "Incorrect historical quest threshold")
    choices=one(xml,"CHero[@id='Kaelthas']").findall("TalentTreeArray")
    selector,=[i for i,n in enumerate(choices) if n.get("Talent")==TALENT and n.get("Tier")=="1"
               and n.get("Column")==str(i+1)]
    return selector


def generate(source,package,kael,prefix,game_dir,controls,output):
    selector=catalog(package,kael)
    src,raw,data,original=load_case(source,SOURCE,41810)
    setup,heroes,levels=history(original)
    picks=first_inputs(src,raw,setup,heroes,levels,{"HeroKaelthas":{}})
    require(sorted((p,row[0],row[-1]) for p,row in picks.items())==[(4,6214,2),(7,1536,2)],
            "Source Kael'thas owners differ")
    index,tick,uid,hero,old_index=picks[7]
    require([e["_eventid"] for e in original if 242<e["_gameloop"]<=355]==[1,10],"Original event interval changed")
    born=original[249]
    require((born["m_unitTypeName"],born["m_unitTagIndex"],born["m_unitTagRecycle"],
             born["m_controlPlayerId"],born["_gameloop"])==(ITEM,182,1,7,tick+1),"Wrong source inventory unit")
    award=stat(tick+1,7,TALENT)
    require(compare([award],original,data,src)==[250] and original[251]["_gameloop"]==365,
            "Wrong award or next source event")
    target=target_protocol()
    before=pinned(prefix,PREFIX)
    previous=frames(before,target)
    projected_setup,projected_heroes,projected_levels=history(e for e,*_ in previous)
    require(projected_setup[uid][1]==7 and projected_heroes[7][1]==hero and
            any(t<tick and level==1 for t,level in projected_levels[7]),"Target opening differs")
    keys=json.loads(pinned(game_dir/"ordinals.private.json","092ca220b8ee28eaab792942ca22e5a83f2c1c4e54c9e101ac7382aae0763829"))
    wire=pinned(game_dir/"game-inputs.private.bin","e2402f0360450c75909b865ff8114f0ac342c770b54175c7632b2b35d0acc9f2")
    choice,=[e for k,e in zip(keys,target.decode_replay_game_events(wire),strict=True) if k[0]==index]
    require((choice["_eventid"],choice["_gameloop"],choice["_userid"]["m_userId"],choice["m_index"])==
            (110,tick,uid,selector),"Wrong target input")
    cases=json.loads(controls.read_bytes())
    require({h for _,h in cases}==CONTROLS and len(cases)==len(CONTROLS),"Missing target witnesses")
    corroboration=[]
    for file,h in cases:
        p,g,tr,events=load_case(Path(file),h,98348)
        require(not any(e.get("m_unitTypeName")==ITEM for e in events),"Unexpected target item birth")
        expected=[]
        for player,r in first_inputs(p,g,*history(events),{"HeroKaelthas":{}}).items():
            if r[-1]==selector:expected.append(stat(r[1]+1,player,TALENT))
        require(expected,"Control has no corresponding purchase")
        ordinals=compare(expected,events,tr,target)
        corroboration.append(dict(sha256=h,awards=ordinals,item_births=0))
    result=before+encode_tracker_events([{**award,"_gameloop":tick+1-previous[-1][0]["_gameloop"]}],target)
    decoded=frames(result,target)
    require(len(decoded)==272 and decoded[-1][0]==award and
            encode_tracker_events([e for e,*_ in decoded],target)==result,"Wrong projected prefix")
    with output.open("xb") as f:f.write(result)
    return dict(map_sha256=MAP,source_sha256=SOURCE,controls=corroboration,
                source_only_birth=dict(ordinal=249,loop=355,player=7,unit=ITEM.decode(),tag_index=182,tag_recycle=1,
                                       replacement_behavior=ABILITY+"Ability",target_tracker_births=0),
                source_input_ordinal=index,source_award_ordinal=250,target_award_ordinal=len(decoded)-1,
                target_selector=selector,frames=len(decoded),bytes=len(result),sha256=digest(result),
                parent_prefix_sha256=PREFIX,last_loop=355,next_source_tracker_ordinal=251,next_loop=365,
                translated_player_4_activation_commands=0,target_unit_allocator_verified=False,
                target_simulation_verified=False,verified_target_syncs=0)


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ("source","package","kael","prefix","game_dir","controls","output"):
        cli.add_argument(name,type=Path)
    print(json.dumps(generate(**vars(cli.parse_args())),indent=2))
