"""Join the evidence-backed War Paint input to either supported map and its MercCapture tracker."""

import argparse
from bisect import bisect_left
from collections import Counter
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from build_extended_spikes_map import PARENT, pinned, require
from encoders import encode_game_events, encode_tracker_events
from initial_talent_tracker import LEDGER, STREAM
from opening_birth_wire import target_protocol
from signed_game_input_map import canonical, digest
from sonya_war_paint import generate
from verify_assembled_inputs import verify
from verify_extended_spikes_choice import CANDIDATE
from verify_signed_tracker import frames

BASES = {
    PARENT:(STREAM, LEDGER, "82a647ba5573d21d2140f8c0db046bdceb37985ddba501a85bf3e890627f20b0"),
    CANDIDATE:("0d412eb98d802c9266f851581020f7a54c708654ed18f89e5cb0c5f5b6338d53",
               "a1644c4b0f6aff6d14db6749f4df02f392ab8a89004f0c52cd9bf17642e78409",
               "20d8f719c926d1964774dc801f26990b5fb8c393729d776b89a6ead6ede7af37"),
}
LABEL = "sonya_war_paint_requires_first_tier_acceptance"


def insert_game_input(source, base, stream_hash, ledger_hash, old, detail, row, label, directory, target):
    before = pinned(base/"game-inputs.private.bin",stream_hash)
    ledger = json.loads(pinned(base/"ordinals.private.json",ledger_hash))
    ids = [r[0] for r in ledger]
    require(ids == sorted(set(ids)) and len(ids) == old["included"] and detail["input_ordinal"] not in ids,
            "Parent game ordinal conflict")
    require((row["_eventid"],row["_gameloop"],row["_userid"]["m_userId"],row["m_index"]) ==
            (110,detail["selection_loop"],detail["user"],detail["target_index"]), "Unexpected talent input")
    at = bisect_left(ids,detail["input_ordinal"])
    game_rows = list(target.decode_replay_game_events(before))
    require(len(game_rows) == len(ledger), "Wrong parent input count")
    game_rows.insert(at,row)
    wire = encode_game_events(game_rows,target)
    checked = list(target.decode_replay_game_events(wire))
    require(checked[at]["m_index"] == detail["target_index"] and
            encode_game_events(checked[:at]+checked[at+1:],target) == before,
            "Removing the new talent did not restore the parent input stream")
    ledger.insert(at,[detail["input_ordinal"],row["_gameloop"],row["_eventid"],[label]])
    kept = Counter(old["included_by_event_id"])
    omitted = Counter(old["omitted_by_event_id"])
    kept["110"] += 1
    omitted["110"] -= 1
    ledger_bytes = canonical(ledger)
    labels = Counter(old["provenance_counts"])
    labels[label] += 1
    report = dict(sha256=digest(wire), bytes=len(wire), included=len(ledger), omitted=sum(omitted.values()),
                  included_by_event_id=dict(kept), omitted_by_event_id=dict(omitted),
                  provenance_counts=dict(labels), first_omitted=old["first_omitted"],
                  last_included_loop=old["last_included_loop"], ledger_sha256=digest(ledger_bytes))
    (directory/"game-inputs.private.bin").write_bytes(wire)
    (directory/"ordinals.private.json").write_bytes(ledger_bytes)
    report["independent_join"] = verify(source,directory,report)
    return report


def join_tracker(base, result, directory, target):
    wire = pinned(base/"TEN.tracker.sparse.bin","d9ec90c5eab4deef5d21dee2d4e8f94c5d5a09e5d8f226e469093c9676fc4202")
    ledger = json.loads(pinned(base/"tracker-ordinals.json","48ded0fc2551975f35a6735c79fdd9c079f6b73fe91f98af7e30adfb4cb8fe2c"))
    ids = [r["source_ordinal"] for r in ledger]
    original = result["ten"]["tracker_ordinal"]
    require(ids == sorted(set(ids)) and original not in ids and len(ids)==440,"Unexpected parent tracker mapping")
    rows = [e for e,*_ in frames(wire,target)]
    zero = len(rows)-len(ids)
    require(zero == 235 and all(r["_gameloop"] == 0 for r in rows[:zero]) and
            [r["target_ordinal"] for r in ledger] == list(range(zero,len(rows))), "Target tracker mapping differs")
    at = bisect_left(ids,original)
    target_at = zero+at
    award, = target.decode_replay_tracker_events(pinned(directory/"award.tracker.private.bin",result["tracker_sha256"]))
    rows.insert(target_at,award)
    ledger.insert(at,dict(source_ordinal=original,target_ordinal=target_at,producer=LABEL))
    for i,item in enumerate(ledger,zero):
        item["target_ordinal"] = i
    data = encode_tracker_events(rows,target)
    restored = [e for e,*_ in frames(data,target)]
    require(restored[target_at] == {k:v for k,v in award.items() if k!="_bits"} and
            encode_tracker_events(restored[:target_at]+restored[target_at+1:],target) == wire,
            "Removing the translated award did not restore the parent tracker")
    prefix = pinned(base/"TEN.tracker.prefix.bin","3c9ebfc479e391ea81746953ace5285f0253be514f0a7671d51dc1f5423bc4af")
    require(data.startswith(prefix), "Earlier continuous prefix changed")
    (directory/"TEN.tracker.sparse.bin").write_bytes(data)
    (directory/"tracker-ordinals.json").write_bytes(canonical(ledger))
    return dict(frames=len(rows), covered_postzero=len(ledger), omitted_postzero=6401-len(ledger),
                bytes=len(data), sha256=digest(data), source_ordinal=original, target_ordinal=target_at,
                parent_recovered_byte_for_byte=True)


def run(source,historical,modern,package,game_library,prefix,controls,base,receipt,output,tracker_base=None):
    require(not output.exists(), "Choose a new output directory")
    target = target_protocol()
    with TemporaryDirectory(dir=output.parent) as temp:
        directory = Path(temp)/"frames"
        evidence = generate(source,historical,modern,package,game_library,prefix,controls,directory)
        result = dict(evidence)
        stream_hash, ledger_hash, receipt_hash = BASES[evidence["map_sha256"]]
        old = json.loads(pinned(receipt,receipt_hash))
        row, = target.decode_replay_game_events(pinned(directory/"choice.game.private.bin",evidence["game_sha256"]))
        result["game"] = insert_game_input(source,base,stream_hash,ledger_hash,old,evidence["ten"],row,LABEL,
                                           directory,target)
        if tracker_base:
            require(evidence["map_sha256"] == PARENT, "Tracker parent belongs to MercCapture")
            result["tracker"] = join_tracker(tracker_base,evidence,directory,target)
        directory.rename(output)
    return result


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for key in ("source","historical","modern","package","game_library","prefix","controls","base","receipt","output"):
        cli.add_argument(key,type=Path)
    cli.add_argument("--tracker-base",type=Path)
    print(json.dumps(run(**vars(cli.parse_args())),indent=2))
