"""Reconstruct unambiguous start-of-match implicit point commands, updates and closes."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from encoders import encode_game_events
from first_point_commands import COMMANDS, FLAGS, first_issue
from first_sync_game import game
from native_game_events import encode_game_events as encode_native, iter_game_events
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE


def analyze(path, digest, build):
    # Bound the comparison identically across cases. Once an ambiguous command is
    # observed, no subsequent sequence for that user is inferred.
    p, raw = game(path, digest, build)
    target = target_protocol()
    users = {}
    counts = Counter()
    accepted = []
    physical = offset = previous = withheld = 0
    for ordinal, e in enumerate(p.decode_replay_game_events(raw)):
        tick, kind, user = e["_gameloop"], e["_eventid"], e["_userid"]["m_userId"]
        if tick >= 4000:
            break
        size, rem = divmod(e["_bits"], 8)
        if rem or not size:
            raise ValueError("Broken source frame boundary")
        original = raw[offset:offset + size]
        offset += size
        prior, previous = previous, tick
        if kind in (101, 102):
            users[user] = ("ended", 0)
            continue
        if kind not in COMMANDS:
            continue
        phase, sequence = users.get(user, ("ready", 0))
        if phase == "ended":
            continue
        row = dict(e)
        if phase == "ready" and first_issue(e, build):
            if e["m_sequence"] != sequence + 1:
                users[user] = ("ended", sequence)
                withheld += 1
                continue
            sequence = e["m_sequence"]
            users[user] = ("open", sequence)
            row.update(m_cmdFlags=FLAGS[98348], m_vector=None)
        elif phase == "open" and (kind == 104 or kind == 103 and e["m_state"] == 0):
            if e["m_sequence"] != sequence and (build == 98348 or e["m_sequence"] is not None):
                raise ValueError("Recorded sequence contradicts the single open command")
            row["m_sequence"] = sequence
            if kind == 103:
                users[user] = ("ready", sequence)
        else:
            users[user] = ("ended", sequence)
            continue
        if encode_game_events([{**e, "_gameloop": tick - prior}], p) != original:
            raise ValueError("Original enclosing command did not round-trip")
        wire = encode_game_events([{**row, "_gameloop": tick - prior}], target)
        if build == 98348:
            if wire != original:
                raise ValueError("Predicted command differs from the physical target frame")
            physical += 1
        counts[kind] += 1
        accepted.append((ordinal, row))
    encoded = encode_game_events([row for _, row in accepted], target)
    decoded = [r.event for r in iter_game_events(encoded)]
    if len(decoded) != len(accepted) or encode_native(decoded) != encoded:
        raise ValueError("Native-layout encoding differs from the named command stream")
    receipt = dict(build=build, replay_sha256=digest, counts=dict(sorted(counts.items())),
                   frames=len(accepted), bytes=len(encoded), sha256=sha256(encoded).hexdigest(),
                   qualifying_physical_target_frames=physical, withheld_nonconsecutive_issues=withheld)
    return accepted, encoded, receipt


def controls(replays):
    import first_sync_game
    pins_path = Path(first_sync_game.__file__).resolve().parent / "observations" / "first-sync-game.json"
    pins = {r["replay_sha256"] for r in json.loads(pins_path.read_bytes())["references"]}
    if len(pins) != 24 or set(replays) != pins:
        raise ValueError("Unexpected target reference set")
    counts = Counter()
    withheld = 0
    for digest, name in sorted(replays.items()):
        _, _, r = analyze(Path(name), digest, 98348)
        counts.update(r["counts"])
        withheld += r["withheld_nonconsecutive_issues"]
    return dict(controls=len(pins), before_loop=4000, enclosing_frames_equal=sum(counts.values()),
                counts=dict(sorted(counts.items())), withheld_nonconsecutive_issues=withheld)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("original", type=Path)
    cli.add_argument("--controls", type=Path)
    cli.add_argument("--private-output", type=Path)
    args = cli.parse_args()
    rows, data, result = analyze(args.original, SOURCE, 41810)
    result["source_ordinals"] = [i for i, _ in rows]
    result["loops"] = [e["_gameloop"] for _, e in rows]
    if args.controls:
        result["cohort"] = controls(json.loads(args.controls.read_bytes()))
    if args.private_output:
        with args.private_output.open("xb") as output:
            output.write(data)
    print(json.dumps(result, indent=2))
