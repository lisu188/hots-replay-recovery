"""Check the first unacknowledged implicit point command and its first two updates."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from encoders import encode_game_events
from mpq_reader import MPQArchive
from predict_camp_captures import SOURCE
from protocol_loader import load_protocol
from smartcam_tags import SRC_SCHEMA, DST_SCHEMA

ISSUE, UPDATE = 27, 104
COMMANDS = {25, ISSUE, 103, UPDATE, 105}
FLAGS = {41810: 0x100108, 98348: 0x80108}


def first_issue(row, build):
    return (row["_eventid"] == ISSUE and row["m_abil"] is None and set(row["m_data"]) == {"TargetPoint"}
            and row["m_cmdFlags"] == FLAGS[build] and row["m_otherUnit"] is None
            and row["m_unitGroup"] is None and row.get("m_vector") is None)


def analyze(replay, digest, build, limit):
    if sha256(replay.read_bytes()).hexdigest() != digest:
        raise ValueError("Unexpected replay")
    p = load_protocol(41810 if build == 41810 else 96477)
    target = load_protocol(96477)
    if p.recovery_schema_sha256 != {41810: SRC_SCHEMA, 98348: DST_SCHEMA}[build] or target.recovery_schema_sha256 != DST_SCHEMA:
        raise ValueError("Unexpected protocol")
    with closing(MPQArchive(replay)) as arc:
        h = p.decode_replay_header(arc.header["user_data_header"]["content"])
        if (h["m_version"]["m_build"], h["m_version"]["m_baseBuild"], h["m_dataBuildNum"]) != (build,) * 3:
            raise ValueError("Wrong recording build")
        raw = arc.read_file("replay.game.events")
    started, active, rows = set(), {}, []
    counts = Counter()
    previous = offset = 0
    for event in p.decode_replay_game_events(raw):
        tick = event["_gameloop"]
        if tick > limit:
            break
        kind, user = event["_eventid"], event["_userid"]["m_userId"]
        size, rem = divmod(event["_bits"], 8)
        if rem:
            raise ValueError("Partial game frame")
        result = None
        if kind in COMMANDS and user not in started:
            started.add(user)
            if first_issue(event, build):
                counts["eligible_initial_commands"] += 1
                if event["m_sequence"] != 1:
                    raise ValueError("Initial issue sequence differs")
                active[user] = (event["m_sequence"], 0)
                result = {**event, "m_cmdFlags": FLAGS[98348], "m_vector": None}
        elif kind in COMMANDS and user in active:
            sequence, n = active[user]
            if kind != UPDATE:
                del active[user]
            else:
                counts["updates_scored"] += 1
                if build == 41810 and event["m_sequence"] not in (None, sequence):
                    raise ValueError("Historical update conflicts with the issued sequence")
                if build == 98348 and event["m_sequence"] != sequence:
                    counts["updates_disagree"] += 1
                if n == 1:
                    del active[user]
                else:
                    active[user] = sequence, n + 1
                result = {**event, "m_sequence": sequence}
        if result is not None:
            if build == 98348:
                physical = encode_game_events([{**result, "_gameloop": tick-previous}], target)
                if physical == raw[offset:offset+size]:
                    counts["physical_frames_equal"] += 1
            rows.append(result)
        previous, offset = tick, offset + size
    payload = encode_game_events(rows, target)
    return payload, dict(build=build, replay_sha256=digest, loop_limit=limit, counts=dict(counts),
                         frames=len(rows), bytes=len(payload), sha256=sha256(payload).hexdigest())


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("replay", type=Path)
    cli.add_argument("sha256")
    cli.add_argument("build", type=int, choices=(41810,98348))
    cli.add_argument("--private-output", type=Path)
    args = cli.parse_args()
    data, receipt = analyze(args.replay,args.sha256,args.build,64 if args.build==41810 else 1500)
    if args.private_output:
        if (args.build, args.sha256, receipt["frames"]) != (41810, SOURCE, 4):
            raise ValueError("Private output requires the original TEN first-sync interval")
        with args.private_output.open("xb") as output:
            output.write(data)
    print(json.dumps(receipt, indent=2))
