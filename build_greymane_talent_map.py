"""Restore selected Greymane cooldown rules in the pinned two-talent Dragon Shire map."""

import argparse
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import xml.etree.ElementTree as ET

from build_dragonshire_talent_map import (
    BEHAVIORS,
    TALENTS,
    conventional_catalog,
    digest,
    inventory,
)
from runtime_catalog_probe import Storm

BASE_MAP = "662a90d5ea72c8454d66a1070b3200e6a2929f3d2069e2c07ecc07cfcc79b800"
HERO_XML = "78a564ee1334eeaee26c4b6c57a7dd5d5b3c048cba63a9b7131440d778b98cff"
HISTORICAL = "aaf264de6c3e31ce4bee1b1a5d658d695036393e4077e539630dd553698e9bbb"
EFFECTS = r"Base.StormData\GameData\EffectData.xml"
ABILITIES = r"Base.StormData\GameData\AbilData.xml"
RUNNING = "GreymaneDarkflightDisengageRunningWild"
HEROIC = "GreymaneGoForTheThroat"
SWITCH = "GreymaneDisengageHeroicUseSwitch"
RESET = HEROIC + "ResetPlayerCooldown"
DEFAULT = "DisengageHeroicUseModifyCooldown"
COOLDOWN_REF = "Abil," + HEROIC + ",Cost[0].Cooldown.TimeUse"


def check(condition, description):
    if not condition:
        raise ValueError(description)


def one(root, xpath):
    found = root.findall(xpath)
    check(len(found) == 1, "Expected precisely one " + xpath)
    return found[0]


def catalog_overrides(stock, historical):
    check(
        digest(stock) == HERO_XML and digest(historical) == HISTORICAL, "Unexpected catalog input"
    )
    (hero,) = (h for h in json.loads(historical) if h["id"] == "Greymane")
    old_abilities = {a["id"]: a for a in hero["abilities"]["Greymane"]}
    (running,) = (t for t in hero["talents"]["13"] if t["id"] == RUNNING)
    check(
        running["description"] == "Increases Darkflight and Disengage's range by 35%.",
        "Historical range",
    )
    entries = ("GreymaneDarkflight", "GreymaneDisengage")
    check([old_abilities[a]["cooldown"] for a in entries] == [5, 5], "Historical base E cooldown")
    old_seconds = old_abilities[HEROIC]["cooldown"]
    check(
        old_seconds == 60 and old_abilities[HEROIC]["heroic"] is True,
        "Historical base heroic cooldown",
    )
    root = ET.fromstring(stock)
    check(
        one(root, "./const[@id='$GreymaneRunningWildRangeModifier']").get("value") == "0.35",
        "Stock range",
    )
    for entry in entries:
        check(
            one(root, f"./CAbilEffectTarget[@id='{entry}']/Cost/Cooldown").get("TimeUse") == "5",
            "Stock E cooldown",
        )
    paths = one(root, f"./CTalent[@id='{RUNNING}']/AbilityModificationArray").findall(
        "Modifications"
    )
    check(len(paths) == 9, "Expected seven range adjustments and two cooldown adjustments")
    talent = ET.Element("CTalent", id=RUNNING)
    modifications = ET.SubElement(talent, "AbilityModificationArray", index="0")
    for i, entry in enumerate(entries, 7):
        mod = paths[i]
        actual = [(e.tag, e.get("value")) for e in mod]
        check(
            actual
            == [
                ("Type", "FlatModification"),
                ("Entry", entry),
                ("Field", "Cost.Cooldown.TimeUse"),
                ("Value", "-1.000000"),
            ],
            "Stock talent cooldown adjustment",
        )
        mod_override = ET.SubElement(modifications, "Modifications", index=str(i))
        ET.SubElement(mod_override, "Value", value="0")
    switch = one(root, f"./CEffectSwitch[@id='{SWITCH}']")
    case = one(switch, "CaseArray")
    check(
        case.attrib
        == {
            "Validator": "GreymaneHasDarkflightDisengageRunningWild",
            "Effect": DEFAULT + "RunningWild",
        }
        and one(switch, "CaseDefault").get("value") == DEFAULT,
        "Stock heroic switch",
    )
    for effect, seconds in [(DEFAULT, "5"), (DEFAULT + "RunningWild", "4")]:
        check(
            one(root, f"./CEffectModifyUnit[@id='{effect}']/Cost").attrib
            == {
                "Abil": "GreymaneDisengage,Execute",
                "CooldownOperation": "Set",
                "CooldownTimeUse": seconds,
            },
            "Stock heroic route",
        )
    heroic_users = {
        s.get("id")
        for s in root
        if s.tag == "CEffectSet"
        and any(e.get("value") == SWITCH for e in s.findall("EffectArray"))
    }
    check(
        heroic_users == {HEROIC + "CastSet", HEROIC + "FreeCastCastSet"}, "Stock heroic dispatch"
    )
    switch_override = ET.Element("CEffectSwitch", id=SWITCH)
    ET.SubElement(switch_override, "CaseArray", index="0", Effect=DEFAULT)
    check(
        one(root, f"./CAbilEffectTarget[@id='{HEROIC}']/Cost/Cooldown").get("TimeUse") == "80",
        "Stock base heroic cooldown",
    )
    reset_rows = one(root, f"./CEffectModifyPlayer[@id='{RESET}']").findall("EffectArray")
    check(
        len(reset_rows) == 3
        and reset_rows[2].attrib == {"Operation": "Set", "Reference": COOLDOWN_REF, "Value": "80"},
        "Stock heroic cooldown reset",
    )
    ability = ET.Element("CAbilEffectTarget", id=HEROIC)
    ET.SubElement(ET.SubElement(ability, "Cost"), "Cooldown", TimeUse=str(old_seconds))
    reset = ET.Element("CEffectModifyPlayer", id=RESET)
    ET.SubElement(reset, "EffectArray", index="2", Value=str(old_seconds))
    return talent, switch_override, reset, ability


def build(source_map, stock_xml, historical_json, output, stormlib=None):
    source, output = Path(source_map), Path(output)
    if output.exists() or output.is_symlink() or source.resolve() == output.resolve():
        raise FileExistsError("A new output is required")
    image = source.read_bytes()
    check(
        len(image) == 2130235 and digest(image) == BASE_MAP,
        "Expected the pinned original-layout two-talent map",
    )
    talent, switch, reset, ability = catalog_overrides(
        Path(stock_xml).read_bytes(), Path(historical_json).read_bytes()
    )
    storm = Storm(stormlib)
    before, source_checks = inventory(source, storm)
    check(
        EFFECTS not in before and ABILITIES not in before,
        "Unexpected existing effect or ability catalog",
    )
    check(
        digest(before[TALENTS])
        == "eb7c819c8f70eb5a97e5400fe54b960de6b72a7da9b77fd28e4f1a476eaacf69"
        and digest(before[BEHAVIORS])
        == "f3dfc79cd3940b6ea3b9de9ee2ed234955609af9a9948b1065e22ced282018c1",
        "Earlier talent rules changed",
    )
    edits = {
        TALENTS: before[TALENTS].replace(
            b"</Catalog>", ET.tostring(talent, encoding="us-ascii") + b"\r\n</Catalog>"
        ),
        EFFECTS: conventional_catalog([switch, reset]),
        ABILITIES: conventional_catalog([ability]),
    }
    with TemporaryDirectory(dir=output.parent) as temp:
        candidate = Path(temp) / "candidate.s2ma"
        candidate.write_bytes(image)
        storm.replace(candidate, edits)
        after, checks = inventory(candidate, storm)
        check(after == {**before, **edits}, "Reopened map member mismatch")
        check(source.read_bytes() == image, "Source map changed")
        new_image = candidate.read_bytes()
        os.link(candidate, output)
    return {
        "format": "dragon-shire-original-layout-greymane-cooldowns-v1",
        "source_map_sha256": BASE_MAP,
        "source_map_bytes": len(image),
        "map_sha256": digest(new_image),
        "map_bytes": len(new_image),
        "hero_xml_sha256": HERO_XML,
        "historical_catalog_sha256": HISTORICAL,
        "members": [
            {"name": k, "before": digest(before[k]) if k in before else None, "after": digest(v)}
            for k, v in sorted(edits.items())
        ],
        "original_content_members_unchanged": len(before.keys() - edits.keys()),
        "base_integrity": source_checks,
        "new_integrity": checks,
        "cooldown_edits": {
            "running_wild_darkflight_flat": [-1, 0],
            "running_wild_disengage_flat": [-1, 0],
            "running_wild_heroic_disengage_case": [DEFAULT + "RunningWild", DEFAULT],
            "go_for_the_throat_base_seconds": [80, 60],
            "go_for_the_throat_reset_seconds": [80, 60],
        },
        "range_bonus_percent": 35,
        "heroic_disengage_41810_absolute_time_independently_verified": False,
        "native_playback_verified": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ["source-map", "stock-xml", "historical-json", "output"]:
        parser.add_argument("--" + arg, required=True, type=Path)
    parser.add_argument("--stormlib")
    args = parser.parse_args()
    print(
        json.dumps(
            build(
                args.source_map, args.stock_xml, args.historical_json, args.output, args.stormlib
            ),
            indent=2,
        )
    )
