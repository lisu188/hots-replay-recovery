"""Build an ordered GatesOpen callback at its original Dragon Shire timer registration."""

import argparse
import json
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from build_dragonshire_talent_map import digest, inventory
from runtime_catalog_probe import Storm


PARENT = "58874aca37caeacaf42789a7e90fd2da830559f6cd744c32f5724e4477a6fcb3"
SCRIPT = "01bb74353fef719b11b0314da6f069e9b43a424705b130ab475fd8e37bbbc68f"
GAME = "a6384749fbe8f676cbd6ccb9ec1aeac004815d37a8e1c2f8f9f8f176b2bfca09"
EVIDENCE = "ded8beecd894b3478374990ef433ee4da9ed5821ebb8a3d3d5cee781ac6ae578"
MEMBER = "MapScript.galaxy"
GATE = "libGame_gt_OpenTheGatesOpenTheGatesTimerExpires"
CALL = "gt_HistoricalGatesOpen_Func"
INIT = "gf_HistoricalGatesOpenInit"
TRIGGERS = "gf_HistoricalGameInitTriggers"
LIB = "gf_HistoricalGameInitLib"
REMOVE = "gf_RemoveGateBlockersInOrder"
GROUPS = ("auto157DB87C", "auto4CAD3EA8")

SORTER = """void gf_RemoveGateBlockersInOrder (unitgroup blockers) {
    int remaining;
    int index;
    unit selected;
    unit candidate;
    point position;
    fixed x;
    fixed y;
    fixed selectedX;
    fixed selectedY;
    remaining = UnitGroupCount(blockers, c_unitCountAll);
    while (remaining > 0) {
        selected = null;
        for (index = remaining; index > 0; index -= 1) {
            candidate = UnitGroupUnitFromEnd(blockers, index);
            if (candidate != null) {
                position = UnitGetPosition(candidate);
                x = PointGetX(position);
                y = PointGetY(position);
                if (selected == null || y < selectedY || (y == selectedY && x < selectedX)) {
                    selected = candidate;
                    selectedX = x;
                    selectedY = y;
                }
            }
        }
        if (selected == null) {
            return;
        }
        UnitGroupRemove(blockers, selected);
        UnitRemove(selected);
        remaining = UnitGroupCount(blockers, c_unitCountAll);
    }
}"""


def definition(source, kind, name):
    pattern = rf"^{kind} {name} \([^\n]*?\) \{{.*?^\}}"
    (body,) = re.findall(pattern, source, re.M | re.S)
    return body


def once(source, old, new):
    if source.count(old) != 1:
        raise ValueError("Unrecognized source splice: " + old[:75])
    return source.replace(old, new)


def iteration(group):
    return f"""        {group}_u = UnitGroupCount({group}_g, c_unitCountAll);
        for (;; {group}_u -= 1) {{
            lv_itBlocker = UnitGroupUnitFromEnd({group}_g, {group}_u);
            if (lv_itBlocker == null) {{ break; }}
            UnitRemove(lv_itBlocker);
        }}"""


def patch(raw, stock, evidence):
    if (digest(raw), digest(stock), digest(evidence)) != (SCRIPT, GAME, EVIDENCE):
        raise ValueError("Wrong script, stock library or spatial control receipt")
    cases = json.loads(evidence)["cases"]
    old = [c for c in cases if c["build"] == 41810]
    if len(old) != 4 or len({c["sha256"] for c in old}) != 4 or any(
        (c["tick"], c["exact_order_positions"]) != (610, 54) for c in old
    ):
        raise ValueError("Unexpected historical controls")
    game = stock.decode("utf-8-sig").replace("\r\n", "\n")
    script = raw.decode("ascii").replace("\r\n", "\n")
    for name in (CALL, INIT, TRIGGERS, LIB, REMOVE):
        if name in game or name in script:
            raise ValueError("Name collision")
    callback = definition(game, "bool", GATE + "_Func")
    callback = once(callback, "bool " + GATE + "_Func (", "bool " + CALL + " (")
    callback = once(callback, "    unit lv_itBlocker;\n", "")
    for group in GROUPS:
        callback = once(callback, f"    int {group}_u;\n", "")
        callback = once(callback, iteration(group), f"        {REMOVE}({group}_g);")
    registration = definition(game, "void", GATE + "_Init")
    registration = once(registration, "void " + GATE + "_Init (", "void " + INIT + " (")
    registration = once(registration, f'TriggerCreate("{GATE}_Func")', f'TriggerCreate("{CALL}")')
    triggers = definition(game, "void", "libGame_InitTriggers")
    triggers = once(triggers, "void libGame_InitTriggers (", "void " + TRIGGERS + " (")
    triggers = once(triggers, GATE + "_Init();", INIT + "();")
    init = definition(game, "void", "libGame_InitLib")
    init = once(init, "void libGame_InitLib (", "void " + LIB + " (")
    init = once(init, "    libGame_InitTriggers();", "    " + TRIGGERS + "();")
    map_init = definition(script, "void", "InitLibs")
    bound = once(map_init, "    libGame_InitLib();", "    " + LIB + "();")
    changed = once(script, map_init, "\n\n".join((SORTER, callback, registration, triggers, init, bound)))
    return changed.replace("\n", "\r\n").encode("ascii")


def build(parent, library, evidence, output, stormlib=None):
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    image = parent.read_bytes()
    if (len(image), digest(image)) != (2141688, PARENT):
        raise ValueError("Unexpected KeepCatapults archive")
    storm = Storm(stormlib)
    before, _ = inventory(parent, storm)
    changed = patch(before[MEMBER], library.read_bytes(), evidence.read_bytes())
    with TemporaryDirectory(dir=output.parent) as tmp:
        candidate = Path(tmp) / "candidate.s2ma"
        candidate.write_bytes(image)
        storm.replace(candidate, {MEMBER: changed})
        after, checks = inventory(candidate, storm)
        if after != {**before, MEMBER: changed} or parent.read_bytes() != image:
            raise ValueError("Unexpected archive mutation")
        result = candidate.read_bytes()
        os.link(candidate, output)
    return dict(parent_sha256=PARENT, map_sha256=digest(result), bytes=len(result),
                game_sha256=GAME, evidence_sha256=EVIDENCE, script_sha256=digest(changed),
                unchanged_content_members=len(before)-1, integrity=checks,
                native_compilation_verified=False, native_playback_verified=False)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("parent", "library", "evidence", "output"):
        cli.add_argument("--" + name, required=True, type=Path)
    cli.add_argument("--stormlib")
    print(json.dumps(build(**vars(cli.parse_args())), indent=2))
