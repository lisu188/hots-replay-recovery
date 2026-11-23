"""Build the historical Dragon Shire keep-only catapult gate from authenticated local scripts."""

import argparse
import json
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from build_dragonshire_talent_map import digest, inventory
from runtime_catalog_probe import Storm

BASE = "f4d3b425cd9df5ed5390c45dc3c770300a64ba95449c82c228eed8b9928c7d6f"
SCRIPT = "d8a61a9d7af2c851499ebbf49f8f429a864ef1b94ba08761269cead38f748560"
GAME = "a6384749fbe8f676cbd6ccb9ec1aeac004815d37a8e1c2f8f9f8f176b2bfca09"
EVIDENCE = "b8601157db5d26f08ae24ca125fa4f507c5f4b654c9f9b9c15ff2d9ec3d0ee37"
MEMBER = "MapScript.galaxy"
STOCK_UNIT = "libGame_gf_MinionSpawnMinion"
UNIT = "gf_HistoricalMinionSpawnMinion"
STOCK_WAVE = "auto_libGame_gf_MinionSpawnWave_TriggerFunc"
WAVE = "gt_HistoricalMinionWave_Func"
DISPATCH = "auto_libGame_gf_MinionSpawnWave_Trigger"
KEEP = "gf_HistoricalEnemyKeepDestroyed"
HOOK = "bool gt_HistoricalWaveStart_Func ("
PERIOD = "        libCore_gv_bALMinionWaveInterval = 30.0625;"


def definition(text, kind, name):
    (body,) = re.findall(
        r"^" + kind + " " + name + r" \([^\n]*?\) \{.*?^\}", text, re.M | re.S
    )
    return body


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("Unrecognized source splice")
    return text.replace(old, new)


def patch_script(raw, library, evidence):
    if (digest(raw), digest(library), digest(evidence)) != (SCRIPT, GAME, EVIDENCE):
        raise ValueError("Unrecognized wave map, GameLib or control evidence")
    cases = json.loads(evidence)
    if len({r["sha256"] for r in cases}) != 19 or any(
        r["rules"][str(r["build"])]["missed"] or r["rules"][str(r["build"])]["excess"]
        for r in cases
    ):
        raise ValueError("Catapult schedule disagrees with recorded controls")
    game = library.decode("utf-8-sig").replace("\r\n", "\n")
    original = raw.decode("ascii").replace("\r\n", "\n")
    if (
        'include "TriggerLibs/GameLib"' not in original
        or original.count("lv_makesCoreVulnerableWhenKilled = true;") != 6
    ):
        raise ValueError("Expected twelve-town Dragon Shire map with six keeps")
    if (
        game.count(DISPATCH + " = TriggerCreate(") != 1
        or ("trigger " + DISPATCH + " = null;") not in game
    ):
        raise ValueError("Unexpected native wave callback registration")
    unit = once(
        definition(game, "void", STOCK_UNIT),
        "void " + STOCK_UNIT + " (",
        "void " + UNIT + " (",
    )
    (line,) = [
        s
        for s in unit.splitlines()
        if s.startswith("    if (") and "libGame_gf_TownsAliveinLane" in s
    ]
    keep_prefix = " || (libGame_gf_TownsAliveinLane("
    pos = line.index(keep_prefix)
    condition = line[:pos]
    if (
        "libGame_gv_minion_CatapultCap_C" not in condition
        or "libGame_gv_minionMapNeverSpawnsCatapults" not in condition
    ):
        raise ValueError("Stock map or cap guard missing")
    limit = condition.count("(") - condition.count(")")
    condition += " || (!" + KEEP + "(lp_lane, lp_owner))" + ")" * limit + " {"
    unit = once(unit, line, condition)
    if (
        "libGame_gf_TownsAliveinLane" in unit
        or "libGame_gv_minion_PeriodicCatapultsFirstWave" in unit
    ):
        raise ValueError("Stock town gate still active")
    wave = once(
        definition(game, "bool", STOCK_WAVE),
        "bool " + STOCK_WAVE + " (",
        "bool " + WAVE + " (",
    )
    wave = once(
        wave,
        STOCK_UNIT + "(lp_lane, lp_owner, lv_minionType, lv_spawnPoint);",
        UNIT + "(lp_lane, lp_owner, lv_minionType, lv_spawnPoint);",
    )
    keep = """bool gf_HistoricalEnemyKeepDestroyed (int lp_lane, int lp_owner) {
    int town;
    int enemy = libGame_gf_ComputerPlayerInTeam(libGame_gf_EnemyTeam(libGame_gf_TeamNumberOfPlayer(lp_owner)));
    for (town = 1; town <= libGame_gv_townTownCount; town += 1) {
        if (libGame_gv_townTownData[town].lv_lane == lp_lane && libGame_gv_townTownData[town].lv_owner == enemy && libGame_gv_townTownData[town].lv_makesCoreVulnerableWhenKilled && libGame_gv_townTownData[town].lv_townHallIndex > 0) {
            return !UnitIsAlive(libGame_gf_TownTownHall(town));
        }
    }
    return false;
}"""
    changed = once(original, HOOK, "\n\n".join([keep, unit, wave, ""]) + HOOK)
    bind = (
        "        if (" + DISPATCH + " == null) {\n"
        "            " + DISPATCH + ' = TriggerCreate("' + WAVE + '");\n        }'
    )
    changed = once(changed, PERIOD, PERIOD + "\n" + bind)
    return changed.replace("\n", "\r\n").encode("ascii")


def build(source, game, evidence, output, stormlib=None):
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    parent = source.read_bytes()
    if len(parent) != 2137204 or digest(parent) != BASE:
        raise ValueError("Unexpected wave clock map")
    storm = Storm(stormlib)
    before, _ = inventory(source, storm)
    changed = patch_script(before[MEMBER], game.read_bytes(), evidence.read_bytes())
    with TemporaryDirectory(dir=output.parent) as tmp:
        candidate = Path(tmp) / "candidate.s2ma"
        candidate.write_bytes(parent)
        storm.replace(candidate, {MEMBER: changed})
        after, checks = inventory(candidate, storm)
        if after != {**before, MEMBER: changed} or source.read_bytes() != parent:
            raise ValueError("Unexpected archive changes")
        result = candidate.read_bytes()
        os.link(candidate, output)
    return dict(
        parent_sha256=BASE,
        map_sha256=digest(result),
        bytes=len(result),
        game_sha256=GAME,
        timing_evidence_sha256=EVIDENCE,
        script_sha256=digest(changed),
        unchanged_content_members=len(before) - 1,
        integrity=checks,
        native_playback_verified=False,
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "game", "evidence", "output"):
        cli.add_argument("--" + name, required=True, type=Path)
    cli.add_argument("--stormlib")
    print(json.dumps(build(**vars(cli.parse_args())), indent=2))
