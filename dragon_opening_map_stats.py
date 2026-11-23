"""Rebuild the 18 loop-zero Dragon Shire map statistics from a pinned map package."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import re
import struct
from xml.etree import ElementTree

from camp_owner_wire import PROFILE_MAPS, read_tracker
from dragon_catapult_waves import town_regions
from dragon_startup_births import indexed, xy
from encoders import encode_tracker_events
from dragonshire_packages import MERC_CAPTURE, SIGNED_ANNOUNCER
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from protocol_loader import load_protocol
from smartcam_tags import DST_SCHEMA

NAMES = {b"GameStart", b"TownStructureInit", b"JungleCampInit"}
EVENT = "NNet.Replay.Tracker.SStatGameEvent"


def stat(name, integers, fixed):
    values = []
    for key, value in fixed:
        scaled = value * 4096
        if scaled != int(scaled):
            raise ValueError("Position not exactly representable in Galaxy fixed point")
        values.append({"m_key": key, "m_value": int(scaled)})
    return dict(_eventid=10, _event=EVENT, _gameloop=0, m_eventName=name,
                m_stringData=None, m_intData=[{"m_key": k, "m_value": v} for k, v in integers] or None,
                m_fixedData=values)


def position(x, y):
    return [(b"PositionX", x), (b"PositionY", y)]


def generate(package, build):
    digest = sha256(package.read_bytes()).hexdigest()
    if digest not in PROFILE_MAPS[build] and not (build == 41810 and digest in (SIGNED_ANNOUNCER, MERC_CAPTURE)):
        raise ValueError("Unexpected map package")
    with closing(MPQArchive(package)) as arc:
        objects = ElementTree.fromstring(read_member(arc, "Objects"))
        info = read_member(arc, "MapInfo")
        terrain = ElementTree.fromstring(read_member(arc, "t3Terrain.xml"))
        script = read_member(arc, "MapScript.galaxy").decode("utf-8-sig")
    width, height = struct.unpack_from("<II", info, 16)
    vertices = terrain.find("heightMap")
    if (info[:4] != b"IpaM" or vertices is None
            or tuple(map(int, vertices.attrib["dim"].split())) != (width + 1, height + 1)):
        raise ValueError("MapInfo dimensions disagree with terrain")
    events = [stat(b"GameStart", [], [(b"MapSizeX", width), (b"MapSizeY", height)])]
    halls = {int(n.get("Id")): xy(n) for n in objects.findall("ObjectUnit")
             if n.get("UnitType") in {"TownTownHallL2", "TownTownHallL3"}}
    used = set()
    for town, (lane, owner, bounds) in enumerate(town_regions(package).values(), 1):
        x0, y0, x1, y1 = bounds
        (hall,) = [i for i, (x, y) in halls.items() if x0 <= x <= x1 and y0 <= y <= y1]
        used.add(hall)
        events.append(stat(b"TownStructureInit", [(b"TownID", town), (b"Team", {11: 1, 12: 2}[owner]),
                                                  (b"Lane", lane)], position(*halls[hall])))
    if used != halls.keys() or len(used) != 12:
        raise ValueError("Expected twelve distinct town halls")
    points = indexed(objects, "ObjectPoint", "Id")
    camps = re.findall(r"lv_mapDataCampCaptainSpawnPoint = PointFromId\((\d+)\);", script)
    if len(camps) != 5 or len(set(camps)) != 5:
        raise ValueError("Expected five camp captain positions")
    for camp, point in enumerate(camps, 1):
        events.append(stat(b"JungleCampInit", [(b"CampID", camp)], position(*xy(points[int(point)]))))
    return events


def audit(replay, expected, build, package):
    if sha256(replay.read_bytes()).hexdigest() != expected:
        raise ValueError("Unexpected replay")
    predicted = generate(package, build)
    src, raw, _ = read_tracker(replay, build)
    target = load_protocol(96477)
    if target.recovery_schema_sha256 != DST_SCHEMA or target.tracker_event_types[10][1] != EVENT:
        raise ValueError("Unexpected target schema")
    matched = 0
    offset = 0
    for observed in src.decode_replay_tracker_events(raw):
        if observed["_gameloop"] > 0:
            break
        length, rem = divmod(observed["_bits"], 8)
        if rem:
            raise ValueError("Unaligned event")
        if observed.get("m_eventName") in NAMES:
            if matched >= len(predicted):
                raise ValueError("Unexpected extra statistic")
            event = predicted[matched]
            if event != {k: v for k, v in observed.items() if k != "_bits"}:
                raise ValueError(f"Map statistic differs at ordinal {matched}")
            if encode_tracker_events([event], target) != raw[offset:offset+length]:
                raise ValueError("Physical frame differs")
            matched += 1
        offset += length
    if matched != len(predicted):
        raise ValueError("Incomplete map statistics")
    payload = encode_tracker_events(predicted, target)
    return payload, dict(build=build, replay_sha256=expected, frames=matched, bytes=len(payload),
                         sha256=sha256(payload).hexdigest())


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("map", type=Path)
    cli.add_argument("replay", type=Path)
    cli.add_argument("digest")
    cli.add_argument("build", choices=(41810, 98348), type=int)
    cli.add_argument("--output", type=Path)
    args = cli.parse_args()
    data, result = audit(args.replay, args.digest, args.build, args.map)
    if args.output:
        with args.output.open("xb") as out:
            out.write(data)
    print(json.dumps(result, indent=2))
