"""Check whether Dragon Shire town deaths predict the original and current catapult allocation requests."""

import argparse
from collections import Counter
from contextlib import closing
import json
from math import floor
from pathlib import Path
import re
from xml.etree import ElementTree

from dragon_lane_roles import layouts, load, physical, PROFILES, tag
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive


def town_regions(map_path):
    with closing(MPQArchive(map_path)) as archive:
        regs = ElementTree.fromstring(read_member(archive, "Regions"))
        script = read_member(archive, "MapScript.galaxy").decode("utf-8-sig")
    (body,) = re.findall(
        r"bool gt_(?:Hookup|Initialize)TownData_Func \(bool testConds, bool runActions\) \{(.*?)\n\}",
        script,
        re.S,
    )
    lanes = {}
    parts = re.split(r"lv_lane = (\d+);", body)[1:]
    for lane, chunk in zip(parts[::2], parts[1::2]):
        if int(lane) not in (1, 2, 3):
            raise ValueError("Unknown lane")
        for town in chunk.split("lv_town += 1;")[1:]:
            (owner,) = re.findall(
                r"lv_owner = libCore_gv_cOMPUTER_Team(Order|Chaos);", town
            )
            (region,) = re.findall(r"lv_townRegion = RegionFromId\((\d+)\);", town)
            r = regs.find("./region[@id='" + region + "']")
            (shape,) = r.findall("shape")
            if shape.get("type") != "rect" or len(shape) != 1 or shape[0].tag != "quad":
                raise ValueError("Town region shape")
            lanes[int(region)] = (
                int(lane),
                11 if owner == "Order" else 12,
                tuple(map(float, shape[0].get("value").split(","))),
            )
    if len(lanes) != 12:
        raise ValueError("Incomplete town regions")
    return lanes


def historical_keys(tr, regions):
    hall = {}
    for e in tr:
        if (
            e.get("m_unitTypeName") not in (b"TownTownHallL2", b"TownTownHallL3")
            or e["_gameloop"] != 0
        ):
            continue
        n, o, u, x, y = physical(e)
        (lane,) = [
            l
            for l, player, (x0, y0, x1, y1) in regions.values()
            if o == u == player and x0 <= x <= x1 and y0 <= y <= y1
        ]
        hall[tag(e)] = lane, o, n
    if len(hall) != 12 or len(set(hall.values())) != 12:
        raise ValueError("Incomplete unique map-to-tracker hall identities")
    return hall


def predict_catapults(events, gates, cutoff, build, regions, lanes, rule):
    halls = historical_keys(events, regions)
    killed = [
        (e["_gameloop"], *halls[tag(e)])
        for e in events
        if e["_eventid"] == 2 and tag(e) in halls
    ]
    _, delay, stride = PROFILES[build]
    first = gates + delay
    # Wave counter increments when the wave dispatch starts, before the first three-unit batch.
    # Native bounds in the tested recordings do not straddle this one-loop boundary.
    periodic_start = ((killed[0][0] - (first - 1)) // stride + 2) if killed else None
    predicted = []
    for wave, base in enumerate(range(first, cutoff + 1, stride), 1):
        for lane in (1, 2, 3):
            tick = base + 3 * lane
            if tick > cutoff:
                continue
            for owner in (12, 11):
                down = [
                    n
                    for t, l, o, n in killed
                    if t < tick and l == lane and 23 - o == owner
                ]
                if rule == 41810:
                    allow = "TownTownHallL3" in down
                else:
                    allow = len(down) == 2 or (
                        len(down) == 1 and (wave - periodic_start) % 3 == 0
                    )
                if allow:
                    waypoint = max(lanes[lane]) if owner == 12 else 0
                    x, y = lanes[lane][waypoint]
                    predicted.append((tick, owner, owner, floor(x), floor(y)))
    return predicted


def audit_cats(path, digest, build, regions, lanes):
    _, tr, gate, cutoff, h = load(path, digest, build)
    actual = [
        (e["_gameloop"], *physical(e)[1:])
        for e in tr
        if e.get("m_unitTypeName") == b"CatapultMinion"
    ]
    out = {}
    for rule in (41810, 98348):
        pred = predict_catapults(tr, gate, cutoff, build, regions, lanes, rule)
        expect = Counter(r[:3] for r in pred)
        seen = Counter(r[:3] for r in actual)
        out[str(rule)] = {
            "predicted": len(pred),
            "actual": len(actual),
            "missed": sum((seen - expect).values()),
            "excess": sum((expect - seen).values()),
            "precise_xy": sum((Counter(pred) & Counter(actual)).values()),
        }
    halls = historical_keys(tr, regions)
    times = {
        halls[tag(e)]: e["_gameloop"]
        for e in tr
        if e["_eventid"] == 2 and tag(e) in halls
    }
    early_keep = {}
    for tick, owner, _, _, _ in predict_catapults(
        tr, gate, cutoff, build, regions, lanes, 41810
    ):
        lane = ((tick - gate - PROFILES[build][1]) % PROFILES[build][2]) // 3
        if tick < times.get((lane, 23 - owner, "TownTownHallL2"), cutoff + 1):
            early_keep[tick, owner] = True
    return dict(
        sha256=digest,
        build=build,
        rules=out,
        candidate_slots_keep_down_fort_still_alive=len(early_keep),
        observed_keep_down_fort_still_alive=sum(
            (tick, owner) in early_keep for tick, owner, _, _, _ in actual
        ),
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--build", type=int, choices=PROFILES, required=True)
    cli.add_argument("--map", type=Path, required=True)
    cli.add_argument("--case", nargs=2, action="append", required=True)
    a = cli.parse_args()
    l, _ = layouts(a.map, a.build)
    r = town_regions(a.map)
    print(
        json.dumps([audit_cats(Path(p), h, a.build, r, l) for p, h in a.case], indent=2)
    )
