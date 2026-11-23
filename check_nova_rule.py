"""Exercise the map's generated effect graph in a small explicit catalog interpreter."""
import argparse
from contextlib import closing
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from build_nova_intended_map import NOVA, PREFIX, RULE, need, pinned
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from project_nova_choice import CANDIDATE,COMBINED


class Model:
    def __init__(self,defs,*,talent=True,hero="HeroNova"):
        self.defs=defs
        self.talent=talent
        self.hero=hero
        self.cloaked=False
        self.t=0
        self.units={"Caster":{}, "Target":{}, "Source":{}}

    def check(self,name):
        if name=="CasterIsCloaked":
            return self.cloaked
        if name=="CasterIsNotNovaHoloClone":
            return self.hero!="NovaHoloClone"
        if name=="NovaPinningShotCovertOpsSourceHasMissileMarker":
            return False
        v=self.defs[name]
        val=v.find("Value").get("value")
        if v.tag=="CValidatorPlayerTalent":
            return self.talent and val==RULE
        if v.tag=="CValidatorUnitType":
            return self.hero==val
        need(v.tag=="CValidatorUnitCompareBehaviorCount","Unexpected validator")
        unit=v.find("WhichUnit").get("Value")
        ct=self.units[unit].get(v.find("Behavior").get("value"),(0,0))[0]
        cmp=v.find("Compare").get("value")
        return {"Eq":ct==int(val),"LT":ct<int(val),"GT":ct>int(val)}[cmp]

    def fire(self,name):
        if name=="NovaPinningShotCovertOpsApplyTimerBehavior" or name=="NovaPinningShotCovertOpsApplyMissileMarkerBehavior":
            need(self.defs[name].find("Chance").get("value")=="0","Modern effect unexpectedly active")
            return
        e=self.defs[name]
        if not all(self.check(v.get("value")) for v in e.findall("ValidatorArray")):
            return
        if e.tag=="CEffectSet":
            for x in e.findall("EffectArray"):
                self.fire(x.get("value"))
        elif e.tag=="CEffectSwitch":
            for x in e.findall("CaseArray"):
                if self.check(x.get("Validator")):
                    self.fire(x.get("Effect"))
                    return
            self.trigger(e,"CaseDefault")
        elif e.tag=="CEffectApplyBehavior":
            link=e.find("Behavior").get("value")
            b=self.defs[link]
            unit=e.find("WhichUnit")
            holder=self.units[unit.get("Value") if unit is not None else "Target"]
            cap=int(b.find("MaxStackCount").get("value")) if b.find("MaxStackCount") is not None else 1
            previous=holder.get(link,(0,0))[0]
            holder[link]=(min(cap,previous+1),self.t)
            if not previous:
                self.trigger(b,"InitialEffect")
        elif e.tag=="CEffectRemoveBehavior":
            holder=self.units[e.find("WhichUnit").get("Value")]
            link=e.find("BehaviorLink").get("value")
            if link in holder:
                ct,then=holder[link]
                remaining=ct-int(e.find("Count").get("value"))
                if remaining>0: holder[link]=(remaining,then)
                else:
                    del holder[link]
                    self.trigger(self.defs[link],"FinalEffect")
        else:
            raise ValueError(e.tag)

    def trigger(self, node, field):
        child=node.find(field)
        if child is not None:
            self.fire(child.get("value"))

    def tick(self,cloaked,advance=1):
        for _ in range(advance):
            self.cloaked=cloaked
            self.t+=1
            if cloaked:
                self.fire(self.defs["NovaPermanentCloak"].find("PeriodicEffect").get("value"))
            caster=self.units["Caster"]
            for link,(count,since) in list(caster.items()):
                if link not in caster: continue
                b=self.defs[link]
                if not all(self.check(x.get("value")) for x in b.findall("RemoveValidatorArray")):
                    del caster[link]
                    self.trigger(b,"FinalEffect")
                    continue
                age=self.t-since
                duration=b.find("Duration")
                if duration is not None and age>=Decimal(duration.get("value"))*16:
                    del caster[link]
                    self.trigger(b,"ExpireEffect")
                    self.trigger(b,"FinalEffect")
                    continue
                period=b.find("Period")
                if period is not None and age>0 and not age%(Decimal(period.get("value"))*16):
                    self.trigger(b,"PeriodicEffect")

    def launch(self):
        self.units["Source"]={}
        self.fire("NovaPinningShotMissileLaunchSet")
        return self.units["Source"].copy()

    def impact(self,missile):
        self.units["Source"]=missile
        self.units["Target"]={}
        self.fire("NovaPinningShotSlowSwitch")
        record,=self.units["Target"]
        buff=self.defs[record]
        need(buff.find("Duration").get("value")=="2.25","Wrong slow duration")
        return -100*Decimal(buff.find("Modification/UnifiedMoveSpeedFactor").get("value"))


def run(map_path,nova):
    h=sha256(map_path.read_bytes()).hexdigest()
    need(h in (CANDIDATE,COMBINED),"Unknown candidate")
    stock=ET.fromstring(pinned(nova,NOVA))
    defs={e.get("id"):e for e in stock if e.tag.startswith(("CEffect","CValidator","CBehavior")) and e.get("id")}
    with closing(MPQArchive(map_path)) as a:
        for kind in ("Effect","Behavior","Validator"):
            for e in ET.fromstring(read_member(a,rf"Base.StormData\GameData\{kind}Data.xml")):
                name=e.get("id")
                if name and name.startswith(PREFIX):
                    defs[name]=e
                elif name in ("NovaPinningShotMissileLaunchSet","NovaPinningShotSlowSwitch","NovaPermanentCloak"):
                    for child in e:
                        if child.get("index") is None:
                            for old in list(defs[name].findall(child.tag)): defs[name].remove(old)
                        defs[name].append(child)
    m=Model(defs)
    m.tick(True)
    saved=[]
    for n in range(11):
        saved.append(m.launch())
        need(m.impact(saved[-1])==40+2*n,"Wrong stack magnitude")
        m.tick(True,16)
    need(m.impact(m.launch())==60,"Cap failed")
    m.tick(False,16)
    need(m.impact(m.launch())==60,"Grace ended early")
    m.tick(True)
    need(m.impact(m.launch())==60,"Recloak lost stored stacks")
    m.tick(False,17)
    need(m.impact(m.launch())==40,"Grace failed to clear")
    for i,missile in enumerate(saved):
        need(m.impact(missile)==40+2*i,"In-flight missile lost its launch magnitude")
    for cfg in (dict(talent=False),dict(hero="NovaHoloClone")):
        denied=Model(defs,**cfg)
        denied.tick(True,200)
        need(not denied.units["Caster"] and not denied.launch(),"Out-of-scope caster received a bonus")
    return dict(candidate_sha256=h,tested_slow_percent=list(range(40,61,2)),crossed_cap=True,
                grace_recloak_and_expiration=True,inflight_cases=11,denied_cases=2,
                evaluation="offline_emitted_graph_model",native_engine_verified=False)


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("map_path",type=Path)
    cli.add_argument("nova",type=Path)
    print(json.dumps(run(**vars(cli.parse_args())),indent=2))
