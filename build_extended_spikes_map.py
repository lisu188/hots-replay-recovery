"""Construct a separate 98348 catalog candidate for TEN's opening Anub'arak purchase."""

import argparse
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET

from build_dragonshire_talent_map import EMPTY_CATALOG, TALENTS, digest, inventory
from runtime_catalog_probe import Storm

PARENT = "54e1a8fbe7e42f00b7b52cde420ed259105228fcdf165097ef52ecd0f5c4125a"
MODERN = "6e575d1c7e852274480b88e89e06ce993a9b8dd6f7988ccdc57e173c337eb799"
HISTORICAL = "aaf264de6c3e31ce4bee1b1a5d658d695036393e4077e539630dd553698e9bbb"
GENN = "78a564ee1334eeaee26c4b6c57a7dd5d5b3c048cba63a9b7131440d778b98cff"
HERO = r"Base.StormData\GameData\HeroData.xml"
EXTENDED = "AnubarakMasteryExtendedSpikesImpale"
ARMOR = "AnubarakNerubianArmor"
ATTRIBUTES = ("Creep", "Tower", "Minion", "Merc", "Structure", "Heroic", "Summoned")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pinned(path, expected):
    data = path.read_bytes()
    require(digest(data) == expected, "Wrong input " + path.name)
    return data


def one(parent, path):
    found, = parent.findall(path)
    return found


def prepare(archive_members, hero_xml, archive_json, genn_xml):
    require(HERO not in archive_members, "Hero catalog already exists")
    for name, raw in archive_members.items():
        if not name.lower().startswith("base.stormdata\\gamedata\\") or not name.lower().endswith(".xml"):
            continue
        root = ET.fromstring(raw)
        require(not root.findall("CHero[@id='Anubarak']") and not root.findall(f"CTalent[@id='{EXTENDED}']"),
                "Conflicting map-local definition")
    old, = (h for h in json.loads(archive_json) if h["id"] == "Anubarak")
    exemplar = one(ET.fromstring(genn_xml),
                   "CHero[@id='GreymaneWorgen']/LevelScalingArray[@index='6']/Modifications[@index='1']")
    require(exemplar.attrib == {"index":"1", "removed":"1"} and not len(exemplar),
            "Nested removal spelling differs from the installed catalog")
    first = old["talents"]["1"][0]
    require(first["id"] == EXTENDED and first["description"] == "Increases the max range of Impale by 25%.",
            "Historical tier, slot or documented purpose differs")
    xml = ET.fromstring(hero_xml)
    tree = one(xml, "CHero[@id='Anubarak']").findall("TalentTreeArray")
    require(len(tree) == 21 and tree[0].attrib == {"Talent":ARMOR,"Tier":"1","Column":"1"} and
            not len(tree[0]) and not any(row.get("Talent") == EXTENDED for row in tree),
            "Unexpected target selector zero or tree")
    ability = one(xml, f"CTalent[@id='{EXTENDED}']/AbilityModificationArray")
    require(ability.get("ModifyAbil") == "AnubarakImpale", "Unexpected target ability")
    fields = [{c.tag:c.attrib["value"] for c in m} for m in ability.findall("Modifications")]
    require(len(fields) == 13, "Unexpected number of modifications")
    require([(m["Entry"], m.get("Field"), m.get("Value")) for m in fields[:6]] == [
        ("AnubarakImpaleCreatePersistent", "PeriodCount", "2.000000"),
        ("AnubarakImpaleModelPersistent", "PeriodCount", "2.000000"),
        ("AnubarakImpaleGuideVisual", "Height", "3.000000"),
        ("AnubarakImpaleSpikes", None, None), ("AnubarakImpaleBedOfBarbsCast", None, None),
        ("AnubarakImpaleSoundPersistent", "PeriodicOffsetArray[0]", "-3.000000")],
        "Unexpected retained range, guide or sound definitions")
    hero = ET.Element("CHero", id="Anubarak")
    ET.SubElement(hero, "TalentTreeArray", index="0", Talent=EXTENDED)
    talent = ET.Element("CTalent", id=EXTENDED)
    corrections = ET.SubElement(talent, "AbilityModificationArray", index="0")
    for index, attribute in reversed(list(enumerate(ATTRIBUTES, 6))):
        require(fields[index] == dict(Type="FlatModification", Catalog="Effect", Entry="AnubarakImpaleDamage",
                                      Field=f"AttributeFactor[{attribute}]", Value="0.250000"),
                f"Unexpected stock damage modifier {index}")
        ET.SubElement(corrections, "Modifications", index=str(index), removed="1")
    talent_data = archive_members[TALENTS]
    require(talent_data.count(b"</Catalog>") == 1, "Unexpected map talent catalog")
    def insert(data, node):
        return data.replace(b"</Catalog>", ET.tostring(node, encoding="ascii", xml_declaration=False) + b"\r\n</Catalog>")
    return {TALENTS:insert(talent_data, talent), HERO:insert(EMPTY_CATALOG, hero)}


def build(parent, target_xml, historical, genn_xml, output, stormlib):
    require(not output.exists() and not output.is_symlink(), "A fresh output path is required")
    stock = pinned(parent, PARENT)
    storm = Storm(stormlib)
    before, parent_checks = inventory(parent, storm)
    edits = prepare(before, pinned(target_xml, MODERN), pinned(historical, HISTORICAL), pinned(genn_xml, GENN))
    with TemporaryDirectory(dir=output.parent) as temp:
        staged = Path(temp) / "candidate.s2ma"
        staged.write_bytes(stock)
        storm.replace(staged, edits)
        after, checks = inventory(staged, storm)
        require(after == {**before, **edits} and parent.read_bytes() == stock, "Unaccounted MPQ changes")
        image = staged.read_bytes()
        os.link(staged, output)
    return dict(parent_sha256=PARENT,candidate_sha256=digest(image),candidate_bytes=len(image),
                source_catalog_sha256=HISTORICAL,current_hero_sha256=MODERN,parent_checks=parent_checks,
                candidate_checks=checks,unchanged_content_members=len(before)-1,added_member=HERO,
                changed_member=TALENTS,member_sha256={k:digest(v) for k,v in edits.items()},
                target_slot=0,tier=1,column=1,stock_choice=ARMOR,projected_choice=EXTENDED,
                removal_exemplar_sha256=GENN,removed_flat_modification_indices=list(range(12,5,-1)),
                unchanged_modification_indices=list(range(6)),
                historic_shape_verified=False,native_catalog_loading_verified=False,replay_written=False)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("parent","target_xml","historical","genn_xml","output"):
        cli.add_argument(name,type=Path)
    cli.add_argument("--stormlib")
    print(json.dumps(build(**vars(cli.parse_args())),indent=2))
