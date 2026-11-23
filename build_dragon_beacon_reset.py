"""Build a HistoricalCamps derivative with the historical Dragon Knight beacon reset delay."""

import argparse
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from build_dragonshire_talent_map import digest, inventory
from build_gate_order_map import definition, once
from runtime_catalog_probe import Storm


PARENT = "5c241e8f9f316909ea237e5dd9f1c4d4ec2e7ea3224d383c596588c7eaf1b9ae"
SCRIPT = "eac619f500d79a9fbdb733bcd65d81fd3d99d27472ba7476cba890ee7aea9b10"
GAME = "a6384749fbe8f676cbd6ccb9ec1aeac004815d37a8e1c2f8f9f8f176b2bfca09"
MECHANICS = "d49dbde21198963f953efa16c8d8bb6b035d2d8bd8f0d41b5989fecbb4e35b1f"
EVIDENCE = "1b571c891d5b5646c21d39e6552af48b1b98926d4b0b948c556ae19408600a94"
TRANSFORM = "libMapM_gt_MMGardensDragonTransformChannelFinish"
GATE = "gf_HistoricalCampInitTriggers"
DISABLE = "libGame_gf_CapturePointDisable"
WORKER = "gf_HistoricalDragonBeaconDisable"
CALLBACK = "gt_HistoricalDragonKnightFinished"
REGISTER = "gf_RegisterHistoricalDragonKnightFinished"
MEMBER = "MapScript.galaxy"


def need(ok, message):
    if not ok:
        raise ValueError(message)


def check_observations(raw):
    doc = json.loads(raw)
    seen = set()
    for key, matches, captures, delay in (("old_replays", 5, 15, 16), ("target_controls", 15, 52, 48)):
        records = doc[key]
        ids = {r["sha256"] for r in records}
        need(len(records) == len(ids) == matches and not seen.intersection(ids), "Incorrect replay cohort")
        seen.update(ids)
        for record in records:
            loops = [row[0] for row in record["knight_loop_shrine_resets_and_beacon_delays"]]
            need(loops and loops == sorted(set(loops)) and loops[0] > record["gates_open"],
                 "Invalid or duplicate Dragon Knight activation loop")
        cycles = [row for r in records for row in r["knight_loop_shrine_resets_and_beacon_delays"]]
        need(len(cycles) == captures and all(row[1:] == [2, [delay, delay]] for row in cycles),
             "Dragon Knight reset interval diverged")
    canonical = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("ascii")
    need(digest(canonical) == EVIDENCE, "Historical shrine receipt differs from the pinned cohort report")


def generate(script_raw, game_raw, mech_raw, evidence):
    need(tuple(map(digest, (script_raw, game_raw, mech_raw))) == (SCRIPT, GAME, MECHANICS),
         "Unexpected parent script or target libraries")
    check_observations(evidence)
    parent, game, mech = [v.decode("utf-8-sig").replace("\r\n", "\n")
                          for v in (script_raw, game_raw, mech_raw)]
    for name in (WORKER, CALLBACK, REGISTER):
        need(all(name not in v for v in (parent, game, mech)), "New Galaxy name collides")
    spec = "auto_" + DISABLE
    declarations = [line for line in game.splitlines() if line.startswith(("trigger " + spec, "int " + spec))]
    need(len(declarations) == 2, "Unexpected callback globals")
    # Preserve the target's asynchronous per-index dispatch and capture of the parameter before its wait.
    wrapper = definition(game, "void", DISABLE)
    body = definition(game, "bool", spec + "_TriggerFunc")
    body = once(body, "Wait(3.0, c_timeGame);", "Wait(1.0, c_timeGame);")
    worker = "\n\n".join(("\n".join(declarations), wrapper, body)).replace(DISABLE, WORKER)
    channel = definition(mech, "bool", TRANSFORM + "_Func")
    channel = once(channel, "bool " + TRANSFORM + "_Func (", "bool " + CALLBACK + " (")
    channel = once(channel, DISABLE + "(", WORKER + "(")
    register = definition(mech, "void", TRANSFORM + "_Init")
    register = once(register, "void " + TRANSFORM + "_Init (", "void " + REGISTER + " (")
    register = once(register, 'TriggerCreate("' + TRANSFORM + '_Func")', 'TriggerCreate("' + CALLBACK + '")')
    stock_init = definition(parent, "void", GATE)
    changed_init = once(stock_init, TRANSFORM + "_Init();", REGISTER + "();")
    script = once(parent, stock_init, "\n\n".join((worker, channel, register, changed_init)))
    return script.replace("\n", "\r\n").encode("ascii")


def build(parent, game, mechanics, evidence, output, stormlib):
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    raw = parent.read_bytes()
    need((len(raw), digest(raw)) == (2159443, PARENT), "Incorrect HistoricalCamps archive")
    storm = Storm(stormlib)
    before, _ = inventory(parent, storm)
    changed = generate(before[MEMBER], game.read_bytes(), mechanics.read_bytes(), evidence.read_bytes())
    with TemporaryDirectory(dir=output.parent) as directory:
        tmp = Path(directory) / "beacon.s2ma"
        tmp.write_bytes(raw)
        storm.replace(tmp, {MEMBER: changed})
        after, check = inventory(tmp, storm)
        need(after == {**before, MEMBER: changed} and parent.read_bytes() == raw, "Archive differs")
        result = tmp.read_bytes()
        os.link(tmp, output)
    return {"parent_sha256": PARENT, "sha256": digest(result), "bytes": len(result),
            "script_sha256": digest(changed), "unchanged_content_members": len(before) - 1, "integrity": check}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("parent", "game", "mechanics", "evidence", "output"):
        parser.add_argument(field, type=Path)
    parser.add_argument("--stormlib")
    print(json.dumps(build(**vars(parser.parse_args())), indent=2))
