"""Extend the verified TEN input prefix until the first unrepresented source event."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from audit_native_game_fidelity import _anonymous
from encoders import encode_game_events
from first_sync_game import game
from initial_point_sessions import analyze
from native_game_events import GameEvent, encode_game_events as encode_native, iter_game_events
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE
from verify_first_sync_inputs import GAME


def identity(row):
    return row["_gameloop"], row["_userid"]["m_userId"], row["_eventid"]


def extend(source, prefix):
    if sha256(prefix).hexdigest() != GAME:
        raise ValueError("Unexpected loop-64 input member")
    old, raw = game(source, SOURCE, 41810)
    target = target_protocol()
    base = list(target.decode_replay_game_events(prefix))
    sessions, _, _ = analyze(source, SOURCE, 41810)
    predicted = dict(sessions)
    combined = []
    overlap = 0
    for ordinal, original in enumerate(old.decode_replay_game_events(raw)):
        row = predicted.get(ordinal)
        if ordinal < len(base):
            if row is not None:
                keys = set(row) | set(base[ordinal])
                if any(row.get(k) != base[ordinal].get(k) for k in keys if k != "_bits"):
                    raise ValueError("Point-session prediction disagrees with the verified prefix")
                overlap += 1
            row = base[ordinal]
        if row is None:
            break
        if identity(row) != identity(original):
            raise ValueError("Target frame refers to another input")
        combined.append(row)
    else:
        raise ValueError("Expected a source input beyond the opening")
    result = encode_game_events(combined, target)
    physical = list(iter_game_events(result))
    named = list(target.decode_replay_game_events(result))
    previous = 0
    for expected, decoded, native in zip(combined, named, physical, strict=True):
        if {k:v for k,v in expected.items() if k != "_bits"} != {k:v for k,v in decoded.items() if k != "_bits"}:
            raise ValueError("Target event changed on encoding")
        tick, user, kind = identity(expected)
        fields = {k:v for k,v in expected.items() if not k.startswith("_")}
        type_id, _ = target.game_event_types[kind]
        anonymous = _anonymous(fields, target.typeinfos, type_id)
        if (native.event != GameEvent(tick - previous, user, kind, anonymous)
                or native.aligned_end_bit - native.start_bit != decoded["_bits"]):
            raise ValueError("Independent native frame or bit extent differs")
        previous = tick
    if not result.startswith(prefix) or encode_native([r.event for r in physical]) != result:
        raise ValueError("Independent encoding or the existing prefix differs")
    return result, dict(build=98348, base_frames=len(base), overlapping_predictions=overlap,
                        added_frames=len(combined)-len(base), total_frames=len(combined),
                        bytes=len(result), sha256=sha256(result).hexdigest(), last_event_loop=previous,
                        first_unconverted=dict(ordinal=ordinal, loop=original["_gameloop"],
                                               event=original["_event"].split(".")[-1]))


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("original", type=Path)
    cli.add_argument("prefix", type=Path)
    cli.add_argument("--private-output", type=Path)
    args = cli.parse_args()
    output, receipt = extend(args.original, args.prefix.read_bytes())
    if args.private_output:
        with args.private_output.open("xb") as f:
            f.write(output)
    print(json.dumps(receipt, indent=2))
