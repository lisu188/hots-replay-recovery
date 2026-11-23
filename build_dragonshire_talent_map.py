"""Build Dragon Shire map copies with the historical Mana Addict thresholds and optional Bed of Barbs slow."""

import argparse
from collections import Counter
from contextlib import closing
import ctypes
from hashlib import md5, sha256
import json
import os
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
import xml.etree.ElementTree as ET

from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from restore_bed_of_barbs import SLOW, restore_bed_of_barbs
from restore_mana_addict_threshold import TALENT, TOKEN, restore_mana_addict, thresholds
from runtime_catalog_probe import MAP_SHA256, Storm

MANIFEST = r"Base.StormData\GameData.xml"
INCLUDE = "GameData/TenGreymaneManaAddict.xml"
MEMBER = "Base.StormData\\" + INCLUDE.replace("/", "\\")
ORIGINAL_MAP = "e0a58745837b3b5351015c933560dbffb178d747009d2d57b4153ef425cf7250"
BEHAVIORS = r"Base.StormData\GameData\BehaviorData.xml"
TALENTS = r"Base.StormData\GameData\TalentData.xml"
INTERNAL = {"(attributes)", "(listfile)"}
EMPTY_CATALOG = b'<?xml version="1.0" encoding="us-ascii"?>\r\n<Catalog>\r\n</Catalog>\r\n'


def digest(data):
    return sha256(data).hexdigest()


def quest_override(stock_hero, historical_catalog):
    corrected, receipt = restore_mana_addict(stock_hero, historical_catalog)
    condition, target = thresholds(corrected)
    root = ET.Element("Catalog")
    token = ET.SubElement(root, "CBehaviorTokenCounter", id=TOKEN)
    ET.SubElement(token, "ConditionalEvents", index="0", CompareValue=str(condition))
    talent = ET.SubElement(root, "CTalent", id=TALENT)
    ET.SubElement(talent, "QuestData", TargetCount=str(target))
    ET.indent(root, space="    ")
    return ET.tostring(root, encoding="us-ascii", xml_declaration=True) + b"\n", receipt


def append_include(raw):
    root = ET.fromstring(raw)
    if (
        root.tag != "Includes"
        or [(e.tag, e.attrib) for e in root] != [("Catalog", {"path": "GameData/DoodadAutoData.xml"})]
        or raw.count(b"</Includes>") != 1
    ):
        raise ValueError("Unexpected base map include manifest")
    return raw.replace(b"</Includes>", f'    <Catalog path="{INCLUDE}" />\r\n</Includes>'.encode("ascii"))


def inventory(path, storm):
    """Account for every live block and cross-check decoded content members."""
    native = storm.members(path)
    with closing(MPQArchive(path)) as archive:
        listing = read_member(archive, "(listfile)").decode("ascii").splitlines()
        if len(listing) != len(set(listing)) or set(listing) & INTERNAL or set(listing) != native.keys():
            raise ValueError("MPQ member lists disagree")
        names = sorted(set(listing) | INTERNAL)
        indexes = [archive.get_hash_table_entry(name).block_table_index for name in names]
        live = {i for i, entry in enumerate(archive.block_table) if entry.flags & 0x80000000}
        if len(indexes) != len(live) or set(indexes) != live:
            raise ValueError("Unaccounted or aliased live block")
        for name in listing:
            if read_member(archive, name) != native[name]:
                raise ValueError("Archive readers disagree for " + name)
        if archive.get_hash_table_entry("(signature)") is not None:
            raise ValueError("Unexpected archive signature")

    lib = storm.lib
    lib.SFileVerifyFile.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
    lib.SFileVerifyFile.restype = ctypes.c_uint32
    lib.SFileVerifyRawData.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p]
    lib.SFileVerifyRawData.restype = ctypes.c_int
    handle = storm.open(path)
    try:
        tables = [lib.SFileVerifyRawData(handle, kind, None) for kind in range(1, 7)]
        flags = [lib.SFileVerifyFile(handle, name.encode("ascii"), 15) for name in names]
    finally:
        if not lib.SFileCloseArchive(handle):
            raise RuntimeError("Failed to close verification archive")
    if any(tables) or any(value & 0x02AB for value in flags):
        raise ValueError("StormLib reported an archive integrity error")
    image = path.read_bytes()
    if (
        image[:4] != b"MPQ\x1a"
        or len(image) != struct.unpack_from("<Q", image, 44)[0]
        or md5(image[:192]).digest() != image[192:208]
        or not all(struct.unpack_from("<QQ", image, 52))
        or struct.unpack_from("<I", image, 108)[0] != 16384
    ):
        raise ValueError("Unexpected v4 map layout")
    return native, dict(
        content_members=len(native),
        live_blocks=len(live),
        raw_table_results=tables,
        native_member_flags=dict(sorted(Counter(flags).items())),
    )


def conventional_catalog(nodes):
    elements = []
    for node in nodes:
        node.tail = None
        raw = ET.tostring(node, encoding="us-ascii", xml_declaration=False)
        elements.append(raw.replace(b"\n", b"\r\n") + b"\r\n")
    return EMPTY_CATALOG.replace(b"</Catalog>", b"".join(elements) + b"</Catalog>")


def build_map(source, hero_xml, historical_catalog, output, library=None, anubarak_xml=None):
    source, output = Path(source), Path(output)
    if output.exists() or output.is_symlink() or source.resolve() == output.resolve():
        raise FileExistsError("A new output path is required")
    image = source.read_bytes()
    map_sha = digest(image)
    known = {MAP_SHA256: (2228175, 98348), ORIGINAL_MAP: (2129774, 41810)}
    if map_sha not in known or len(image) != known[map_sha][0]:
        raise ValueError("Expected the pinned original or target Dragon Shire map")
    historical = Path(historical_catalog).read_bytes()
    override, correction = quest_override(Path(hero_xml).read_bytes(), historical)
    storm = Storm(library)
    before, stock_checks = inventory(source, storm)
    if before.get(BEHAVIORS) != EMPTY_CATALOG:
        raise ValueError("Unexpected map-authored behavior catalog")
    behavior_edits = []
    if map_sha == ORIGINAL_MAP:
        if MANIFEST in before or TALENTS in before:
            raise ValueError("Unexpected historical map catalog layout")
        behavior, talent = tuple(ET.fromstring(override))
        behavior_edits.append(behavior)
        edits = {TALENTS: conventional_catalog([talent])}
    else:
        if MEMBER in before:
            raise ValueError("Catalog override already present")
        edits = {MANIFEST: append_include(before[MANIFEST]), MEMBER: override}
    slow_correction = None
    if anubarak_xml is not None:
        restored, slow_correction = restore_bed_of_barbs(Path(anubarak_xml).read_bytes(), historical)
        (slow,) = ET.fromstring(restored).findall(
            f"./CBehaviorBuff[@id='{SLOW}']/Modification/UnifiedMoveSpeedFactor"
        )
        record = ET.Element("CBehaviorBuff", id=SLOW)
        modification = ET.SubElement(record, "Modification")
        ET.SubElement(modification, "UnifiedMoveSpeedFactor", value=slow.attrib["value"])
        behavior_edits.append(record)
    if behavior_edits:
        edits[BEHAVIORS] = conventional_catalog(behavior_edits)
    with TemporaryDirectory(dir=output.parent) as temp:
        staged = Path(temp) / "candidate.s2ma"
        staged.write_bytes(image)
        storm.replace(staged, edits)
        after, new_checks = inventory(staged, storm)
        if after != {**before, **edits}:
            raise ValueError("Reopened map differs outside the intended members")
        new_image = staged.read_bytes()
        if digest(source.read_bytes()) != map_sha:
            raise ValueError("Input map changed during conversion")
        # Atomic no-clobber publication of a fully validated file on the same volume.
        os.link(staged, output)

    changes = [
        dict(
            member=name,
            before_sha256=digest(before[name]) if name in before else None,
            after_sha256=digest(data),
        )
        for name, data in sorted(edits.items())
    ]
    return dict(
        format="dragon-shire-historical-talent-map-v1",
        map_reference_build=known[map_sha][1],
        target_catalog_build=98348,
        historical_rule_build=41810,
        base_map_sha256=map_sha,
        new_map_sha256=digest(new_image),
        new_map_bytes=len(new_image),
        mana_addict_correction=correction,
        bed_of_barbs_slow_correction=slow_correction,
        member_changes=changes,
        stock_integrity=stock_checks,
        new_integrity=new_checks,
        unchanged_original_content_members=len(before.keys() - edits.keys()),
        original_document_header_preserved=True,
        regenerated_map_sync_checksum=None,
        effective_native_catalog_verified=False,
        converted_replay_written=False,
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("source-map", "hero-xml", "historical-catalog", "output"):
        cli.add_argument("--" + name, required=True, type=Path)
    cli.add_argument("--stormlib", help="Optional path to the native archive library")
    cli.add_argument(
        "--anubarak-xml", type=Path, help="Include the historical Bed of Barbs slow from the pinned hero XML"
    )
    args = cli.parse_args()
    result = build_map(
        args.source_map, args.hero_xml, args.historical_catalog, args.output, args.stormlib, args.anubarak_xml
    )
    sys.stdout.buffer.write((json.dumps(result, indent=2, sort_keys=True) + "\n").encode())
