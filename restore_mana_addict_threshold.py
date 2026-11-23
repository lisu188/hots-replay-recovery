"""Restore the two 41810 Mana Addict quest thresholds in a copy of the pinned 98348 catalog."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

STOCK_SHA256 = "39cf6954288e32edd73dfed13f82e45ab5f944a54f9f3fa9adaf2aacc7ffc13b"
HISTORICAL_SHA256 = "aaf264de6c3e31ce4bee1b1a5d658d695036393e4077e539630dd553698e9bbb"
TOKEN = "KaelthasManaAddictQuestToken"
TALENT = "KaelthasManaAddict"
FIELDS = (
    ("CBehaviorTokenCounter", TOKEN, "ConditionalEvents", "CompareValue"),
    ("CTalent", TALENT, "QuestData", "TargetCount"),
)


def thresholds(data):
    root = ET.fromstring(data)
    (gate,) = root.findall(f"./CBehaviorTokenCounter[@id='{TOKEN}']/ConditionalEvents")
    (award,) = gate.findall("Event")
    (display,) = root.findall(f"./CTalent[@id='{TALENT}']/QuestData")
    if (
        gate.get("Compare") != "GE"
        or award.attrib
        != {"EventId": "QuestComplete", "Effect": "KaelthasArcaneBarrierApplyUnlockingCarry"}
        or display.get("StackBehavior") != TOKEN
    ):
        raise ValueError("Unexpected token condition, award, or quest counter")
    return int(gate.attrib["CompareValue"]), int(display.attrib["TargetCount"])


def restore_mana_addict(stock, historical):
    if (
        len(stock) != 276044
        or sha256(stock).hexdigest() != STOCK_SHA256
        or thresholds(stock) != (20, 20)
    ):
        raise ValueError("Expected the original pinned KaelthasData.xml from 98348")
    if sha256(historical).hexdigest() != HISTORICAL_SHA256:
        raise ValueError("Expected the pinned build-41810 hero catalog")
    (hero,) = [h for h in json.loads(historical) if h["id"] == "Kaelthas"]
    (option,) = [t for t in hero["talents"]["1"] if t["id"] == TALENT]
    if "gathered 25 Regeneration Globes" not in option["description"]:
        raise ValueError("Unexpected historical unlock rule")

    # Locate each attribute inside its own record. Keep the surrounding XML bytes
    # intact, including comments, formatting and fields owned by other talents.
    corrected = bytearray(stock)
    changes = []
    for kind, entry, child, attribute in FIELDS:
        opening = f'<{kind} id="{entry}"'.encode("ascii")
        start = stock.index(opening)
        end = stock.index(f"</{kind}>".encode("ascii"), start)
        child_start = stock.index(f"<{child} ".encode("ascii"), start, end)
        child_end = stock.index(b">", child_start, end)
        needle = f'{attribute}="20"'.encode("ascii")
        offset = stock.index(needle, child_start, child_end) + len(needle) - 2
        corrected[offset] = ord("5")
        changes.append(
            dict(
                record=entry,
                field=f"{child}.{attribute}",
                byte_offset=offset,
                stock=20,
                historical=25,
            )
        )

    restored = bytes(corrected)
    if thresholds(restored) != (25, 25) or sum(a != b for a, b in zip(restored, stock)) != 2:
        raise ValueError("Corrected catalog failed field or byte accounting")
    report = dict(
        format="kaelthas-mana-addict-threshold-restoration-v1",
        source_build=41810,
        target_build=98348,
        stock_xml_sha256=STOCK_SHA256,
        historical_catalog_sha256=HISTORICAL_SHA256,
        corrected_xml_sha256=sha256(restored).hexdigest(),
        xml_bytes=len(restored),
        changes=changes,
        effective_map_catalog_verified=False,
        native_playback_verified=False,
    )
    return restored, report


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--target-xml", required=True, type=Path)
    cli.add_argument("--historical-catalog", required=True, type=Path)
    cli.add_argument(
        "--emit-xml",
        action="store_true",
        help="Emit corrected XML bytes instead of the change report",
    )
    args = cli.parse_args()
    raw, report = restore_mana_addict(
        args.target_xml.read_bytes(), args.historical_catalog.read_bytes()
    )
    sys.stdout.buffer.write(
        raw if args.emit_xml else (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    )
