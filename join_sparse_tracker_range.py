"""Append an already projected contiguous block of the sparse MercCapture tracker to the continuous prefix.

The sparse fragment (assemble_signed_tracker.py on MercCapture) maps each later target
frame to one physical 41810 tracker ordinal. When the continuous prefix has reached
the source ordinal just before a block, and the candidate package differs from
MercCapture only by appended talent records and localized strings, that block's
target frames can join the prefix unchanged apart from the first frame's clock delta.
The default range is the loop-610 gate opening: GatesOpen, ten GatesAreOpen upgrades
and 54 gate-blocker removals (source ordinals 252..316).
"""

import argparse
from contextlib import closing
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from build_extended_spikes_map import pinned, require
from encoders import encode_tracker_events
from initial_talent_tracker import load_case
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE
from signed_game_input_map import digest
from verify_signed_tracker import frames

MERC = "54e1a8fbe7e42f00b7b52cde420ed259105228fcdf165097ef52ecd0f5c4125a"
CANDIDATE = "fa349ed928b649ea203133237999e8d4202a6e13b328224619eb1399cff23d6c"
PREFIX = "8d037868f6778a9b92fc22c8a3157eb7dbc6b82781437eb67098293059464a63"
SPARSE = "d9ec90c5eab4deef5d21dee2d4e8f94c5d5a09e5d8f226e469093c9676fc4202"
SPARSE_LEDGER = "48ded0fc2551975f35a6735c79fdd9c079f6b73fe91f98af7e30adfb4cb8fe2c"
FIRST, LAST = 252, 316
PRODUCERS = {"gates_open", "GatesAreOpen", "gate_blocker_removal"}
TALENT_MEMBERS = {f"Base.StormData\\GameData\\{name}.xml" for name in
                  ("AbilData", "BehaviorData", "ButtonData", "EffectData", "HeroData", "TalentData", "ValidatorData")}
STRINGS = {"enUS.StormData\\LocalizedData\\GameStrings.txt", "plPL.StormData\\LocalizedData\\GameStrings.txt"}


def members(path):
    with closing(MPQArchive(path)) as archive:
        return {n: read_member(archive, n) for n in read_member(archive, "(listfile)").decode().splitlines()}


def keyed(raw):
    out = {}
    for node in ET.fromstring(raw):
        node.tail = None
        key = (node.tag, node.get("id"))
        require(key not in out, "Duplicate catalog record")
        out[key] = ET.tostring(node)
    return out


def append_only_difference(parent, candidate):
    """Every difference must be an appended talent-catalog record or appended localized text."""
    old, new = members(parent), members(candidate)
    require(old.keys() <= new.keys(), "Candidate removed a member")
    changed = sorted(n for n in new if old.get(n) != new[n])
    added_records = 0
    for name in changed:
        if name in STRINGS:
            require(name in old and new[name].startswith(old[name]), "Localized text is not appended")
            continue
        require(name in TALENT_MEMBERS, "Non-talent member differs: " + name)
        before = keyed(old[name]) if name in old else {}
        after = keyed(new[name])
        require(all(after.get(k) == v for k, v in before.items()), "Existing catalog record changed in " + name)
        added_records += len(after.keys() - before.keys())
    return dict(changed_members=changed, appended_records=added_records, unchanged_members=len(new) - len(changed))


def source_agrees(source_event, target_event):
    """The only target difference admitted is the documented zero killer player for gate blockers."""
    s = {k: v for k, v in source_event.items() if k not in ("_bits", "_event")}
    t = {k: v for k, v in target_event.items() if k != "_event"}
    if s["_eventid"] == 2:
        require(s["m_killerPlayerId"] is None and t["m_killerPlayerId"] == 0, "Unexpected blocker killer fields")
        s = {**s, "m_killerPlayerId": 0}
    return s == t


def generate(source, prefix, sparse_dir, merc, candidate, output, first=FIRST, last=LAST):
    require(not output.exists(), "A fresh output path is required")
    pinned(merc, MERC)
    pinned(candidate, CANDIDATE)
    maps = append_only_difference(merc, candidate)
    target = target_protocol()
    before = pinned(prefix, PREFIX)
    previous = frames(before, target)
    sparse = pinned(sparse_dir / "TEN.tracker.sparse.bin", SPARSE)
    ledger = json.loads(pinned(sparse_dir / "tracker-ordinals.json", SPARSE_LEDGER))
    rows = {r["source_ordinal"]: r for r in ledger}
    require(all(o in rows for o in range(first, last + 1)), "Block is not covered by the sparse fragment")
    targets = [rows[o]["target_ordinal"] for o in range(first, last + 1)]
    require(targets == list(range(targets[0], targets[0] + len(targets))) and
            {rows[o]["producer"] for o in range(first, last + 1)} <= PRODUCERS, "Block is not one contiguous admitted group")
    decoded = frames(sparse, target)
    block = [decoded[t] for t in targets]
    _, _, data, original = load_case(source, SOURCE, 41810)
    require(source_agrees(original[first - 1], previous[-1][0]), "Prefix does not end at the source ordinal before the block")
    for ordinal, (event, *_ ) in zip(range(first, last + 1), block):
        require(source_agrees(original[ordinal], event), f"Target frame differs from source ordinal {ordinal}")
    start = previous[-1][0]["_gameloop"]
    require(block[0][0]["_gameloop"] >= start, "Block precedes the prefix clock")
    shifted = [{**e, "_gameloop": e["_gameloop"] - start} for e, *_ in block]
    result = before + encode_tracker_events(shifted, target)
    joined = frames(result, target)
    require(len(joined) == len(previous) + len(block) and [e for e, *_ in joined[len(previous):]] == [e for e, *_ in block] and
            encode_tracker_events([e for e, *_ in joined], target) == result, "Joined prefix does not round-trip")
    for (_, _, offset, size), (_, _, s_off, s_size) in zip(joined[len(previous) + 1:], block[1:]):
        require(result[offset:offset + size] == sparse[s_off:s_off + s_size], "Physical frame bytes differ")
    following = original[last + 1]
    with output.open("xb") as stream:
        stream.write(result)
    return dict(parent_prefix_sha256=PREFIX, sparse_sha256=SPARSE, sparse_ledger_sha256=SPARSE_LEDGER,
                sparse_map_sha256=MERC, candidate_sha256=CANDIDATE, map_difference=maps,
                source_ordinals=[first, last], target_sparse_ordinals=[targets[0], targets[-1]],
                producers=sorted({rows[o]["producer"] for o in range(first, last + 1)}), joined_frames=len(block),
                loop=sorted({e["_gameloop"] for e, *_ in block}), frames=len(joined), bytes=len(result), sha256=digest(result),
                byte_identical_frames_after_first=len(block) - 1, next_source_ordinal=last + 1,
                next_loop=following["_gameloop"], next_source_event=(following.get("m_eventName") or b"").decode() or following["_eventid"],
                killer_player_zero_for_omitted_source_value=sum(1 for e, *_ in block if e["_eventid"] == 2),
                target_simulation_verified=False, verified_target_syncs=0)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    for name in ("source", "prefix", "sparse_dir", "merc", "candidate", "output"):
        cli.add_argument(name, type=Path)
    print(json.dumps(generate(**vars(cli.parse_args())), indent=2))
