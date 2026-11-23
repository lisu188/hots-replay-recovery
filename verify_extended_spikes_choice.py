"""Verify the conditional loop-102 choice and loop-103 award for ExtendedSpikesRange."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from build_extended_spikes_map import ATTRIBUTES, EXTENDED, ARMOR, HERO, MODERN, TALENTS, one, pinned, require
from build_gate_order_map import definition
from encoders import encode_game_events, encode_tracker_events
from first_sound_timing import verify_manifest
from initial_talent_tracker import GAME, PREFIX, compare, first_inputs, history, load_case, stat
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE

CANDIDATE = "e7ce5d12d5a93840a333a6e27b3f15d9cab9917be2e88d0040f19d638e4f9bbf"
CONTROL = "ce9c2b6160f5b6154abe8cbcecae982dc00c61910bee691627c3a57c8c99dc77"


def effective(map_path, anub, game_script):
    xml = ET.fromstring(pinned(anub, MODERN))
    stock = one(xml, "CHero[@id='Anubarak']").findall("TalentTreeArray")
    require(stock[0].attrib == dict(Talent=ARMOR,Tier="1",Column="1"), "Unexpected stock choice")
    pinned(map_path, CANDIDATE)
    with closing(MPQArchive(map_path)) as a:
        h = ET.fromstring(read_member(a, HERO))
        t = ET.fromstring(read_member(a, TALENTS))
    selected = one(h, "CHero[@id='Anubarak']/TalentTreeArray")
    require(selected.attrib == dict(index="0",Talent=EXTENDED), "Map selector override differs")
    effective_first = {**stock[0].attrib, "Talent":selected.attrib["Talent"]}
    # Names feed the tracker only through the overlaid column and its target CTalent entry.
    talent = one(xml, "CTalent[@id='" + effective_first["Talent"] + "']")
    group = one(talent, "AbilityModificationArray")
    stock_mods = group.findall("Modifications")
    require(len(stock_mods) == 13, "Unexpected stock modifier list")
    original = [dict((c.tag,c.get("value")) for c in m) for m in stock_mods]
    changed = original.copy()
    corrections = one(t, f"CTalent[@id='{EXTENDED}']/AbilityModificationArray")
    require(corrections.attrib == {"index":"0"} and len(corrections) == 7, "Unexpected map modifier scope")
    for idx, n in zip(range(12,5,-1), corrections, strict=True):
        require(n.tag == "Modifications" and n.attrib == {"index":str(idx),"removed":"1"} and len(n) == 0,
                "Unexpected non-tail removal")
        m = changed.pop(int(n.get("index")))
        require((m["Entry"],m["Field"],m["Value"]) == ("AnubarakImpaleDamage",
                "AttributeFactor[" + ATTRIBUTES[idx-6] + "]","0.250000"), "Unexpected excluded target effect")
    require(changed == original[:6], "A retained target modifier changed")
    libs = pinned(game_script,GAME).decode("utf-8-sig").replace("\r\n","\n")
    setup = definition(libs,"void","libGame_gf_TalentsSetupTalentChoicesFromHeroDataForPlayer")
    for field in ("Tier","Talent","Column"):
        require('"TalentTreeArray[" + IntToString((lv_itTalent - 1)) + "].'+field+'"' in setup,
                "Changed native catalog setup script")
    require("lv_talentData[lv_column].lv_talentCatalogLink = (lv_talentID);" in setup and
            '].Modifications", c_playerAny)' in setup,"Unexpected catalog link or count")
    choose = definition(libs,"void","libGame_gf_TalentsChooseTalentForPlayer")
    key = 'lv_talentData[lp_buttonIndex].lv_talentCatalogLink'
    require(any('"PurchaseName"' in s and key in s for s in choose.splitlines()) and
            'StatEventCreate("TalentChosen")' in choose, "Unexpected award emitter")
    event = definition(libs,"bool","libGame_gt_TalentsChoiceSelected_Func")
    require("TalentTreeGetSelectedHeroTalentTreeColumn(EventPlayer()" in event, "Selector path differs")
    return effective_first["Talent"], original[:6]


def input_row(tick, uid):
    return dict(_event="NNet.Game.SHeroTalentTreeSelectedEvent",_eventid=110,
                _userid={"m_userId":uid},_gameloop=tick,m_index=0)


def physical_input(ordinal, protocol, raw, target, wanted):
    offset = previous = 0
    for i, row in enumerate(protocol.decode_replay_game_events(raw)):
        size, remainder = divmod(row["_bits"],8)
        require(not remainder and size, "Unaligned input")
        if i == ordinal:
            require(wanted == {k:v for k,v in row.items() if k!="_bits"}, "Selection shape differs")
            at_delta = {**wanted,"_gameloop":wanted["_gameloop"]-previous}
            require(raw[offset:offset+size] == encode_game_events([at_delta],target), "Target input frame differs")
            return
        previous = row["_gameloop"]
        offset += size
    raise ValueError("Missing selection")


def run(manifest, candidate, anub, gamelib, prefix, output=None):
    chosen, retained = effective(candidate, anub, gamelib)
    target = target_protocol()
    prefix_state = history(target.decode_replay_tracker_events(pinned(prefix,PREFIX)))
    old, controls, historical_controls = [], [], []
    checked = 0
    for file,h,b in verify_manifest(json.loads(manifest.read_bytes())):
        p, raw, data, rows = load_case(Path(file),h,b)
        checked += 1
        setup, heroes, levels = history(rows)
        initial = first_inputs(p,raw,setup,heroes,levels,{"HeroAnubarak":{}})
        qualifying = [(pid,rec) for pid,rec in initial.items() if rec[-1] == 0]
        for pid, (index, tick, uid, hero, ix) in qualifying:
            selection = input_row(tick,uid)
            physical_input(index,p,raw,target,selection)
            award = stat(tick+1,pid,chosen if b == 41810 else ARMOR)
            track, = compare([award],rows,data,target)
            detail = dict(replay_sha256=h,build=b,player=pid,user=uid,input_ordinal=index,tick=tick,
                          tracker_ordinal=track,award_tick=tick+1,hero=hero,selector=ix,
                          purchase=award["m_stringData"][0]["m_value"].decode())
            if h != SOURCE:
                (historical_controls if b == 41810 else controls).append(detail)
                continue
            projected_setup,projected_heroes,projected_levels = prefix_state
            require(projected_setup[uid][1] == pid and projected_heroes[pid][1] == hero and
                    any(t < tick and v == 1 for t,v in projected_levels[pid]), "Opening identity or level changed")
            require(sum(hh == hero for _, hh in heroes.values()) == 1 and tick == 102,
                    "Different TEN hero or selection")
            old.append(detail)
            g = encode_game_events([selection],target)
            s = encode_tracker_events([award],target)
            for row, packed, decoder in [(selection,g,target.decode_replay_game_events),
                                         (award,s,target.decode_replay_tracker_events)]:
                check, = decoder(packed)
                require(row == {k:v for k,v in check.items() if k!="_bits"}, "Target round trip differs")
    require(len(old) == 1 and any(c["replay_sha256"] == CONTROL for c in controls), "Expected pinned pair")
    if output:
        output.mkdir()
        (output/"choice.game.private.bin").write_bytes(g)
        (output/"award.tracker.private.bin").write_bytes(s)
    return dict(candidate_sha256=CANDIDATE,ten=old[0],archive_count=checked,
                historical_control_awards=historical_controls,stock_counterexamples=controls,
                private_game_bytes=len(g),private_game_sha256=sha256(g).hexdigest(),
                private_tracker_bytes=len(s),private_tracker_sha256=sha256(s).hexdigest(),
                retained_target_entries=[m["Entry"] for m in retained],target_catalog_applied_at_runtime=False,
                genuine_target_extended_spikes_award_witnesses=0,historical_spell_geometry_verified=False)


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ("manifest","candidate","anub","gamelib","prefix"):
        cli.add_argument(name,type=Path)
    cli.add_argument("--output",type=Path)
    print(json.dumps(run(**vars(cli.parse_args())),indent=2))
