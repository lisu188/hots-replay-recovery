"""Restore the Dragon Shire wave-start callback timing on the historical respawn map."""

import argparse
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from build_dragonshire_talent_map import digest, inventory
from runtime_catalog_probe import Storm


BASE = "d41c5841a5719e76246265940d28b244bae91f4e3fef33e621f3a2e2a0ee7bbd"
SCRIPT = "cbde228bbfaa6dad7e2cc9bad02651d30ab7435838ab25e732c4bea2aa85b7d6"
GAME = "a6384749fbe8f676cbd6ccb9ec1aeac004815d37a8e1c2f8f9f8f176b2bfca09"
CORE = "15f0314a1c48a0391e76e22360847e7ef0c91b12a29da15d79453045c175a683"
CLOCK = "d5923c7f2816b817227a98d4004cfe8513983073025db074b49c1737e83c50b3"
MEMBER = "MapScript.galaxy"
START = "libGame_gt_SpawnMinionsMinionSpawnStartTimerExpires"
TIMER = "libGame_gv_minionSpawnStartTimer"
PERIOD = "libCore_gv_bALMinionWaveInterval"
CALLBACK = "gt_HistoricalWaveStart_Func"


def clock_profile(evidence):
    if digest(evidence) != CLOCK:
        raise ValueError("Unknown wave timing evidence")
    cases = json.loads(evidence)["cases"]
    if len({c["sha256"] for c in cases}) != 19 or len(cases) != 19:
        raise ValueError("Incomplete reference set")
    clocks = {}
    for case in cases:
        strides = case["start_intervals"]
        if len(strides) != 1 or sum(strides.values()) != case["observed_wave_starts"] - 1:
            raise ValueError("Irregular wave timing")
        timing = case["first_delay"], int(next(iter(strides)))
        if clocks.setdefault(case["build"], timing) != timing:
            raise ValueError("Wave profiles differ within one build")
    return clocks


def patch(raw, game_data, core_data, evidence):
    if (digest(raw), digest(game_data), digest(core_data)) != (SCRIPT, GAME, CORE):
        raise ValueError("Unexpected parent script or libraries")
    clocks = clock_profile(evidence)
    old_start, old_stride = clocks[41810]
    stock_start, stock_stride = clocks[98348]
    game = game_data.decode("utf-8-sig")
    core = core_data.decode("utf-8-sig")
    init = f'TriggerAddEventTimer({START}, {TIMER});'
    if (game.count(init) != 1 or game.count(f'{START} = TriggerCreate("{START}_Func");') != 1
            or game.count(f'TimerStart(lv_waveTimer, {PERIOD}, false, c_timeGame);') != 1
            or core.count(f"{PERIOD} = 30.0;") != 1 or stock_stride != 480):
        raise ValueError("Unexpected stock timer registration or cadence")
    wait = (old_start - stock_start) / 16
    period = old_stride / 16
    decl = "bool gt_InitializeMap_Func (bool testConds, bool runActions) {\r\n"
    dispatch = "    TriggerExecute(libCore_gt_InitializeStormMod, true, true);\r\n"
    script = raw.decode("ascii")
    if script.count(decl) != 1 or script.count(dispatch) != 1 or CALLBACK in script:
        raise ValueError("Unrecognized map initialization")
    callback = [
        f"bool {CALLBACK} (bool testConds, bool runActions) {{",
        "    if (runActions) {",
        f"        Wait({wait}, c_timeGame);",
        f"        {PERIOD} = {period};",
        "    }",
        f"    return {START}_Func(testConds, runActions);",
        "}", "", "",
    ]
    binding = [
        f"    TriggerEnable({START}, false);",
        f'    {START} = TriggerCreate("{CALLBACK}");',
        f"    {init}", "",
    ]
    changed = script.replace(decl, "\r\n".join(callback) + decl)
    changed = changed.replace(dispatch, "\r\n".join(binding) + dispatch)
    return changed.encode("ascii"), (wait, period)


def build(source, game, core, evidence, output, stormlib=None):
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    parent = source.read_bytes()
    if (len(parent), digest(parent)) != (2134122, BASE):
        raise ValueError("Unexpected parent map")
    storm = Storm(stormlib)
    before, _ = inventory(source, storm)
    script, (wait, period) = patch(before[MEMBER], game.read_bytes(), core.read_bytes(), evidence.read_bytes())
    with TemporaryDirectory(dir=output.parent) as tmp:
        staged = Path(tmp) / "wave.s2ma"
        staged.write_bytes(parent)
        storm.replace(staged, {MEMBER: script})
        after, checks = inventory(staged, storm)
        if after != {**before, MEMBER: script} or source.read_bytes() != parent:
            raise ValueError("Map content mismatch")
        image = staged.read_bytes()
        os.link(staged, output)
    return dict(parent_sha256=BASE, map_sha256=digest(image), bytes=len(image), script_sha256=digest(script),
                unchanged_content_members=len(before) - 1, callback_delay_seconds=wait,
                wave_period_seconds=period, integrity=checks, native_playback_verified=False)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for key in ("source", "game", "core", "evidence", "output"):
        cli.add_argument("--" + key, type=Path, required=True)
    cli.add_argument("--stormlib")
    print(json.dumps(build(**vars(cli.parse_args())), indent=2))
