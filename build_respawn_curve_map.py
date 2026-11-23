"""Restore observed build-41810 ordinary respawn times on the Greymane Dragon Shire map."""

import argparse
import json
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from build_dragonshire_talent_map import digest, inventory
from runtime_catalog_probe import Storm


BASE = "e6167145ee82e6c139f07336cd65fced5c86d162da19baad57a2d3e82b3a455e"
SCRIPT = "3cbca9c5b3c95bd0b5f8eb8d2218d129d89e21c3466cb242e7c54b22e67c7e18"
HEROESLIB = "15f0314a1c48a0391e76e22360847e7ef0c91b12a29da15d79453045c175a683"
HISTORICAL = "d3155fc0d75ad42b35b11ab1cc977e8c6b155b9e2733b364b5eb1693edff356b"
MEMBER = "MapScript.galaxy"
TRIGGER = "gt_HistoricalRespawnTimes_Func"
DECL = b"bool gt_InitializeMap_Func (bool testConds, bool runActions) {\r\n"
DISPATCH = b"    TriggerExecute(libCore_gt_InitializeStormMod, true, true);\r\n"


def patch_script(raw, heroeslib, evidence):
    if len(raw) != 32044 or digest(raw) != SCRIPT:
        raise ValueError("Unexpected original-layout map script")
    if len(heroeslib) != 268519 or digest(heroeslib) != HEROESLIB or digest(evidence) != HISTORICAL:
        raise ValueError("Unexpected dependency or historical timer observations")
    code = heroeslib.decode("utf-8-sig")
    initializer = code.split("bool libCore_gt_DataDeathTimes_Func (", 1)[1].split("\n}", 1)[0]
    stock = {int(k): int(v) for k, v in re.findall(r"libCore_gv_bALDeathTimes\[(\d+)\] = (\d+)\.0;", initializer)}
    old = {int(k): v for k, v in json.loads(evidence)["seconds_by_level"].items()}
    if set(stock) != set(range(1, 31)) or set(old) != set(range(1, 24)):
        raise ValueError("Unexpected level coverage")
    if (code.count("TriggerExecute(libCore_gt_DataDeathTimes, true, true);") != 1
            or code.count('libCore_gt_DataDeathTimes = TriggerCreate("libCore_gt_DataDeathTimes_Func");') != 1
            or code.count("TriggerExecute(libCore_gt_InitializeData, true, false);") != 1):
        raise ValueError("Unrecognized death table dispatch")
    if raw.count(DECL) != 1 or raw.count(DISPATCH) != 1 or TRIGGER.encode() in raw:
        raise ValueError("Unrecognized map callback")
    changes = {level: [stock[level], seconds] for level, seconds in sorted(old.items())
               if stock[level] != seconds}
    fn = [
        f"bool {TRIGGER} (bool testConds, bool runActions) {{",
        "    bool result = libCore_gt_DataDeathTimes_Func(testConds, runActions);",
        "    if (result && runActions) {",
        *(f"        libCore_gv_bALDeathTimes[{level}] = {seconds}.0;" for level, (_, seconds) in changes.items()),
        "    }", "    return result;", "}", "", "",
    ]
    install = f'    libCore_gt_DataDeathTimes = TriggerCreate("{TRIGGER}");\r\n'.encode("ascii")
    patched = raw.replace(DECL, "\r\n".join(fn).encode("ascii") + DECL)
    patched = patched.replace(DISPATCH, install + DISPATCH)
    return patched, changes


def build(source, library, evidence, output, stormlib=None):
    if output.exists() or output.is_symlink() or output.resolve() == source.resolve():
        raise FileExistsError("A new output is required")
    image = source.read_bytes()
    if len(image) != 2131152 or digest(image) != BASE:
        raise ValueError("Unexpected source map")
    storm = Storm(stormlib)
    before, _ = inventory(source, storm)
    replacement, changes = patch_script(before[MEMBER], library.read_bytes(), evidence.read_bytes())
    with TemporaryDirectory(dir=output.parent) as temp:
        candidate = Path(temp) / "candidate.s2ma"
        candidate.write_bytes(image)
        storm.replace(candidate, {MEMBER: replacement})
        after, checks = inventory(candidate, storm)
        if after != {**before, MEMBER: replacement} or source.read_bytes() != image:
            raise ValueError("Unexpected archive changes")
        final = candidate.read_bytes()
        os.link(candidate, output)
    return dict(source_map_sha256=BASE, map_sha256=digest(final), map_bytes=len(final),
                member=MEMBER, source_member_sha256=SCRIPT, member_sha256=digest(replacement),
                dependency_sha256=HEROESLIB, historical_observations_sha256=HISTORICAL,
                old_and_new_seconds_by_changed_level=changes,
                unsupported_levels_with_stock_values=list(range(24, 31)),
                unchanged_content_members=len(before)-1, integrity=checks,
                native_playback_verified=False)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for arg in ("source", "library", "evidence", "output"):
        cli.add_argument("--" + arg, required=True, type=Path)
    cli.add_argument("--stormlib")
    args = cli.parse_args()
    print(json.dumps(build(args.source, args.library, args.evidence, args.output, args.stormlib), indent=2))
