"""Build a separate GateOrder derivative that restores TEN's delayed first mercenary wave."""

import argparse
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from build_dragonshire_talent_map import digest, inventory
from build_gate_order_map import definition, once
from dragon_startup_births import MECHANICS_SHA
from first_camp_event_order import layout
from hero_revive_wire import GATE_MAP
from runtime_catalog_probe import Storm

SCRIPT_SHA = "6b6f8f51778ed77cc6bd183827a349d9f8b817ca51b1fa9b816926df9d603d6e"
MEMBER = "MapScript.galaxy"
TABLE = "libMapM_gv_jungleCreepCamps"
STOCK_INIT = "libMapM_gf_JungleInitializeCreepCamp"
TIMER = "libMapM_gt_JungleCreepCampRespawnTimerExpires"
GATE = "gt_HistoricalGatesOpen_Func"
INIT = "gf_OpenHistoricalCamp"
SCHEDULE = "gf_ScheduleHistoricalCampOpening"
CALLBACK = "gt_HistoricalCampBirthTimer_Func"
REGISTER = "gf_RegisterHistoricalCampBirthTimer"
PENDING = "gv_HistoricalCampOpeningPending"

SCHEDULER = """void gf_ScheduleHistoricalCampOpening () {
    int camp;
    if (!libCore_gv_sYSJungleCreepCamps || libMapM_gv_jungleNumberOfCreepCamps != 5) {
        return;
    }
    for (camp = 1; camp <= 5; camp += 1) {
        if (libMapM_gv_jungleCreepCamps[camp].lv_stateIsEnabled || libMapM_gv_jungleCreepCamps[camp].lv_campIconUnit != null) {
            return;
        }
    }
    gv_HistoricalCampOpeningPending = true;
    for (camp = 1; camp <= 5; camp += 1) {
        TimerStart(libMapM_gv_jungleCreepCamps[camp].lv_stateCreepBirthTimer, 120.0, false, c_timeGame);
        TimerStart(libMapM_gv_jungleCreepCamps[camp].lv_stateCreepRespawnTimer, 120.0 + libMapM_gv_bALJungleBirthDelay, false, c_timeGame);
    }
}"""

HANDLER = """bool gt_HistoricalCampBirthTimer_Func (bool testConds, bool runActions) {
    int camp;
    if (runActions && gv_HistoricalCampOpeningPending && libCore_gv_sYSJungleCreepCamps) {
        for (camp = 1; camp <= 5; camp += 1) {
            if (EventTimer() == libMapM_gv_jungleCreepCamps[camp].lv_stateCreepBirthTimer) {
                gv_HistoricalCampOpeningPending = false;
                for (camp = 1; camp <= 5; camp += 1) {
                    gf_OpenHistoricalCamp(camp);
                }
                break;
            }
        }
    }
    return libMapM_gt_JungleCreepCampRespawnTimerExpires_Func(testConds, runActions);
}"""


def generate(script_raw, library_raw, flags):
    if (
        digest(script_raw) != SCRIPT_SHA
        or digest(library_raw) != MECHANICS_SHA
        or len(set(flags)) != 5
    ):
        raise ValueError(
            "Unexpected parental script, installed library or flag mapping"
        )
    script = script_raw.decode("ascii").replace("\r\n", "\n")
    stock = library_raw.decode("utf-8-sig").replace("\r\n", "\n")
    if any(
        name in script + stock for name in (SCHEDULE, INIT, CALLBACK, REGISTER, PENDING)
    ):
        raise ValueError("Historical helper name collision")
    getter = (
        "unit gf_HistoricalCampFlag (int camp) {\n"
        + "".join(
            f"    if (camp == {i}) {{ return UnitFromId({flag}); }}\n"
            for i, flag in enumerate(flags, 1)
        )
        + "    return null;\n}"
    )
    icon = definition(stock, "void", STOCK_INIT)
    icon = once(icon, "void " + STOCK_INIT + " (", "void " + INIT + " (")
    (lookup,) = [ln for ln in icon.splitlines() if 'UnitGroup("LootBannerSconce"' in ln]
    icon = once(
        icon,
        lookup,
        f"    {TABLE}[lp_camp].lv_campOwnershipFlagUnit = gf_HistoricalCampFlag(lp_camp);",
    )
    (banner,) = [
        ln
        for ln in icon.splitlines()
        if "libMapM_gf_JungleDropLootBannerinMercCamp(" in ln
    ]
    icon = once(icon, banner, f"    {TABLE}[lp_camp].lv_stateIsEnabled = true;")
    created = "    lv_iconUnit = UnitLastCreated();"
    icon = once(
        icon,
        created,
        created
        + f"\n    UnitSetOwner({TABLE}[lp_camp].lv_campOwnershipFlagUnit, libCore_gv_cOMPUTER_Hostile, true);",
    )
    # Keep the original timer global, initialization order, enabled state and ordinary post-opening callback.
    registration = definition(stock, "void", TIMER + "_Init")
    registration = once(
        registration, "void " + TIMER + "_Init (", "void " + REGISTER + " ("
    )
    registration = once(
        registration,
        'TriggerCreate("' + TIMER + '_Func")',
        'TriggerCreate("' + CALLBACK + '")',
    )
    trigger_init = definition(stock, "void", "libMapM_InitTriggers")
    trigger_init = once(
        trigger_init,
        "void libMapM_InitTriggers (",
        "void gf_HistoricalCampInitTriggers (",
    )
    trigger_init = once(trigger_init, TIMER + "_Init();", REGISTER + "();")
    lib_init = definition(stock, "void", "libMapM_InitLib")
    lib_init = once(
        lib_init, "void libMapM_InitLib (", "void gf_HistoricalCampInitLib ("
    )
    lib_init = once(
        lib_init, "    libMapM_InitTriggers();", "    gf_HistoricalCampInitTriggers();"
    )
    gate = definition(script, "bool", GATE)
    origin = "    TriggerExecute(libMapM_gt_StartJungleCampTimers, true, false);"
    changed_gate = once(gate, origin, origin + "\n    " + SCHEDULE + "();")
    support = "\n\n".join(
        [
            "bool " + PENDING + " = false;",
            getter,
            icon,
            SCHEDULER,
            HANDLER,
            registration,
            trigger_init,
            lib_init,
        ]
    )
    script = once(script, gate, support + "\n\n" + changed_gate)
    script = once(script, "    libMapM_InitLib();", "    gf_HistoricalCampInitLib();")
    return script.replace("\n", "\r\n").encode("ascii")


def build(parent, library, output, stormlib):
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    image = parent.read_bytes()
    if digest(image) != GATE_MAP:
        raise ValueError("Expected the preserved GateOrder derivative")
    mapping = [flag[0] for _, flag, _ in layout(parent)]
    storm = Storm(stormlib)
    before, _ = inventory(parent, storm)
    script = generate(before[MEMBER], library.read_bytes(), mapping)
    with TemporaryDirectory(dir=output.parent) as tmp:
        temp = Path(tmp) / "historical-camps.s2ma"
        temp.write_bytes(image)
        storm.replace(temp, {MEMBER: script})
        after, integrity = inventory(temp, storm)
        if after != {**before, MEMBER: script} or parent.read_bytes() != image:
            raise ValueError("Map content or parent integrity differs")
        data = temp.read_bytes()
        os.link(temp, output)
    return dict(
        parent_sha256=GATE_MAP,
        map_sha256=digest(data),
        bytes=len(data),
        script_sha256=digest(script),
        flag_object_ids=mapping,
        unchanged_content_members=len(before) - 1,
        integrity=integrity,
        native_galaxy_compilation_verified=False,
        full_simulation_verified=False,
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for field in ("parent", "library", "output"):
        cli.add_argument(field, type=Path)
    cli.add_argument("--stormlib", required=True)
    print(json.dumps(build(**vars(cli.parse_args())), indent=2))
