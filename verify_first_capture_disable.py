"""Verify the first eligible capture-point disable on the HistoricalCamps layout."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import re
from xml.etree import ElementTree

from build_dragon_beacon_reset import EVIDENCE, GATE, PARENT, SCRIPT, check_observations, need
from build_gate_order_map import definition
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from protocol_loader import load_protocol


MANIFEST = "87b44ff3f91d9058f5001f926129a04d225f8a11fa05b99e1571362539ec3b7b"
CAMP = b"TownMercCampCaptureBeacon"
SHRINE = b"DragonballCaptureBeacon"
LOCATIONS = [(101, 76), (100, 110), (147, 76), (148, 110), (124, 32), (124, 155), (124, 47)]


def digest(data):
    return sha256(data).hexdigest()


def lines_ordered(text, requirements):
    offsets = [text.index(token) for token in requirements]
    need(offsets == sorted(set(offsets)), "Startup call order differs")


def check_prerequisites(scripts, camp):
    functions = {}
    for source in scripts.values():
        functions.update(re.findall(r"^\w+ (\w+) \([^\n]*?\) \{(.*?)^\}", source, re.M | re.S))
    functions["camp_prefix"] = camp.split("libGame_gf_CapturePointDisable(", 1)[0]
    pending = ["libGame_gt_InitializeCodeLaneSystem_Func", "libGame_gt_InitializeWatchTowers_Func",
               "libGame_gt_InitializeTownSystem_Func", "camp_prefix"]
    listeners = set(re.findall(r"libGame_gf_TownDataInitialized\((\w+)\);", "\n".join(scripts.values())))
    need(len(listeners) == 3, "Town initialization listener set differs")
    pending.extend(name + "_Func" for name in listeners)
    seen = set()
    sends = []
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        body = functions[name]
        calls = set(re.findall(r"\b(\w+)\(",body))
        need(not calls.intersection({"Wait","TriggerWaitForTrigger","TriggerQueueEnter","TriggerExecute"}),
             "A prerequisite can explicitly suspend or dispatch another trigger")
        sends.extend(re.findall(r"TriggerSendEvent\(([^)]+)\)",body))
        pending.extend(calls.intersection(functions).difference(seen))
    need(sends == ["libGame_gv_eventID_TownDataInitialized_C"], "Unexpected prerequisite event")


def first_call(scripts, parent):
    need(digest(parent.read_bytes()) == PARENT, "Incorrect parent")
    with closing(MPQArchive(parent)) as arc:
        script = read_member(arc, "MapScript.galaxy")
        objects = ElementTree.fromstring(read_member(arc, "Objects")).findall("ObjectUnit")
    need(digest(script) == SCRIPT and all(x.get("UnitType") != "XelNagaWatchTower" for x in objects),
         "Incorrect startup map")
    script = script.decode("ascii").replace("\r\n", "\n")
    raw = (scripts / "member.json").read_bytes()
    need(digest(raw) == MANIFEST, "Unexpected target library manifest")
    all_scripts = {}
    for row in json.loads(raw)["members"]:
        path = scripts / row["saved_name"]
        raw = path.read_bytes()
        need(digest(raw) == row["sha256"], "Target script differs")
        all_scripts[path.name] = raw.decode("utf-8-sig").replace("\r\n", "\n")
    sites = {}
    for name, source in {"map": script, **all_scripts}.items():
        positions = [source.count("\n", 0, m.start()) + 1 for m in re.finditer(r"^[ \t]*libGame_gf_CapturePointDisable\(", source, re.M)]
        need(source.count("libGame_gf_CapturePointDisable(") == len(positions), "Additional call form")
        if positions:
            sites[name] = positions
    need(sites == {"mapmechanicslib.galaxy": [1681, 3547, 3580, 4946, 7549]}, "Unexpected ordinary disable callers")
    require_map = definition(script, "bool", "gt_InitializeMap_Func")
    lines_ordered(require_map, ["TriggerExecute(gt_HookupJungleCreepData, true, true);",
                                "libMapM_gf_MapMechanicAdd(", "libCore_gv_sYSJungleCreepCamps = true;",
                                "TriggerExecute(libCore_gt_InitializeStormMod, true, true);"])
    hookup = definition(script, "bool", "gt_HookupJungleCreepData_Func")
    need(re.findall(r"lv_mapDataCampCaptainSpawnPoint = PointFromId\((\d+)\);", hookup)
         == ["244", "252", "245", "253", "178"], "Camp setup order differs")
    need("libMapM_gt_InitializeJungleCamps_Init();" in definition(script, "void", GATE),
         "The active parent lacks the ordinary camp registration slot")
    heroes, game, mech = [all_scripts[n+".galaxy"] for n in ("heroeslib","gamelib","mapmechanicslib")]
    lines_ordered(definition(heroes,"bool","libCore_gt_InitializeStormMod_Func"),
                  ["TriggerExecute(libGame_gt_InitializeGameSystems,", "TriggerExecute(libMapM_gt_InitializeMapMechanics,"])
    systems = definition(game,"bool","libGame_gt_InitializeGameSystems_Func")
    lines_ordered(systems, ["libGame_gt_InitializeCodeLaneSystem,", "libGame_gt_InitializeWatchTowers,",
                            "libGame_gt_InitializeTownSystem,", "libMapM_gt_InitializeJungleCamps,"])
    camp = definition(mech,"bool","libMapM_gt_InitializeJungleCamps_Func")
    lines_ordered(camp, ["lv_camp = 1;", ".lv_stateIsEnabled == false", '"TownMercCampCaptureBeacon"',
                         "libGame_gf_CapturePointCreate(", "libGame_gf_LastCreatedCapturePoint();",
                         "libGame_gf_CapturePointDisable(", "libMapM_gf_JungleInitializeCreepCamp("])
    need("Wait(" not in camp and "lv_stateIsEnabled = true;" in mech,
         "Startup camp can suspend or skips the default")
    check_prerequisites(all_scripts,camp)
    # The other camp path requires a matching point and a team capture. Startup creates neutral beacons.
    owner = definition(mech,"bool","libMapM_gt_JungleCampOwnershipChange_Func")
    need("libMapM_gf_JungleTurnOffCampCaptureBeacon(" in owner and ".lv_captureCapturePointIndex == lv_index" in owner
         and "lv_owner == libCore_gv_cOMPUTER_TeamOrder" in owner and "lv_owner == libCore_gv_cOMPUTER_TeamChaos" in owner,
         "Ordinary camp shutdown no longer requires the team's capture")
    tower = definition(mech,"bool","auto_libMapM_gf_MMGardensDragonInitTowers_TriggerFunc")
    need(tower.count('UnitCreate(1, "DragonballCaptureBeacon"') == 2
         and tower.count("libGame_gf_CapturePointDisable(") == 2, "Shrine initialization differs")
    need("libGame_gf_CapturePointDisable(" not in definition(game,"void","libGame_gf_CapturePointCreate")
         and "CapturePointDisable(" not in definition(game,"void","libGame_gf_CapturePointEnable"),
         "Creator already invokes disable")
    return sites


def observe(path, sha, build, expected_map):
    need(digest(path.read_bytes()) == sha, "Wrong replay")
    p = load_protocol(41810 if build == 41810 else 96477)
    with closing(MPQArchive(path)) as archive:
        header = p.decode_replay_header(archive.header["user_data_header"]["content"])
        need([header["m_version"]["m_build"], header["m_version"]["m_baseBuild"], header["m_dataBuildNum"]] == [build]*3,
             "Incorrect native build")
        details = p.decode_replay_details(archive.read_file("replay.details"))
        need(details["m_cacheHandles"][-1][8:].hex() == expected_map, "Wrong map handle")
        tracker = list(p.decode_replay_tracker_events(archive.read_file("replay.tracker.events")))
        result, roles = [], {}
        for event in tracker:
            if event["_gameloop"] or not event["_event"].endswith(".SUnitBornEvent"):
                continue
            name = event.get("m_unitTypeName")
            if name in (CAMP, SHRINE):
                need(event["m_controlPlayerId"] == event["m_upkeepPlayerId"] == 0, "Non-neutral opening beacon")
                result.append((event["m_unitTypeName"], event["m_x"], event["m_y"], event["m_unitTagIndex"]))
            if name in (b"DragonShireShrineSun", b"DragonShireShrineMoon", SHRINE):
                roles[(event["m_unitTagIndex"], event["m_unitTagRecycle"])] = (name == SHRINE,event["m_y"])
    need([r[0] for r in result] == [CAMP]*5 + [SHRINE]*2 and [r[1:3] for r in result] == LOCATIONS,
         "Shrine or camp birth order differs")
    need(len(roles) == 4, "Expected two shrine units and two linked beacons")
    neutral = {}
    for event in tracker:
        ident = (event.get("m_unitTagIndex"),event.get("m_unitTagRecycle"))
        if (ident in roles and event["_event"].endswith(".SUnitOwnerChangeEvent")
                and event["m_controlPlayerId"] == event["m_upkeepPlayerId"] == 0):
            neutral.setdefault(event["_gameloop"], []).append(roles[ident])
    activations = [r["_gameloop"] for r in tracker if r.get("m_eventName") == b"DragonKnightActivated"]
    delay = {41810:16,98348:48}[build]
    for loop in activations:
        need(neutral[loop] == [(False,155),(False,47)] and neutral[loop+delay] == [(True,47),(True,155)],
             "Recorded shrine or delayed beacon write order differs")
    return [sha, build, result[0][3], len(activations)]


def verify(parent, scripts, evidence, old_paths, control_paths):
    check_observations(evidence.read_bytes())
    doc = json.loads(evidence.read_bytes())
    rows = []
    for key, pathmap, build, map_sha in (
        ("old_replays", old_paths, 41810, doc["old_map"]["sha256"]),
        ("target_controls", control_paths, 98348, "f557190f8aaab160789272ce086b8b69d6a8037b152de150332603dae3dc098f"),
    ):
        paths = json.loads(pathmap.read_bytes())
        for record in doc[key]:
            sha = record["sha256"]
            rows.append(observe(Path(paths[sha]), sha, build, map_sha))
    sites = first_call(scripts, parent)
    need([sum(r[3] for r in rows if r[1]==build) for build in (41810,98348)]==[15,52],
         "Unexpected activation count")
    return {"parent_sha256": PARENT, "shrine_observations_canonical_sha256": EVIDENCE,
            "eligible_disable_call_lines": sites, "first_ordinary_call_line": 4946,
            "first_camp_setup_index": 1, "first_captain_point_id": 244,
            "first_beacon_position": list(LOCATIONS[0]), "shrine_order": ["Sun","Moon"],
            "later_beacon_order": ["Moon","Sun"], "replay_sha256_build_first_camp_tag_activations": rows}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for field in ("parent","scripts","evidence","old_paths","control_paths"):
        p.add_argument(field,type=Path)
    print(json.dumps(verify(**vars(p.parse_args())),indent=2))
