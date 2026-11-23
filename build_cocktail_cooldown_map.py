"""Restore the build-41810 base Gilnean Cocktail cooldown on the Greymane v2 map."""

import argparse
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import xml.etree.ElementTree as ET

from build_greymane_talent_map import (
    ABILITIES,
    HERO_XML,
    HISTORICAL,
    check,
    digest,
    inventory,
    one,
    Storm,
)

V2_MAP = "e8d151e5d574babf187e3c0b06cd4b29d2280ac085773afda36a3ebb9c79ffa7"
COCKTAIL = "GreymaneGilneanCocktail"


def build_cocktail(source_map, hero_xml, historical_json, output, stormlib=None):
    source, output = Path(source_map), Path(output)
    if output.is_symlink() or output.exists() or source.resolve() == output.resolve():
        raise FileExistsError("A new output is required")
    image = source.read_bytes()
    check(digest(image) == V2_MAP and len(image) == 2130976, "Expected the pinned Greymane v2 map")
    stock, historical = Path(hero_xml).read_bytes(), Path(historical_json).read_bytes()
    check(digest(stock) == HERO_XML and digest(historical) == HISTORICAL, "Catalog identity")
    root = ET.fromstring(stock)
    active = one(root, f"./CAbilEffectTarget[@id='{COCKTAIL}']")
    check(
        one(active, "Cost/Cooldown").attrib == {"TimeUse": "9"},
        "Expected the 98348 nine-second base cooldown",
    )
    check(
        one(active, "Effect").attrib == {"value": COCKTAIL + "InitialSet"},
        "Unexpected target ability",
    )
    (genn,) = [h for h in json.loads(historical) if h["id"] == "Greymane"]
    (old,) = [a for a in genn["abilities"]["Greymane"] if a["id"] == COCKTAIL]
    check(
        old["shortcut"] == "Q" and old["name"] == "Gilnean Cocktail" and old["cooldown"] == 8,
        "Unexpected historical Q",
    )
    override = ET.Element("CAbilEffectTarget", id=COCKTAIL)
    ET.SubElement(ET.SubElement(override, "Cost"), "Cooldown", TimeUse=str(old["cooldown"]))
    storm = Storm(stormlib)
    before, _ = inventory(source, storm)
    ability_catalog = before[ABILITIES]
    check(
        ability_catalog.count(b"</Catalog>") == 1
        and len(ET.fromstring(ability_catalog)) == 1
        and one(ET.fromstring(ability_catalog), "./CAbilEffectTarget").get("id")
        == "GreymaneGoForTheThroat",
        "Unexpected existing ability declarations",
    )
    corrected = ability_catalog.replace(
        b"</Catalog>", ET.tostring(override, encoding="us-ascii") + b"\r\n</Catalog>"
    )
    with TemporaryDirectory(dir=output.parent) as temp:
        candidate = Path(temp) / "candidate.s2ma"
        candidate.write_bytes(image)
        storm.replace(candidate, {ABILITIES: corrected})
        after, checks = inventory(candidate, storm)
        check(
            after == {**before, ABILITIES: corrected},
            "Reopened candidate differs outside the intended edit",
        )
        check(source.read_bytes() == image, "Input changed")
        new_image = candidate.read_bytes()
        os.link(candidate, output)
    return {
        "format": "41810-original-layout-gilnean-cocktail-base-cooldown-v1",
        "source_map_sha256": V2_MAP,
        "map_sha256": digest(new_image),
        "map_bytes": len(new_image),
        "hero_xml_sha256": HERO_XML,
        "historical_catalog_sha256": HISTORICAL,
        "member": ABILITIES,
        "before_member_sha256": digest(ability_catalog),
        "after_member_sha256": digest(corrected),
        "unchanged_content_members": len(before) - 1,
        "integrity": checks,
        "change": {"id": COCKTAIL, "field": "Cost.Cooldown.TimeUse", "stock": 9, "restored": 8},
        "incendiary_elixir_historical_cooldown_and_damage_restored": False,
        "concentrated_blast_restored": False,
        "damage_restored": False,
        "native_playback_verified": False,
    }


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ["source-map", "stock-xml", "historical-json", "output"]:
        cli.add_argument("--" + name, required=True, type=Path)
    cli.add_argument("--stormlib")
    args = cli.parse_args()
    print(
        json.dumps(
            build_cocktail(
                args.source_map, args.stock_xml, args.historical_json, args.output, args.stormlib
            ),
            indent=2,
        )
    )
