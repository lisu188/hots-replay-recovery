"""Place TEN Tyrande's historical Seasoned Marksman in a separate derived Dragon Shire package.

The 41810 catalog export lists GenericTalentSeasonedMarksman as Tyrande's third
level-one talent, and original game input 1547 selects index 2. Build 98348 still
defines the shared talent but its Tyrande tree has TyrandeTrueshotAura in tier 1,
column 3. The candidate appends one map-local CHero record that relinks only that
row. It leaves the shared talent's 98348 behavior unchanged; the post-41810
quest reward and completion point and the historical minion credit remain
explicitly open in the receipt.
"""

import argparse
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET

from build_combined_first_talents import appended, entries
from build_dragonshire_talent_map import digest, inventory
from build_extended_spikes_map import HISTORICAL, one, pinned, require
from runtime_catalog_probe import Storm

PARENT = "13493e67e36594f908239dd0cce37fda0c0b386bbef385dcef22a83848f589d1"
TYRANDE = "8dc1f32eca0299e4007a99ac487bf816ff3a7f8a24e0f3301ea050e3f7b8fd29"
SHARED = "7e2d25e6bff1ae57db34f652c86edac04d2881e7e288b373b7b685676031960c"
HERO = "Base.StormData\\GameData\\HeroData.xml"
TALENT = "GenericTalentSeasonedMarksman"
STOCK = "TyrandeTrueshotAura"
SLOT = 2
DESCRIPTION = ("For every 6 enemy Minion kills near your Hero, gain 1 Basic Attack damage. "
               "Hero Takedowns count as 3 Minion kills.")
TARGET_BEHAVIORS = ["TalentSeasonedMarksmanCarryBehavior", "TalentSeasonedMarksmanTokenCounter",
                    "GenericSeasonedMarksmanItem"]


def prepare(members, tyrande_xml, shared_talents, historical_json):
    """Return the single changed member after checking every input relationship."""
    require(HERO in members, "Parent package lacks its map-local hero catalog")
    for name, raw in members.items():
        lower = name.lower()
        if lower.startswith("base.stormdata\\gamedata\\") and lower.endswith(".xml"):
            root = ET.fromstring(raw)
            require(not root.findall("CHero[@id='Tyrande']") and not root.findall(f"CTalent[@id='{TALENT}']"),
                    "Conflicting map-local Tyrande or Seasoned Marksman definition")
    old, = (h for h in json.loads(historical_json) if h["id"] == "Tyrande")
    tier = old["talents"]["1"]
    require([t["id"] for t in tier][SLOT] == TALENT and tier[SLOT]["description"] == DESCRIPTION,
            "Historical slot or documented rule differs")
    xml = ET.fromstring(tyrande_xml)
    rows = one(xml, "CHero[@id='Tyrande']").findall("TalentTreeArray")
    require(len(rows) == 21 and rows[SLOT].attrib == {"Talent": STOCK, "Tier": "1", "Column": "3"} and
            not len(rows[SLOT]) and not any(r.get("Talent") == TALENT for r in rows),
            "Unexpected target tier-one slot or tree")
    require(xml.find(f"CTalent[@id='{TALENT}']") is None, "Hero file unexpectedly defines the shared talent")
    shared = one(ET.fromstring(shared_talents), f"CTalent[@id='{TALENT}']")
    behaviors = [n.get("value") for n in one(shared, "RankArray").findall("BehaviorArray")]
    require(behaviors == TARGET_BEHAVIORS and one(shared, "QuestData").attrib ==
            {"StackBehavior": "TalentSeasonedMarksmanTokenCounter", "TargetCount": "40"},
            "Shared 98348 talent differs from the inspected definition")
    hero = ET.Element("CHero", id="Tyrande")
    ET.SubElement(hero, "TalentTreeArray", index=str(SLOT), Talent=TALENT)
    base = members[HERO]
    require(base.count(b"</Catalog>") == 1, "Unexpected map hero catalog")
    result = base.replace(b"</Catalog>", ET.tostring(hero, encoding="ascii", xml_declaration=False) + b"\r\n</Catalog>")
    before, after = entries(base), entries(result)
    require(after.keys() - before.keys() == {"tyrande"} and all(after[k] == v for k, v in before.items()),
            "Hero catalog change is not a single appended record")
    appended(base, result)
    return {HERO: result}


def build(parent, tyrande_xml, shared_talents, historical, output, stormlib=None):
    require(not output.exists() and not output.is_symlink(), "A fresh output path is required")
    stock = pinned(parent, PARENT)
    storm = Storm(stormlib)
    before, parent_checks = inventory(parent, storm)
    edits = prepare(before, pinned(tyrande_xml, TYRANDE), pinned(shared_talents, SHARED), pinned(historical, HISTORICAL))
    with TemporaryDirectory(dir=output.parent) as temp:
        staged = Path(temp) / "candidate.s2ma"
        staged.write_bytes(stock)
        storm.replace(staged, edits)
        after, checks = inventory(staged, storm)
        require(after == {**before, **edits} and parent.read_bytes() == stock, "Unaccounted MPQ changes")
        image = staged.read_bytes()
        os.link(staged, output)
    return dict(parent_sha256=PARENT, candidate_sha256=digest(image), candidate_bytes=len(image),
                source_catalog_sha256=HISTORICAL, current_hero_sha256=TYRANDE, shared_talent_catalog_sha256=SHARED,
                parent_checks=parent_checks, candidate_checks=checks, changed_member=HERO,
                changed_member_sha256=digest(edits[HERO]), unchanged_content_members=len(before) - 1,
                target_slot=SLOT, tier=1, column=3, stock_choice=STOCK, projected_choice=TALENT,
                retained_target_behaviors=TARGET_BEHAVIORS,
                open_historical_differences=[
                    "Quest reward (activatable attack speed) and 40-stack completion point were added on 2016-05-17",
                    "41810 tooltip implies 1/6 damage per nearby minion kill; target minion credit is 0.2001",
                    "Exact 41810 stack representation and rounding are unrecovered"],
                historic_behavior_restored=False, native_catalog_loading_verified=False, replay_written=False)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    for name in ("parent", "tyrande_xml", "shared_talents", "historical", "output"):
        cli.add_argument(name, type=Path)
    cli.add_argument("--stormlib")
    print(json.dumps(build(**vars(cli.parse_args())), indent=2))
