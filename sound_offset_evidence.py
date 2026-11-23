"""Compare recorded offset handles in pinned replay openings, retaining physical frame deltas."""

import argparse
from collections import defaultdict
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from encoders import encode_game_events
from first_sync_game import game, sound_key
from mpq_reader import MPQArchive
from native_game_events import GameEvent, encode_game_events as encode_native, iter_game_events
from predict_camp_captures import SOURCE


STOCK = "f557190f8aaab160789272ce086b8b69d6a8037b152de150332603dae3dc098f"
END = 1024


def signature(value):
    return sha256(json.dumps(value, separators=(",", ":")).encode("ascii")).hexdigest()


def audit(path, digest, build):
    protocol, raw = game(path, digest, build)
    with closing(MPQArchive(path)) as archive:
        details = protocol.decode_replay_details(archive.read_file("replay.details"))
        map_hash = details["m_cacheHandles"][-1][8:].hex()
    physical = bytearray()
    native = []
    descriptors = []
    offsets = []
    position = previous = 0
    for e in protocol.decode_replay_game_events(raw):
        tick, eid, user = e["_gameloop"], e["_eventid"], e["_userid"]["m_userId"]
        if tick > END:
            break
        size, remainder = divmod(e["_bits"], 8)
        if remainder or not size:
            raise ValueError("Unaligned physical input")
        frame = raw[position:position + size]
        if eid == 56 and tick <= 64:
            descriptors.append((tick, user, signature(sound_key(e))))
        if eid == 46:
            word = e["m_sound"]
            if encode_game_events([{**e, "_gameloop":tick-previous}], protocol) != frame:
                raise ValueError("Official schema disagrees with physical offset frame")
            native.append(GameEvent(tick-previous, user, eid, (word,)))
            physical.extend(frame)
            offsets.append((tick, user, word, frame.hex()))
        position += size
        previous = tick
    else:
        raise ValueError("Replay ended inside observation window")
    if not offsets:
        raise ValueError("No offsets through observation window")
    if build == 98348:
        if encode_native(native) != physical or [x.event for x in iter_game_events(bytes(physical))] != native:
            raise ValueError("Pinned native schema disagrees with physical offsets")
    return dict(sha256=digest, build=build, map=map_hash, descriptors=descriptors, offsets=offsets)


def summarize(rows):
    ten, = [r for r in rows if r["sha256"] == SOURCE and r["build"] == 41810]
    targets = [r for r in rows if r["build"] == 98348]
    if len(rows) != len({r["sha256"] for r in rows}) or len(targets) < 2:
        raise ValueError("Distinct independent target replays required")
    first = ten["offsets"][0][2]
    def descriptor_set(r):
        return tuple(sorted({s for _,_,s in r["descriptors"]}))
    def first_group(rs):
        words = {r["offsets"][0][2] for r in rs}
        return dict(replays=len(rs), distinct_first_words=len(words), first_equal_ten=sum(r["offsets"][0][2]==first for r in rs),
                    ever_equal_ten_first=sum(any(w==first for _,_,w,_ in r["offsets"]) for r in rs),
                    physical_offsets=sum(len(r["offsets"]) for r in rs))
    def counterexamples(descriptor):
        groups = defaultdict(list)
        for r in targets:
            tick,user,word,_ = r["offsets"][0]
            groups[(r["map"], descriptor(r), tick, user)].append((r["sha256"], word))
        examples = []
        for (map_hash,ds,tick,user), members in sorted(groups.items()):
            if len({w for _,w in members}) < 2:
                continue
            samples = [members[0], next(m for m in members if m[1] != members[0][1])]
            examples.append(dict(map=map_hash, descriptors=ds, tick=tick, user=user, examples=samples))
        return examples
    return dict(end_loop_inclusive=END, source_first=ten["offsets"][0], source_second=ten["offsets"][1],
                native=first_group(targets), stock_dragon=first_group([r for r in targets if r["map"]==STOCK]),
                native_matching_ten_descriptor_set=first_group([r for r in targets if descriptor_set(r)==descriptor_set(ten)]),
                native_matching_ten_ordered_descriptors=first_group([r for r in targets if r["descriptors"]==ten["descriptors"]]),
                same_map_loop_user_and_descriptor_set=counterexamples(descriptor_set),
                same_map_loop_user_and_ordered_descriptors=counterexamples(lambda r: signature(r["descriptors"])),
                target_ten_frame_emitted=False,
                replays=[dict(sha256=r["sha256"], build=r["build"], map=r["map"], first=r["offsets"][0],
                              descriptors=descriptor_set(r), ordered_descriptor_digest=signature(r["descriptors"]),
                              offsets=len(r["offsets"])) for r in sorted(rows,key=lambda x:(x["build"],x["sha256"]))])


if __name__ == "__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--case", nargs=3, action="append", required=True, metavar=("BUILD","SHA256","REPLAY"))
    args=cli.parse_args()
    print(json.dumps(summarize([audit(Path(p),h,int(b)) for b,h,p in args.case]), indent=2))
