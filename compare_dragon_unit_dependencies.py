"""Identify which Dragon Shire unit-catalog layers accompany the three pinned maps."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive

MAPS = {
    "original": "e0a58745837b3b5351015c933560dbffb178d747009d2d57b4153ef425cf7250",
    "stock_target": "f557190f8aaab160789272ce086b8b69d6a8037b152de150332603dae3dc098f",
    "historical_copy": "662a90d5ea72c8454d66a1070b3200e6a2929f3d2069e2c07ecc07cfcc79b800",
}
HEROES_UNITS = "e313828c13bf3b053abd3d58e5d78da72b111202977f0873617eefbfadc61bd5"
DRAGON_UNITS = "871c23230d951d1fd7bf61e57b51cf0d3e0e275c85a00a3bcd794223d9cf4217"
DRAGON_INFO = "14011927f94f9fb7531bc2f7ec533fd00881eba9a2c34b01e21a7049c0a48056"


def pinned(path, digest):
    data = path.read_bytes()
    if sha256(data).hexdigest() != digest:
        raise ValueError("Unexpected file digest for " + path.name)
    return data


def dependencies(info):
    return [node.text for node in ET.fromstring(info).findall("./Dependencies/Value")]


def unit_ids(raw):
    return sorted({n.attrib["id"] for n in ET.fromstring(raw) if n.tag.startswith("CUnit") and n.get("id")})


def inspect(original, target, historical, data_units, mod_units, mod_info):
    maps = {}
    for (name, digest), path in zip(MAPS.items(), (original, target, historical)):
        pinned(path, digest)
        with closing(MPQArchive(path)) as arc:
            info = read_member(arc, "DocumentInfo")
            catalog = read_member(arc, r"Base.StormData\GameData\UnitData.xml")
        maps[name] = dict(
            map_sha256=digest,
            dependency=dependencies(info),
            info_sha256=sha256(info).hexdigest(),
            unitdata_sha256=sha256(catalog).hexdigest(),
            unit_ids=unit_ids(catalog),
        )
    heroes = pinned(data_units, HEROES_UNITS)
    dragon = pinned(mod_units, DRAGON_UNITS)
    mod_deps = dependencies(pinned(mod_info, DRAGON_INFO))
    old, new, restored = [maps[name] for name in MAPS]
    if not (
        old["dependency"] == restored["dependency"] == mod_deps
        and old["dependency"] != new["dependency"]
        and old["unitdata_sha256"] == restored["unitdata_sha256"]
        and old["info_sha256"] == restored["info_sha256"]
    ):
        raise ValueError("Unexpected layout dependency or UnitData content")
    core = ET.fromstring(dragon).find('./CUnit[@id="KingsCore"]')
    return dict(
        maps=maps,
        dragon_mod=dict(
            document_sha256=DRAGON_INFO,
            direct_dependencies=mod_deps,
            unitdata_sha256=DRAGON_UNITS,
            unit_ids=unit_ids(dragon),
            kings_core_abilities=[n.attrib["Link"] for n in core.findall("AbilArray")],
            kings_core_ai=core.find("AIThinkTree").attrib["value"],
        ),
        heroes_unitdata_sha256=HEROES_UNITS,
        also_in_heroes_unitdata=sorted(set(unit_ids(dragon)) & set(unit_ids(heroes))),
        target_numeric_links_for_historical_layout_verified=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("original", "target", "historical", "data-units", "mod-units", "mod-info"):
        parser.add_argument("--" + name, type=Path, required=True)
    a = parser.parse_args()
    print(
        json.dumps(
            inspect(a.original, a.target, a.historical, a.data_units, a.mod_units, a.mod_info), indent=2
        )
    )
