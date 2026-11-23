"""Verify shared trigger allocation and suspend the emitted workers across unrelated capture requests."""

import argparse
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import re
import subprocess

from build_dragon_beacon_reset import DISABLE, GAME, GATE, MECHANICS, MEMBER, PARENT, SCRIPT, TRANSFORM, check_observations, need
from build_dragonshire_talent_map import digest, inventory
from build_gate_order_map import definition
from build_shared_beacon_reset import CAMP, CAMP_CALLBACK, CHAN, ENTRY, MARK, REG_CAMP, REG_DRAGON, STOCK_WORK, WORK, check_first, normalized
from mpq_reader import MPQArchive
from runtime_catalog_probe import Storm


def verify(parent,candidate,game,mechanics,evidence,first,stormlib,cc):
    check_observations(evidence.read_bytes())
    check_first(first.read_bytes())
    old,_ = inventory(parent,Storm(stormlib))
    new,_ = inventory(candidate,Storm(stormlib))
    need(tuple(map(digest,(parent.read_bytes(),old[MEMBER],game.read_bytes(),mechanics.read_bytes()))) ==
         (PARENT,SCRIPT,GAME,MECHANICS), "Wrong verification input")
    need(old.keys() == new.keys() and [k for k in old if old[k] != new[k]] == [MEMBER], "Unexpected archive diff")
    with closing(MPQArchive(candidate)) as archive:
        need(archive.read_file(MEMBER) == new[MEMBER], "Independent script reader disagrees")
    source,patched,game,rules = map(normalized,(old[MEMBER],new[MEMBER],game.read_bytes(),mechanics.read_bytes()))
    old_lib,new_lib = [definition(s,"void",GATE) for s in (source,patched)]
    restore = new_lib.replace(REG_CAMP+"();",CAMP+"_Init();").replace(REG_DRAGON+"();",TRANSFORM+"_Init();")
    need(restore == old_lib and "gf_HistoricalCampInitLib();" in definition(patched,"void","InitLibs")
         and GATE+"();" in definition(patched,"void","gf_HistoricalCampInitLib"), "Initializer order differs")
    for name,callback,reg in [(CAMP,CAMP_CALLBACK,REG_CAMP),(TRANSFORM,CHAN,REG_DRAGON)]:
        actual = definition(patched,"void",reg)
        need(actual.replace("void "+reg+" (","void "+name+"_Init (").replace('"'+callback+'"','"'+name+'_Func"')
             == definition(rules,"void",name+"_Init"), "Changed native event registration or trigger global")
    first_fn = definition(patched,"void",ENTRY)
    stock = definition(game,"void",DISABLE)
    need(first_fn.replace("void "+ENTRY+" (","void "+DISABLE+" (").replace('"'+WORK+'"','"'+STOCK_WORK+'"') == stock,
         "First-use wrapper must allocate the stock trigger at its original point")
    camp = definition(patched,"bool",CAMP_CALLBACK)
    need(camp.replace(CAMP_CALLBACK+" (",CAMP+"_Func (").replace(ENTRY+"(",DISABLE+"(") == definition(rules,"bool",CAMP+"_Func"),
         "Camp initializer changed beyond its first-use wrapper")
    channel = definition(patched,"bool",CHAN)
    match = re.search(r"(?m)^[ ]*"+MARK+r" = true;\n([ ]*libGame_gf_CapturePointDisable\([^;]+;)",channel)
    need(match is not None, "Missing Dragon scope")
    start = match.start()
    end = channel.index(MARK+" = false;",match.end())+len(MARK+" = false;")
    scoped = channel[start:end]
    restored = channel[:start]+match[1]+channel[end:]
    need(restored.replace("bool "+CHAN+" (","bool "+TRANSFORM+"_Func (") == definition(rules,"bool",TRANSFORM+"_Func"),
         "Dragon finish changed outside its scoped call")
    worker = definition(patched,"bool",WORK)
    override = re.search(r"    fixed lv_resetDelay = 3\.0;\n    if \("+MARK+r"\) \{\n        "+
                         MARK+r" = false;\n        lv_resetDelay = 1\.0;\n    \}\n",worker)
    need(override is not None and worker.index("int lp_capturePointIndex") < override.start()
         < worker.index("if (((lp_capturePointIndex"), "The one-shot marker must be consumed before guard and native calls")
    restored = worker.replace(override[0],"").replace("Wait(lv_resetDelay,", "Wait(3.0,").replace("bool "+WORK+" (","bool "+STOCK_WORK+" (")
    need(restored == definition(game,"bool",STOCK_WORK), "Worker behavior changed beyond chosen duration")
    start = patched.index("bool "+MARK+" = false;")
    end = patched.index("void "+GATE+" (",start)
    need((patched[:start]+patched[end:]).replace(new_lib,old_lib) == source,
         "Changes outside the two registration slots and their corresponding functions")
    declarations = [s for s in game.splitlines() if s.startswith(("trigger auto_"+DISABLE,"int auto_"+DISABLE))]
    need(len(declarations)==2, "Stock global layout differs")
    emitted = "\n".join([*declarations,"bool "+MARK+" = false;", first_fn, stock, worker,
                          "struct { int lv_captureBeaconIndex; } libMapM_gv_mMGardensDragonDragonTowers[9];",
                          "static void extracted_dragon_call(int lv_itObelisk) {",
                          "libMapM_gv_mMGardensDragonDragonTowers[lv_itObelisk].lv_captureBeaconIndex=lv_itObelisk;",
                          scoped,"}"])
    with TemporaryDirectory() as folder:
        here = Path(folder)
        (here/"emitted.h").write_text(emitted,encoding="ascii")
        harness = Path(__file__).with_name("shared_beacon_harness.c")
        exe = here/"test"
        subprocess.run([cc,"-std=c11","-O0","-I",str(here),str(harness),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    return {"sha256":digest(candidate.read_bytes()),"script_sha256":digest(new[MEMBER]),
            "other_content_members_identical":len(old)-1,"stock_registrations_replaced_in_place":2,
            "mock_first_startup_calls":7,"mock_total_worker_dispatches":13,"mock_shared_trigger_allocations":1,
            "ordinary_interval_loops":48,"specialized_interval_loops":16,"observed_reset_pairs":[15,52],
            "reverse_due_order_from_replays_tested":True,"nested_ordinary_dispatch_preserves_48":True,
            "native_galaxy_compilation_or_playback_verified":False}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for field in ("parent","candidate","game","mechanics","evidence","first"):
        p.add_argument(field,type=Path)
    p.add_argument("--stormlib")
    p.add_argument("--cc",default="cc")
    print(json.dumps(verify(**vars(p.parse_args())),indent=2))
