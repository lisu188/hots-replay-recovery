"""Restore Dragon Shire's modern default announcer assignment on two pinned historical layouts."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from build_dragonshire_talent_map import inventory
from build_gate_order_map import definition
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from runtime_catalog_probe import Storm

MEMBER = "MapScript.galaxy"
OLD = "e0a58745837b3b5351015c933560dbffb178d747009d2d57b4153ef425cf7250"
STOCK = "f557190f8aaab160789272ce086b8b69d6a8037b152de150332603dae3dc098f"
PARENTS = {
    "2d5cba9c5fd8276ae62468533fae558222730d55b146d41b7ebb7d30532e70b7": (2171327, "8d990dfbdc32b50d8667aafdcd409c02a3ecffd39fb5cfc351833e234f047b40"),
    "786f04a19c4222d5e81faefd7363c5422c16b49216732c28a773c74d853e10a9": (2171315, "5ec2366f97c21b21d00233aa3c078b42f266ef5cce2e9ff5561ccacaca8fcd29"),
}
OLD_CALL = b"    libCore_gf_DataAnnouncerVOSetAnnouncerPackForPlayerGroup(PlayerGroupAll(), 1);"
OLD_INIT = b'    libCore_gf_DataInitializeAnnouncerVOPackSingle(1, "LadyofThorns", StringExternal("Param/Value/92AA5A0D"));'
DEFAULT = b'    libCore_gf_DataAnnouncerVOSetDefaultAnnouncerForPlayerGroup(PlayerGroupAll(), "LadyofThorns");'
CORE = b"    TriggerExecute(libCore_gt_InitializeStormMod, true, true);"
TRIBUTE = b"    TriggerExecute(gt_InitializeTribute, true, true);"


def require(check, message):
    if not check:
        raise ValueError(message)


def digest(raw):
    return sha256(raw).hexdigest()


def script(path):
    with closing(MPQArchive(path)) as archive:
        return read_member(archive, MEMBER)


def init_lines(data):
    text = data.decode("utf-8-sig").replace("\r\n", "\n")
    return definition(text, "bool", "gt_InitializeMap_Func").encode("ascii").splitlines()


def check_parent(parent):
    data = parent.read_bytes()
    entry = PARENTS.get(digest(data))
    require(entry is not None and entry == (len(data), digest(script(parent))), "Unexpected parent map")
    return data


def expected(parent_script, stock, historical):
    require(digest(stock.read_bytes()) == STOCK and digest(historical.read_bytes()) == OLD, "Wrong reference archives")
    stock_lines = init_lines(script(stock))
    original_lines = init_lines(script(historical))
    lines = init_lines(parent_script)
    i = stock_lines.index(CORE)
    require(stock_lines[i:i+3] == [CORE, TRIBUTE, DEFAULT] and stock_lines.count(DEFAULT) == 1, "Stock init differs")
    for candidate in (lines, original_lines):
        i = candidate.index(CORE)
        require(candidate[i:i+4] == [CORE, OLD_INIT, OLD_CALL, b"    return true;"], "Historical init differs")
    require(parent_script.count(OLD_CALL) == 1 and DEFAULT not in parent_script, "Ambiguous patch")
    require(parent_script.count(OLD_CALL+b"\r\n") == 1, "Wrong line endings")
    return parent_script.replace(OLD_CALL+b"\r\n", OLD_CALL+b"\r\n"+DEFAULT+b"\r\n", 1)


def verify(parent, candidate, stock, historical, stormlib):
    original = check_parent(parent)
    storm = Storm(stormlib)
    old, old_checks = inventory(parent, storm)
    new, new_checks = inventory(candidate, storm)
    generated = new[MEMBER]
    require(new == {**old, MEMBER: expected(old[MEMBER], stock, historical)}, "Unexpected member changes")
    require(script(candidate) == generated and generated.replace(DEFAULT+b"\r\n", b"") == old[MEMBER],
            "Inserted line cannot be reversed")
    require(new_checks["content_members"] == old_checks["content_members"] == 70 and
            not any(new_checks["raw_table_results"]), "Archive integrity differs")
    require(parent.read_bytes() == original, "Parent modified")
    return dict(parent_sha256=digest(original), map_sha256=digest(candidate.read_bytes()), map_bytes=candidate.stat().st_size,
                script_sha256=digest(generated), inserted_script_bytes=len(DEFAULT)+2,
                identical_other_members=len(new)-1, archive_checks=new_checks, native_playback_verified=False)


def build(parent, output, stock, historical, stormlib):
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    original = check_parent(parent)
    generated = expected(script(parent), stock, historical)
    with TemporaryDirectory(dir=output.parent) as folder:
        temp = Path(folder) / "map.s2ma"
        temp.write_bytes(original)
        Storm(stormlib).replace(temp, {MEMBER: generated})
        result = verify(parent, temp, stock, historical, stormlib)
        os.link(temp, output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("parent", "output", "stock", "historical"):
        parser.add_argument(field, type=Path)
    parser.add_argument("--stormlib")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    action = verify if args.verify else build
    print(json.dumps(action(args.parent, args.output, args.stock, args.historical, args.stormlib), indent=2))
