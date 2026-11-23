"""Independently check binding, complete callback and compiled map-emitted ordering code."""

import argparse
from contextlib import closing
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import random
import re
import subprocess
from tempfile import TemporaryDirectory
from xml.etree import ElementTree

from encoders import encode_tracker_events
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from protocol_loader import load_protocol


def member(path, name):
    with closing(MPQArchive(path)) as archive:
        return read_member(archive, name)


def function(source, name):
    return re.findall(r"^\w+ " + name + r" \([^\n]*\) \{.*?^\}", source, re.M | re.S)[0]


def verify_source(parent, candidate, manifest):
    if sha256(manifest.read_bytes()).hexdigest() != "87b44ff3f91d9058f5001f926129a04d225f8a11fa05b99e1571362539ec3b7b":
        raise ValueError("Unrecognized pinned library inventory")
    programs = {}
    for row in json.loads(manifest.read_bytes())["members"]:
        raw = (manifest.parent / row["saved_name"]).read_bytes()
        assert len(raw) == row["bytes"] and sha256(raw).hexdigest() == row["sha256"]
        programs[row["saved_name"]] = raw.decode("utf-8-sig").replace("\r\n", "\n")
    source = member(parent, "MapScript.galaxy").decode("ascii").replace("\r\n", "\n")
    emitted = member(candidate, "MapScript.galaxy").decode("ascii").replace("\r\n", "\n")
    assert sha256(parent.read_bytes()).hexdigest() == "58874aca37caeacaf42789a7e90fd2da830559f6cd744c32f5724e4477a6fcb3"
    include = re.compile(r'^include "TriggerLibs/(\w+)"', re.M)
    queue = include.findall(source)
    reachable = set()
    while queue:
        name = queue.pop().lower() + ".galaxy"
        if name not in reachable:
            reachable.add(name)
            queue.extend(include.findall(programs[name]))
    assert reachable == set(programs) and len(reachable) == 22
    game = programs["gamelib.galaxy"]
    stock = "libGame_gt_OpenTheGatesOpenTheGatesTimerExpires"
    names = ["gf_RemoveGateBlockersInOrder", "gt_HistoricalGatesOpen_Func", "gf_HistoricalGatesOpenInit",
             "gf_HistoricalGameInitTriggers", "gf_HistoricalGameInitLib"]
    sorter, callback, register, triggers, library = [function(emitted, n) for n in names]
    restored = emitted
    for name in names:
        assert name not in source and all(name not in text for text in programs.values())
        restored = restored.replace(function(restored, name) + "\n\n", "", 1)
    assert restored.replace(names[4]+"();", "libGame_InitLib();") == source
    assert function(emitted, "InitLibs").replace(names[4]+"();", "libGame_InitLib();") == function(source, "InitLibs")
    assert function(game, "libGame_InitLib") == library.replace(names[4]+" (", "libGame_InitLib (").replace(names[3]+"();", "libGame_InitTriggers();")
    stock_triggers = function(game, "libGame_InitTriggers")
    assert stock_triggers == triggers.replace(names[3]+" (", "libGame_InitTriggers (").replace(names[2]+"();", stock+"_Init();")
    assert function(game, stock+"_Init") == register.replace(names[2]+" (", stock+"_Init (").replace('"'+names[1]+'"', '"'+stock+'_Func"')
    assert f'TriggerAddEventTimer({stock}, libGame_gv_openTheGatesTimer);' in register
    for name, total in (("libGame_InitLib", 1), ("libGame_InitTriggers", 1), (stock+"_Init", 1)):
        assert sum(t.count(name+"();") for t in [source, *programs.values()]) == total
        assert all('"'+name+'"' not in t for t in [source, *programs.values()])
    original = function(game, stock+"_Func").splitlines()
    altered = callback.replace(names[1]+" (", stock+"_Func (").splitlines()
    group_calls = []
    while original:
        l = original.pop(0)
        if re.fullmatch(r"    (?:unit lv_itBlocker|int auto(?:157DB87C|4CAD3EA8)_u);", l):
            continue
        match = re.fullmatch(r"        (auto\w+)_u = UnitGroupCount\(\1_g, c_unitCountAll\);", l)
        if match:
            group = match.group(1)
            assert original[:5] == [
                f"        for (;; {group}_u -= 1) {{",
                f"            lv_itBlocker = UnitGroupUnitFromEnd({group}_g, {group}_u);",
                "            if (lv_itBlocker == null) { break; }",
                "            UnitRemove(lv_itBlocker);", "        }"]
            del original[:5]
            assert altered.pop(0) == f"        {names[0]}({group}_g);"
            group_calls.append(group)
        else:
            assert altered.pop(0) == l
    assert not altered and group_calls == ["auto157DB87C", "auto4CAD3EA8"]
    registrations = re.findall(r"^    (libGame_\w+_Init)\(\);$", stock_triggers, re.M)
    assert len(registrations) == len(set(registrations))
    return sorter, dict(libraries=len(reachable), copied_game_initializer_calls=len(registrations),
                        gates_registration_position=registrations.index(stock+"_Init")+1,
                        only_two_iteration_bodies_changed=True, same_completion_flag_timer_and_registration=True)


HARNESS_HEAD = """
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
typedef int32_t fixed;
typedef struct {int id; fixed x,y; int removed;} Actor;
typedef Actor *unit;
typedef Actor *point;
typedef struct {unit slots[128]; int count;} Group;
typedef Group *unitgroup;
#define null NULL
#define c_unitCountAll 0
static int UnitGroupCount(unitgroup g, int kind) {assert(kind==0);return g->count;}
static unit UnitGroupUnitFromEnd(unitgroup g,int i) {assert(i>0 && i<=g->count);return g->slots[g->count-i];}
static point UnitGetPosition(unit p) {assert(p && !p->removed);return p;}
static fixed PointGetX(point p) {return p->x;}
static fixed PointGetY(point p) {return p->y;}
static void UnitGroupRemove(unitgroup g,unit u) {int i;
    for(i=0; i<g->count && g->slots[i]!=u; ++i) {}
    assert(i<g->count); --g->count;
    memmove(g->slots+i,g->slots+i+1,(g->count-i)*sizeof(unit));}
static void UnitRemove(unit p) {assert(p && !p->removed);p->removed=1;printf(" %d",p->id);}
"""
HARNESS_MAIN = """
int main(void) {
  int n;
  while(scanf("%d",&n)==1) {
    Group g={0}; Actor actors[128]={0}; assert(n>=0 && n<=128);
    for(int i=0;i<n;i++) {
      assert(scanf("%d%d%d",&actors[i].id,&actors[i].x,&actors[i].y)==3);
      g.slots[g.count++]=actors+i;
    }
    gf_RemoveGateBlockersInOrder(&g);
    assert(g.count==0);
    for(int i=0;i<n;i++) assert(actors[i].removed);
    puts("");
  }
  return 0;
}
"""


def verify_sorter(parent, sorter, cc):
    nodes = sorted(ElementTree.fromstring(member(parent, "Objects")).findall("ObjectUnit"), key=lambda e:int(e.get("Id")))
    groups = [[], []]
    types = ["StormGameStartPathingBlocker", "StormGameStartPathingBlockerDiagonal"]
    for index, node in enumerate(nodes):
        if node.get("UnitType") in types:
            x,y,_ = [Decimal(z)*4096 for z in node.get("Position").split(",")]
            assert x == int(x) and y == int(y)
            groups[types.index(node.get("UnitType"))].append((index,int(x),int(y)))
    assert list(map(len,groups)) == [30,24] and all(len({r[1:] for r in g})==len(g) for g in groups)
    cases = []
    generator = random.Random(4181098348)
    for _ in range(256):
        for group in groups:
            shuffled = group.copy()
            generator.shuffle(shuffled)
            cases.append(shuffled)
    cases.extend([[], [(71,-1,5)], [(9,0,-8192),(8,-32,-8192),(7,-31,-8192),(1,21,0)]])
    expected = [[r[0] for r in sorted(group,key=lambda r:(r[2],r[1]))] for group in cases]
    payload = "".join(str(len(group))+"\n"+"".join(f"{i} {x} {y}\n" for i,x,y in group) for group in cases)
    with TemporaryDirectory() as t:
        build = Path(t)
        path = build/"sort.c"
        exe = build/"sort"
        path.write_text(HARNESS_HEAD+sorter+HARNESS_MAIN)
        subprocess.run([cc,"-std=c11","-Wall","-Wextra","-Werror",str(path),"-o",str(exe)],check=True)
        out = subprocess.run([str(exe)],input=payload,text=True,capture_output=True,check=True)
    orders = [[int(s) for s in line.split()] for line in out.stdout.splitlines()]
    assert orders == expected
    coords = {i:(x//4096,y//4096) for group in groups for i,x,y in group}
    raw = encode_tracker_events([dict(_eventid=2,_event="NNet.Replay.Tracker.SUnitDiedEvent",
            _gameloop=610,m_unitTagIndex=i,m_unitTagRecycle=1,m_killerPlayerId=0,m_x=coords[i][0],
            m_y=coords[i][1],m_killerUnitTagIndex=None,m_killerUnitTagRecycle=None)
        for i in orders[0]+orders[1]],load_protocol(96477))
    signature = sha256(raw).hexdigest()
    assert (len(raw),signature)==(1836,"b5d20bbe65a5b09b83f2ec0822a96541809a8b2b7e7068d47dcfe13409f83a94")
    return dict(shuffled_group_pairs=256,synthetic_edge_cases=3,unit_removals=sum(map(len,orders)),source_sparse_bytes=len(raw),
                source_sparse_sha256=signature, authentic_group_sizes=list(map(len,groups)))


def verify(parent, candidate, manifest, cc="cc"):
    if not __debug__:
        raise RuntimeError("Assertions are required")
    sorter, report = verify_source(parent, candidate, manifest)
    return {**report, **verify_sorter(parent, sorter, cc)}


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("parent","candidate","manifest"):
        cli.add_argument("--"+name,type=Path,required=True)
    cli.add_argument("--cc", default="cc")
    print(json.dumps(verify(**vars(cli.parse_args())),indent=2))
