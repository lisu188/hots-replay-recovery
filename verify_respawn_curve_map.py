"""Check the packed map script independently and exercise its small callback in a C harness."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

from mpq_reader import MPQArchive
from mpq_mixed_sectors import read_member


def sha(path):
    return sha256(path.read_bytes()).hexdigest()


def map_script(path):
    with closing(MPQArchive(path)) as archive:
        return read_member(archive, "MapScript.galaxy")


def verify(base, candidate, library, evidence, cc):
    if (sha(base), sha(candidate), sha(library), sha(evidence)) != (
        "e6167145ee82e6c139f07336cd65fced5c86d162da19baad57a2d3e82b3a455e",
        "d41c5841a5719e76246265940d28b244bae91f4e3fef33e621f3a2e2a0ee7bbd",
        "15f0314a1c48a0391e76e22360847e7ef0c91b12a29da15d79453045c175a683",
        "d3155fc0d75ad42b35b11ab1cc977e8c6b155b9e2733b364b5eb1693edff356b",
    ):
        raise ValueError("Unexpected verification input")
    script = map_script(candidate).decode("ascii")
    callback, = re.findall(r"bool gt_HistoricalRespawnTimes_Func\b.*?\r\n\}", script, re.S)
    binding = '    libCore_gt_DataDeathTimes = TriggerCreate("gt_HistoricalRespawnTimes_Func");\r\n'
    original = script.replace(callback + "\r\n\r\n", "", 1).replace(binding, "", 1).encode("ascii")
    if original != map_script(base):
        raise ValueError("Original map script differs outside the two insertions")
    if not re.search(re.escape(binding) + r"    TriggerExecute\(libCore_gt_InitializeStormMod, true, true\);", script):
        raise ValueError("Missing pre-dispatch binding")
    body, = re.findall(r"bool libCore_gt_DataDeathTimes_Func\b.*?\n\}", library.read_text(), re.S)
    stock = {int(l): int(s) for l, s in re.findall(r"\[(\d+)\] = (\d+)\.0;", body)}
    old = {int(l): s for l, s in json.loads(evidence.read_bytes())["seconds_by_level"].items()}
    if set(stock) != set(range(1, 31)) or set(old) != set(range(1, 24)):
        raise ValueError("Incomplete timer evidence")
    target = {**stock, **old}
    array = lambda mapping: ",".join(str(mapping.get(i, -1)) for i in range(31))
    # The stub models the pinned initializer's value table, plus a failed initializer case.
    program = """
#include <stdbool.h>
static const double stock[31] = {STOCK_VALUES};
static const double expected[31] = {MERGED_VALUES};
static double libCore_gv_bALDeathTimes[31];
static bool available;
static bool observed_conds, observed_actions;
static int calls;
static bool libCore_gt_DataDeathTimes_Func(bool conds, bool actions) {
    calls++;
    observed_conds = conds;
    observed_actions = actions;
    if (available && actions) {
        for (int i = 1; i <= 30; i++) libCore_gv_bALDeathTimes[i] = stock[i];
    }
    return available;
}
CALLBACK_SOURCE
int main(void) {
    for (int cfg = 0; cfg < 8; cfg++) {
        const bool actions = (cfg & 1) != 0;
        const bool conds = (cfg & 2) != 0;
        available = (cfg & 4) != 0;
        calls = 0;
        for (int i = 0; i <= 30; i++) libCore_gv_bALDeathTimes[i] = -1;
        if (gt_HistoricalRespawnTimes_Func(conds, actions) != available) return 1;
        if (calls != 1 || observed_conds != conds || observed_actions != actions) return 2;
        for (int i = 0; i <= 30; i++) {
            if (libCore_gv_bALDeathTimes[i] != (available && actions ? expected[i] : -1)) return 3;
        }
    }
    return 0;
}
"""
    program = program.replace("STOCK_VALUES",array(stock)).replace("MERGED_VALUES",array(target))
    with TemporaryDirectory() as directory:
        cfile = Path(directory) / "test.c"
        exe = Path(directory) / "test"
        cfile.write_text(program.replace("CALLBACK_SOURCE", callback), encoding="ascii")
        subprocess.run([cc, "-std=c99", "-pedantic", "-Wall", "-Wextra", "-Werror",
                        str(cfile), "-o", str(exe)], check=True)
        subprocess.run([str(exe.resolve())], check=True)
    return dict(map_sha256=sha(candidate), script_outside_insertions_matches=True,
                delegated_calls_per_dispatch=1, callback_cases=8, slots_checked_per_case=31,
                changed_levels=[i for i in old if old[i] != stock[i]],
                unchanged_unobserved_levels=list(range(24,31)), native_playback_verified=False)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("base", "candidate", "library", "evidence"):
        cli.add_argument("--"+name, required=True, type=Path)
    cli.add_argument("--cc", default="cc")
    args = cli.parse_args()
    print(json.dumps(verify(args.base, args.candidate, args.library, args.evidence, args.cc), indent=2))
