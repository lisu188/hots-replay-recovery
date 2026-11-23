"""Match successive opening camp flag, icon and defender events to independent map positions."""

import argparse
from collections import Counter
from contextlib import closing
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import re
from xml.etree import ElementTree

import first_sync_game
from first_sync_game import game
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from predict_camp_captures import SOURCE, CONTROLS
from project_rank_targets import MAP


def layout(package):
    with closing(MPQArchive(package)) as a:
        script = read_member(a, "MapScript.galaxy").decode("utf-8-sig")
        objects = ElementTree.fromstring(read_member(a, "Objects"))
    points = {
        int(e.get("Id")): tuple(Decimal(v) for v in e.get("Position").split(",")[:2])
        for e in objects.findall("ObjectPoint")
    }
    flags = [
        (int(e.get("Id")), tuple(Decimal(v) for v in e.get("Position").split(",")[:2]))
        for e in objects.findall("ObjectUnit")
        if e.get("UnitType") == "CampOwnershipFlag"
    ]
    result = []
    for block in script.split("lv_junglecamp += 1;")[1:]:
        (pid,) = re.findall(
            r"lv_mapDataCampCaptainSpawnPoint = PointFromId\((\d+)\);", block
        )
        center = points[int(pid)]
        (kind,) = re.findall(
            r"lv_mapDataCampDefenderType = libMapM_ge_JungleCampDefenderTypes_(\w+);",
            block,
        )
        types = {
            "Knights": ["MercDefenderMeleeKnight"] * 3 + ["MercDefenderRangedMage"],
            "SiegeGiants": ["MercDefenderSiegeGiant"] * 2,
        }[kind]
        slots = re.findall(
            r"lv_mapDataDefenderSpawnPoints\[(\d+)\] = PointFromId\((\d+)\);", block
        )
        if [int(k) for k, _ in slots] != list(range(1, len(types) + 1)):
            raise ValueError("Unexpected camp position slots")
        close = [
            (fid, tuple(map(int, position)))
            for fid, position in flags
            if sum((v - p) ** 2 for v, p in zip(center, position)) < 64
        ]
        if flags and len(close) != 1:
            raise ValueError("No unique nearby historical flag")
        defenders = [
            (v, *map(int, points[int(point)]))
            for v, (_, point) in zip(types, slots, strict=True)
        ]
        result.append((tuple(map(int, center)), close[0] if close else None, defenders))
    if len(result) != 5 or (flags and len({r[1][0] for r in result}) != 5):
        raise ValueError("Unexpected map layout")
    return result


def compare(replay, digest, build, package):
    p, _ = game(replay, digest, build)
    with closing(MPQArchive(replay)) as ar:
        actual_map = p.decode_replay_details(ar.read_file("replay.details"))[
            "m_cacheHandles"
        ][-1][8:].hex()
        if (
            actual_map != MAP[build]
            or actual_map != sha256(package.read_bytes()).hexdigest()
        ):
            raise ValueError("Mismatched package")
        events = list(
            p.decode_replay_tracker_events(ar.read_file("replay.tracker.events"))
        )
    camps = layout(package)
    (gates,) = [e["_gameloop"] for e in events if e.get("m_eventName") == b"GatesOpen"]
    first = next(
        e["_gameloop"]
        for e in events
        if e["_eventid"] == 1 and e["m_unitTypeName"].startswith(b"MercDefender")
    )
    physical = [
        (e["m_unitTypeName"].decode(), e["m_x"], e["m_y"])
        for e in events
        if e["_eventid"] == 1
        and e["_gameloop"] == first
        and e["m_unitTypeName"].startswith(b"MercDefender")
        and (e["m_controlPlayerId"], e["m_upkeepPlayerId"]) == (15, 15)
    ]
    forward = [x for _, _, defenders in camps for x in defenders]
    reverse = [x for _, _, defenders in reversed(camps) for x in defenders]
    if Counter(physical) != Counter(forward):
        raise ValueError("Wrong type or position in first wave")
    order = (
        "reverse"
        if physical == reverse
        else "forward" if physical == forward else "other"
    )
    flag_keys = {
        (e["m_unitTagIndex"], e["m_unitTagRecycle"]): (e["m_x"], e["m_y"])
        for e in events
        if e["_eventid"] == 1
        and e["_gameloop"] == 0
        and e["m_unitTypeName"] == b"CampOwnershipFlag"
    }
    planned = []
    if build == 41810:
        for center, flag, _ in camps:
            planned.extend([("icon", center), ("flag", flag[1])])
    observed = []
    for e in events:
        if e["_gameloop"] != first - 2:
            continue
        if e["_eventid"] == 1 and e["m_unitTypeName"] == b"JungleCampIconUnitTeamColor":
            if (e["m_controlPlayerId"], e["m_upkeepPlayerId"]) != (0, 0):
                raise ValueError("Unexpected icon owner")
            observed.append(("icon", (e["m_x"], e["m_y"])))
        if (
            e["_eventid"] == 3
            and (e["m_unitTagIndex"], e["m_unitTagRecycle"]) in flag_keys
        ):
            if (e["m_controlPlayerId"], e["m_upkeepPlayerId"]) != (15, 15):
                raise ValueError("Unexpected flag owner")
            observed.append(
                ("flag", flag_keys[e["m_unitTagIndex"], e["m_unitTagRecycle"]])
            )
    if build == 41810 and (
        order != "reverse" or observed != planned or first - gates != 1922
    ):
        raise ValueError("Historical first wave diverges")
    return dict(
        build=build,
        replay_sha256=digest,
        gate=gates,
        first_defender=first,
        ordered_defenders=order,
        ordered_legacy_icon_and_flag_events=len(planned) if planned == observed else 0,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("ten", "source_map", "stock_map", "controls"):
        parser.add_argument(field, type=Path)
    parser.add_argument("--historical", action="append", required=True, type=Path)
    a = parser.parse_args()
    historical = [(a.ten, SOURCE)] + [
        (p, sha256(p.read_bytes()).hexdigest()) for p in a.historical
    ]
    if len(historical) != 4 or set(k for _, k in historical) != {SOURCE, *CONTROLS}:
        raise ValueError("Expected original and three historical controls")
    cases = [compare(path, k, 41810, a.source_map) for path, k in historical]
    stock = json.loads(a.controls.read_bytes())
    reference = (
        Path(first_sync_game.__file__).with_name("observations")
        / "first-sync-game.json"
    )
    target_pins = {
        row["replay_sha256"] for row in json.loads(reference.read_bytes())["references"]
    }
    if len(target_pins) != 24 or set(stock) != target_pins:
        raise ValueError("Expected the 24 independently pinned target recordings")
    for digest, path in sorted(stock.items()):
        p, _ = game(Path(path), digest, 98348)
        with closing(MPQArchive(path)) as ar:
            match = p.decode_replay_details(ar.read_file("replay.details"))[
                "m_cacheHandles"
            ][-1][8:].hex()
        if match == MAP[98348]:
            cases.append(compare(Path(path), digest, 98348, a.stock_map))
    if len(cases) != 19 or any(
        (case["ordered_defenders"], case["gate"], case["first_defender"])
        != ("reverse", 610, 1044)
        for case in cases[4:]
    ):
        raise ValueError(
            "Expected 15 stock Dragon Shire recordings with reverse camp birth order"
        )
    print(
        json.dumps(
            dict(
                cases=cases,
                native_schedule_counts=dict(
                    Counter(
                        c["ordered_defenders"] for c in cases if c["build"] == 98348
                    )
                ),
            ),
            indent=2,
        )
    )
