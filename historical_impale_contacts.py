"""Measure link-494 point orders, owned beetle births and primary-hero kills in seven build-41810 archives."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from math import hypot
from pathlib import Path
from xml.etree import ElementTree as ET

from initial_talent_tracker import history, load_case, require
from predict_camp_captures import SOURCE

MINE_CASE = "d5af3e6672c102a5b33abc7df7884ea2648d01af8f7921f16ff6ad69f3c69a97"
CASES = {SOURCE, MINE_CASE, "e5931b469dae86d95741bff08b71fc06bb28d5344f7c2ea64c4cc91f60570b2b",
    "4f02c8c4b4ae7eb7ec5e290df4f2da26ebe3d71221a3c9b3db064306066b400d",
    "8beb4370c5c6638d5481c25e88970ad49d5651edacf876cb623be7c2f593504b",
    "ac9ede2e7bc241a54209d723fb40594920734138f38347b21cea3a7797ae1372",
    "a6c7c6232f19b9b264ef39bf36b4ce7dfcad56e59c470731b53c28700b9d2603"}


def tag(r):
    return r["m_unitTagIndex"],r["m_unitTagRecycle"]


def unpack(word):
    return word>>18, word&0x3ffff


def xy(r):
    return [r["m_x"],r["m_y"]]


def target(r):
    if r["_eventid"] == 27:
        return r["m_data"].get("TargetUnit")
    if r["_eventid"] == 105:
        return r["m_target"]
    return None


def report(path, h):
    p,gm,tm,tr = load_case(path,h,41810)
    gs = list(p.decode_replay_game_events(gm))
    setup,heroes,levels = history(tr)
    births = {tag(r):(i,r) for i,r in enumerate(tr) if r["_eventid"] == 1}
    shots = defaultdict(list)
    for i,r in enumerate(gs):
        obj = target(r)
        if obj and obj["m_tag"] not in (0,0xffffffff):
            shots[unpack(obj["m_tag"])].append((r["_gameloop"],i))
    totals = Counter()
    early = []
    same_loop = []
    for pid,(_,hero) in heroes.items():
        if hero != "HeroAnubarak":
            continue
        uid, = (u for u,(_,v) in setup.items() if v == pid)
        hero_tag, = (key for key,(_,r) in births.items() if r["m_unitTypeName"] == b"HeroAnubarak" and
                     r["m_controlPlayerId"] == r["m_upkeepPlayerId"] == pid)
        fourth = next(t for t,v in levels[pid] if v >= 4)
        choices = [(r["_gameloop"],r["m_stringData"][0]["m_value"].decode()) for r in tr
                   if r.get("m_eventName") == b"TalentChosen" and
                   any(v == {"m_key":b"PlayerID","m_value":pid} for v in r["m_intData"])]
        cmds = [(i,r) for i,r in enumerate(gs) if r["_userid"]["m_userId"] == uid and r["_eventid"] == 27]
        spells = [(i,r) for i,r in cmds if r["m_abil"]]
        beetles = defaultdict(list)
        for i,r in births.values():
            if r["m_controlPlayerId"] == r["m_upkeepPlayerId"] == pid and r["m_unitTypeName"] == b"AnubarakBeetleSpitBeetle":
                beetles[r["_gameloop"]].append((i,r))
        killed = [(i,r) for i,r in enumerate(tr) if r["_eventid"] == 2 and r["m_killerPlayerId"] == pid and
                  (r["m_killerUnitTagIndex"],r["m_killerUnitTagRecycle"]) == hero_tag]
        for i,order in spells:
            t = order["_gameloop"]
            if (order["m_abil"]["m_abilLink"],order["m_abil"]["m_abilCmdIndex"]) != (494,0) or "TargetPoint" not in order["m_data"]:
                continue
            totals["point_orders"] += 1
            if len(beetles[t+9]) != 1 or sum(t <= r["_gameloop"] <= t+9 for _,r in spells) != 1:
                continue
            totals["qualifying_orders"] += 1
            totals["before_level4"] += int(t < fourth)
            bi,beetle = beetles[t+9][0]
            deaths = [(j,r) for j,r in killed if t <= r["_gameloop"] <= t+32]
            totals["primary_hero_tag_deaths_within_32"] += len(deaths)
            totals["pre4_primary_hero_tag_deaths_within_32"] += len(deaths) if t < fourth else 0
            totals["orders_with_any_death_and_same_loop_caster_snapshot"] += int(bool(deaths) and any(
                tick == t for tick,_ in shots[hero_tag]))
            for _,ordinal in (shot for shot in shots[hero_tag] if shot[0] == t and deaths):
                obj = target(gs[ordinal])
                origin = [obj["m_snapshotPoint"][k]/4096 for k in "xy"]
                aim = [order["m_data"]["TargetPoint"][k]/4096 for k in "xy"]
                dx,dy = [b-a for a,b in zip(origin,aim)]
                denom = hypot(dx,dy)
                contacts = []
                for j,v in deaths:
                    x,y = [b-a for a,b in zip(origin,xy(v))]
                    contacts.append(dict(death_ordinal=j,death_loop=v["_gameloop"],victim=births[tag(v)][1]["m_unitTypeName"].decode(),
                        death_xy=xy(v),caster_snapshot_to_victim=hypot(x,y),
                        along_aim=(x*dx+y*dy)/denom if denom else None,
                        cross_aim=abs(x*dy-y*dx)/denom if denom else None))
                same_loop.append(dict(issue_ordinal=i,issue_loop=t,hero_tag=hero_tag,first_talents=[n for at,n in choices if at<=t],
                    caster_snapshot_ordinal=ordinal,caster_snapshot_user=gs[ordinal]["_userid"]["m_userId"],caster_snapshot_xy=origin,
                    point_aim_xy=aim,contacts=contacts))
            if t >= fourth:
                continue
            for j,v in deaths:
                birth_ord,victim = births[tag(v)]
                data = dict(input_ordinal=i,issue_loop=t,player=pid,user=uid,
                    prior_talents=[n for at,n in choices if at <= t],
                    prior_talent_awards=[(at,n) for at,n in choices if at <= t],killer_index_generation=hero_tag,
                    beetle_ordinal=bi,beetle_xy=xy(beetle),death_ordinal=j,death_loop=v["_gameloop"],
                    victim_name=victim["m_unitTypeName"].decode(),victim_birth_ordinal=birth_ord,
                    victim_birth_loop=victim["_gameloop"],victim_index_generation=tag(v),birth_xy=xy(victim),
                    death_xy=xy(v),aim_fixed=order["m_data"]["TargetPoint"])
                aim = [data["aim_fixed"][k]/4096 for k in "xy"]
                dx,dy = [b-a for a,b in zip(xy(beetle),xy(v))]
                ax,ay = [b-a for a,b in zip(xy(beetle),aim)]
                length = hypot(ax,ay)
                if length:
                    data["display_grid_measurements"] = dict(beetle_to_victim=hypot(dx,dy),
                        beetle_to_aim=length,aim_to_victim=hypot(dx-ax,dy-ay),
                        along_aim=(dx*ax+dy*ay)/length,cross_aim=abs(dx*ay-dy*ax)/length)
                close = sorted(shots[hero_tag],key=lambda a:abs(a[0]-t))
                data["nearest_caster_target_snapshot_loop"] = close[0][0] if close else None
                data["other_explicit_spell_orders_minus80_through_death"] = [
                    (k,r["_gameloop"],r["m_abil"]["m_abilLink"]) for k,r in spells
                    if k != i and t-80 <= r["_gameloop"] <= v["_gameloop"]]
                data["implicit_order_targets_until_death"] = [
                    (k,r["_gameloop"],unpack(target(r)["m_tag"]) if target(r) else None)
                    for k,r in cmds if not r["m_abil"] and t <= r["_gameloop"] <= v["_gameloop"]]
                early.append(data)
    ten_choices=[]
    if h==SOURCE:
        ten_choices=[(i,r["_gameloop"],r["m_stringData"][0]["m_value"].decode()) for i,r in enumerate(tr)
                     if r.get("m_eventName")==b"TalentChosen" and
                     {"m_key":b"PlayerID","m_value":2} in r["m_intData"]]
    return dict(archive_sha256=h,game_sha256=sha256(gm).hexdigest(),tracker_sha256=sha256(tm).hexdigest(),
                counts=dict(totals),pre4_deaths=early,same_loop_caster_snapshots_with_deaths=same_loop,
                ten_player2_awards=ten_choices)


def target_effects(path):
    raw=path.read_bytes()
    require(sha256(raw).hexdigest()=="6e575d1c7e852274480b88e89e06ce993a9b8dd6f7988ccdc57e173c337eb799",
            "Unexpected target XML")
    root=ET.fromstring(raw)
    def node(kind,name):
        entry,=root.findall(kind+"[@id='"+name+"']")
        return entry
    def word(n,field):
        v,=n.findall(field)
        return v.attrib["value"]
    def includes(n,field,name):
        require(any(m.get("value")==name for m in n.findall(field)), "Missing effect link "+name)
    abil=node("CAbilEffectTarget","AnubarakImpale")
    start=node("CEffectSet",word(abil,"Effect"))
    damage_path="AnubarakImpaleCreatePersistent"
    barbs_path="AnubarakImpaleModelPersistent"
    includes(start,"EffectArray",damage_path)
    includes(start,"EffectArray",barbs_path)
    ext=node("CTalent","AnubarakMasteryExtendedSpikesImpale")
    added={word(n,"Entry"):int(float(word(n,"Value"))) for n in ext.findall("AbilityModificationArray/Modifications")
           if n.find("Field") is not None and word(n,"Field")=="PeriodCount"}
    require(added=={damage_path:2,barbs_path:2},"Different talent offsets")
    damage=node("CEffectCreatePersistent",damage_path)
    delay=node("CEffectCreatePersistent",word(damage,"InitialEffect"))
    require(word(damage,"PeriodicEffectArray")==delay.get("id") and word(delay,"PeriodCount")=="1","Search path changed")
    search_set=node("CEffectSet",word(delay,"PeriodicEffectArray"))
    search=node("CEffectEnumArea",word(search_set,"EffectArray"))
    impact=node("CEffectSet",search.find("AreaArray").get("Effect"))
    includes(impact,"EffectArray","AnubarakImpaleDamage")
    model=node("CEffectCreatePersistent",barbs_path)
    branch=node("CEffectSet",word(model,"PeriodicEffectArray"))
    barbs_delay=node("CEffectCreatePersistent",word(branch,"EffectArray"))
    talent=node("CTalent","AnubarakMasteryBedOfBarbs")
    chance,=[n for n in talent.findall("AbilityModificationArray/Modifications") if word(n,"Entry")==barbs_delay.get("id")]
    require((word(chance,"Type"),word(chance,"Field"),float(word(chance,"Value")))==("FlatModification","Chance",1)
            and float(word(barbs_delay,"Chance"))==0,"Different Barbs enable semantics")
    barbs=node("CEffectCreatePersistent",word(barbs_delay,"InitialEffect"))
    area=node("CEffectEnumArea",word(barbs,"PeriodicEffectArray"))
    switch=node("CEffectSwitch",area.find("AreaArray").get("Effect"))
    default=node("CEffectSet",word(switch,"CaseDefault"))
    includes(default,"EffectArray","AnubarakImpaleBedOfBarbsApplyBehavior")
    dot=node("CEffectApplyBehavior","AnubarakImpaleBedOfBarbsApplyDoT")
    includes(default,"EffectArray",dot.get("id"))
    dot_buff=node("CBehaviorBuff",word(dot,"Behavior"))
    node("CEffectDamage",word(dot_buff,"InitialEffect"))
    n=int(word(damage,"PeriodCount"))
    count=int(word(barbs,"PeriodCount"))
    require(n==int(word(model,"PeriodCount"))==7 and count==28,"Changed branch counts")
    return dict(xml_sha256=sha256(raw).hexdigest(),input_order_range=float(word(abil,"Range")),
        attack_search_delays_seconds=float(word(delay,"InitialDelay")),attack_step_seconds=float(word(damage,"PeriodicPeriodArray")),
        initial_attack_searches=1,periodic_stock=n,periodic_extended=n+added[damage_path],
        attack_search_requests=[1+n,1+n+added[damage_path]],
        model_branch_delay_seconds=float(word(model,"InitialDelay")),barbs_additional_delay_seconds=float(word(barbs_delay,"InitialDelay")),
        barbs_period_seconds=float(word(barbs,"PeriodicPeriodArray")),barbs_area_queries_per_enabled_position=count,
        extra_barbs_query_requests_if_enabled=added[barbs_path]*count,all_counts_conditional_on_scheduled_effects=True)


def measure(paths, target_xml):
    by_hash={sha256(p.read_bytes()).hexdigest():p for p in paths}
    require(len(paths) == len(by_hash) and set(by_hash) == CASES, "Wrong seven historical archives")
    rows = [report(by_hash[h],h) for h in sorted(CASES)]
    totals = sum((Counter(r["counts"]) for r in rows),Counter())
    focus, = [v for r in rows if r["archive_sha256"] == MINE_CASE for v in r["pre4_deaths"] if v["issue_loop"] == 1268]
    require(focus["victim_name"] == "AbathurToxicNest" and focus["victim_index_generation"] == (141,2)
            and focus["birth_xy"] == focus["death_xy"] and focus["prior_talents"] == ["AnubarakMasteryExtendedSpikesImpale"],
            "Early contact witness differs")
    return dict(historical_build=41810,fixtures=len(rows),counts=dict(totals),archives=rows,current_98348=target_effects(target_xml),
                historical_period_count=None,historical_offsets=None,historical_contact_range=None,
                map_adjustment_supported=False)


if __name__ == "__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--target-xml",required=True,type=Path)
    cli.add_argument("replays",type=Path,nargs="+")
    args=cli.parse_args()
    print(json.dumps(measure(args.replays,args.target_xml),indent=2))
