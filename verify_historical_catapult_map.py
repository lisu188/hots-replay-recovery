"""Verify the installed wave callback and exercise its actual per-unit catapult condition."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
from xml.etree import ElementTree

from build_historical_catapult_map import (
    BASE,
    GAME,
    KEEP,
    UNIT,
    STOCK_UNIT,
    WAVE,
    STOCK_WAVE,
    DISPATCH,
    HOOK,
    PERIOD,
    definition,
)
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive


def local_script(path):
    with closing(MPQArchive(path)) as archive:
        data = read_member(archive, "MapScript.galaxy")
    return data.decode("ascii").replace("\r\n", "\n")


def mapping(base, script):
    with closing(MPQArchive(base)) as archive:
        objects = ElementTree.fromstring(read_member(archive, "Objects"))
        regions = ElementTree.fromstring(read_member(archive, "Regions"))
    halls = [
        e
        for e in objects.findall("ObjectUnit")
        if e.get("UnitType") in ("TownTownHallL2", "TownTownHallL3")
    ]
    inspected = []
    body = definition(script, "bool", "gt_HookupTownData_Func")
    lanes = re.split(r"lv_lane = (\d+);", body)[1:]
    for lane, chunk in zip(lanes[::2], lanes[1::2]):
        for town in chunk.split("lv_town += 1;")[1:]:
            (rid,) = re.findall(r"lv_townRegion = RegionFromId\((\d+)\);", town)
            (team,) = re.findall(
                r"lv_owner = libCore_gv_cOMPUTER_Team(Order|Chaos);", town
            )
            x0, y0, x1, y1 = map(
                float,
                regions.find("./region[@id='" + rid + "']/shape/quad")
                .get("value")
                .split(","),
            )
            matches = []
            for h in halls:
                x, y, _ = map(float, h.get("Position").split(","))
                if x0 <= x <= x1 and y0 <= y <= y1:
                    matches.append(h)
            (hall,) = matches
            is_keep = "lv_makesCoreVulnerableWhenKilled = true;" in town
            if is_keep != (hall.get("UnitType") == "TownTownHallL3"):
                raise ValueError("Town flag disagrees with authored hall type")
            inspected.append((int(lane), team, is_keep))
    if len(inspected) != 12 or len(set(inspected)) != 12:
        raise ValueError("Not two distinct buildings on each side of each lane")
    return inspected


def verify(base, candidate, game_path, cc):
    if (
        sha256(base.read_bytes()).hexdigest() != BASE
        or sha256(game_path.read_bytes()).hexdigest() != GAME
    ):
        raise ValueError("Wrong map parent or GameLib")
    original = local_script(base)
    changed = local_script(candidate)
    game = game_path.read_text(encoding="utf-8-sig")
    for symbol in (KEEP, UNIT, WAVE):
        if symbol in original:
            raise ValueError("Destination symbol collision")
    bind = (
        "        if (" + DISPATCH + " == null) {\n"
        "            " + DISPATCH + ' = TriggerCreate("' + WAVE + '");\n        }'
    )
    if changed.count(bind) != 1 or changed.count(PERIOD + "\n" + bind) != 1:
        raise ValueError("Wave callback binding")
    start = changed.index("bool " + KEEP + " (")
    stop = changed.index(HOOK)
    if (changed[:start] + changed[stop:]).replace(
        PERIOD + "\n" + bind, PERIOD
    ) != original:
        raise ValueError("Parent script outside insertions changed")
    native = definition(game, "void", STOCK_UNIT).splitlines()
    alt = (
        definition(changed, "void", UNIT)
        .replace("void " + UNIT, "void " + STOCK_UNIT, 1)
        .splitlines()
    )
    if len(native) != len(alt):
        raise ValueError("Per-unit helper length")
    ((old_gate, gate),) = [(a, b) for a, b in zip(native, alt) if a != b]
    if not (
        "TownsAliveinLane" in old_gate
        and "TownsAliveinLane" not in gate
        and KEEP in gate
    ):
        raise ValueError("Wrong gate splice")
    stock_wave = definition(game, "bool", STOCK_WAVE)
    candidate_wave = (
        definition(changed, "bool", WAVE)
        .replace(WAVE + " (", STOCK_WAVE + " (", 1)
        .replace(UNIT + "(", STOCK_UNIT + "(")
    )
    if stock_wave != candidate_wave:
        raise ValueError("Wave body differs outside callback names")
    keep = definition(changed, "bool", KEEP)
    inspected = mapping(base, original)
    pre = """#include <stdbool.h>
#include <stdio.h>
typedef struct { int lv_lane,lv_owner,lv_townHallIndex; bool lv_makesCoreVulnerableWhenKilled; } Town;
Town libGame_gv_townTownData[13]; int libGame_gv_townTownCount=12;
int libGame_gv_minion_CatapultGroup[3]; int libGame_gv_minion_CatapultCap_C=15;
enum {libCore_ge_MinionTypes_Catapult=4,libCore_ge_MinionTypes_CustomCatapult1=5,libCore_ge_MinionTypes_CustomCatapult2=6,c_unitCountAlive=1};
bool libGame_gv_minionMapNeverSpawnsCatapults,libGame_gv_minion_CapCatapults,alive[13];
int UnitGroupCount(int n,int mask){return n;}
int libGame_gf_TeamNumberOfPlayer(int p){return p-10;}
int libGame_gf_EnemyTeam(int t){return 3-t;}
int libGame_gf_ComputerPlayerInTeam(int t){return 10+t;}
int libGame_gf_TownTownHall(int t){return t;}
bool UnitIsAlive(int u){return alive[u];}
"""
    snippet = (
        pre
        + keep
        + "\nbool allow(int lp_lane,int lp_owner,int lp_type){\n    int lv_minionTeam=lp_owner-10;\n"
        + gate
        + "\nreturn false; } return true; }\n"
    )
    snippet += """int main(void) {
 int trials=0;
 for(int lane=1;lane<=3;lane++)for(int owner=11;owner<=12;owner++)for(int keep=0;keep<2;keep++)
 for(int fort=0;fort<2;fort++)for(int never=0;never<2;never++)for(int cap=0;cap<2;cap++)
 for(int count=14;count<=15;count++)for(int type=1;type<=6;type++) {
   int id=1,opposing=23-owner;
   for(int l=1;l<=3;l++)for(int o=11;o<=12;o++)for(int k=0;k<=1;k++,id++) {
     libGame_gv_townTownData[id]=(Town){l,o,1,k};
     alive[id]=(l==lane && o==opposing) ? (k ? keep:fort) : !(k ? keep:fort);
   }
   libGame_gv_minionMapNeverSpawnsCatapults=never;
   libGame_gv_minion_CapCatapults=cap;libGame_gv_minion_CatapultGroup[owner-10]=count;
   bool expected=type<4 || (!keep && !never && !(cap && count>=15));
   if(allow(lane,owner,type)!=expected)return 1;
   trials++;
 }
 printf("%d",trials);return 0;
}
"""
    with TemporaryDirectory() as tmp:
        src = Path(tmp) / "model.c"
        exe = Path(tmp) / "model"
        src.write_text(snippet, encoding="ascii")
        subprocess.run([cc, "-std=c99", str(src), "-o", str(exe)], check=True)
        n = int(subprocess.check_output([str(exe)], text=True))
    return dict(
        authenticated_per_unit_function_differing_body_lines=1,
        native_wave_body_equal=True,
        parent_outside_insertions_equal=True,
        fort_and_keep_map_regions=len(inspected),
        gate_harness_cases=n,
        fort_alive_keep_dead_exercised=True,
        native_runtime_verified=False,
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for key in ("base", "candidate", "game"):
        cli.add_argument("--" + key, type=Path, required=True)
    cli.add_argument("--cc", default="cc")
    a = cli.parse_args()
    print(json.dumps(verify(a.base, a.candidate, a.game, a.cc), indent=2))
