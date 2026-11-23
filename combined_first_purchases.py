"""Reconstruct four successive TEN first-tier awards on the opt-in combined historical-rule map."""

import argparse
from contextlib import closing
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET

from build_extended_spikes_map import HERO, HISTORICAL, TALENTS, one, pinned, require
from encoders import encode_game_events, encode_tracker_events
from initial_talent_tracker import HEROES, compare, first_inputs, history, load_case, stat
from join_war_paint import insert_game_input
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE
from signed_game_input_map import canonical, digest
from verify_extended_spikes_choice import physical_input
from verify_signed_tracker import frames

MAP = "13493e67e36594f908239dd0cce37fda0c0b386bbef385dcef22a83848f589d1"
BASE_MAP = "9c223f3e4d9fb31324126b91f7e51048dd6c011ac0d4dcdf6f582e2978f92870"
BASE_GAME = "6a5d93173e71cdd1b015899c645e01dac4568401bb056295c911508606fc63e4"
PREFIX = "83e2bf4db5d7161246cbc65e4444011234f636dc21a37f269d37b98bd08d6a72"
CATALOGS = {
    "Nova":"721086138a01ff65659616556ea617c85f968d8bd28ec888fa6397bde0ce113a",
    "FaerieDragon":"0331a785983525abcbd58d95159ce4b12d8652c8a7294967e1231b30f5053064",
    "Barbarian":"1e4bc827d905d70772f6e3cd06707b147fa2e8349e94ae9c659b6aa91a79444f",
    "Greymane":HEROES["HeroGreymane"],
}
COORDINATES = [(844,245,133),(914,246,148),(1171,247,200),(1286,248,241)]
ALIAS = {"BarbarianMasteryWarPaint":"BarbarianWarPaint"}


def effective_trees(package, paths):
    pinned(package,MAP)
    with closing(MPQArchive(package)) as arc:
        patch = ET.fromstring(read_member(arc,HERO))
        definitions = ET.fromstring(read_member(arc,TALENTS))
    trees = {}
    for (name,fingerprint),path in zip(CATALOGS.items(),paths,strict=True):
        stock = ET.fromstring(pinned(path,fingerprint))
        rows = [dict(e.attrib) for e in one(stock,f"CHero[@id='{name}']").findall("TalentTreeArray")]
        for e in patch.findall(f"CHero[@id='{name}']/TalentTreeArray"):
            index = int(e.attrib["index"])
            require(index<=len(rows) and not len(e) and "removed" not in e.attrib,"Unsupported tree override")
            if index==len(rows): rows.append({})
            rows[index].update({k:v for k,v in e.attrib.items() if k!="index"})
        first = {i:r["Talent"] for i,r in enumerate(rows) if r["Tier"]=="1"}
        require(all(int(rows[i]["Column"])==i+1 for i in first) and len(set(first.values()))==len(first),
                "Ambiguous first tier or selector")
        for talent in first.values():
            key = f"CTalent[@id='{talent}']"
            require(stock.find(key) is not None or definitions.find(key) is not None,"Unresolved first-tier talent")
        trees[name] = first
    return trees


def generate(source, historical, package, nova, bright, sonya, greymane, prefix, base, receipt, output):
    require(not output.exists(),"Choose a fresh output directory")
    first = effective_trees(package,[nova,bright,sonya,greymane])
    old_trees = {h["id"]:h["talents"]["1"] for h in json.loads(pinned(historical,HISTORICAL))}
    protocol, game, tracker, original = load_case(source,SOURCE,41810)
    setup,heroes,levels = history(original)
    choices = first_inputs(protocol,game,setup,heroes,levels,{"Hero"+n:t for n,t in first.items()})
    target = target_protocol()
    before = pinned(prefix,PREFIX)
    existing = frames(before,target)
    target_setup,target_heroes,target_levels = history(r for r,*_ in existing)
    require(len(existing)==267 and existing[-1][0]["_gameloop"]==103,"Unexpected tracker prefix")
    require([i for i,e in enumerate(original) if 103 < e["_gameloop"] <= 242]==[n for _,n,_ in COORDINATES],
            "Unaccounted original records in the projected segment")
    original_awards, awards, selected, rows = [], [], [], []
    for index,ordinal,tick in COORDINATES:
        (player,pick), = [(p,v) for p,v in choices.items() if v[0]==index]
        _,loop,uid,hero,source_index = pick
        require(loop==tick and target_setup[uid][1]==player and target_heroes[player][1]==hero and
                any(t<tick and level==1 for t,level in target_levels[player]),"Different target opening state")
        name = hero.removeprefix("Hero")
        old_id = old_trees[name][source_index]["id"]
        new_id = ALIAS.get(old_id,old_id)
        selector, = [i for i,v in first[name].items() if v==new_id]
        row = dict(_event="NNet.Game.SHeroTalentTreeSelectedEvent",_eventid=110,
                   _gameloop=loop,_userid={"m_userId":uid},m_index=selector)
        physical_input(index,protocol,game,protocol,{**row,"m_index":source_index})
        original_awards.append(stat(loop+1,player,old_id))
        awards.append(stat(loop+1,player,first[name][selector]))
        selected.append(row)
        rows.append(dict(hero=hero,player=player,user=uid,source_index=source_index,target_index=selector,
                         source_talent=old_id,target_talent=new_id,input_ordinal=index,selection_loop=loop,
                         source_tracker_ordinal=ordinal,award_loop=loop+1))
    require(compare(original_awards,original,tracker,protocol)==[n for _,n,_ in COORDINATES],
            "Original physical awards disagree with the catalog-derived choices")
    new_tracker = encode_tracker_events([e for e,*_ in existing]+awards,target)
    checked = frames(new_tracker,target)
    require(new_tracker.startswith(before) and [e for e,*_ in checked[267:]]==awards and
            len(checked)==271 and original[249]["_gameloop"]==355 and original[249]["_eventid"]==1,
            "Invalid continuous tracker reconstruction")
    previous = json.loads(receipt.read_bytes())
    parent = previous["game"]
    require(previous["map_sha256"]==BASE_MAP and digest(canonical(parent))==BASE_GAME,"Different base inputs")
    base_ids = json.loads(pinned(base/"ordinals.private.json",parent["ledger_sha256"]))
    base_wire = pinned(base/"game-inputs.private.bin",parent["sha256"])
    by_id = {item[0]:e for item,e in zip(base_ids,target.decode_replay_game_events(base_wire),strict=True)}
    for detail,row in zip(rows[2:],selected[2:],strict=True):
        found = by_id[detail["input_ordinal"]]
        require({k:v for k,v in found.items() if k!="_bits"}==row,"Changed existing talent choice")
    with TemporaryDirectory(dir=output.parent) as name:
        temp = Path(name)
        prev_dir = base
        for detail,row in zip(rows[:2],selected[:2],strict=True):
            pending = temp/detail["hero"]
            pending.mkdir()
            label = detail["target_talent"]+"_requires_reconstructed_first_tier"
            parent = insert_game_input(source,prev_dir,parent["sha256"],parent["ledger_sha256"],parent,detail,row,
                                       label,pending,target)
            prev_dir = pending
        (prev_dir/"TEN.tracker.prefix.bin").write_bytes(new_tracker)
        prev_dir.rename(output)
    return dict(map_sha256=MAP,parent_map_sha256=BASE_MAP,source_sha256=SOURCE,awards=rows,game=parent,
                tracker_frames=len(checked),tracker_bytes=len(new_tracker),tracker_sha256=digest(new_tracker),
                prior_tracker_bytes=len(before),prior_prefix_sha256=PREFIX,last_tracker_loop=242,
                next_source_tracker_ordinal=249,next_source_tracker_loop=355,
                next_source_type=original[249]["m_unitTypeName"].decode("ascii"),verified_target_syncs=0,
                conditional_on=["initial unit allocation and projected hero identities",
                                "the prior sparse input conditions including command flags and session state",
                                "native first-tier availability at each recorded selection",
                                "early cloak and healing callbacks preserving tracker ordering and feedback schedules",
                                "the reconstructed passive healing, recipient filters and spell effects"],
                target_only_tracker_interleaving_verified=False,
                nova_intended_timing_verified_in_41810=False,historical_brightwing_absolute_radius_verified=False,
                target_simulation_verified=False)


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ("source","historical","package","nova","bright","sonya","greymane","prefix","base","receipt","output"):
        cli.add_argument(name,type=Path)
    print(json.dumps(generate(**vars(cli.parse_args())),indent=2))
