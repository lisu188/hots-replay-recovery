"""Restore the recorded build-41810 Bed of Barbs slow in a copy of the 98348 Anub'arak XML."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from xml.etree import ElementTree as ET


HISTORICAL_SHA = "aaf264de6c3e31ce4bee1b1a5d658d695036393e4077e539630dd553698e9bbb"
TARGET_SHA = "6e575d1c7e852274480b88e89e06ce993a9b8dd6f7988ccdc57e173c337eb799"
SLOW = "AnubarakImpaleBedOfBarbsSlow"


def restore_bed_of_barbs(stock, historical):
    """Return the corrected XML bytes and public field-level change report."""
    if len(stock) != 234204 or sha256(stock).hexdigest() != TARGET_SHA:
        raise ValueError("Expected the pinned 98348 AnubarakData.xml")
    if sha256(historical).hexdigest() != HISTORICAL_SHA:
        raise ValueError("Expected the pinned build-41810 hero catalog")
    hero, = (h for h in json.loads(historical) if h["id"] == "Anubarak")
    talent, = (t for t in hero["talents"]["7"] if t["id"] == "AnubarakMasteryBedOfBarbs")
    if "slows enemy Move Speed by 30%" not in talent["description"]:
        raise ValueError("Unexpected historical slow")

    field = "UnifiedMoveSpeedFactor"
    path = f"./CBehaviorBuff[@id='{SLOW}']/Modification/{field}"
    before, = ET.fromstring(stock).findall(path)
    if before.get("value") != "-0.25":
        raise ValueError("Unexpected target slow")
    start = stock.index(f'<CBehaviorBuff id="{SLOW}"'.encode("ascii"))
    end = stock.index(b"</CBehaviorBuff>", start)
    prefix = f'<{field} value="'.encode("ascii")
    attribute = prefix + b'-0.25"'
    if stock.count(attribute, start, end) != 1:
        raise ValueError("Ambiguous slow field in the target record")
    offset = stock.index(attribute, start, end) + len(prefix)
    restored = stock[:offset] + b"-0.30" + stock[offset + len(b"-0.25"):]
    after, = ET.fromstring(restored).findall(path)
    if after.get("value") != "-0.30" or len(restored) != len(stock):
        raise ValueError("Restored XML verification failed")

    report = dict(
        format="bed-of-barbs-slow-restoration-v1", source_build=41810, target_build=98348,
        historical_catalog_sha256=HISTORICAL_SHA, input_sha256=TARGET_SHA, size=len(restored),
        updated_sha256=sha256(restored).hexdigest(),
        edits=[dict(record=SLOW, field=field, stock=before.get("value"), restored=after.get("value"),
                    value_offset=offset)],
        changed_byte_offsets=[i for i, (a, b) in enumerate(zip(stock, restored)) if a != b],
        effective_native_catalog_verified=False, native_playback_verified=False,
    )
    return restored, report


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--target-xml", type=Path, required=True)
    cli.add_argument("--historical-catalog", type=Path, required=True)
    cli.add_argument("--emit-xml", action="store_true", help="Emit corrected XML bytes")
    args = cli.parse_args()
    data, report = restore_bed_of_barbs(args.target_xml.read_bytes(), args.historical_catalog.read_bytes())
    sys.stdout.buffer.write(data if args.emit_xml else (json.dumps(report, indent=2, sort_keys=True) + "\n").encode())
