"""Resolve the static live CUnit Radius on the GateOrder map for TEN's opening slots."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from contextlib import nullcontext
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive


PROJECTION = "80c64713d4a9183d98e61e9b67f624ba230daa08d303dfb237b971733113eb7c"
GATE_ORDER = "bda7aafd1d63c77b3b4d29ff2afee96da09a3104b54b4a1d625bb299607d9008"
OPENING = "ffd00f3962dc232a303f23a45d12647e18d18ff87be0aa141e73a9e140bcf731"
MEMBER_SET = "7204da7f17be980c81eb82bc0df8bbef889e6261b386fff43e4d000b0a508daf"
CORE = "mods/core.stormmod/base.stormdata/"
HEROES = "mods/heroesdata.stormmod/base.stormdata/"
TRY_MODE = (
    "mods/heroes.stormmod/base.stormmaps/maps/heroes/singleplayermaps/"
    "(10)trymemode.stormmap/base.stormdata/gamedata/unitdata.xml"
)


def digest(data):
    return sha256(data).hexdigest()


def check(condition, message):
    if not condition:
        raise ValueError(message)


def pinned(path, expected):
    raw = path.read_bytes()
    check(digest(raw) == expected, "Unexpected content digest for " + path.name)
    return raw


def projected_catalogs(projection, archive):
    files = {
        r["path"]: r for r in json.loads(pinned(projection, PROJECTION))["source_files"]
        if r["kind"] == "XML"
    }
    found = []
    nodes = []
    directory = archive.is_dir()
    with (nullcontext() if directory else ZipFile(archive)) as z:
        for name in (files if directory else z.namelist()):
            raw = (archive / name).read_bytes() if directory else z.read(name)
            file = files[name]
            file_sha = digest(raw)
            check(file_sha == file["sha256"] and len(raw) == file["bytes"], name)
            root = ET.fromstring(raw)
            ids = [n for n in root if n.tag.startswith("CUnit")]
            if root.tag == "Includes" or ids:
                found.append((name, file_sha))
                nodes.extend((name, n) for n in ids)
    encoded = json.dumps(sorted(found), separators=(",", ":")).encode()
    check(digest(encoded) == MEMBER_SET, "CUnit and Includes member enumeration differs")
    check(len(files) == 5575 and len(nodes) == 1997, "Cohort changed")
    return files, nodes


def map_catalogs(map_path):
    pinned(map_path, GATE_ORDER)
    with closing(MPQArchive(map_path)) as archive:
        info = ET.fromstring(read_member(archive, "DocumentInfo"))
        deps = [n.text for n in info.findall("./Dependencies/Value")]
        check(deps == ["bnet:Heroes of the Storm (Data Mod)/0.0/999,file:Mods/HeroesData.StormMod"],
              "Expected the historical map dependency")
        objects = list(ET.fromstring(read_member(archive, "Objects")).iter("ObjectUnit"))
        check(len(objects) == 165 and all(n.get("Scale") == "1,1,1" for n in objects),
              "Unexpected authored unit scale or object count")
        names = read_member(archive, "(listfile)").decode().splitlines()
        nodes = []
        for path in names:
            if path.lower().endswith(".xml"):
                root = ET.fromstring(read_member(archive, path))
                if root.tag == "Catalog":
                    nodes.extend(("GateOrder/" + path.replace(chr(92), "/"), n)
                                 for n in root if n.tag.startswith("CUnit"))
    return Counter(n.attrib["UnitType"] for n in objects), nodes


def index_nodes(rows):
    out = defaultdict(list)
    for path, node in rows:
        check(node.tag == "CUnit", "Unrecognized unit class")
        out[node.get("id")].append((path, node))
    return out


def resolve_radius(index, unit):
    current = unit
    chain = []
    while current not in chain:
        chain.append(current)
        nodes = index[current]
        check(nodes, "Unbound CUnit parent " + str(current))
        parents = set()
        declarations = []
        for path, node in nodes:
            check(not (set(node.attrib) - {"id", "parent", "default"}), "Unhandled CUnit override")
            if node.get("parent"):
                parents.add(node.attrib["parent"])
            for field in node.findall("Radius"):
                check(set(field.attrib) == {"value"}, "Unsupported Radius field")
                declarations.append((path, Fraction(field.attrib["value"])))
        check(len(parents) <= 1, "Conflicting parents for " + str(current))
        if declarations:
            values = {v for _, v in declarations}
            check(len(values) == 1, "Conflicting Radius for " + str(current))
            fixed = values.pop() * 4096
            check(fixed.denominator == 1, "Radius does not map exactly to 1/4096")
            return {
                "radius_fixed4096": fixed.numerator,
                "field_owner": current if current is not None else "CUnit class default",
                "field_source": sorted({path for path, _ in declarations}),
                "chain": [v if v is not None else "CUnit class default" for v in chain],
            }
        current = next(iter(parents), None)
    raise ValueError("Cyclic or absent live Radius for " + unit)


def generate(projection, archive, gate_map, opening):
    files, installed_nodes = projected_catalogs(projection, archive)
    authored, map_nodes = map_catalogs(gate_map)
    rows = [x for x in json.loads(pinned(opening, OPENING)) if x["loop"] == 0]
    check([x["slot"] for x in rows] == list(range(172)), "First-epoch slots changed")
    units = Counter(r["unit"] for r in rows)
    check(units == authored + Counter(TownMercCampCaptureBeacon=5, DragonballCaptureBeacon=2),
          "Opening unit types differ from the map and script model")
    active = index_nodes([(p,n) for p,n in installed_nodes if p.startswith((CORE, HEROES))] + map_nodes)
    superset = index_nodes([(p,n) for p,n in installed_nodes if p != TRY_MODE] + map_nodes)
    all_nodes = installed_nodes + map_nodes
    dead_fields = [(p,n.get("id")) for p,n in all_nodes
                   if n.find("DeadRadius") is not None or "DeadRadius" in n.attrib]
    check(not dead_fields, "Found an explicit DeadRadius")
    by_unit = {}
    for unit in sorted(units):
        result = resolve_radius(active, unit)
        alternative = resolve_radius(superset, unit)
        check(result["radius_fixed4096"] == alternative["radius_fixed4096"]
              and result["chain"] == alternative["chain"], "Additional package changes " + unit)
        result["slots"] = [r["slot"] for r in rows if r["unit"] == unit]
        by_unit[unit] = result
    try_values = [n.find("Radius").get("value") for p,n in installed_nodes
                  if p == TRY_MODE and n.get("id") == "KingsCore"]
    check(try_values == ["0"], "Try Mode exception changed")
    return {
        "format": "ten-opening-live-catalog-radius-v1",
        "map_sha256": GATE_ORDER, "projection_sha256": PROJECTION,
        "verified_xml_files": len(files), "verified_xml_bytes": sum(f["bytes"] for f in files.values()),
        "unit_nodes_whole_projection": len(installed_nodes),
        "unit_nodes_gate_map": len(map_nodes), "opening_slots": len(rows),
        "distinct_opening_unit_types": len(by_unit), "authored_objects_with_uniform_unit_scale": 165,
        "all_other_packages_except_single_player_try_mode_preserve_each_value_and_chain": True,
        "explicit_dead_radius_fields": len(dead_fields), "dead_radius_fixed4096": None,
        "qualification": "Static live CUnit Radius from Core, HeroesData and GateOrder. Runtime use requires the live catalog branch without a per-instance size/radius modifier. The native DeadRadius default and per-object gameplay branch are separate.",
        "by_unit": by_unit,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("projection","archive","gate-map","opening","output"):
        parser.add_argument("--"+key, type=Path, required=True)
    args = parser.parse_args()
    result = generate(args.projection, args.archive, args.gate_map, args.opening)
    args.output.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8", newline="\r\n")
