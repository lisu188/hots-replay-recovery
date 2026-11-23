"""Recover the 98348 ObjectUnit decimal-to-signed-20.12 path for ordinary map decimals."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import re
from xml.etree import ElementTree as ET

from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive

GATE = "bda7aafd1d63c77b3b4d29ff2afee96da09a3104b54b4a1d625bb299607d9008"


def fixed_coordinate(value):
    """The ordinary bounded map spelling, no scientific notation or saturation."""
    text = str(value)
    if not re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]{1,12})?", text):
        raise ValueError("Unsupported authored decimal")
    integer, _, digits = text.lstrip("+-").partition(".")
    denominator = 10**12
    numerator = int(digits.ljust(12, "0"))
    fixed = int(integer)*4096 + (4096*numerator + denominator//2)//denominator
    if text.startswith("-"):
        fixed = -fixed
    if not -(1 << 31) <= fixed < 1 << 31:
        raise ValueError("Outside verified signed coordinate range")
    return fixed


def object_rows(package, expected_digest):
    if sha256(package.read_bytes()).hexdigest() != expected_digest:
        raise ValueError("Map content differs")
    with closing(MPQArchive(package)) as a:
        root = ET.fromstring(read_member(a, "Objects"))
    rows = {}
    for unit in root.iter("ObjectUnit"):
        if unit.get("UnitType") is None:
            continue
        obj = int(unit.attrib["Id"])
        x, y, z = unit.attrib["Position"].split(",")
        if obj in rows:
            raise ValueError("Duplicate placed object ID")
        rows[obj] = dict(unit=unit.attrib["UnitType"], object_id=obj, x=fixed_coordinate(x),
                         y=fixed_coordinate(y), inexact_x=(Fraction(x)*4096).denominator != 1,
                         inexact_y=(Fraction(y)*4096).denominator != 1)
    return rows


def generate(package):
    rows = object_rows(package, GATE)
    inexact = sorted((r for r in rows.values() if r["inexact_x"] or r["inexact_y"]),
                     key=lambda r:r["object_id"])
    if len(rows) != 165 or [r["object_id"] for r in inexact] != [22,477,478,718,760]:
        raise ValueError("Unexpected opening map")
    for r in inexact:
        r["quarter_x_mod8"] = (r["x"] >> 10) & 7
        r["quarter_y_mod8"] = (r["y"] >> 10) & 7
    return dict(map_sha256=GATE, authored=len(rows), previously_inexact=len(inexact), rows=inexact)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map",type=Path)
    args=parser.parse_args()
    print(json.dumps(generate(args.map),indent=2))
