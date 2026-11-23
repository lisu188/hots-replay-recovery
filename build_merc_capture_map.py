"""Build the Dragon Shire historical camp capture overlay from the actual SignedAnnouncer."""

import argparse
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from build_dragon_beacon_reset import DISABLE, GAME, GATE, MECHANICS, MEMBER, need
from build_dragonshire_talent_map import digest, inventory
from build_gate_order_map import definition, once
from build_shared_beacon_reset import CHAN, ENTRY, WORK, normalized, registration
from runtime_catalog_probe import Storm
from signed_beacon_reset import exercise as check_shared_worker


PARENT = "150bdcea5435021263c84648d892c2c3dcc26bff8c72d1be5198c31a4bb09791"
PARENT_SCRIPT = "dbf9e1fd81e63250961e2fddb7ede47d84ff7c441a94335a60dc20c7d915c4c8"
RESET_EVIDENCE = "ca2330221dcf2b633d8a532e8d72fc03db73c88b1baba745eaf1b502804bf8bf"
FLAG_EVIDENCE = "54824ed79887205ddc5c262f2b8af49f955b914ef577796a75e6b68302113d0b"
OWN = "libMapM_gt_JungleCampOwnershipChange"
TURN = "libMapM_gf_JungleTurnOffCampCaptureBeacon"
HIDE = "libMapM_gf_JungleTransitionCampCaptureBeacontoHidden"
GRANT = "libMapM_gf_JungleGrantCaptureRewards"
DROP = "libMapM_gf_JungleDropLootBannerinMercCamp"
BANNER = "libGame_gf_DropLootBannerinSconce"
STOCK = "auto_" + BANNER + "_Trigger"
OFF = "gf_HistoricalTurnOffMercBeacon"
REWARD = "gf_HistoricalMercRewards"
CREDIT = "gf_HistoricalMercBannerCredit"
CALL = "gf_HistoricalMercBanner"
WORKER = "gt_HistoricalMercBanner"
HANDLE = "gv_HistoricalMercBannerTrigger"
CALLBACK = "gt_HistoricalMercOwnership"
REGISTER = "gf_RegisterHistoricalMercOwnership"
PREDICATE = "gf_HistoricalIsCampFlag"
FLAG_CHECK = """bool gf_HistoricalIsCampFlag (unit flag) {
    int camp;
    if (flag == null) { return false; }
    for (camp = 1; camp <= 5; camp += 1) {
        if (flag == gf_HistoricalCampFlag(camp)) { return true; }
    }
    return false;
}"""


def named(text, kind, original, name):
    return once(definition(text, kind, original), kind + " " + original + " (", kind + " " + name + " (")


def make_script(raw, lib_game, lib_mechanics):
    need(tuple(map(digest, (raw, lib_game, lib_mechanics))) == (PARENT_SCRIPT, GAME, MECHANICS),
         "Wrong map or stock script")
    parent, game, mech = map(normalized, (raw, lib_game, lib_mechanics))
    direct = [line.strip() for line in mech.splitlines() if line.strip().startswith(BANNER + "(")]
    need(len(direct) == 3 and sum(line.endswith(", true);") for line in direct) == 2
         and sum(line.endswith(", lv_randomPlayerInCreditGroup, false);") for line in direct) == 1,
         "Stock banner callers or text-tag conventions differ")
    for name in (HANDLE, OFF, REWARD, CREDIT, CALL, WORKER, CALLBACK, REGISTER, PREDICATE):
        need(name not in parent + game + mech, "Local symbol collides with an input")
    off = named(mech, "void", TURN, OFF)
    hide = definition(mech, "void", HIDE)
    (call,) = [s.strip() for s in hide.splitlines() if s.strip().endswith(";")]
    need(call == DISABLE + "(libMapM_gv_jungleCreepCamps[lp_camp].lv_captureCapturePointIndex);",
         "Unexpected original camp disable")
    off = once(off, HIDE + "(lp_camp);", once(call, "(libMapM", "(-libMapM"))
    # Keep stock argument assignments before lazy construction and use the same transfer slots.
    entry = named(game, "void", BANNER, CALL)
    primary = f'if ({STOCK} == null) {{\n        {STOCK} = TriggerCreate("{STOCK}Func");\n    }}'
    scoped = f'''if ({HANDLE} == null) {{
        if ({STOCK} != null && (lp_createTextTag || !{PREDICATE}(lp_sconceUnit))) {{
            TriggerExecute({STOCK}, false, false);
            return;
        }}
        {HANDLE} = TriggerCreate("{WORKER}");
        if ({STOCK} == null) {{ {STOCK} = {HANDLE}; }}
    }}'''
    entry = once(entry, f"TriggerExecute({STOCK}, false, false);", f"TriggerExecute({HANDLE}, false, false);")
    entry = once(entry, primary, scoped)
    worker = named(game, "bool", STOCK + "Func", WORKER)
    retarget = "UnitSetOwner(lp_sconceUnit, lp_owningPlayer, true);"
    worker = once(worker, retarget, f"if (lp_createTextTag || !{PREDICATE}(lp_sconceUnit)) {{\n        {retarget}\n    }}")
    credit = named(mech, "void", DROP, CREDIT)
    credit = once(credit, BANNER + "(", CALL + "(")
    reward = named(mech, "void", GRANT, REWARD)
    reward = once(reward, DROP + "(lp_camp, lv_creditGroup);", CREDIT + "(lp_camp, lv_creditGroup);")
    callback = named(mech, "bool", OWN + "_Func", CALLBACK)
    for team in ("TeamOrder", "TeamChaos"):
        args = "(lv_itCamp, libCore_gv_cOMPUTER_" + team
        callback = once(callback, TURN + args, OFF + args)
        callback = once(callback, GRANT + args, REWARD + args)
    reg = registration(mech, OWN, REGISTER, CALLBACK)
    init = definition(parent, "void", GATE)
    updated = once(init, OWN + "_Init();", REGISTER + "();")
    dragon = definition(parent, "bool", CHAN)
    updated_dragon = once(dragon, BANNER + "(", CALL + "(")
    # Place support after the pre-existing flag lookup and before its earliest direct use.
    anchor = definition(parent, "unit", "gf_HistoricalCampFlag")
    support = "\n\n".join((f"trigger {HANDLE};", FLAG_CHECK, worker, entry, credit, reward, off, callback, reg))
    result = once(parent, anchor, anchor + "\n\n" + support)
    result = once(result, dragon, updated_dragon)
    result = once(result, init, updated)
    need(result.index(anchor) < result.index(entry) < result.index(updated_dragon)
         and result.index(reg) < result.index(updated), "Generated functions appear after use")
    return result.replace("\n", "\r\n").encode("ascii")


def evidence(path, expected):
    record = json.loads(path.read_bytes())
    need(digest(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()) == expected,
         "Wrong physical evidence")


def exercise(code, game, harness, cc):
    source = harness.read_text(encoding="ascii")
    need(digest(source.encode("ascii")) == "caff3d82febdcb5a98b61bf15115e8425dc228c4717338cb2bb2675a0cf3671a",
         "Wrong mercenary callback test harness")
    pieces = [
        ("void", ENTRY), ("bool", WORK),
        ("unit", "gf_HistoricalCampFlag"), ("bool", PREDICATE), ("bool", WORKER),
        ("void", CALL), ("void", CREDIT), ("void", OFF), ("bool", CALLBACK),
    ]
    emitted = "\n\n".join(definition(code, t, n) for t, n in pieces)
    # The checked entry uses stock argument transfers; both workers consume the same registered globals.
    declarations = [line for line in game.splitlines() if line.startswith(("trigger auto_" + DISABLE + "_Trigger =",
                    "int auto_" + DISABLE + "_lp_", "trigger " + STOCK + " = null;", "unit auto_" + BANNER + "_lp_",
                    "string auto_" + BANNER + "_lp_", "int auto_" + BANNER + "_lp_", "bool auto_" + BANNER + "_lp_"))]
    need(len(declarations) == 7, "Missing stock global declarations")
    emitted = "\n".join([*declarations, f"trigger {HANDLE};", definition(game, "void", DISABLE), emitted])
    with TemporaryDirectory() as tmp:
        w = Path(tmp)
        (w/"emitted.h").write_text(emitted, encoding="ascii")
        (w/"test.c").write_text(source, encoding="ascii")
        subprocess.run([cc, "-std=c11", "-O0", str(w/"test.c"), "-o", str(w/"merc-test")], check=True)
        run = subprocess.run([str(w/"merc-test")], check=True, capture_output=True, text=True)
        counts = json.loads(run.stdout)
        need(counts == dict(capture_team_branches=2, banner_tasks_completed=5, credit_rng_draws=3,
                            ordinary_prebound_delegations=1, shared_capture_handle=1), "Missing callback test path")
        return counts


def build(parent, game, mechanics, resets, flags, shared_harness, merc_harness, output, stormlib, cc):
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    evidence(resets, RESET_EVIDENCE)
    evidence(flags, FLAG_EVIDENCE)
    original = parent.read_bytes()
    need(digest(original) == PARENT, "Expected actual SignedAnnouncer")
    storm = Storm(stormlib)
    before, _ = inventory(parent, storm)
    stock = game.read_bytes()
    result = make_script(before[MEMBER], stock, mechanics.read_bytes())
    with TemporaryDirectory(dir=output.parent) as tmp:
        candidate = Path(tmp)/"candidate.s2ma"
        candidate.write_bytes(original)
        storm.replace(candidate, {MEMBER:result})
        after, checks = inventory(candidate, storm)
        need(after == {**before, MEMBER:result} and parent.read_bytes() == original, "Unexpected package change")
        code = normalized(after[MEMBER])
        check_shared_worker(code, normalized(stock), shared_harness, cc)
        tests = exercise(code, normalized(stock), merc_harness, cc)
        raw = candidate.read_bytes()
        os.link(candidate, output)
    return dict(parent_sha256=PARENT, map_sha256=digest(raw), bytes=len(raw), script_sha256=digest(result),
                unchanged_content_members=len(before)-1, physical_reset_cohort={"41810":39, "98348":246},
                physical_flag_cohort={"41810":41, "98348":260}, ordinary_reset_loops=48,
                team_mercenary_reset_loops=16, extra_banner_handles_if_stock_bound_before_scoped_use=1,
                stock_capture_credit_rng_preserved=True, historical_rng_state_verified=False,
                native_playback_verified=False, tests=tests, integrity=checks)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("parent", "game", "mechanics", "resets", "flags", "shared_harness", "merc_harness", "output"):
        cli.add_argument(name, type=Path)
    cli.add_argument("--stormlib")
    cli.add_argument("--cc", default="cc")
    print(json.dumps(build(**vars(cli.parse_args())), indent=2))
