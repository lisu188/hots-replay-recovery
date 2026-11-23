"""Build the HistoricalCamps Dragon Knight reset using the existing capture-point trigger slot."""

import argparse
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from build_dragon_beacon_reset import DISABLE, GAME, GATE, MECHANICS, MEMBER, PARENT, SCRIPT, TRANSFORM, check_observations, need
from build_dragonshire_talent_map import digest, inventory
from build_gate_order_map import definition, once
from runtime_catalog_probe import Storm


FIRST = "e451a9e00f199d7cb2650a2b40149d432ecd7ee2fdc9e8773d884480b583e953"
CAMP = "libMapM_gt_InitializeJungleCamps"
MARK = "gv_HistoricalDragonDisablePending"
ENTRY = "gf_HistoricalFirstCampDisable"
WORK = "gt_HistoricalCapturePointDisable"
CHAN = "gt_HistoricalDragonFinishShared"
CAMP_CALLBACK = "gt_HistoricalCampSharedDisable"
REG_CAMP = "gf_RegisterHistoricalCampSharedDisable"
REG_DRAGON = "gf_RegisterHistoricalDragonFinishShared"
STOCK_WORK = "auto_" + DISABLE + "_TriggerFunc"
DRAGON_CALL = "libGame_gf_CapturePointDisable(libMapM_gv_mMGardensDragonDragonTowers[lv_itObelisk].lv_captureBeaconIndex);"
SCOPED_CALL = MARK + " = true;\n        " + DRAGON_CALL + "\n        " + MARK + " = false;"


def normalized(raw):
    return raw.decode("utf-8-sig").replace("\r\n", "\n")


def check_first(raw):
    d = json.loads(raw)
    need(digest(json.dumps(d,sort_keys=True,separators=(",",":")).encode("ascii")) == FIRST,
         "Unexpected first-call report")


def registration(mechanics, stock, name, callback):
    reg = definition(mechanics,"void",stock + "_Init")
    reg = once(reg,"void " + stock + "_Init (","void " + name + " (")
    return once(reg,'TriggerCreate("' + stock + '_Func")','TriggerCreate("' + callback + '")')


def generate(parent, game, mech):
    need(tuple(map(digest,(parent,game,mech))) == (SCRIPT,GAME,MECHANICS), "Incorrect map or library scripts")
    old, game, mech = map(normalized,(parent,game,mech))
    for sym in (MARK,ENTRY,WORK,CHAN,CAMP_CALLBACK,REG_CAMP,REG_DRAGON):
        need(all(sym not in s for s in (old,game,mech)), "Identifier collision")
    first = definition(game,"void",DISABLE)
    first = once(first,"void " + DISABLE + " (","void " + ENTRY + " (")
    # Same argument global, null test, creation location, trigger global and dispatch mode as stock.
    first = once(first,'TriggerCreate("' + STOCK_WORK + '")', 'TriggerCreate("' + WORK + '")')
    worker = definition(game,"bool",STOCK_WORK)
    worker = once(worker,"bool " + STOCK_WORK + " (","bool " + WORK + " (")
    anchor = "    int lp_capturePointIndex = auto_" + DISABLE + "_lp_capturePointIndex;"
    worker = once(worker,anchor,anchor + """
    fixed lv_resetDelay = 3.0;
    if (gv_HistoricalDragonDisablePending) {
        gv_HistoricalDragonDisablePending = false;
        lv_resetDelay = 1.0;
    }""")
    worker = once(worker,"Wait(3.0, c_timeGame);","Wait(lv_resetDelay, c_timeGame);")
    camp = definition(mech,"bool",CAMP + "_Func")
    camp = once(camp,"bool " + CAMP + "_Func (","bool " + CAMP_CALLBACK + " (")
    camp = once(camp,DISABLE + "(",ENTRY + "(")
    channel = definition(mech,"bool",TRANSFORM + "_Func")
    channel = once(channel,"bool " + TRANSFORM + "_Func (","bool " + CHAN + " (")
    channel = once(channel,DRAGON_CALL,SCOPED_CALL)
    lib = definition(old,"void",GATE)
    changed = once(once(lib,CAMP + "_Init();",REG_CAMP + "();"),TRANSFORM + "_Init();",REG_DRAGON + "();")
    additions = ("bool " + MARK + " = false;", first, worker, camp,
                 registration(mech,CAMP,REG_CAMP,CAMP_CALLBACK), channel,
                 registration(mech,TRANSFORM,REG_DRAGON,CHAN), changed)
    return once(old,lib,"\n\n".join(additions)).replace("\n","\r\n").encode("ascii")


def build(parent, game, mechanics, evidence, first, output, stormlib):
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    check_observations(evidence.read_bytes())
    check_first(first.read_bytes())
    raw = parent.read_bytes()
    need((len(raw),digest(raw)) == (2159443,PARENT), "Incorrect HistoricalCamps map")
    storm = Storm(stormlib)
    before,_ = inventory(parent,storm)
    emitted = generate(before[MEMBER],game.read_bytes(),mechanics.read_bytes())
    with TemporaryDirectory(dir=output.parent) as folder:
        tmp = Path(folder)/"map.s2ma"
        tmp.write_bytes(raw)
        storm.replace(tmp,{MEMBER:emitted})
        after,checks = inventory(tmp,storm)
        need(after == {**before,MEMBER:emitted} and parent.read_bytes() == raw, "Unexpected map change")
        data = tmp.read_bytes()
        os.link(tmp,output)
    return {"parent_sha256":PARENT,"map_sha256":digest(data),"bytes":len(data),"script_sha256":digest(emitted),
            "unchanged_content_members":len(before)-1,"integrity":checks}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for field in ("parent","game","mechanics","evidence","first","output"):
        p.add_argument(field,type=Path)
    p.add_argument("--stormlib")
    print(json.dumps(build(**vars(p.parse_args())),indent=2))
