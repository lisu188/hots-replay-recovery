"""Build a separate Brightwing historical aura hypothesis on the pinned PerfectAim map."""

import argparse
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET

from build_dragonshire_talent_map import EMPTY_CATALOG, TALENTS, digest, inventory
from build_extended_spikes_map import HERO, HISTORICAL, one, pinned, require
from runtime_catalog_probe import Storm

PARENT="9c223f3e4d9fb31324126b91f7e51048dd6c011ac0d4dcdf6f582e2978f92870"
BRIGHT="0331a785983525abcbd58d95159ce4b12d8652c8a7294967e1231b30f5053064"
OLD="BrightwingUnfurlingSpraySoothingMist"
SEARCH="BrightwingSoothingMistSearchArea"
GATE="BrightwingSoothingMistNoInjuredAllyNearbyProximity"
HEAL="BrightwingSoothingMistCreateHealer"
FLARE="BrightwingArcaneFlareInnerHeroImpactSet"
FACE="TenGreymaneUnfurlingSpray"
BASE="Base.StormData\\GameData\\"
EFFECTS=BASE+"EffectData.xml"
VALIDATORS=BASE+"ValidatorData.xml"
BUTTONS=BASE+"ButtonData.xml"
STRINGS="enUS.StormData\\LocalizedData\\GameStrings.txt"


def add(n,field,value):
    return ET.SubElement(n,field,value=str(value))


def value(n,field):
    return one(n,field).attrib["value"]


def edits(members, historical, modern):
    old,=(h for h in json.loads(historical) if h["id"]=="FaerieDragon")
    choice=old["talents"]["1"][0]
    require(choice==dict(id=OLD,name="Unfurling Spray",description="Increases Soothing Mist's range by 33.3%.",
                         icon="storm_ui_icon_brightwing_soothingmist.dds"),"Unexpected 41810 choice")
    passive,=(a for rows in old["abilities"].values() for a in rows if a["id"]=="BrightwingSoothingMist")
    require(passive["description"]=="Brightwing heals nearby allied Heroes for 96 (+0.04 per level) every 4 seconds.",
            "Historical baseline changed")
    doc=ET.fromstring(modern)
    def entry(kind,name):
        return one(doc,kind+"[@id='"+name+"']")
    current=entry("CHero","FaerieDragon").findall("TalentTreeArray")
    require(current[0].attrib=={"Talent":"BrightwingGreaterPolymorphPolymorph","Tier":"1","Column":"1"} and
            not any(v.get("Talent")==OLD for v in current),"Unexpected target tree")
    require(not doc.findall("CTalent[@id='"+OLD+"']") and
            value(entry("CBehaviorBuff","BrightwingSoothingMistCooldown"),"Duration")=="4" and
            one(entry("CAbilEffectInstant","BrightwingSoothingMistDummyCooldown"),"Cost/Cooldown").get("TimeUse")=="4",
            "Different passive cycle")
    require(value(entry("CEffectCreateHealer",HEAL),"RechargeVitalRate")=="110" and
            value(entry("CEffectEnumArea",SEARCH),"AreaArray/Radius")=="7" and
            value(entry("CValidatorLocationEnumArea",GATE),"AreaArray/Radius")=="7","Different stock aura")
    require(value(entry("CEffectSwitch","BrightwingSoothingMistRangeSwitch"),"CaseDefault")=="BrightwingSoothingMistActiveApplyBehavior"
            and value(entry("CEffectApplyBehavior","BrightwingSoothingMistActiveApplyBehavior"),"Behavior")=="BrightwingSoothingMistActive"
            and value(entry("CBehaviorBuff","BrightwingSoothingMistActive"),"RemoveValidatorArray")=="BrightwingSoothingMistCombineValidator"
            and GATE in [n.get("value") for n in entry("CValidatorCombine","BrightwingSoothingMistCombineValidator").findall("CombineArray")],
            "Different ordinary injury gate")
    require([n.get("value") for n in entry("CEffectSet",FLARE).findall("EffectArray")]==
            ["BrightwingArcaneFlareAddToken",SEARCH,"BrightwingArcaneFlareDreamShotInnerDelayPersistent"],"Different Q edge")
    require(SEARCH in [n.get("value") for n in entry("CEffectSet","BrightwingSoothingMistSearchSet").findall("EffectArray")]
            and HEAL in [n.get("value") for n in entry("CEffectSet","BrightwingSoothingMistImpactSet").findall("EffectArray")],
            "Invalid passive connection")
    icon=value(entry("CButton","BrightwingSoothingMist"),"Icon")
    require(icon.rsplit(chr(92),1)[-1].lower()==choice["icon"],"Source and target trait icon differ")
    guarded={OLD,FACE,"FaerieDragon",HEAL,SEARCH,FLARE,GATE}
    for k,member in members.items():
        if k.startswith(BASE) and k.endswith(".xml"):
            require(all(n.get("id") not in guarded for n in ET.fromstring(member)),"Unexpected parent override")

    hero=ET.Element("CHero",id="FaerieDragon")
    ET.SubElement(hero,"TalentTreeArray",index="0",Talent=OLD)
    talent=ET.Element("CTalent",id=OLD)
    add(talent,"Face",FACE)
    group=ET.SubElement(talent,"AbilityModificationArray")
    for cat,name in (("Effect",SEARCH),("Validator",GATE)):
        m=ET.SubElement(group,"Modifications")
        for k,v in (("Type","FlatModification"),("Catalog",cat),("Entry",name),("Field","AreaArray[0].Radius"),("Value","2")):
            add(m,k,v)
    effect=ET.Element("CEffectEnumArea",id=SEARCH)
    add(ET.SubElement(effect,"AreaArray",index="0"),"Radius",6)
    gate=ET.Element("CValidatorLocationEnumArea",id=GATE)
    add(ET.SubElement(gate,"AreaArray",index="0"),"Radius",6)
    heal=ET.Element("CEffectCreateHealer",id=HEAL)
    add(heal,"RechargeVitalRate",96)
    q=ET.Element("CEffectSet",id=FLARE)
    ET.SubElement(q,"EffectArray",index="1",removed="1")
    button=ET.Element("CButton",id=FACE,parent="StormButtonParent")
    add(button,"Icon",icon)
    strings=[]
    for field,text in (("Name",choice["name"]),("Tooltip",choice["description"])):
        key="Button/"+field+"/"+FACE
        add(button,field,key)
        strings.append((key+"="+text+"\r\n").encode("ascii"))
    result={}
    for k,nodes in ((HERO,[hero]),(TALENTS,[talent]),(EFFECTS,[effect,heal,q]),(VALIDATORS,[gate]),(BUTTONS,[button])):
        raw=members.get(k,EMPTY_CATALOG)
        require(raw.count(b"</Catalog>")==1,"Unexpected catalog shape")
        block=b"".join(ET.tostring(n,encoding="ascii",xml_declaration=False)+b"\r\n" for n in nodes)
        result[k]=raw.replace(b"</Catalog>",block+b"</Catalog>")
    localized=members[STRINGS]
    require(FACE.encode() not in localized,"Duplicate localization")
    result[STRINGS]=localized+(b"" if localized.endswith(b"\n") else b"\r\n")+b"".join(strings)
    return result


def build(parent,historical,modern,output,stormlib=None):
    require(not output.exists() and not output.is_symlink(),"Fresh output path required")
    raw=pinned(parent,PARENT)
    storm=Storm(stormlib)
    before,pc=inventory(parent,storm)
    override=edits(before,pinned(historical,HISTORICAL),pinned(modern,BRIGHT))
    with TemporaryDirectory(dir=output.parent) as temp:
        working=Path(temp)/"map.s2ma"
        working.write_bytes(raw)
        storm.replace(working,override)
        after,ac=inventory(working,storm)
        require(after=={**before,**override} and raw==parent.read_bytes(),"Other map members changed")
        result=working.read_bytes()
        os.link(working,output)
    return dict(parent_sha256=PARENT,candidate_sha256=digest(result),candidate_bytes=len(result),
               historical_source_sha256=HISTORICAL,stock_xml_sha256=BRIGHT,
               parent_checks=pc,candidate_checks=ac,changed_or_added={k:digest(v) for k,v in sorted(override.items())},
               unchanged_parent_members=len(before.keys()-override.keys()),source_selector=0,target_selector=0,
               player_scoped_ordinary_radius_model=[6,8],historical_absolute_radius_independently_measured=False,
               recorded_41810_relative_bonus_percent_text="33.3",source_baseline_heal=96,passive_duration_seconds=4,
               native_effective_per_player_validator_verified=False,exact_healing_targets_and_ticks_verified=False,
               effective_runtime=False)


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ("parent","historical","modern","output"):
        cli.add_argument(name,type=Path)
    cli.add_argument("--stormlib")
    print(json.dumps(build(**vars(cli.parse_args())),indent=2))
