"""Translate TEN's first Sonya talent purchase and check its target award."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET

from build_extended_spikes_map import HISTORICAL, PARENT, one, pinned, require
from build_gate_order_map import definition
from encoders import encode_game_events, encode_tracker_events
from initial_talent_tracker import GAME, PREFIX, compare, history, load_case, stat
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE
from verify_extended_spikes_choice import CANDIDATE, physical_input

MODERN = "1e4bc827d905d70772f6e3cd06707b147fa2e8349e94ae9c659b6aa91a79444f"
MODERN_ID = "BarbarianWarPaint"
OLD_ID = "BarbarianMasteryWarPaint"
WITNESS = "6987fe1729e6cc3afc272d1089c74d7ef001f5e340b60ac37610132586fb9939"


def catalog(historical, modern, package, game_library):
    entries = json.loads(pinned(historical, HISTORICAL).decode("utf-8-sig"))
    hero, = [entry for entry in entries if entry["id"] == "Barbarian"]
    old = hero["talents"]["1"][0]
    require(old["id"] == OLD_ID and old["description"] == "Basic Attacks heal you for 30% of the damage dealt.",
            "Historical first-tier behavior differs")
    doc = ET.fromstring(pinned(modern, MODERN))
    tree = one(doc, "CHero[@id='Barbarian']").findall("TalentTreeArray")
    first = {i: row.attrib["Talent"] for i, row in enumerate(tree) if row.attrib.get("Tier") == "1"}
    selector, = [i for i, name in first.items() if name == MODERN_ID]
    require(tree[selector].attrib == dict(Talent=MODERN_ID, Tier="1", Column=str(selector + 1))
            and not len(tree[selector]), "Target selector has additional restrictions")
    talent = one(doc, f"CTalent[@id='{MODERN_ID}']")
    face = one(talent, "Face").attrib["value"]
    behavior = one(talent, "RankArray/BehaviorArray").attrib["value"]
    carry = one(doc, f"CBehaviorBuff[@id='{behavior}']")
    basic = one(carry, "Modification/VitalDamageLeechArray[@index='Life']/KindArray")
    require(carry.get("parent") == "CarryBehaviorParent" and basic.attrib == {"index":"Basic","value":"0.3"}
            and one(carry, "Face").get("value") == face and len(talent) == 3
            and len(one(talent, "RankArray")) == 1 and not len(one(talent, "AbilityModificationArray"))
            and one(carry, "Modification/VitalDamageLeechScoreArray").get("Value") == "SelfHealing",
            "The War Paint passive or score sink differs")
    button = one(doc, f"CButton[@id='{face}']/Icon").get("value")
    require(button.split(chr(92))[-1] == old["icon"], "Source and target talent icons differ")
    package_id = sha256(package.read_bytes()).hexdigest()
    require(package_id in (PARENT, CANDIDATE), "Unknown map")
    protected = {"Barbarian", MODERN_ID, behavior, face, "CarryBehaviorParent", "HeroBarbarian"}
    with closing(MPQArchive(package)) as arc:
        for name in read_member(arc, "(listfile)").decode("ascii").splitlines():
            if name.lower().startswith("base.stormdata"+chr(92)+"gamedata"+chr(92)) and name.lower().endswith(".xml"):
                local = ET.fromstring(read_member(arc, name))
                require(all(n.get("id") not in protected and n.get("default") != "1" for n in local),
                        "Map-local catalog change needs assessment")
    lib = pinned(game_library, GAME).decode("utf-8-sig").replace("\r\n", "\n")
    setup = definition(lib, "void", "libGame_gf_TalentsSetupTalentChoicesFromHeroDataForPlayer")
    require(all('"].'+s+'"' in setup for s in ("Tier","Column","Talent")) and
            "lv_talentData[lv_column].lv_talentCatalogLink = (lv_talentID);" in setup, "Column binding changed")
    choose = definition(lib, "void", "libGame_gf_TalentsChooseTalentForPlayer")
    require(any('"PurchaseName"' in line and "lv_talentData[lp_buttonIndex].lv_talentCatalogLink" in line
                for line in choose.splitlines()), "Purchase name source differs")
    return selector, first, package_id


def opening_case(path, fingerprint, build, first, selector):
    protocol, raw, tracker, rows = load_case(path, fingerprint, build)
    setup, heroes, levels = history(rows)
    players = {p for p, (_, hero) in heroes.items() if hero == "HeroBarbarian"}
    by_uid = {uid:p for uid, (_,p) in setup.items() if p in players}
    require(len(by_uid) == len(players) and bool(players), "Expected a Sonya control")
    results = []
    target = target_protocol()
    for i, row in enumerate(protocol.decode_replay_game_events(raw)):
        uid = row["_userid"]["m_userId"]
        if row["_eventid"] != 110 or uid not in by_uid:
            continue
        player = by_uid.pop(uid)
        tick, original = row["_gameloop"], row["m_index"]
        require(heroes[player][0] < tick and any(t < tick and level == 1 for t,level in levels[player]),
                "Missing prior hero or level")
        source = {k:v for k,v in row.items() if k != "_bits"}
        physical_input(i, protocol, raw, protocol, source)
        if build == 41810:
            require(fingerprint == SOURCE and original == 0 and len(players) == 1, "Wrong original purchase")
            original_name, translated = OLD_ID, selector
        else:
            original_name, translated = first[original], original
        observed = stat(tick + 1, player, original_name)
        ordinal, = compare([observed], rows, tracker, protocol)
        event = {**source, "m_index":translated}
        award = stat(tick + 1, player, first[translated])
        if build == 98348:
            physical_input(i, protocol, raw, target, event)
            compare([award], rows, tracker, target)
        results.append((dict(build=build, sha256=fingerprint, player=player, user=uid, input_ordinal=i,
                             selection_loop=tick, source_index=original, target_index=translated,
                             source_award=original_name, target_award=first[translated],
                             tracker_ordinal=ordinal, award_loop=tick+1), event, award))
        if not by_uid:
            break
    require(not by_uid, "Missing first purchase")
    return results


def generate(source, historical, modern, package, game_library, prefix, controls, output):
    selector, first, package_id = catalog(historical, modern, package, game_library)
    ten, = opening_case(source, SOURCE, 41810, first, selector)
    detail, event, award = ten
    require((detail["selection_loop"], detail["input_ordinal"], detail["tracker_ordinal"]) == (200,1171,247),
            "TEN source coordinates differ")
    target = target_protocol()
    setup, heroes, levels = history(target.decode_replay_tracker_events(pinned(prefix, PREFIX)))
    player, uid = detail["player"], detail["user"]
    require(setup[uid][1] == player and heroes[player][1] == "HeroBarbarian"
            and any(t < detail["selection_loop"] and lv == 1 for t,lv in levels[player]),
            "Target opening identity differs")
    cases = json.loads(controls.read_bytes())
    require(len({h for _,h in cases}) == len(cases), "Repeated control")
    evidence = [r for file,h in cases for r,_,_ in opening_case(Path(file), h, 98348, first, selector)]
    require(any(r["sha256"] == WITNESS and r["target_index"] == selector for r in evidence)
            and {r["target_index"] for r in evidence} == set(first),
            "Missing positive War Paint or alternate first-column controls")
    game_bytes = encode_game_events([event], target)
    tracker_bytes = encode_tracker_events([award], target)
    for raw, decoder, expected in ((game_bytes,target.decode_replay_game_events,event),
                                   (tracker_bytes,target.decode_replay_tracker_events,award)):
        single, = decoder(raw)
        require(single.pop("_bits") == len(raw) * 8 and single == expected, "Projected wire differs")
    require(not output.exists(), "Use a new output directory")
    with TemporaryDirectory(dir=output.parent) as temp:
        pending = Path(temp) / "frames"
        pending.mkdir()
        (pending / "choice.game.private.bin").write_bytes(game_bytes)
        (pending / "award.tracker.private.bin").write_bytes(tracker_bytes)
        pending.rename(output)
    return dict(map_sha256=package_id, startup_prefix_sha256=PREFIX, ten=detail, controls=evidence,
                controls_with_target_award=sum(r["target_index"] == selector for r in evidence),
                basic_attack_life_leech="0.3", game_sha256=sha256(game_bytes).hexdigest(), game_bytes=len(game_bytes),
                tracker_sha256=sha256(tracker_bytes).hexdigest(), tracker_bytes=len(tracker_bytes),
                verified_hit_heal_totals=False, verified_target_syncs=0)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("source","historical","modern","package","game_library","prefix","controls","output"):
        cli.add_argument(name,type=Path)
    print(json.dumps(generate(**vars(cli.parse_args())),indent=2))
