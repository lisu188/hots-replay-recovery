"""Generate a private candidate tracker loop zero for TEN's team-matched standard lobby."""

import argparse
from contextlib import closing
from hashlib import sha256
from itertools import groupby, takewhile
import json
from pathlib import Path

from dragon_mastery_ring_history import historical
from encoders import encode_tracker_events
from mpq_reader import MPQArchive
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE
from protocol_loader import load_protocol
from tracker_player_prefix import generate

BRAXIS = "05ec458110db57dd5cf6c044cb6b7270d880282ec803abce725f048f91fc3e75"
LOST = "a3c97e9a669e73e4c2b19a8f6c5e2de0315cbc5725be82cf1e887ed6319a01c4"
TEN_RUNS = [(9, 10), (1, 165), (5, 3), (1, 7), (10, 28)]
TARGET_RUNS = [(9, 10), (1, 165), (5, 15), (1, 7), (10, 28), (5, 10)]
PROFILES = {
    SOURCE: (41810, b"Dragon Shire", b"Amm", True, None, TEN_RUNS),
    BRAXIS: (98285, b"Braxis Holdout", b"Amm", True, 50001,
             [(9, 10), (1, 332), (5, 15), (1, 10), (10, 24), (5, 10)]),
    LOST: (98348, b"Lost Cavern", b"Priv", False, None,
           [(9, 10), (1, 82), (5, 15), (10, 15)]),
}


def digest(raw):
    return sha256(raw).hexdigest()


def runs(rows):
    return [(kind, sum(1 for _ in group)) for kind, group in groupby(rows, lambda e: e["_eventid"])]


def witness(replay, expected):
    if digest(replay.read_bytes()) != expected:
        raise ValueError("Replay hash differs")
    build, title, game_type, amm, mode_id, expected_runs = PROFILES[expected]
    protocol = load_protocol(41810) if build == 41810 else target_protocol()
    with closing(MPQArchive(replay)) as archive:
        h = protocol.decode_replay_header(archive.header["user_data_header"]["content"])
        attrs = archive.read_file("replay.attributes.events")
        details = archive.read_file("replay.details")
        init = protocol.decode_replay_initdata(archive.read_file("replay.initData"))
        raw = archive.read_file("replay.tracker.events")
    d = protocol.decode_replay_details(details)
    a = protocol.decode_replay_attributes_events(attrs)["scopes"][16]
    o = init["m_syncLobbyState"]["m_gameDescription"]["m_gameOptions"]
    v = h["m_version"]
    if (v["m_build"], v["m_baseBuild"], h["m_dataBuildNum"]) != (build,) * 3:
        raise ValueError("Version differs")
    if d["m_title"] != title or not d["m_isBlizzardMap"] or len(d["m_playerList"]) != 10:
        raise ValueError("Map or player count differs")
    if [[r["value"] for r in a[k]] for k in (3009, 4010, 4018)] != [[game_type], [b"stan"], [b"fcfs"]]:
        raise ValueError("Game type, lobby mode or ready mode differs")
    if (o["m_amm"], "m_ammId" in o, o.get("m_ammId"), o["m_cooperative"]) != (amm, build != 41810, mode_id, False):
        raise ValueError("Matchmaking options differ")
    stream = protocol.decode_replay_tracker_events(raw)
    rows = list(takewhile(lambda e: e["_gameloop"] == 0, stream))
    if runs(rows) != expected_runs:
        raise ValueError("Physical opening order differs")
    bits = sum(r["_bits"] for r in rows)
    if bits >= len(raw)*8 or bits % 8 or encode_tracker_events(rows, protocol) != raw[:bits//8]:
        raise ValueError("Physical opening extent or bytes differ")
    return dict(replay_sha256=expected, build=build, map=title.decode(),
                global_attributes={"3009":game_type.decode(), "4010":"stan", "4018":"fcfs"},
                matchmaking_enabled=amm, amm_id=mode_id, contains_amm_id_field=build!=41810,
                attributes_sha256=digest(attrs), details_sha256=digest(details),
                loop_zero_bytes=bits//8, loop_zero_sha256=digest(raw[:bits//8]),
                physical_event_runs=expected_runs)


def candidate(replay, braxis, lost, package, mechanics, support):
    evidence = [witness(p, h) for p, h in ((replay, SOURCE), (braxis, BRAXIS), (lost, LOST))]
    prefix, _ = generate(replay, SOURCE, 41810)
    body, _ = historical(replay, SOURCE, package, mechanics, support)
    wire = prefix + body
    target = target_protocol()
    rows = list(target.decode_replay_tracker_events(wire))
    if (len(rows) != 235 or runs(rows) != TARGET_RUNS or any(r["_gameloop"] for r in rows)
            or sum(r["_bits"] for r in rows) != len(wire)*8
            or sum(r["_bits"] for r in rows[:10]) != len(prefix)*8
            or encode_tracker_events(rows, target) != wire):
        raise ValueError("Incomplete target loop-zero candidate")
    return wire, dict(format="TEN-quick-match-loop-zero-candidate-v1", direct_98348_quick_match_witness=False,
                      target_build=98348, map_sha256=digest(package.read_bytes()),
                      frames=len(rows), setup_bytes=len(prefix), map_block_bytes=len(body),
                      candidate_bytes=len(wire), candidate_sha256=digest(wire), candidate_runs=TARGET_RUNS,
                      source_same_queue_and_target_standard_controls=evidence)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("replay", "braxis", "lost", "map", "mechanics", "support"):
        parser.add_argument(arg, type=Path)
    parser.add_argument("--private-output", type=Path)
    args = parser.parse_args()
    data, receipt = candidate(args.replay, args.braxis, args.lost, args.map, args.mechanics, args.support)
    if args.private_output:
        with args.private_output.open("xb") as out:
            out.write(data)
    print(json.dumps(receipt, indent=2))
