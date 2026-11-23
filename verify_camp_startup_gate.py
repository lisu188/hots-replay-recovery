"""Verify Dragon Shire's 98348 camp-state guard and the recorded 41810 camp behavior."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import re
from xml.etree import ElementTree

from mpq_reader import MPQArchive
from protocol_loader import load_protocol

SOURCE = "e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824"
SOURCE_MAP = "e0a58745837b3b5351015c933560dbffb178d747009d2d57b4153ef425cf7250"
ROOT = "c3b3c8bc82e3a5a62e550fdde9a40c28"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def verify(folder, map_path, replay):
    require(
        sha256(map_path.read_bytes()).hexdigest() == SOURCE_MAP
        and sha256(replay.read_bytes()).hexdigest() == SOURCE,
        "Unexpected source map or replay",
    )
    meta = json.loads((folder / "member.json").read_bytes())
    require(
        meta["actual_root_content_md5"] == ROOT and meta["version"] == "2.57.0.98348",
        "Incorrect installed game data",
    )
    sources = {}
    manifest = {}
    for member in meta["members"]:
        name = member["saved_name"]
        raw = (folder / name).read_bytes()
        require(sha256(raw).hexdigest() == member["sha256"], "Script hash mismatch")
        sources[name] = raw.decode("utf-8-sig").splitlines()
        manifest[name] = member["sha256"]
    with closing(MPQArchive(map_path)) as a:
        objs = ElementTree.fromstring(a.read_file("Objects"))
        map_script = a.read_file("MapScript.galaxy").decode("utf-8-sig").splitlines()
    queue = ["map"]
    all_names = {"map": map_script, **sources}
    visited = set()
    while queue:
        name = queue.pop()
        if name in visited:
            continue
        visited.add(name)
        for line in all_names[name]:
            m = re.match(r'^\s*include\s+"([^"]+)"', line)
            if m:
                path = m[1].lower()
                require(path.startswith("triggerlibs/"), "Unknown include")
                queue.append(path.split("/")[-1] + ".galaxy")
    require(
        visited == all_names.keys(),
        "Inspected scripts differ from the map include closure",
    )
    scan = {}
    for token in (
        "lv_stateIsEnabled",
        "lv_campOwnershipFlagUnit",
        "lv_campOwnershipFlagPosition",
        "libMapM_gf_JungleInitializeCreepCamp(",
        "libMapM_gf_JungleRespawnCreepsForCamp(",
        "libMapM_gf_JungleTurnOnCampCaptureBeacon(",
        '"CampOwnershipFlag"',
        '"LootBannerSconce"',
        '"JungleCampInit"',
    ):
        scan[token] = {
            name: [i for i, line in enumerate(lines, 1) if token in line]
            for name, lines in all_names.items()
            if any(token in line for line in lines)
        }
    require(
        scan["lv_stateIsEnabled"]
        == {
            "mapmechanicslib.galaxy": [95, 697, 1037, 4913, 4992],
            "mapmechanicslib_h.galaxy": [199],
        },
        "Unexpected enabled-flag references",
    )
    require(
        not scan['"CampOwnershipFlag"'],
        "Found a current script path for the historical unit type",
    )
    checks = {
        "mapmechanicslib.galaxy": {
            694: 'UnitGroup("LootBannerSconce"',
            697: "lv_stateIsEnabled = false",
            698: "return",
            1037: "lv_stateIsEnabled == false",
            1231: "CreateUnitsAtPoint2",
            1666: "CapturePointEnable",
            1721: 'StatEventCreate("JungleCampCapture")',
            1759: "UnitXPGetCurrentXP",
            1792: "UnitXPSetCurrentXP",
            1818: "JungleSpawnMercMinions",
            4935: "TriggerAddEventTimer",
            4936: '"TownMercCampCaptureBeacon"',
            4944: "CapturePointCreate(",
            4946: "CapturePointDisable(",
            4947: "JungleInitializeCreepCamp(",
            4953: "VisRevealArea(",
            4992: "lv_stateIsEnabled == true",
            4993: "TimerStart",
            4994: "TimerStart",
            5047: "EventTimer()",
            5056: "lv_campIconUnit == null",
            5057: "JungleRespawnCreepsForCamp",
            5230: "JungleTurnOnCampCaptureBeacon",
            5397: "SendEventMercCampCaptured",
        },
        "gamelib.galaxy": {
            9425: "UnitXPAddXP",
            16334: "TriggerEnable(libMapM_gt_JungleCreepCampRespawnTimerExpires, true)",
            16335: "TriggerExecute(libMapM_gt_StartJungleCampTimers",
        },
        "supportlib.galaxy": {
            676: "jungleNumberOfCreepCamps",
            679: 'StatEventCreate("JungleCampInit")',
            683: "StatEventSend",
        },
    }
    for name, entries in checks.items():
        for line, fragment in entries.items():
            require(
                fragment in sources[name][line - 1],
                f"Changed binding {name} line {line}",
            )
    units = sorted(objs.findall("ObjectUnit"), key=lambda n: int(n.attrib["Id"]))
    flags = {
        i: int(n.attrib["Id"])
        for i, n in enumerate(units)
        if n.get("UnitType") == "CampOwnershipFlag"
    }
    p = load_protocol(41810)
    with closing(MPQArchive(replay)) as a:
        wire = a.read_file("replay.tracker.events")
    events = list(p.decode_replay_tracker_events(wire))
    flag_changes = {}
    for index, object_id in flags.items():
        changes = [
            (e["_gameloop"], e["m_controlPlayerId"], e["m_upkeepPlayerId"])
            for e in events
            if e["_event"].endswith(".SUnitOwnerChangeEvent")
            and (e["m_unitTagIndex"], e["m_unitTagRecycle"]) == (index, 1)
        ]
        require(changes[0] == (2530, 15, 15), "Unexpected first flag transition")
        flag_changes[object_id] = changes
    icons = [
        (e["_gameloop"], e["m_x"], e["m_y"])
        for e in events
        if e["_event"].endswith(".SUnitBornEvent")
        and e["m_unitTypeName"] == b"JungleCampIconUnitTeamColor"
    ]
    require(
        Counter(loop for loop, x, y in icons)[2530] == 5
        and min(o[0] for o in icons) == 2530,
        "Unexpected first minimap icons",
    )
    defenders = [
        e
        for e in events
        if e["_event"].endswith(".SUnitBornEvent")
        and e["m_unitTypeName"].startswith(b"MercDefender")
        and e["m_controlPlayerId"] == 15
    ]
    first = min(e["_gameloop"] for e in defenders)
    first_defenders = Counter(
        e["m_unitTypeName"].decode() for e in defenders if e["_gameloop"] == first
    )
    require(
        first == 2532 and first_defenders.total() == 16, "Unexpected first defenders"
    )
    captures = []
    for e in events:
        if e.get("m_eventName") != b"JungleCampCapture":
            continue
        camp = next(k["m_value"] for k in e["m_intData"] if k["m_key"] == b"CampID")
        team = next(k["m_value"] for k in e["m_fixedData"] if k["m_key"] == b"TeamID")
        require(team in (4096, 8192), "Unexpected capture team")
        owner = 10 + team // 4096
        ids = [
            i
            for i, changes in flag_changes.items()
            if (e["_gameloop"], owner, owner) in changes
        ]
        require(len(ids) == 1, "Capture did not identify one original flag")
        captures.append(
            dict(loop=e["_gameloop"], camp=camp, object_id=ids[0], owner=owner)
        )
    require(len(captures) == 13 and len(flags) == 5, "Unexpected flag or capture count")
    return dict(
        format="dragon-shire-mercenary-camp-activation-v1",
        installed_root=ROOT,
        include_closure_script_hashes=manifest,
        scanned_literal_locations=scan,
        checked_bound_lines={n: sorted(d) for n, d in checks.items()},
        source_replay_sha256=SOURCE,
        source_map_sha256=SOURCE_MAP,
        source_tracker_sha256=sha256(wire).hexdigest(),
        source_flags=[
            dict(
                authored_id=value,
                tag_index=key,
                recorded_owner_changes=len(flag_changes[value]),
            )
            for key, value in flags.items()
        ],
        first_hostile_owner_all_five_flags=2530,
        source_first_icon_loop=2530,
        source_first_icon_xy=[(x, y) for loop, x, y in icons if loop == 2530],
        source_first_defender_loop=first,
        source_first_defenders=dict(first_defenders),
        source_captures=captures,
        source_loopzero_camp_init_events=sum(
            e.get("m_eventName") == b"JungleCampInit" and e["_gameloop"] == 0
            for e in events
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("installed_scripts", "original_map", "original_replay"):
        parser.add_argument(key, type=Path)
    a = parser.parse_args()
    print(
        json.dumps(
            verify(a.installed_scripts, a.original_map, a.original_replay), indent=2
        )
    )
