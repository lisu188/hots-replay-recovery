"""Check the emitted trigger chain and run its two Galaxy worker functions with mock native calls."""

import argparse
from contextlib import closing
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from build_dragonshire_talent_map import digest, inventory
from build_dragon_beacon_reset import (
    CALLBACK, DISABLE, EVIDENCE, GAME, GATE, MECHANICS, MEMBER, PARENT, REGISTER, SCRIPT,
    TRANSFORM, WORKER, check_observations, need,
)
from build_gate_order_map import definition
from mpq_reader import MPQArchive
from runtime_catalog_probe import Storm


def as_text(raw):
    return raw.decode("utf-8-sig").replace("\r\n", "\n")


def negative_evidence_checks(raw):
    def reject(doc):
        try:
            check_observations(json.dumps(doc).encode("ascii"))
        except ValueError:
            return
        raise ValueError("Accepted fabricated historical evidence")

    modified = json.loads(raw)
    modified["old_replays"][0]["sha256"] = "0" * 64
    reject(modified)
    modified = json.loads(raw)
    modified["old_replays"][0]["sha256"] = modified["old_replays"][1]["sha256"]
    reject(modified)
    modified = json.loads(raw)
    cycles = modified["old_replays"][0]["knight_loop_shrine_resets_and_beacon_delays"]
    cycles[1][0] = cycles[0][0]
    reject(modified)
    modified = json.loads(raw)
    for record in modified["old_replays"]:
        for cycle in record["knight_loop_shrine_resets_and_beacon_delays"]:
            cycle[0] = 0
    reject(modified)


def verify(parent, candidate, game, mechanics, evidence, stormlib, cc):
    storm = Storm(stormlib)
    old, _ = inventory(parent, storm)
    updated, _ = inventory(candidate, storm)
    need((digest(parent.read_bytes()), digest(old[MEMBER]), digest(game.read_bytes()), digest(mechanics.read_bytes()))
         == (PARENT, SCRIPT, GAME, MECHANICS), "Input identity differs")
    need(old.keys() == updated.keys() and [k for k in old if old[k] != updated[k]] == [MEMBER],
         "Unexpected modified members")
    check_observations(evidence.read_bytes())
    negative_evidence_checks(evidence.read_bytes())
    stock_map, patched, game_code, rules = map(as_text, (old[MEMBER], updated[MEMBER], game.read_bytes(), mechanics.read_bytes()))
    with closing(MPQArchive(candidate)) as a:
        need(a.read_file(MEMBER) == updated[MEMBER], "Readers disagree on emitted script")
    need(definition(patched, "void", "InitLibs").count("gf_HistoricalCampInitLib();") == 1
         and definition(patched, "void", "gf_HistoricalCampInitLib").count(GATE + "();") == 1,
         "Historical library registration is unreachable")
    stock_init, new_init = [definition(s, "void", GATE) for s in (stock_map, patched)]
    need(new_init.replace(REGISTER + "();", TRANSFORM + "_Init();") == stock_init
         and new_init.count(REGISTER + "();") == 1, "Trigger registration order differs")
    registration = definition(patched, "void", REGISTER)
    need(registration.replace(REGISTER, TRANSFORM + "_Init").replace('"' + CALLBACK + '"', '"' + TRANSFORM + '_Func"')
         == definition(rules, "void", TRANSFORM + "_Init"), "Altered trigger global, event, or initial state")
    channel = definition(patched, "bool", CALLBACK)
    need(channel.replace("bool " + CALLBACK + " (", "bool " + TRANSFORM + "_Func (").replace(WORKER + "(", DISABLE + "(")
         == definition(rules, "bool", TRANSFORM + "_Func"), "Altered Dragon Knight callback")
    helper = definition(patched, "void", WORKER)
    worker = definition(patched, "bool", "auto_" + WORKER + "_TriggerFunc")
    need(helper.replace(WORKER, DISABLE) == definition(game_code, "void", DISABLE), "Altered async call mode")
    need(worker.count("Wait(1.0, c_timeGame);") == 1
         and worker.replace(WORKER, DISABLE).replace("Wait(1.0,", "Wait(3.0,")
         == definition(game_code, "bool", "auto_" + DISABLE + "_TriggerFunc"), "Altered worker actions or guards")
    start = patched.index("trigger auto_" + WORKER)
    end = patched.index("void " + GATE + " (", start)
    restored = (patched[:start] + patched[end:]).replace(new_init, stock_init)
    need(restored == stock_map and patched.count(WORKER + "(") == 1,
         "Changes outside intended map section")
    globals_ = "\n".join(l for l in patched.splitlines()
                         if l.startswith(("trigger auto_" + WORKER, "int auto_" + WORKER)))
    preamble = r"""
#define _XOPEN_SOURCE 700
#include <assert.h>
#include <stdbool.h>
#include <string.h>
#include <ucontext.h>
typedef int trigger;
#define null 0
struct Capture { bool lv_enabled; int lv_captureBeaconUnit; int owner; } libGame_gv_capturePoints[4];
int libGame_gv_capturePointCurrentCount=3, libCore_gv_cOMPUTER_Neutral=0, c_timeGame=1;
static int now, armed, dispatched, current=-1, signal_count, write_count, actors[4], units[4], times[4];
enum state { UNUSED, RUNNING, WAITING, DONE };
struct task { ucontext_t context; unsigned char stack[65536]; enum state state; int deadline; };
static struct task tasks[5];
static ucontext_t scheduler;
bool auto_gf_HistoricalDragonBeaconDisable_TriggerFunc(bool, bool);
static trigger TriggerCreate(const char *name) {
    assert(strcmp(name,"auto_gf_HistoricalDragonBeaconDisable_TriggerFunc")==0);
    return ++armed;
}
static void worker_entry(void) {
    assert(auto_gf_HistoricalDragonBeaconDisable_TriggerFunc(false, true));
    tasks[current].state=DONE;
}
static void resume(int id) {
    current=id;
    tasks[id].state=RUNNING;
    assert(swapcontext(&scheduler,&tasks[id].context)==0);
    assert(tasks[id].state==WAITING || tasks[id].state==DONE);
    current=-1;
}
static void TriggerExecute(trigger t, bool conditions, bool wait) {
    assert(t==1 && !conditions && !wait && dispatched<5);
    int id=dispatched++;
    struct task *task=&tasks[id];
    assert(getcontext(&task->context)==0);
    task->context.uc_stack.ss_sp=task->stack;
    task->context.uc_stack.ss_size=sizeof(task->stack);
    task->context.uc_stack.ss_flags=0;
    task->context.uc_link=&scheduler;
    makecontext(&task->context,worker_entry,0);
    resume(id);
}
static void advance(int tick) {
    assert(tick>=now);
    now=tick;
    for (int i=dispatched-1;i>=0;i--) {
        if (tasks[i].state==WAITING && tasks[i].deadline<=now) resume(i);
    }
}
static int libNtve_gf_MainActorofUnit(int unit) { return unit; }
static void ActorSend(int actor,const char *signal) {
    assert(strcmp(signal,"Signal Hide")==0); actors[signal_count++]=actor;
}
static void Wait(double delay, int clock) {
    const int id=current;
    assert(clock==1 && tasks[id].state==RUNNING);
    tasks[id].deadline=now+(int)(16*delay);
    tasks[id].state=WAITING;
    assert(swapcontext(&tasks[id].context,&scheduler)==0);
    assert(current==id && tasks[id].state==RUNNING && now==tasks[id].deadline);
}
static void UnitSetOwner(int unit,int owner,bool change) {
    assert(unit>=101 && unit<=103 && owner==0 && change);
    libGame_gv_capturePoints[unit-100].owner=owner;
    units[write_count]=unit; times[write_count++]=now;
}
"""
    test = r"""
int main(void) {
    for (int i=1;i<=3;i++) { libGame_gv_capturePoints[i]=(struct Capture){true,100+i,12}; }
    now=2514;
    gf_HistoricalDragonBeaconDisable(1);
    gf_HistoricalDragonBeaconDisable(2);
    gf_HistoricalDragonBeaconDisable(2);
    gf_HistoricalDragonBeaconDisable(4);
    assert(dispatched==4 && armed==1 && signal_count==2 && write_count==0);
    assert(tasks[0].state==WAITING && tasks[1].state==WAITING);
    assert(tasks[2].state==DONE && tasks[3].state==DONE);
    assert(!libGame_gv_capturePoints[1].lv_enabled && !libGame_gv_capturePoints[2].lv_enabled);
    assert(libGame_gv_capturePoints[3].lv_enabled);
    advance(2529);
    assert(!write_count && libGame_gv_capturePoints[1].owner==12 && libGame_gv_capturePoints[2].owner==12);
    advance(2530);
    assert(write_count==2 && tasks[0].state==DONE && tasks[1].state==DONE);
    assert(actors[0]==101 && units[0]==102 && times[0]==2530);
    assert(actors[1]==102 && units[1]==101 && times[1]==2530);
    assert(libGame_gv_capturePoints[1].owner==0 && libGame_gv_capturePoints[2].owner==0);
    assert(libGame_gv_capturePoints[3].owner==12);
    libGame_gv_capturePoints[1].lv_enabled=true; libGame_gv_capturePoints[1].owner=11;
    advance(7734);
    gf_HistoricalDragonBeaconDisable(1);
    advance(7749);
    assert(write_count==2 && libGame_gv_capturePoints[1].owner==11 && tasks[4].state==WAITING);
    advance(7750);
    assert(armed==1 && write_count==3 && units[2]==101 && times[2]==7750);
    return 0;
}
"""
    with TemporaryDirectory() as td:
        path = Path(td)
        source = path / "worker.c"
        binary = path / "check"
        source.write_text("\n".join((preamble, globals_, helper, worker, test)), encoding="ascii")
        subprocess.run([cc, "-std=c11", "-O0", str(source), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
    return {"map_sha256": digest(candidate.read_bytes()), "script_sha256": digest(updated[MEMBER]),
            "other_content_members_identical": len(old) - 1, "stock_registration_slot_verified": True,
            "opening_and_ordinary_disable_paths_preserved": True, "stock_transform_single_call_changed": True,
            "extracted_worker_mock_native_test": "passed", "dedicated_trigger_created_lazily": True,
            "posix_workers_suspended_concurrently": 2, "owner_unchanged_through_wait_loop": 15,
            "mock_simultaneous_beacon_resume_order": "reverse_dispatch",
            "resumed_write_loop_after_dispatch": 16, "canonical_evidence_sha256": EVIDENCE,
            "fabricated_cohort_and_loop_negative_tests": 4,
            "native_compile_or_execution_verified": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("parent", "candidate", "game", "mechanics", "evidence"):
        parser.add_argument(field, type=Path)
    parser.add_argument("--stormlib")
    parser.add_argument("--cc", default="cc")
    print(json.dumps(verify(**vars(parser.parse_args())), indent=2))
