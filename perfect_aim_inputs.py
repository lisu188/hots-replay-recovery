"""Project TEN's historical Perfect Aim purchase on the corrected Dragon Shire map."""

import argparse
from contextlib import closing
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET

from build_extended_spikes_map import pinned, require
from build_perfect_aim_map import MEMBER, PARENT, REFUND, TALENT, check_catalog, source_date_and_choice
from encoders import encode_game_events, encode_tracker_events
from initial_talent_tracker import PREFIX, compare, first_inputs, history, load_case, stat
from join_war_paint import insert_game_input
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from opening_birth_wire import target_protocol
from perfect_aim_control import check as check_control
from predict_camp_captures import SOURCE
from signed_game_input_map import canonical, digest
from verify_extended_spikes_choice import physical_input

MAP = "9c223f3e4d9fb31324126b91f7e51048dd6c011ac0d4dcdf6f582e2978f92870"
PARENT_GAME = "a1b17f1b0f6b25dac3f216bf29d8d48734cfc63e5b8c039ccc2c01838d607b68"


def verify_map(parent, package):
    pinned(parent,PARENT)
    pinned(package,MAP)
    with closing(MPQArchive(parent)) as a, closing(MPQArchive(package)) as b:
        names = read_member(a,"(listfile)").decode("ascii").splitlines()
        require(len(names)==len(set(names))==71 and
                set(names)==set(read_member(b,"(listfile)").decode("ascii").splitlines()),"Map membership differs")
        changed = [n for n in names if read_member(a,n)!=read_member(b,n)]
        require(changed==[MEMBER], "Unexpected map members changed")
        old = ET.fromstring(read_member(a,MEMBER))
        new = ET.fromstring(read_member(b,MEMBER))
        refund, = new.findall(f"CEffectCreateHealer[@id='{REFUND}']")
        rate, = refund
        require(refund.attrib=={"id":REFUND} and rate.tag=="RechargeVitalRate" and
                rate.attrib=={"value":"50"} and not len(rate), "Unexpected added effect fields")
        new.remove(refund)
        for doc in (old,new):
            for element in doc.iter():
                if element.text and not element.text.strip(): element.text = None
                if element.tail and not element.tail.strip(): element.tail = None
        require(ET.tostring(old)==ET.tostring(new), "Removing the new effect did not restore the prior catalog")


def generate(source,historical,modern,parent,package,prefix,control,base,receipt,output):
    require(not output.exists(), "Choose a new output directory")
    verify_map(parent,package)
    catalog = check_catalog(historical,modern)
    witness = check_control(control,modern)
    match = source_date_and_choice(source)
    old, raw, data, tracker = load_case(source,SOURCE,41810)
    setup, heroes, levels = history(tracker)
    choices = first_inputs(old,raw,setup,heroes,levels,{"HeroGreymane":{}})
    ordinal,tick,uid,hero,source_index = choices[match["player"]]
    require((ordinal,tick,uid,source_index)==(match["input_ordinal"],match["input_loop"],match["user_id"],match["selector"])
            and hero=="HeroGreymane" and witness["award"]==TALENT, "Different first Greymane selection")
    old_hero, = [h for h in json.loads(historical.read_bytes()) if h["id"]=="Greymane"]
    require(old_hero["talents"]["1"][source_index]["id"]==TALENT,"Historical column differs")
    tree, = ET.fromstring(modern.read_bytes()).findall("CHero[@id='Greymane']")
    selector, = [i for i,n in enumerate(tree.findall("TalentTreeArray")) if n.get("Talent")==TALENT and
                 n.get("Tier")=="1" and n.get("Column")==str(i+1)]
    require(witness["selector"]==selector,"Native target selection disagrees with the catalog")
    target = target_protocol()
    target_setup,target_heroes,target_levels = history(target.decode_replay_tracker_events(pinned(prefix,PREFIX)))
    require(target_setup[uid][1]==match["player"] and target_heroes[match["player"]][1]==hero and
            any(t<tick and level==1 for t,level in target_levels[match["player"]]), "Different starting Greymane")
    row = dict(_event="NNet.Game.SHeroTalentTreeSelectedEvent",_eventid=110,_gameloop=tick,_userid={"m_userId":uid},
               m_index=selector)
    require(row["m_index"]==source_index,"Historical and current selectors differ")
    physical_input(ordinal,old,raw,target,row)
    award = stat(tick+1,match["player"],TALENT)
    require(compare([award],tracker,data,target)==[match["award_ordinal"]], "Original award differs")
    previous = json.loads(receipt.read_bytes())
    old_game = previous["game"]
    require(previous["map_sha256"]==PARENT and digest(canonical(old_game))==PARENT_GAME,"Different parent input receipt")
    ledger = json.loads(pinned(base/"ordinals.private.json",old_game["ledger_sha256"]))
    before = pinned(base/"game-inputs.private.bin",old_game["sha256"])
    # The refund effect is gated by purchase. Only these existing projections survive after it.
    safe_names = {"camera","literal_trigger_chat","recorded_final_departure"}
    late = 0
    for (index,_,_,labels),e in zip(ledger,target.decode_replay_game_events(before),strict=True):
        if index<=ordinal: continue
        pure = set(labels)<=safe_names and bool(labels)
        ping = labels==["ping_map_or_no_target"] and e["m_unit"]==0
        initial = (labels==["talent_index_requires_target_award_state"] and index in (1536,6214)
                   and e["m_index"]==2 and e["_userid"]["m_userId"]!=uid)
        require(pure or ping or initial,"Later input requires additional refund dependent checks")
        late+=1
    detail = dict(input_ordinal=ordinal,selection_loop=tick,user=uid,target_index=row["m_index"])
    game_frame = encode_game_events([row],target)
    tracker_frame = encode_tracker_events([award],target)
    with TemporaryDirectory(dir=output.parent) as temp:
        pending = Path(temp)/"projection"
        pending.mkdir()
        (pending/"choice.game.private.bin").write_bytes(game_frame)
        (pending/"award.tracker.private.bin").write_bytes(tracker_frame)
        game = insert_game_input(source,base,old_game["sha256"],old_game["ledger_sha256"],old_game,detail,row,
                                 "perfect_aim_requires_first_tier_acceptance",pending,target)
        pending.rename(output)
    return dict(map_sha256=MAP,parent_map_sha256=PARENT,source=match,control_sha256=witness["replay_sha256"],
                native_control_input=witness["input"]["ordinal"],native_control_award=witness["tracker"]["ordinal"],
                game=game,game_frame_sha256=digest(game_frame),tracker_frame_sha256=digest(tracker_frame),
                tracker_frame_bytes=len(tracker_frame),catalog=catalog,later_parent_rows_checked=late,
                historic_absolute_distance_verified=False,target_simulation_verified=False,verified_target_syncs=0)


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    for key in ("source","historical","modern","parent","package","prefix","control","base","receipt","output"):
        cli.add_argument(key,type=Path)
    print(json.dumps(generate(**vars(cli.parse_args())),indent=2))
