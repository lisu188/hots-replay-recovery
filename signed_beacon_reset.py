"""Build the map-scoped Dragon reset with the stock capture trigger and argument global."""

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

from build_dragon_beacon_reset import DISABLE, MEMBER, PARENT, SCRIPT, check_observations, need
from build_dragonshire_talent_map import digest, inventory
from build_gate_order_map import definition, once
from build_shared_beacon_reset import CHAN, DRAGON_CALL, ENTRY, MARK, SCOPED_CALL, WORK, check_first, normalized
from mpq_reader import MPQArchive
from runtime_catalog_probe import Storm
from verify_first_capture_disable import MANIFEST


SHARED = "2d5cba9c5fd8276ae62468533fae558222730d55b146d41b7ebb7d30532e70b7"
SHARED_SCRIPT = "8d990dfbdc32b50d8667aafdcd409c02a3ecffd39fb5cfc351833e234f047b40"
ARG = "auto_" + DISABLE + "_lp_capturePointIndex"
SOURCE_BRANCH = "if (" + MARK + ") {\n        " + MARK + " = false;"
SIGNED_BRANCH = ("if (lp_capturePointIndex < 0) {\n        lp_capturePointIndex = -lp_capturePointIndex;\n        "
                 + ARG + " = lp_capturePointIndex;")
NEGATIVE_CALL = DRAGON_CALL.replace("(libMapM", "(-libMapM")


def argument_domain(folder, map_script):
    raw = (folder/"member.json").read_bytes()
    need(digest(raw) == MANIFEST, "Unexpected target closure manifest")
    files = {"map": map_script}
    for member in json.loads(raw)["members"]:
        raw = (folder/member["saved_name"]).read_bytes()
        need(digest(raw) == member["sha256"], "Target library differs")
        files[member["saved_name"]] = normalized(raw)
    closure = "\n".join(files.values())
    game = files["gamelib.galaxy"]
    counter = "libGame_gv_capturePointCurrentCount"
    key = "libGame_gv_capturePointLastCreatedCapturePointIndex_C"
    need("const int libGame_gv_capturePointMaxCount_C = 15;" in files["gamelib_h.galaxy"]
         and "int "+counter+";" in files["gamelib_h.galaxy"], "Incorrect capture point domain")
    writes = re.findall(r"\b"+counter+r"\s*(?:[+*/%-]=|=(?!=)|\+\+|--)[^;]*;",closure)
    need(writes == [counter+" += 1;"], "Additional capture counter write")
    creator = definition(game,"void","libGame_gf_CapturePointCreate")
    limit = creator.index("if (("+counter+" == libGame_gv_capturePointMaxCount_C))")
    need(limit < creator.index("return ;",limit) < creator.index(counter+" += 1;")
         < creator.index("DataTableSetInt(false, "+key+", "+counter+");"), "Creator no longer caps its index")
    need(closure.count('"CapturePointLastCreatedCapturePointIndex"') == 1 and closure.count(key) == 4
         and "return DataTableGetInt(false, "+key+");" in definition(game,"int","libGame_gf_LastCreatedCapturePoint"),
         "Unexpected last-created slot access")
    # No other field arithmetic or wholesale array element assignment may provide a signed index.
    fields = re.findall(r"\.(lv_captureCapturePointIndex|lv_captureBeaconIndex)\s*(?:[+*/%-]=|=(?!=)|\+\+|--)([^;]*);",closure)
    need(sorted(fields) == sorted([(f," libGame_gf_LastCreatedCapturePoint()") for f in
                                   ("lv_captureCapturePointIndex","lv_captureBeaconIndex","lv_captureBeaconIndex")]),
         "Unexpected stored index writer")
    need(not re.search(r"(?:jungleCreepCamps|mMGardensDragonDragonTowers)\[(?:[^\[\]\n;]|\[[^\[\]\n;]*\])*\]\s*=(?!=)", closure)
         and not re.search(r"(?:structref|arrayref)\s*<[^>]*(?:JungleCreepCamps|MMGardensDragon)",closure),
         "An aggregate may replace stored capture indices")
    stock = definition(game,"void",DISABLE)
    stock_worker = definition(game,"bool","auto_"+DISABLE+"_TriggerFunc")
    need(closure.count(ARG) == 3 and "int "+ARG+";" in game
         and ARG+" = lp_capturePointIndex;" in stock and "int lp_capturePointIndex = "+ARG+";" in stock_worker,
         "Unexpected stock argument observer")
    return game


def convert(shared):
    need(digest(shared) == SHARED_SCRIPT, "Incorrect SharedBeaconReset script")
    code = normalized(shared)
    code = once(code,"bool "+MARK+" = false;\n\n","")
    code = once(code,SOURCE_BRANCH,SIGNED_BRANCH)
    code = once(code,SCOPED_CALL,NEGATIVE_CALL)
    need(MARK not in code, "Scope marker survived")
    return code.replace("\n","\r\n").encode("ascii")


def exercise(signed, game, harness, cc):
    """Compile the actual wrappers and worker. Check that the argument is restored at every native observation."""
    worker = definition(signed,"bool",WORK)
    anchor = "int lp_capturePointIndex = "+ARG+";"
    argument_lines = [line.strip() for line in signed.splitlines() if ARG in line]
    need(argument_lines == [ARG+" = lp_capturePointIndex;", anchor, ARG+" = lp_capturePointIndex;"],
         "Unexpected map-script transfer-slot access")
    need(worker.index(anchor) < worker.index(SIGNED_BRANCH) < worker.index("if (((lp_capturePointIndex")
         < worker.index("ActorSend(") < worker.index("Wait("), "The shared index is not restored at entry")
    channel = definition(signed,"bool",CHAN)
    need(channel.count(NEGATIVE_CALL)==1, "Incorrect specialized call")
    declarations = [l for l in game.splitlines() if l.startswith(("trigger auto_"+DISABLE,"int "+ARG))]
    emitted = "\n".join([*declarations,definition(signed,"void",ENTRY),definition(game,"void",DISABLE),worker,
                          "struct { int lv_captureBeaconIndex; } libMapM_gv_mMGardensDragonDragonTowers[17];",
                          "static void extracted_dragon_call(int lv_itObelisk) {",
                          "libMapM_gv_mMGardensDragonDragonTowers[lv_itObelisk].lv_captureBeaconIndex=lv_itObelisk;",
                          NEGATIVE_CALL,"}"])
    code = harness.read_text(encoding="ascii")
    need(digest(code.encode("ascii")) == "4510a4b1d73e0594efe46e97dc5a84d4049fb6739f0843bc10aa8c43628d9ba3",
         "Unexpected shared-worker harness")
    # Keep the reviewed shared scheduler and reentrant trace. Now the stock argument is the only temporary.
    code = once(code,"!gv_HistoricalDragonDisablePending", ARG+"==3")
    code = once(code,"assert(actor>=101", "assert("+ARG+"==actor-100);\n    assert(actor>=101")
    code = once(code,"assert(clock==1", "assert("+ARG+">=0);\n    assert(clock==1")
    code = once(code,"assert(unit>=101", "assert("+ARG+">=0);\n    assert(unit>=101")
    code = once(code,"extracted_dragon_call(6);","extracted_dragon_call(6);\n    assert("+ARG+"==2);")
    code = once(code,"extracted_dragon_call(8);","extracted_dragon_call(8);\n    assert("+ARG+"==8);")
    with TemporaryDirectory() as folder:
        w = Path(folder)
        (w/"emitted.h").write_text(emitted,encoding="ascii")
        (w/"test.c").write_text(code,encoding="ascii")
        subprocess.run([cc,"-std=c11","-O0",str(w/"test.c"),"-o",str(w/"test")],check=True)
        subprocess.run([str(w/"test")],check=True)


def build(parent, shared, scripts, evidence, first, harness, output, stormlib, cc):
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    check_observations(evidence.read_bytes())
    check_first(first.read_bytes())
    raw = parent.read_bytes()
    need(digest(raw)==PARENT and digest(shared.read_bytes())==SHARED, "Unexpected source maps")
    storm = Storm(stormlib)
    before,_ = inventory(parent,storm)
    existing,_ = inventory(shared,storm)
    need(digest(before[MEMBER])==SCRIPT and before.keys()==existing.keys()
         and [k for k in before if before[k]!=existing[k]]==[MEMBER], "Unexpected reference overlay")
    game = argument_domain(scripts,normalized(before[MEMBER]))
    expected = convert(existing[MEMBER])
    with TemporaryDirectory(dir=output.parent) as folder:
        tmp = Path(folder)/"signed.s2ma"
        tmp.write_bytes(raw)
        storm.replace(tmp,{MEMBER:expected})
        after,checks = inventory(tmp,storm)
        need(after=={**before,MEMBER:expected} and parent.read_bytes()==raw, "Unexpected content change")
        with closing(MPQArchive(tmp)) as archive:
            physical = archive.read_file(MEMBER)
        need(physical==expected, "Readers disagree")
        exercise(normalized(physical),game,harness,cc)
        data = tmp.read_bytes()
        os.link(tmp,output)
    return {"map_sha256":digest(data),"bytes":len(data),"script_sha256":digest(expected),"parent_sha256":PARENT,
            "unchanged_content_members":len(before)-1,"reference_shared_map_sha256":SHARED,
            "registered_capture_index_domain":[1,15],"original_argument_symbol_mentions":3,
            "new_script_globals":0,"new_trigger_allocations":0,"mock_worker_dispatches":13,
            "mock_shared_handle_allocations":1,"ordinary_delay_loops":48,"dragon_delay_loops":16,
            "physical_activation_counts":{"41810":15,"98348":52},"native_execution_verified":False,
            "integrity":checks}


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for field in ("parent","shared","scripts","evidence","first","harness","output"):
        p.add_argument(field,type=Path)
    p.add_argument("--stormlib")
    p.add_argument("--cc",default="cc")
    print(json.dumps(build(**vars(p.parse_args())),indent=2))
