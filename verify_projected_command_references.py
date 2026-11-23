"""Check per-user command lookup dependencies in the assembled sparse target stream."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from opening_birth_wire import target_protocol


def audit(directory, receipt):
    stream = (directory/"game-inputs.private.bin").read_bytes()
    if len(stream) != receipt["bytes"] or sha256(stream).hexdigest() != receipt["sha256"]:
        raise ValueError("Stream differs from the specified target assembly")
    ledger = json.loads((directory/"ordinals.private.json").read_bytes())
    issued, references, states = Counter(), Counter(), Counter()
    first_unmatched = None
    previous = -1
    for entry, row in zip(ledger,target_protocol().decode_replay_game_events(stream),strict=True):
        ordinal, tick, kind, labels = entry
        if ordinal <= previous or (tick,kind) != (row["_gameloop"],row["_eventid"]):
            raise ValueError("Input ledger disagrees with target stream")
        previous = ordinal
        if kind not in (27,103,104,105):
            continue
        seq = row["m_sequence"]
        key = (row["_userid"]["m_userId"], seq)
        if kind == 27:
            if seq is None:
                raise ValueError("Target issue has no sequence")
            issued[key] += 1
            continue
        if kind == 103:
            states[row["m_state"]] += 1
        count = issued[key]
        outcome = ("sequence_absent" if seq is None else "no_preceding_issue" if not count
                   else "one_preceding_issue" if count == 1 else "reused_issue_key")
        references[f"{kind}_{outcome}"] += 1
        if outcome in ("sequence_absent","no_preceding_issue") and first_unmatched is None:
            first_unmatched = dict(ordinal=ordinal,loop=tick,kind=kind)
    if len(ledger) != receipt["included"]:
        raise ValueError("Unexpected ledger length")
    return dict(build=receipt["build"],stream_sha256=receipt["sha256"],issued_frames=issued.total(),
                distinct_issue_keys=len(issued),references=dict(sorted(references.items())),
                manager_states=dict(states),first_unmatched=first_unmatched,
                native_object_liveness_proven=False)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("directory",type=Path)
    cli.add_argument("receipt",type=Path)
    args = cli.parse_args()
    print(json.dumps(audit(args.directory,json.loads(args.receipt.read_bytes())),indent=2))
