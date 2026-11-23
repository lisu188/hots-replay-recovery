"""Check the extracted map callback, roster upgrade times and complete regular wave schedule."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

from camp_owner_wire import read_tracker
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive

MAP = "f4d3b425cd9df5ed5390c45dc3c770300a64ba95449c82c228eed8b9928c7d6f"
PARENT = "d41c5841a5719e76246265940d28b244bae91f4e3fef33e621f3a2e2a0ee7bbd"
GAME = "a6384749fbe8f676cbd6ccb9ec1aeac004815d37a8e1c2f8f9f8f176b2bfca09"
START = "libGame_gt_SpawnMinionsMinionSpawnStartTimerExpires"
TIMER = "libGame_gv_minionSpawnStartTimer"
PERIOD = "libCore_gv_bALMinionWaveInterval"
HOOK = "gt_HistoricalWaveStart_Func"


def pinned(path, digest):
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != digest:
        raise ValueError("Incorrect input hash")
    return raw


def script(path, digest):
    pinned(path, digest)
    with closing(MPQArchive(path)) as arc:
        return read_member(arc, "MapScript.galaxy").decode("ascii").splitlines(keepends=True)


def function(text, symbol):
    match, = re.findall(r"^bool " + symbol + r" \(bool testConds, bool runActions\) \{.*?^\}", text, re.S | re.M)
    return match


def check_map(base, output, gamelib, cc):
    original = "".join(script(base, PARENT))
    changed = "".join(script(output, MAP))
    library = pinned(gamelib, GAME).decode("utf-8-sig")
    hook = function(changed, HOOK)
    dispatch = function(library, START + "_Func")
    install = (f"    TriggerEnable({START}, false);\r\n"
               f'    {START} = TriggerCreate("{HOOK}");\r\n'
               f"    TriggerAddEventTimer({START}, {TIMER});\r\n")
    if changed.replace(hook + "\r\n\r\n", "", 1).replace(install, "", 1) != original:
        raise ValueError("Changes outside timer registration or callback")
    if install + "    TriggerExecute(libCore_gt_InitializeStormMod, true, true);" not in changed:
        raise ValueError("Unexpected registration location")
    # Compile the actual two callback bodies against a deterministic game-loop harness.
    prefix = """
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
static int now, upgrades, started, enabled, last_player;
static const int libCore_gv_bALMaxPlayers = 10, c_timeGame = 1;
static bool libCore_gv_sYSMinionAI, libCore_gv_sYSMinionSpawningOn;
static double libCore_gv_bALMinionWaveInterval;
static void Wait(double seconds, int clock) {
    if (clock != c_timeGame || seconds <= 0 || (int)(16 * seconds) != 16 * seconds) exit(8);
    now += (int)(16 * seconds);
}
static void libNtve_gf_SetUpgradeLevelForPlayer(int p, const char *u, int v) {
    if (p != ++last_player || v != 1 || !u) exit(9);
    ++upgrades;
}
static void libGame_gf_MinionStartStopMinionSystem(bool value) { enabled += value; }
static void libGame_gf_MinionStartStopMinionSpawnCycle(bool value) { started += value; }
"""
    main = """
int main(void) {
    for (int mask=0; mask<16; ++mask) {
        now = 1; upgrades = started = enabled = last_player = 0;
        libCore_gv_bALMinionWaveInterval = 30.0;
        bool conditions = mask & 1, actions = mask & 2;
        libCore_gv_sYSMinionAI = mask & 4; libCore_gv_sYSMinionSpawningOn = mask & 8;
        if (!gt_HistoricalWaveStart_Func(conditions, actions)) return 1;
        if (now != (actions ? 80 : 1) || upgrades != (actions ? 10 : 0)) return 2;
        if (enabled != (actions && libCore_gv_sYSMinionAI)) return 3;
        if (started != (actions && libCore_gv_sYSMinionAI && libCore_gv_sYSMinionSpawningOn)) return 4;
        if (16 * libCore_gv_bALMinionWaveInterval != (actions ? 481 : 480)) return 5;
    }
    return 0;
}
"""
    with TemporaryDirectory() as tmp:
        src, exe = Path(tmp) / "callback.c", Path(tmp) / "callback"
        src.write_text("\n".join((prefix, dispatch, hook, main)), encoding="ascii")
        subprocess.run([cc, "-std=c99", "-o", str(exe), str(src)], check=True)
        subprocess.run([str(exe)], check=True)
    return dict(map_sha256=MAP, preserved_parent_sha256=PARENT, callback_flag_combinations=16,
                stock_duration_loops=480, restored_duration_loops=481,
                action_delay_loops=79, native_execution_verified=False)


def verify_case(path, digest, build):
    pinned(path, digest)
    proto, raw, horizon = read_tracker(path, build)
    events = list(proto.decode_replay_tracker_events(raw))
    if sum(e["_bits"] for e in events) != len(raw) * 8:
        raise ValueError("Tracker coverage")
    gate, = [e["_gameloop"] for e in events if e.get("m_eventName") == b"GatesOpen"]
    offset, stride = {41810: (80, 481), 98348: (1, 480)}[build]
    def upgrades(name):
        return Counter((e["_gameloop"], e["m_playerId"], e["m_count"]) for e in events
                       if e.get("m_upgradeTypeName") == name)
    for name, tick in ((b"GatesAreOpen", gate), (b"MinionsAreSpawning", gate + offset)):
        if upgrades(name) != Counter((tick, player, 1) for player in range(1, 11)):
            raise ValueError("Gate or minion upgrade differs from predicted dispatch")
    cores = {(e["m_unitTagIndex"], e["m_unitTagRecycle"]) for e in events
             if e.get("m_unitTypeName") == b"KingsCore" and e["_gameloop"] == 0}
    end = min([horizon] + [e["_gameloop"] for e in events if e["_eventid"] == 2
                           and (e["m_unitTagIndex"], e["m_unitTagRecycle"]) in cores])
    shape = ((b"FootmanMinion", 3), (b"WizardMinion", 1), (b"RangedMinion", 3))
    observed = Counter((e["_gameloop"], e["m_unitTypeName"], e["m_controlPlayerId"], e["m_upkeepPlayerId"])
                       for e in events if e.get("m_unitTypeName") in dict(shape) and e["_eventid"] == 1
                       and e["_gameloop"] <= end)
    wanted = Counter()
    starts = range(gate + offset + 1, end + 1, stride)
    for first in starts:
        for lane in range(3):
            for group, (unit, count) in enumerate(shape):
                tick = first + 3 * lane + group
                if tick <= end:
                    for team in (11, 12):
                        wanted[tick, unit, team, team] += count
    if wanted != observed:
        raise ValueError("Regular wave schedule differs from physical births")
    return dict(sha256=digest, build=build, start_upgrade_delay=offset, first_birth_delay=offset + 1,
                all_ten_gate_upgrades=True, all_ten_start_upgrades=True, waves=len(starts),
                exact_regular_births=sum(wanted.values()), cutoff=end)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for arg in ("base", "map", "game"):
        cli.add_argument("--" + arg, type=Path, required=True)
    cli.add_argument("--cc", default="cc")
    cli.add_argument("--case", nargs=3, action="append", required=True, metavar=("REPLAY", "SHA256", "BUILD"))
    args = cli.parse_args()
    if len({h for _, h, _ in args.case}) != len(args.case):
        raise ValueError("Duplicate recording")
    checks = check_map(args.base, args.map, args.game, args.cc)
    print(json.dumps(dict(callback=checks, cases=[verify_case(Path(p), h, int(b)) for p, h, b in args.case]), indent=2))
