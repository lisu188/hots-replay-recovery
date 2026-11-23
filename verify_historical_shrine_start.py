"""Audit first shrine captures and Dragon Knight resets directly from replay archives."""

import argparse
from collections import defaultdict
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from xml.etree import ElementTree

from mpq_reader import MPQArchive
from protocol_loader import load_protocol


OLD_MAP = "e0a58745837b3b5351015c933560dbffb178d747009d2d57b4153ef425cf7250"
GATE_ORDER = "bda7aafd1d63c77b3b4d29ff2afee96da09a3104b54b4a1d625bb299607d9008"
NEW_MAP = "f557190f8aaab160789272ce086b8b69d6a8037b152de150332603dae3dc098f"
TEN = "e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824"
LIBRARY = "d49dbde21198963f953efa16c8d8bb6b035d2d8bd8f0d41b5989fecbb4e35b1f"
HEADER = "cef6f04b1723e88bfb33b8a04584798276fea30f9920d1bd21055646e2bb52da"
GAME = "a6384749fbe8f676cbd6ccb9ec1aeac004815d37a8e1c2f8f9f8f176b2bfca09"
SHRINES = {b"DragonShireShrineSun", b"DragonShireShrineMoon"}
BEACON = b"DragonballCaptureBeacon"


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest(data):
    return sha256(data).hexdigest()


def read_map(path, expected):
    need(digest(path.read_bytes()) == expected, "Incorrect map archive")
    with closing(MPQArchive(path)) as archive:
        script = archive.read_file("MapScript.galaxy")
        triggers = archive.read_file("Triggers")
        info = archive.read_file("DocumentInfo")
        members = archive.read_file("(listfile)")
        for prefix in ("", "Base.StormData\\", "Base.SC2Data\\"):
            for suffix in ("", "_h"):
                key = prefix + "TriggerLibs\\MapMechanicsLib" + suffix + ".galaxy"
                need(archive.get_hash_table_entry(key) is None, "Map contains targeted library")
    need(b'MapMechanicsLib' not in members and b'include "TriggerLibs/MapMechanicsLib"' in script
         and b'libMapM_gf_MMGardensDragonInitTowers(UnitFromId(38), UnitFromId(397));' in script
         and b'DragonTowerStartTimer' not in script and b'DragonTowerWarningTimer' not in script,
         "Unexpected local map timer path")
    trigger_refs = sum(x.get("Library") == "MapM" for x in ElementTree.fromstring(triggers).iter())
    need(trigger_refs == 177, "Editor reference count differs")
    return {"sha256": expected, "map_script_sha256": digest(script), "triggers_sha256": digest(triggers),
            "editor_MapM_references": trigger_refs, "document_info_sha256": digest(info),
            "dependencies": [x.text for x in ElementTree.fromstring(info).findall("Dependencies/Value")]}


def current_timing(folder):
    script = (folder / "mapmechanicslib.galaxy").read_bytes()
    header = (folder / "mapmechanicslib_h.galaxy").read_bytes()
    game = (folder / "gamelib.galaxy").read_bytes()
    need((digest(script), digest(header)) == (LIBRARY, HEADER), "Incorrect 98348 Galaxy files")
    for line in ("DragonWarningTime_C = 30.0;", "DragonDragonTowerStartTime_C = 60.0;"):
        need(line.encode() in header, "Timer constant differs")
    for line in (
        "TriggerAddEventTimer(libMapM_gt_MMGardensDragonGateOpen, libGame_gv_openTheGatesTimer);",
        "TimerStart(libMapM_gv_mMGardensDragonDragonTowerStartTimer, libMapM_gv_mMGardensDragonDragonTowerStartTime_C, false, c_timeGame);",
        "TriggerAddEventTimer(libMapM_gt_MMGardensDragonWarningTimerStart, libMapM_gv_mMGardensDragonDragonTowerStartTimer);",
        "TimerStart(libMapM_gv_mMGardensDragonDragonTowerWarningTimer, libMapM_gv_mMGardensDragonWarningTime_C, false, c_timeGame);",
        "TriggerAddEventTimer(libMapM_gt_MMGardensDragonWarningTimerExpires, libMapM_gv_mMGardensDragonDragonTowerWarningTimer);",
        "libMapM_gv_mMGardensDragonCurrentState = libMapM_ge_MMGardensDragonState_ObelisksAvailable;",
    ):
        need(line.encode() in script, "Missing current timer edge")
    need(digest(game) == GAME, "Incorrect target GameLib")
    channel = script.split(b"bool libMapM_gt_MMGardensDragonTransformChannelFinish_Func (", 1)[1].split(b"\n}", 1)[0]
    disable = game.split(b"bool auto_libGame_gf_CapturePointDisable_TriggerFunc (", 1)[1].split(b"\n}", 1)[0]
    def ordered(source, fragments):
        offsets = [source.index(part) for part in fragments]
        need(offsets == sorted(offsets), "Unexpected order of actions")
    ordered(channel, [b'StatEventCreate("DragonKnightActivated")', b"StatEventSend(StatEventLastCreated())",
                      b"UnitSetOwner(libMapM_gv_mMGardensDragonDragonTowers[lv_itObelisk].lv_shrineUnit",
                      b"libGame_gf_CapturePointDisable(libMapM_gv_mMGardensDragonDragonTowers[lv_itObelisk].lv_captureBeaconIndex)"])
    ordered(disable, [b".lv_enabled = false", b'"Signal Hide"', b"Wait(3.0, c_timeGame)",
                      b"UnitSetOwner(libGame_gv_capturePoints[lp_capturePointIndex].lv_captureBeaconUnit"])
    return {"script_sha256": LIBRARY, "header_sha256": HEADER, "game_sha256": GAME,
            "neutral_beacon_post_dragon_loops": 48, "warning_after_gates_loops": 960,
            "available_after_gates_loops": 1440}


def replay(path, expected, build):
    need(digest(path.read_bytes()) == expected, "Replay SHA mismatch")
    protocol = load_protocol({41810: 41810, 98348: 96477}[build])
    with closing(MPQArchive(path)) as archive:
        header = protocol.decode_replay_header(archive.header["user_data_header"]["content"])
        need((header["m_version"]["m_build"], header["m_version"]["m_baseBuild"],
              header["m_dataBuildNum"]) == (build,) * 3, "Replay build mismatch")
        deps = protocol.decode_replay_details(archive.read_file("replay.details"))["m_cacheHandles"]
        lobby = protocol.decode_replay_initdata(archive.read_file("replay.initData"))["m_syncLobbyState"]
        need(deps == lobby["m_gameDescription"]["m_cacheHandles"] and deps[-1][:4] == b"s2ma",
             "Replay map handles disagree")
        if deps[-1][8:].hex() != {41810: OLD_MAP, 98348: NEW_MAP}[build]:
            need(build == 98348, "Historical map differs")
            return None
        tracker = list(protocol.decode_replay_tracker_events(archive.read_file("replay.tracker.events")))
        game = protocol.decode_replay_game_events(archive.read_file("replay.game.events"))
        gate, = [e["_gameloop"] for e in tracker if e.get("m_eventName") == b"GatesOpen"]
        groups = defaultdict(list)
        for e in game:
            if e["_gameloop"] > gate + 1800:
                break
            if e["_event"].endswith(".STriggerTransmissionCompleteEvent"):
                groups[e["m_transmissionId"]].append((e["_gameloop"] - gate, e["_userid"]["m_userId"]))
    opening = [(e["m_unitTagIndex"], e["m_unitTagRecycle"], e["m_unitTypeName"], e["m_x"], e["m_y"])
               for e in tracker if e["_event"].endswith(".SUnitBornEvent") and e["_gameloop"] == 0
               and e["m_unitTypeName"] in (SHRINES | {BEACON})]
    need(len(opening) == 4 and {row[3:] for row in opening if row[2] == BEACON}
         == {row[3:] for row in opening if row[2] in SHRINES}, "Shrine and beacon identity mismatch")
    units = {(idx, gen): name for idx, gen, name, _, _ in opening}
    changes = [(e["_gameloop"], units[(e["m_unitTagIndex"], e["m_unitTagRecycle"])],
                e["m_controlPlayerId"], e["m_upkeepPlayerId"], e["m_unitTagIndex"])
               for e in tracker if e["_event"].endswith(".SUnitOwnerChangeEvent")
               and (e["m_unitTagIndex"], e["m_unitTagRecycle"]) in units]
    captures = [r for r in changes if r[1] == BEACON and r[2] in (11, 12) and r[2] == r[3]]
    knights = [e["_gameloop"] for e in tracker if e.get("m_eventName") == b"DragonKnightActivated"]
    resets = []
    for loop in knights:
        shrine_tags = [i for at, name, owner, upkeep, i in changes
                       if at == loop and name in SHRINES and owner == upkeep == 0]
        first_reset = {}
        for at, name, owner, upkeep, tag in changes:
            if name == BEACON and at >= loop and owner == upkeep == 0:
                first_reset.setdefault(tag, at - loop)
        resets.append([loop, len(set(shrine_tags)), sorted(first_reset.values())])
    first_by_tag = {}
    for loop, _, owner, _, tag in captures:
        first_by_tag.setdefault(tag, [loop, owner])
    return {"sha256": expected, "gates_open": gate, "first_beacon_capture_after_gates": captures[0][0] - gate,
            "first_capture_by_beacon": first_by_tag, "knight_loop_shrine_resets_and_beacon_delays": resets,
            "completion_groups_after_gates": [
                [key, min(v[0] for v in values), max(v[0] for v in values), len({v[1] for v in values})]
                for key, values in sorted(groups.items())
            ]}


def read_cohort(index, build):
    return [r for sha, path in sorted(json.loads(index.read_bytes()).items())
            if (r := replay(Path(path), sha, build)) is not None]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("source_map", "gate_order", "scripts", "old_paths", "control_paths"):
        parser.add_argument(key, type=Path)
    args = parser.parse_args()
    old = read_cohort(args.old_paths, 41810)
    modern = read_cohort(args.control_paths, 98348)
    bound = min(r["first_beacon_capture_after_gates"] for r in old)
    need(len(old) == 5 and len(modern) == 15 and bound == 1284, "Unexpected cohorts or bound")
    need(all(r["first_beacon_capture_after_gates"] < 1440 for r in old), "Old timing assertion failed")
    need(all(r["first_beacon_capture_after_gates"] >= 1440 for r in modern), "Modern control diverged")
    source, = [r for r in old if r["sha256"] == TEN]
    need(source["knight_loop_shrine_resets_and_beacon_delays"]
         == [[v, 2, [16, 16]] for v in [2514, 7734, 11318, 17151]], "Unexpected TEN reset cycle")
    need(source["first_capture_by_beacon"] == {171: [2011, 12], 170: [2277, 12]},
         "Unexpected TEN initial ownership")
    result = {"old_map": read_map(args.source_map, OLD_MAP), "overlay": read_map(args.gate_order, GATE_ORDER),
              "target_timing": current_timing(args.scripts), "old_replays": old, "target_controls": modern,
              "old_first_availability_upper_bound_after_gates_loops": bound,
              "old_exact_warning": None, "old_exact_availability": None}
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
