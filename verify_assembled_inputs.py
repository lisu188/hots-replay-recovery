"""Independently compare the private target input stream and ordinal ledger with original TEN."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from first_sync_game import game
from native_game_events import iter_game_events
from predict_camp_captures import SOURCE
from verify_first_sync_inputs import GAME


def verify(source, directory, receipt):
    data = (directory/"game-inputs.private.bin").read_bytes()
    ledger = json.loads((directory/"ordinals.private.json").read_bytes())
    if sha256(data).hexdigest() != receipt["sha256"] or len(data) != receipt["bytes"]:
        raise ValueError("Target stream differs from the assembly receipt")
    if sha256(data[:671]).hexdigest() != GAME:
        raise ValueError("Previously validated original opening disappeared")
    indices = [r[0] for r in ledger]
    if len(indices) != len(set(indices)) or indices != sorted(indices):
        raise ValueError("Duplicate or out-of-order original input")
    selected = dict(zip(indices,ledger,strict=True))
    native = iter(iter_game_events(data))
    old, raw = game(source, SOURCE, 41810)
    kept, gaps, labels = Counter(),Counter(),Counter()
    previous = 0
    first_gap = None
    for ordinal, event in enumerate(old.decode_replay_game_events(raw)):
        kind, tick = event["_eventid"], event["_gameloop"]
        if ordinal not in selected:
            gaps[kind] += 1
            if first_gap is None:
                first_gap = dict(ordinal=ordinal,loop=tick,kind=kind)
            continue
        index, loop, event_id, sources = selected[ordinal]
        if (index,loop,event_id) != (ordinal,tick,kind) or not sources or len(set(sources))!=len(sources):
            raise ValueError("Ledger no longer aligns with the original frame")
        decoded = next(native).event
        previous += decoded.delta
        if (previous,decoded.event_id,decoded.user_id) != (tick,kind,event["_userid"]["m_userId"]):
            raise ValueError("The target wire no longer addresses the same original input")
        labels.update(sources)
        kept[kind] += 1
    if next(native,None) is not None or len(indices) != kept.total():
        raise ValueError("Unclaimed target frames or ordinals")
    for counter,key in ((kept,"included_by_event_id"), (gaps,"omitted_by_event_id")):
        if dict(counter) != {int(i):v for i,v in receipt[key].items()}:
            raise ValueError("Missing or extra inputs compared to the published accounting")
    if (dict(labels) != receipt["provenance_counts"] or first_gap != receipt["first_omitted"]
            or previous != receipt["last_included_loop"]):
        raise ValueError("Evidence category, first gap or final represented loop changed")
    return dict(independently_joined_inputs=kept.total(), unrepresented=gaps.total(),
                last_joined_loop=previous, target_bytes=len(data), opening_prefix_preserved=True)


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ("source","directory","receipt"):
        cli.add_argument(name,type=Path)
    a=cli.parse_args()
    print(json.dumps(verify(a.source,a.directory,json.loads(a.receipt.read_bytes())),indent=2))
