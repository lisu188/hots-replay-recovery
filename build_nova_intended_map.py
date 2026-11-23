"""Build the opt-in intended 41810 Nova Covert Ops rule on the PerfectAim map."""
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET

from build_dragonshire_talent_map import digest, inventory
from runtime_catalog_probe import Storm

PARENT = "9c223f3e4d9fb31324126b91f7e51048dd6c011ac0d4dcdf6f582e2978f92870"
NOVA = "721086138a01ff65659616556ea617c85f968d8bd28ec888fa6397bde0ce113a"
SONYA = "1e4bc827d905d70772f6e3cd06707b147fa2e8349e94ae9c659b6aa91a79444f"
ABATHUR = "b2ecee56c24e3a6e62c904f066f858dd5fb9fa144c2e17af423320efaf9c69e1"
HISTORICAL = "aaf264de6c3e31ce4bee1b1a5d658d695036393e4077e539630dd553698e9bbb"
RULE = "NovaMasteryCovertOpsPinningShot"
PREFIX = "TEN41810NovaCovertOps"
EMPTY = b'<?xml version="1.0" encoding="us-ascii"?>\r\n<Catalog>\r\n</Catalog>\r\n'


def need(value, message):
    if not value:
        raise ValueError(message)


def pinned(path, expected):
    data = path.read_bytes()
    need(digest(data) == expected, "Unexpected input " + path.name)
    return data


def node(parent, tag, **fields):
    return ET.SubElement(parent, tag, fields)


def value(parent, tag, val):
    return node(parent, tag, value=str(val))


def check_stock(nova, sonya, abathur, old):
    def attr(xml, expr, key="value"):
        (item,) = xml.findall(expr)
        return item.get(key)
    direct = [t.attrib for t in nova.findall("CHero[@id='Nova']/TalentTreeArray")]
    need(direct[:3] == [dict(Talent=t,Tier="1",Column=str(i)) for i,t in enumerate(
        ("NovaMasteryLongshot","NovaCovertOps","NovaAdvancedCloaking"),1)] and
        all("index" not in t and int(t["Tier"])>1 for t in direct[3:]), "Unexpected stock talent array")
    entry, = (x for x in old if x["id"] == "Nova")
    need(entry["talents"]["1"][3]["id"] == RULE and len(entry["talents"]["1"]) == 4, "Historical slot")
    w, = (x for x in entry["abilities"]["Nova"] if x["id"] == "NovaPinningShot")
    need(w["manaCost"] == 65 and w["cooldown"] == 12, "Historical input cost")
    for path, expected in {
        "CAbilEffectTarget[@id='NovaPinningShot']/Cost/Vital[@index='Energy']":"65",
        "CBehaviorBuff[@id='NovaPermanentCloak']/Period":"0.0625",
        "CBehaviorBuff[@id='NovaPermanentCloak']/PeriodicEffect":"NovaPinningShotCovertOpsApplyTimerBehavior",
        "CBehaviorBuff[@id='PinningShotSlow']/Modification/UnifiedMoveSpeedFactor":"-0.4",
        "CBehaviorBuff[@id='PinningShotSlow']/Duration":"2.25",
        "CBehaviorBuff[@id='NovaPinningShotCovertOpsTimer']/Duration":"2",
        "CBehaviorBuff[@id='NovaPinningShotCovertOpsActiveTimed']/Duration":"1",
        "CEffectLaunchMissile[@id='PinningShotLaunchMissile']/LaunchEffect":"NovaPinningShotMissileLaunchSet",
        "CEffectSet[@id='NovaPinningShotMissileLaunchSet']/EffectArray":"NovaPinningShotCovertOpsApplyMissileMarkerBehavior",
        "CEffectSwitch[@id='PinningShotImpactSwitch']/CaseDefault":"NovaPinningShotSlowSwitch",
        "CEffectSwitch[@id='NovaPinningShotSlowSwitch']/CaseDefault":"NovaPinningShotApplySlow",
    }.items():
        need(attr(nova,path)==expected, "Stock path " + path)
    need(attr(nova,"CEffectApplyBehavior[@id='NovaPinningShotCovertOpsApplyMissileMarkerBehavior']/WhichUnit","Value")=="Source"
         and attr(nova,"CValidatorUnitCompareBehaviorCount[@id='NovaPinningShotCovertOpsSourceHasMissileMarker']/WhichUnit","Value")=="Source",
         "Stock launch and impact marker unit")
    need(attr(sonya,"CBehaviorBuff[@id='BarbarianToughAsNailsChargedArmorBehavior']/MaxStackCount")=="3"
         and attr(abathur,"CEffectRemoveBehavior[@id='DeepTunnelRemoveDisablerBehavior']/Count")=="1",
         "Stack and removal exemplars")
    return direct


def records(nova, tree):
    by_kind = defaultdict(list)
    def record(tag, name, **attrs):
        entry=ET.Element(tag,id=name,**attrs)
        kind=next(s for s in ("Hero","Talent","Behavior","Effect","Validator","Button") if tag.startswith("C"+s))
        by_kind[kind].append(entry)
        return entry
    def private(tag, suffix, **attrs):
        return record(tag,PREFIX+suffix,**attrs)
    def buff(suffix):
        item=private("CBehaviorBuff",suffix)
        node(item,"InfoFlags",index="Hidden",value="1")
        return item
    def apply(suffix, behavior, which="Caster", validators=()):
        item=private("CEffectApplyBehavior",suffix)
        node(item,"WhichUnit",Value=which)
        value(item,"Behavior",PREFIX+behavior)
        for validator in validators:
            value(item,"ValidatorArray",validator)
        return item
    def count_check(suffix, behavior, which, n, compare="Eq"):
        item=private("CValidatorUnitCompareBehaviorCount",suffix)
        node(item,"WhichUnit",Value=which)
        value(item,"Behavior",PREFIX+behavior)
        value(item,"Compare",compare)
        value(item,"Value",n)
    def remove(suffix, behavior, n):
        item=private("CEffectRemoveBehavior",suffix)
        node(item,"WhichUnit",Value="Caster")
        value(item,"BehaviorLink",PREFIX+behavior)
        value(item,"Count",n)
    hero=record("CHero","Nova")
    node(hero,"TalentTreeArray",index="3",Talent=RULE,Tier="1",Column="4")
    for i,row in enumerate(tree[3:],4):
        node(hero,"TalentTreeArray",index=str(i),**row)
    talent=record("CTalent",RULE)
    value(talent,"Face",PREFIX+"Button")
    value(talent,"Abil","NovaPinningShot")
    node(talent,"RankArray")
    button=private("CButton","Button",parent="StormButtonParent")
    value(button,"Icon",r"Assets\Textures\storm_ui_icon_nova_pinningshot_var1.dds")
    value(button,"Name","Button/Name/NovaCovertOpsTalent")
    value(button,"Tooltip","Button/Tooltip/"+PREFIX+"Button")
    spell_button=record("CButton","NovaPinningShot")
    node(spell_button,"TooltipAppender",index="4",Validator=PREFIX+"HasTalent",Face=PREFIX+"Button")
    # The standard cloak's own active-period callback starts the driver after purchase.
    has=private("CValidatorPlayerTalent","HasTalent")
    node(has,"WhichPlayer",Value="Caster")
    value(has,"Find",1)
    value(has,"Value",RULE)
    actual=private("CValidatorUnitType","CasterIsHeroNova")
    node(actual,"WhichUnit",Value="Caster")
    value(actual,"Find",1)
    value(actual,"Value","HeroNova")
    count_check("NoDriver","Driver","Caster",0)
    count_check("BelowCap","Stacks","Caster",10,"LT")
    cloak=record("CBehaviorBuff","NovaPermanentCloak")
    value(cloak,"PeriodicEffect",PREFIX+"CloakPoll")
    poll=private("CEffectSet","CloakPoll")
    value(poll,"EffectArray","NovaPinningShotCovertOpsApplyTimerBehavior")
    value(poll,"EffectArray",PREFIX+"StartDriver")
    gate=(PREFIX+"HasTalent",PREFIX+"CasterIsHeroNova","CasterIsCloaked",PREFIX+"NoDriver")
    apply("StartDriver","Driver",validators=gate)
    driver=buff("Driver")
    value(driver,"RemoveValidatorArray","CasterIsCloaked")
    value(driver,"RemoveValidatorArray",PREFIX+"HasTalent")
    value(driver,"InitialEffect",PREFIX+"CancelGrace")
    value(driver,"Period",1)
    value(driver,"PeriodicEffect",PREFIX+"AddStack")
    value(driver,"FinalEffect",PREFIX+"StartGrace")
    stacks=buff("Stacks")
    value(stacks,"MaxStackCount",10)
    apply("AddStack","Stacks",validators=(PREFIX+"BelowCap",PREFIX+"HasTalent","CasterIsCloaked"))
    grace=buff("Grace")
    value(grace,"Duration",1)
    value(grace,"ExpireEffect",PREFIX+"ClearStacks")
    apply("StartGrace","Grace")
    remove("CancelGrace","Grace",1)
    remove("ClearStacks","Stacks",10)
    launch=record("CEffectSet","NovaPinningShotMissileLaunchSet")
    node(launch,"EffectArray",index="1",value=PREFIX+"MarkMissile")
    switch=private("CEffectSwitch","MarkMissile")
    value(switch,"ValidatorArray",PREFIX+"HasTalent")
    value(switch,"ValidatorArray",PREFIX+"CasterIsHeroNova")
    impact=record("CEffectSwitch","NovaPinningShotSlowSwitch")
    for level in range(1,11):
        n=str(level)
        count_check("CasterStacks"+n,"Stacks","Caster",level)
        node(switch,"CaseArray",Validator=PREFIX+"CasterStacks"+n,Effect=PREFIX+"Mark"+n)
        buff("Missile"+n)
        apply("Mark"+n,"Missile"+n,which="Source")
        count_check("SourceMarker"+n,"Missile"+n,"Source",0,"GT")
        node(impact,"CaseArray",index=n,Validator=PREFIX+"SourceMarker"+n,Effect=PREFIX+"ApplySlow"+n)
        slow=private("CBehaviorBuff","Slow"+n,parent="StormSlowParent")
        value(slow,"Duration","2.25")
        value(node(slow,"Modification"),"UnifiedMoveSpeedFactor",f"-0.{40+2*level}")
        applied=private("CEffectApplyBehavior","ApplySlow"+n,parent="StormSlowApply")
        value(applied,"Behavior",PREFIX+"Slow"+n)
    return by_kind


def prepare(before, nova, sonya, abathur, old):
    tree=check_stock(nova,sonya,abathur,old)
    parts=records(nova,tree)
    edits={}
    for kind, entries in parts.items():
        member=rf"Base.StormData\GameData\{kind}Data.xml"
        initial=before.get(member,EMPTY)
        indices={e.get("id") for e in ET.fromstring(initial)}
        ids=[e.get("id") for e in entries]
        need(len(ids)==len(set(ids)) and not indices.intersection(ids), "Overlapping map declaration")
        need(initial.count(b"</Catalog>")==1,"Unexpected catalog root")
        addition=b"".join(ET.tostring(e,encoding="us-ascii",xml_declaration=False)+b"\r\n" for e in entries)
        edits[member]=initial.replace(b"</Catalog>",addition+b"</Catalog>")
        ET.fromstring(edits[member])
    localized={
        "enUS": "Each second Nova is Cloaked adds 2 percentage points to Pinning Shot's Slow, up to 60%. The bonus lasts for 1 second after Nova loses Cloak.",
        "plPL": "Każda sekunda ukrycia zwiększa spowolnienie od Spowalniającego Strzału o 2 punkty procentowe, maksymalnie do 60%. Premia utrzymuje się przez 1 sekundę po wyjściu z ukrycia.",
    }
    for locale, text in localized.items():
        member=rf"{locale}.StormData\LocalizedData\GameStrings.txt"
        old=before[member]
        key=("Button/Tooltip/"+PREFIX+"Button=").encode()
        need(key not in old,"Unexpected tooltip collision")
        sep=b"\r\n" if b"\r\n" in old else b"\n"
        edits[member]=old+(b"" if old.endswith(b"\n") else sep)+key+text.encode()+sep
    return edits


def build(parent,nova,sonya,abathur,historical,output,stormlib):
    original=pinned(parent,PARENT)
    need(not output.exists() and not output.is_symlink(),"Fresh output required")
    storm=Storm(stormlib)
    before,_=inventory(parent,storm)
    edits=prepare(before,ET.fromstring(pinned(nova,NOVA)),ET.fromstring(pinned(sonya,SONYA)),
                  ET.fromstring(pinned(abathur,ABATHUR)),json.loads(pinned(historical,HISTORICAL)))
    with TemporaryDirectory(dir=output.parent) as folder:
        copy=Path(folder)/"candidate.s2ma"
        copy.write_bytes(original)
        storm.replace(copy,edits)
        after,checks=inventory(copy,storm)
        need(after=={**before,**edits} and parent.read_bytes()==original, "Archive content mismatch")
        data=copy.read_bytes()
        os.link(copy,output)
    return dict(parent_sha256=PARENT,candidate_sha256=digest(data),candidate_bytes=len(data),
                catalogs={n:digest(d) for n,d in edits.items()},new_members=sorted(after.keys()-before.keys()),
                archive_content_members=len(after),target_tier=1,target_column=4,target_selector=3,
                movement_slow_percent=list(range(40,61,2)),mana=65,grace_seconds=1,target_slow_seconds=2.25,
                native_catalog_loading_verified=False,exact_41810_behavior_verified=False,scope="opt_in_intended_rule")


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ("parent","nova","sonya","abathur","historical","output"):
        cli.add_argument(name,type=Path)
    cli.add_argument("--stormlib",required=True)
    print(json.dumps(build(**vars(cli.parse_args())),indent=2))
