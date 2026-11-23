"""Measure GatesOpen to the first Dragon Shire mercenary defender wave in physical replays."""

import argparse
from collections import Counter
from contextlib import closing
from decimal import Decimal
from hashlib import sha256
import json
import re
from pathlib import Path
from xml.etree import ElementTree

from mpq_reader import MPQArchive
from protocol_loader import load_protocol


def need(ok, description):
    if not ok:
        raise ValueError(description)


def map_wave(map_path):
    with closing(MPQArchive(map_path)) as a:
        script = a.read_file("MapScript.galaxy").decode("utf-8-sig")
        objects = ElementTree.fromstring(a.read_file("Objects"))
    points = {int(n.get("Id")): n for n in objects.findall("ObjectPoint")}
    kinds = {
        "Knights": ("MercDefenderMeleeKnight",) * 3 + ("MercDefenderRangedMage",),
        "SiegeGiants": ("MercDefenderSiegeGiant",) * 2,
    }
    need(
        not re.search(
            r"initialSpawnDelay|defenderDefendersStaggeredBirthPeriod|gf_Initialize(?:Hellbat|Sapper)MercType",
            script,
            re.I,
        ),
        "Unsupported map timer override",
    )
    wave = Counter()
    camps = []
    for block in script.split("lv_junglecamp += 1;")[1:]:
        (kind,) = re.findall(
            r"lv_mapDataCampDefenderType = libMapM_ge_JungleCampDefenderTypes_(\w+);",
            block,
        )
        slots = re.findall(
            r"lv_mapDataDefenderSpawnPoints\[(\d+)\] = PointFromId\((\d+)\);", block
        )
        need(
            kind in kinds
            and [int(i) for i, _ in slots] == list(range(1, len(kinds[kind]) + 1)),
            "Unexpected defender point slots",
        )
        for name, (_, pid) in zip(kinds[kind], slots):
            x, y, _ = map(Decimal, points[int(pid)].get("Position").split(","))
            need(0 <= x < 256 and 0 <= y < 256, "Unsupported defender position")
            wave[name, int(x), int(y)] += 1
        camps.append(kind)
    need(
        Counter(camps) == {"SiegeGiants": 2, "Knights": 3} and wave.total() == 16,
        "Unexpected camp mix",
    )
    return camps, wave


def first_wave(events, expected):
    gates = []
    first = None
    wave = Counter()
    for e in events:
        if e.get("m_eventName") == b"GatesOpen":
            gates.append(e["_gameloop"])
        if (
            e["_event"] != "NNet.Replay.Tracker.SUnitBornEvent"
            or not e["m_unitTypeName"].startswith(b"MercDefender")
            or (e["m_controlPlayerId"], e["m_upkeepPlayerId"]) != (15, 15)
        ):
            continue
        if first is None:
            first = e["_gameloop"]
        if first == e["_gameloop"]:
            wave[e["m_unitTypeName"].decode(), e["m_x"], e["m_y"]] += 1
    need(
        len(gates) == 1 and first is not None and first > gates[0],
        "Missing, ambiguous, or unordered gates and defender events",
    )
    need(
        wave == expected,
        "First hostile defender batch does not match every authored type and position",
    )
    return gates[0], first


def verify(map_path, build, replays):
    camps, expected = map_wave(map_path)
    s = sha256(map_path.read_bytes()).hexdigest()
    p = load_protocol({41810: 41810, 98348: 96477}[build])
    cases = []
    for path in replays:
        with closing(MPQArchive(path)) as a:
            h = p.decode_replay_header(a.header["user_data_header"]["content"])
            d = p.decode_replay_details(a.read_file("replay.details"))
            g = p.decode_replay_initdata(a.read_file("replay.initData"))[
                "m_syncLobbyState"
            ]["m_gameDescription"]
            need(
                (
                    h["m_version"]["m_build"],
                    h["m_version"]["m_baseBuild"],
                    h["m_dataBuildNum"],
                )
                == (build,) * 3,
                "Physical build differs",
            )
            deps = d["m_cacheHandles"]
            need(
                deps == g["m_cacheHandles"]
                and deps[-1][:4] == b"s2ma"
                and deps[-1][8:].hex() == s,
                "Map SHA-256 differs",
            )
            wire = a.read_file("replay.tracker.events")
        gates, first = first_wave(p.decode_replay_tracker_events(wire), expected)
        cases.append(
            dict(
                replay_sha256=sha256(path.read_bytes()).hexdigest(),
                tracker_sha256=sha256(wire).hexdigest(),
                gates_open_loop=gates,
                first_defender_loop=first,
                elapsed_loops=first - gates,
                elapsed_game_seconds_at_16_loops_per_second=(first - gates) / 16,
            )
        )
    need(
        cases and len({c["replay_sha256"] for c in cases}) == len(cases),
        "Expected distinct replay files",
    )
    return dict(
        physical_build=build,
        map_sha256=s,
        camps=camps,
        matched_first_wave_units=expected.total(),
        cases=cases,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map", type=Path)
    parser.add_argument("replays", type=Path, nargs="+")
    parser.add_argument("--build", type=int, choices=(41810, 98348), required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.map, args.build, args.replays), indent=2))
