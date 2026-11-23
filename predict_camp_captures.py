"""Predict 41810 Dragon Shire capture stats from beacon ownership alone, then score other witnesses."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from decimal import Decimal
from hashlib import sha256
import json
from math import floor
from pathlib import Path
import re
from xml.etree import ElementTree

from encoders import encode_tracker_events
from mpq_reader import MPQArchive
from protocol_loader import load_protocol

SOURCE = "e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824"
CONTROLS = (
    "7efa1c335816eebe802747ae4b16252ed22fcd8387b09d24b115b2917542b52a",
    "2fca3c78d0e459d4452e3fb1f41ff3fce22b9c1f8f113019389195ff171bf618",
    "8c4fb83989b528ea3227f6c97758293d1f650e33caa3d38c6a2a84d27ab0850d",
)
MAP = "e0a58745837b3b5351015c933560dbffb178d747009d2d57b4153ef425cf7250"
WAVES = {
    "SiegeGiants": Counter({"MercLanerSiegeGiant": 2}),
    "Knights": Counter({"MercLanerMeleeKnight": 3, "MercLanerRangedMage": 1}),
}


def need(ok, msg):
    if not ok:
        raise ValueError(msg)


def coordinates(node):
    return tuple(Decimal(x) for x in node.attrib["Position"].split(",")[:2])


def map_camps(path):
    need(sha256(path.read_bytes()).hexdigest() == MAP, "Original map digest")
    with closing(MPQArchive(path)) as arc:
        objs = ElementTree.fromstring(arc.read_file("Objects"))
        script = arc.read_file("MapScript.galaxy").decode("utf-8-sig")
    points = {int(n.attrib["Id"]): coordinates(n) for n in objs.findall("ObjectPoint")}
    flags = [
        coordinates(n)
        for n in objs.findall("ObjectUnit")
        if n.attrib["UnitType"] == "CampOwnershipFlag"
    ]
    camps = {}
    for num, block in enumerate(script.split("lv_junglecamp += 1;")[1:], 1):
        (pid,) = re.findall(r"lv_mapDataCampCaptainSpawnPoint = PointFromId\((\d+)\)", block)
        (kind,) = re.findall(
            r"lv_mapDataCampDefenderType = libMapM_ge_JungleCampDefenderTypes_(\w+);", block
        )
        pos = points[int(pid)]
        nearby = [f for f in flags if sum((a - b) ** 2 for a, b in zip(f, pos)) <= 8**2]
        (flag,) = nearby
        need(kind in WAVES, "Unrecognized camp")
        camps[num] = (kind, pos, flag)
    need(
        len(camps)
        == len(set(c[1] for c in camps.values()))
        == len(set(c[2] for c in camps.values()))
        == 5,
        "Camp placement uniqueness",
    )
    return camps


def birth_keys(events, unit, coords, *, initial=False):
    hits = defaultdict(list)
    for e in events:
        if (
            e["_event"].endswith(".SUnitBornEvent")
            and e["m_unitTypeName"] == unit
            and (not initial or e["_gameloop"] == 0)
        ):
            hits[e["m_x"], e["m_y"]].append((e["m_unitTagIndex"], e["m_unitTagRecycle"]))
    result = {}
    for cid, xy in coords.items():
        (identity,) = hits[tuple(map(floor, xy))]
        result[identity] = cid
    need(len(result) == len(coords), "Repeated startup tag")
    return result


def predict(beacon_tags, owner_events):
    """Reads only authenticated beacon identities and their owner changes. Includes late predictions."""
    predicted = Counter()
    other_transitions = 0
    for loop, identity, control, upkeep in owner_events:
        if identity not in beacon_tags:
            continue
        if control == upkeep and control in (11, 12):
            predicted[loop + 1, beacon_tags[identity], control - 10] += 1
        else:
            other_transitions += 1
    return predicted, other_transitions


def number(e, section, field):
    (n,) = [v["m_value"] for v in e[section] if v["m_key"] == field.encode()]
    return n


def score(path, expected, camps):
    protocol = load_protocol(41810)
    need(sha256(path.read_bytes()).hexdigest() == expected, "Replay digest")
    with closing(MPQArchive(path)) as arc:
        head = protocol.decode_replay_header(arc.header["user_data_header"]["content"])
        need(
            (head["m_version"]["m_build"], head["m_version"]["m_baseBuild"]) == (41810, 41810), "Build"
        )
        need(
            protocol.decode_replay_details(arc.read_file("replay.details"))["m_cacheHandles"][-1][
                8:
            ].hex()
            == MAP,
            "Map",
        )
        raw = arc.read_file("replay.tracker.events")
    events = list(protocol.decode_replay_tracker_events(raw))
    need(encode_tracker_events(events, protocol) == raw, "Source tracker full round-trip")
    cap_points = {cid: data[1] for cid, data in camps.items()}
    beacon_keys = birth_keys(events, b"TownMercCampCaptureBeacon", cap_points, initial=True)
    owners = [
        (
            e["_gameloop"],
            (e["m_unitTagIndex"], e["m_unitTagRecycle"]),
            e["m_controlPlayerId"],
            e["m_upkeepPlayerId"],
        )
        for e in events
        if e["_event"].endswith(".SUnitOwnerChangeEvent")
    ]
    predicted, other = predict(beacon_keys, owners)
    # No capture stats, flag/icon events or laner births are available to the predictor.
    actual = Counter()
    for e in events:
        if e.get("m_eventName") == b"JungleCampCapture":
            team = number(e, "m_fixedData", "TeamID")
            cid = number(e, "m_intData", "CampID")
            need(team in (4096, 8192) and cid in camps, "Capture stat shape")
            actual[e["_gameloop"], cid, team // 4096] += 1
    witnesses = {}
    for label, kind, coords, initial in [
        ("flag", b"CampOwnershipFlag", {i: c[2] for i, c in camps.items()}, True),
        ("icon", b"JungleCampIconUnitTeamColor", cap_points, False),
    ]:
        keys = birth_keys(events, kind, coords, initial=initial)
        seen = Counter(
            (loop, keys[key], c - 10)
            for loop, key, c, u in owners
            if key in keys and c == u and c in (11, 12)
        )
        witnesses[label] = score_events(predicted, seen)
    groups = defaultdict(Counter)
    ambiguous_laners = 0
    for e in events:
        if not e["_event"].endswith(".SUnitBornEvent") or not e["m_unitTypeName"].startswith(
            b"MercLaner"
        ):
            continue
        x, y, owner = e["m_x"], e["m_y"], e["m_controlPlayerId"]
        nearby = [cid for cid, (a, b) in cap_points.items() if (x - a) ** 2 + (y - b) ** 2 <= 8**2]
        if len(nearby) != 1 or owner not in (11, 12) or e["m_upkeepPlayerId"] != owner:
            ambiguous_laners += 1
            continue
        groups[e["_gameloop"], nearby[0], owner - 10][e["m_unitTypeName"].decode()] += 1
    complete_waves = Counter(
        {key: 1 for key, wave in groups.items() if wave == WAVES[camps[key[1]][0]]}
    )
    witnesses["full_waves"] = score_events(predicted, complete_waves)
    return dict(
        replay_sha256=expected,
        tracker_sha256=sha256(raw).hexdigest(),
        tracker_reencoded_byte_equal=True,
        predictions=predicted.total(),
        observed_stats=actual.total(),
        capture_stats=score_events(predicted, actual),
        witnesses=witnesses,
        other_beacon_owner_transitions=other,
        laners_outside_scope=ambiguous_laners,
        partial_or_different_wave_groups=len(groups) - len(complete_waves),
        wave_units=sum(w.total() for w in groups.values()),
        negative_zero_offset=score_events(
            Counter({(t - 1, c, s): n for (t, c, s), n in predicted.items()}), actual
        ),
    )


def score_events(predicted, actual):
    return dict(
        matches=(predicted & actual).total(),
        false_positives=(predicted - actual).total(),
        misses=(actual - predicted).total(),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, required=True)
    parser.add_argument("--replay", type=Path, nargs=4, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    camps = map_camps(args.map)
    files = {sha256(f.read_bytes()).hexdigest(): f for f in args.replay}
    need(set(files) == {SOURCE, *CONTROLS}, "Expected one development case and three disjoint controls")
    cases = [score(files[h], h, camps) for h in (SOURCE, *CONTROLS)]
    report = dict(
        map_sha256=MAP,
        predictor="Only loop-zero map-matched beacon identities and their ownership transitions. "
        "Each owner pair (11,11) or (12,12) predicts a capture at the next loop for team 1 or 2, respectively. "
        "The rule was selected on TEN_GREYMANE before testing the other three.",
        cases=cases,
    )
    data = (json.dumps(report, indent=2) + "\n").encode()
    if args.output.exists():
        need(args.output.read_bytes() == data, "Existing aggregate differs")
    else:
        with args.output.open("xb") as stream:
            stream.write(data)
    print([(r["predictions"], r["observed_stats"], r["capture_stats"], r["witnesses"]) for r in cases])


if __name__ == "__main__":
    main()
