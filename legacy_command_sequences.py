"""Recover 41810 target-update sequence fields from adjacent command-manager records."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from migrate_replay import decode_events, encode_events
from mpq_reader import MPQArchive
from protocol_loader import load_protocol

RESET, ISSUE, MANAGER, POINT, UNIT = 25, 27, 103, 104, 105
UPDATES = {POINT, UNIT}


def paired_legacy_sequences(events):
    """Recover only legacy updates paired with a same-loop command-manager record.

    Within each user's command stream, only the immediate successor can bind an
    update. Never examine a target-update sequence to select its own value.
    """
    pending = {}
    predicted = {}
    for ordinal, event in enumerate(events):
        kind = event["_eventid"]
        if kind not in (RESET, ISSUE, MANAGER, POINT, UNIT):
            continue
        user = event["_userid"]["m_userId"]
        loop = event["_gameloop"]
        prior = pending.pop(user, None)
        if (
            prior is not None
            and prior[1] == loop
            and kind == MANAGER
            and event["m_state"] in (0, 1, 2)
        ):
            predicted[prior[0]] = event["m_sequence"]
        if kind in UPDATES:
            pending[user] = ordinal, loop
    return predicted


def compare(path, expected, build):
    if sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError("Replay SHA-256 mismatch")
    if build not in (41810, 98348):
        raise ValueError("Unsupported build")
    protocol = load_protocol(41810 if build == 41810 else 96477)
    with closing(MPQArchive(path)) as archive:
        header = protocol.decode_replay_header(archive.header["user_data_header"]["content"])
        version = header["m_version"]
        if (version["m_build"], version["m_baseBuild"], header["m_dataBuildNum"]) != (build,) * 3:
            raise ValueError("Physical replay build mismatch")
        raw = archive.read_file("replay.game.events")
    events = list(decode_events(raw, protocol, "game"))
    recorded = {i: e.pop("m_sequence") for i, e in enumerate(events) if e["_eventid"] in UPDATES}
    paired = paired_legacy_sequences(events)
    stats = {str(t): Counter() for t in sorted(UPDATES)}
    for ordinal, actual in recorded.items():
        event = events[ordinal]
        row = stats[str(event["_eventid"])]
        row["absent" if actual is None else "present"] += 1
        if ordinal in paired:
            row["paired_absent" if paired[ordinal] is None else "paired_present"] += 1
            row["paired_matched" if paired[ordinal] == actual else "paired_different"] += 1
        else:
            row["unpaired_absent" if actual is None else "unpaired_present"] += 1
        event["m_sequence"] = paired.get(ordinal, actual) if build == 41810 else actual
    managers = Counter(str(e["m_state"]) for e in events if e["_eventid"] == MANAGER)
    return {
        "build": build,
        "replay_sha256": expected,
        "game_sha256": sha256(raw).hexdigest(),
        "updates": stats,
        "manager_state_counts": managers,
        "full_game_equal": encode_events(events, protocol, "game") == raw,
        "reencoded_with_recovered_pairs": build == 41810,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("replay", type=Path)
    p.add_argument("--sha256", required=True)
    p.add_argument("--build", type=int, choices=(41810, 98348), required=True)
    args = p.parse_args()
    print(json.dumps(compare(args.replay, args.sha256, args.build), indent=2))


if __name__ == "__main__":
    main()
