"""Encode a sparse tracker member for Dragon Shire camp beacon changes from recorded capture statistics."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from decimal import Decimal
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
from xml.etree import ElementTree

from dragon_startup_births import predict
from dragonshire_packages import HISTORICAL_PACKAGE, HISTORICAL_PACKAGES
from encoders import VersionedEncoder, encode_tracker_events
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from predict_camp_captures import SOURCE, MAP, number
from protocol_loader import load_protocol

STOCK = "f557190f8aaab160789272ce086b8b69d6a8037b152de150332603dae3dc098f"
STOCK_PACKAGE = "2de7e30ecf97cb975f483e8dc33ec05035d5b42d1e45a9a011dfecb4984b1632"
SCHEMAS = {41810: 41810, 98348: 96477}
PROFILE_MAPS = {41810: {MAP, *HISTORICAL_PACKAGES}, 98348: {STOCK, STOCK_PACKAGE}}
RESET = {41810: 16, 98348: 48}
TARGET_SCHEMA_SHA = "e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84"
HISTORICAL_SCHEMA_SHA = (
    "879d228d9d8acd21d63563538dd15841aaf49259ee0bb468b8a46b6a4ef866fd"
)
OWNER = "NNet.Replay.Tracker.SUnitOwnerChangeEvent"
FIELDS = ("m_unitTagIndex", "m_unitTagRecycle", "m_controlPlayerId", "m_upkeepPlayerId")


def anchors(path, layout, mechanics):
    digest = sha256(path.read_bytes()).hexdigest()
    if digest not in PROFILE_MAPS[layout]:
        raise ValueError("Unsupported Dragon Shire layout")
    with closing(MPQArchive(path)) as arc:
        objects, regions, script = (
            read_member(arc, k) for k in ("Objects", "Regions", "MapScript.galaxy")
        )
    placements, meta = predict(objects, regions, script, mechanics.read_bytes())
    beacons = [
        b for b in placements if b["m_unitTypeName"] == b"TownMercCampCaptureBeacon"
    ]
    coords = {
        int(p.get("Id")): p.get("Position").split(",")[:2]
        for p in ElementTree.fromstring(objects).findall("ObjectPoint")
    }
    result = {}
    for camp, c in enumerate(meta["camps"], 1):
        xy = tuple(int(Decimal(n)) for n in coords[c["captain_point_id"]])
        hits = [b for b in beacons if (b["m_x"], b["m_y"]) == xy]
        if len(hits) != 1:
            raise ValueError("Beacon placement ambiguity")
        result[camp] = (hits[0]["m_unitTagIndex"], hits[0]["m_unitTagRecycle"])
    if len(result) != 5 or len(set(result.values())) != 5 or len(beacons) != 5:
        raise ValueError("Incomplete beacon set")
    return result, digest


@lru_cache(maxsize=1)
def target_protocol():
    p = load_protocol(96477)
    tid, name = p.tracker_event_types[3]
    if (
        p.recovery_schema_sha256 != TARGET_SCHEMA_SHA
        or name != OWNER
        or tuple(item[0] for item in p.typeinfos[tid][1][0]) != FIELDS
    ):
        raise ValueError("Unsupported target tracker graph")
    return p


def read_tracker(path, build):
    p = load_protocol(SCHEMAS[build])
    if p.recovery_schema_sha256 != (
        HISTORICAL_SCHEMA_SHA if build == 41810 else TARGET_SCHEMA_SHA
    ):
        raise ValueError("Unexpected source tracker schema")
    with closing(MPQArchive(path)) as arc:
        header = p.decode_replay_header(arc.header["user_data_header"]["content"])
        d = p.decode_replay_details(arc.read_file("replay.details"))["m_cacheHandles"]
        i = p.decode_replay_initdata(arc.read_file("replay.initData"))[
            "m_syncLobbyState"
        ]["m_gameDescription"]["m_cacheHandles"]
        if (
            header["m_version"]["m_build"],
            header["m_version"]["m_baseBuild"],
            header["m_dataBuildNum"],
        ) != (build,) * 3:
            raise ValueError("Physical replay version differs")
        if (
            not d
            or d != i
            or d[-1][:4] != b"s2ma"
            or d[-1][8:].hex() != (MAP if build == 41810 else STOCK)
        ):
            raise ValueError("Physical replay map differs")
        raw = arc.read_file("replay.tracker.events")
    return p, raw, header["m_elapsedGameLoops"]


def capture_stats(events):
    """Read capture loop, camp and team; the caller also obtains the horizon from the header."""
    for event in events:
        if event.get("m_eventName") == b"JungleCampCapture":
            raw = number(event, "m_fixedData", "TeamID")
            if raw not in (4096, 8192):
                raise ValueError("Unrecognized team")
            yield event["_gameloop"], number(event, "m_intData", "CampID"), raw // 4096


def project(stats, tags, reset, horizon):
    if type(horizon) is not int or horizon < 0 or reset not in RESET.values():
        raise ValueError("Invalid capture timing profile")
    result = []
    censored = 0
    for tick, camp, team in stats:
        if (
            any(type(n) is not int for n in (tick, camp, team))
            or not 1 <= tick <= horizon
            or camp not in tags
            or team not in (1, 2)
        ):
            raise ValueError("Invalid capture")
        index, recycle = tags[camp]
        for when, owner in ((tick - 1, 10 + team), (tick + reset, 0)):
            if when > horizon:
                censored += 1
                continue
            result.append(
                dict(
                    _gameloop=when,
                    _eventid=3,
                    _event=OWNER,
                    m_unitTagIndex=index,
                    m_unitTagRecycle=recycle,
                    m_controlPlayerId=owner,
                    m_upkeepPlayerId=owner,
                )
            )
    result.sort(key=lambda r: r["_gameloop"])
    if any(a["_gameloop"] == b["_gameloop"] for a, b in zip(result, result[1:])):
        raise ValueError(
            "Two projected beacon changes share a loop; their ordering is unverified"
        )
    return result, censored


def normalized(events):
    return [(e["_gameloop"], e["_eventid"], *(e[k] for k in FIELDS)) for e in events]


def encode_sparse(events):
    p = target_protocol()
    raw = encode_tracker_events(events, p)
    decoded = list(p.decode_replay_tracker_events(raw))
    if (
        normalized(decoded) != normalized(events)
        or sum(e["_bits"] for e in decoded) != len(raw) * 8
    ):
        raise ValueError("Target decoder disagrees with sparse member")
    return raw, decoded


def frame_bytes(event, previous_tick, p):
    delta = event["_gameloop"] - previous_tick
    if not 0 <= delta < 2**32:
        raise ValueError("Invalid tracker delta")
    n = next(w for w in (6, 14, 22, 32) if delta < 1 << w)
    enc = VersionedEncoder(p.typeinfos)
    enc.instance(p.svaruint32_typeid, {"m_uint" + str(n): delta})
    enc.instance(p.tracker_eventid_typeid, 3)
    enc.instance(p.tracker_event_types[3][0], event)
    return enc.getvalue()


def sparse_source(source, map_path, mechanics, target_layout):
    if sha256(source.read_bytes()).hexdigest() != SOURCE:
        raise ValueError("Unexpected TEN_GREYMANE file")
    p, wire, horizon = read_tracker(source, 41810)
    tags, digest = anchors(map_path, target_layout, mechanics)
    rows = list(capture_stats(p.decode_replay_tracker_events(wire)))
    events, censored = project(rows, tags, RESET[target_layout], horizon)
    raw, decoded = encode_sparse(events)
    if len(events) != 26 or len(rows) != 13 or censored:
        raise ValueError("Unexpected historical selection")
    return raw, dict(
        format="sparse-camp-owner-98348-v1",
        source_sha256=SOURCE,
        target_layout=target_layout,
        target_wire_profile_build=96477,
        target_schema_sha256=TARGET_SCHEMA_SHA,
        map_sha256=digest,
        capture_stats=len(rows),
        team_changes=len(rows),
        neutral_changes=len(events) - len(rows),
        reset_after_stat=RESET[target_layout],
        records=len(decoded),
        bytes=len(raw),
        sha256=sha256(raw).hexdigest(),
        beacon_indices_by_camp={k: v[0] for k, v in tags.items()},
        all_initial_recycles_one=all(v[1] == 1 for v in tags.values()),
        record_bits=dict(sorted(Counter(e["_bits"] for e in decoded).items())),
        generated_record_ties=0,
        uses_recorded_capture_stats=True,
        uses_observed_owner_payloads_for_generation=False,
        entire_tracker_generated=False,
    )


def verify(replay, expected, build, map_path, mechanics):
    if sha256(replay.read_bytes()).hexdigest() != expected:
        raise ValueError("Wrong replay digest")
    tags, digest = anchors(map_path, build, mechanics)
    p, raw, horizon = read_tracker(replay, build)
    events = list(p.decode_replay_tracker_events(raw))
    # Freeze the complete sparse output before inspecting owner records, their tags or the frame positions.
    stats = list(capture_stats(events))
    predictions, censored = project(stats, tags, RESET[build], horizon)
    sparse, _ = encode_sparse(predictions)
    predicted = {r["_gameloop"]: r for r in predictions}
    tags_scope = set(tags.values())
    actual = [
        e
        for e in events
        if e["_eventid"] == 3
        and (e["m_unitTagIndex"], e["m_unitTagRecycle"]) in tags_scope
    ]
    if normalized(actual) != normalized(predictions):
        raise ValueError("Recorded beacon owner sequence differs from projection")
    candidate_slots = defaultdict(list)
    all_slots = Counter(e["_gameloop"] for e in events)
    for ordinal, e in enumerate(events):
        if e["_eventid"] == 3 and e["_gameloop"] in predicted:
            candidate_slots[e["_gameloop"]].append(ordinal)
    tie_owner = 0
    tied_any = 0
    slots = {}
    for tick, value in predicted.items():
        choices = candidate_slots[tick]
        if len(choices) > 1:
            # Comparison only: existing unrelated same-loop owners have no inferred insertion order.
            choices = [
                o
                for o in choices
                if (events[o]["m_unitTagIndex"], events[o]["m_unitTagRecycle"])
                == (value["m_unitTagIndex"], value["m_unitTagRecycle"])
            ]
            tie_owner += 1
        if len(choices) != 1:
            raise ValueError("Unresolved owner frame in recorded scaffold")
        slots[choices[0]] = value
        tied_any += all_slots[tick] > 1
    physical_bits = 0
    same_loop_before = 0
    same_loop_after = 0
    before_tick = 0
    for ordinal, e in enumerate(events):
        bits = e["_bits"]
        if ordinal in slots:
            value = slots[ordinal]
            generated = frame_bytes(value, before_tick, target_protocol())
            if (
                physical_bits % 8
                or bits % 8
                or generated != raw[physical_bits // 8 : (physical_bits + bits) // 8]
            ):
                raise ValueError(
                    "Target encoding differs at physical tracker frame cursor"
                )
            same_loop_before += (
                ordinal > 0 and events[ordinal - 1]["_gameloop"] == e["_gameloop"]
            )
            same_loop_after += (
                ordinal + 1 < len(events)
                and events[ordinal + 1]["_gameloop"] == e["_gameloop"]
            )
            events[ordinal] = value
        physical_bits += bits
        before_tick = e["_gameloop"]
    if physical_bits != len(raw) * 8 or encode_tracker_events(events, p) != raw:
        raise ValueError("Full physical tracker scaffolding does not round-trip")
    return dict(
        replay_sha256=expected,
        build=build,
        layout_input_sha256=digest,
        tracker_sha256=sha256(raw).hexdigest(),
        tracker_bytes=len(raw),
        capture_stats=len(stats),
        projected_records=len(predictions),
        censored_records=censored,
        sparse_encoded_bytes=len(sparse),
        sparse_sha256=sha256(sparse).hexdigest(),
        generated_record_ties=0,
        physical_spans_equal=len(slots),
        mixed_same_loop_neighbors=tied_any,
        same_loop_other_owner_records=tie_owner,
        same_loop_preceding_neighbor=same_loop_before,
        same_loop_following_neighbor=same_loop_after,
        full_tracker_equal_after_slot_substitution=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    make = sub.add_parser("generate")
    make.add_argument("--source-replay", type=Path, required=True)
    make.add_argument("--layout", type=int, choices=(41810, 98348), required=True)
    make.add_argument("--output", type=Path, required=True)
    check = sub.add_parser("verify-control")
    check.add_argument("--replay", type=Path, required=True)
    check.add_argument("--sha256", required=True)
    check.add_argument("--build", type=int, choices=(41810, 98348), required=True)
    for command in (make, check):
        command.add_argument("--map", type=Path, required=True)
        command.add_argument("--mechanics", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "generate":
        raw, result = sparse_source(
            args.source_replay, args.map, args.mechanics, args.layout
        )
        with args.output.open("xb") as output:
            output.write(raw)
    else:
        result = verify(args.replay, args.sha256, args.build, args.map, args.mechanics)
    print(json.dumps(result, indent=2, sort_keys=True))
