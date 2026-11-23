"""Assemble the original TEN game inputs through loop 64 in the target protocol."""

import argparse
from collections import Counter, deque
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from encoders import encode_game_events
from first_point_commands import analyze as point_commands
from mpq_reader import MPQArchive
from predict_camp_captures import SOURCE
from protocol_loader import load_protocol
from smartcam_tags import SRC_SCHEMA, DST_SCHEMA

LOADING, OPTIONS, SOUNDS = 5, 7, 56
SUPPORT = {LOADING, OPTIONS, SOUNDS}
SELECTION_DIGEST = "b1dc360f1539f5ac7800730f34f410f5d9f7bb4f3f61eafacf9d9b675f67d90b"


def support_event(event, build):
    if event["_eventid"] == OPTIONS:
        if (event["m_buildNum"], event["m_baseBuildNum"]) != (build, build):
            raise ValueError("Options advertise an unexpected source build")
        return {**event, "m_buildNum": 98348, "m_baseBuildNum": 98348}
    return event


def game(path, digest, build):
    if sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("Unexpected replay")
    p = load_protocol(41810 if build == 41810 else 96477)
    if p.recovery_schema_sha256 != {41810:SRC_SCHEMA,98348:DST_SCHEMA}[build]:
        raise ValueError("Unexpected game protocol")
    with closing(MPQArchive(path)) as a:
        h = p.decode_replay_header(a.header["user_data_header"]["content"])
        if (h["m_version"]["m_build"], h["m_version"]["m_baseBuild"], h["m_dataBuildNum"]) != (build,) * 3:
            raise ValueError("Unexpected native build")
        return p, a.read_file("replay.game.events")


def opening(raw, p):
    offset = previous = 0
    for e in p.decode_replay_game_events(raw):
        tick = e["_gameloop"]
        if tick > 64:
            return
        size, rem = divmod(e["_bits"], 8)
        if rem or not size:
            raise ValueError("Unaligned or empty input")
        yield e, previous, raw[offset:offset+size]
        previous, offset = tick, offset + size
    raise ValueError("Physical game stream ended before the first sync boundary")


def sound_key(event):
    descriptor = event["m_syncInfo"]
    return tuple(descriptor["m_soundHash"]), tuple(descriptor["m_length"])


def control(path, digest, original_sound):
    p, raw = game(path, digest, 98348)
    counts = Counter()
    shared_sound = 0
    for e, prev, frame in opening(raw, p):
        kind = e["_eventid"]
        if kind not in SUPPORT:
            continue
        row = support_event(e, 98348)
        if encode_game_events([{**row, "_gameloop":row["_gameloop"]-prev}], p) != frame:
            raise ValueError("Native input bytes differ")
        counts[kind] += 1
        if kind == SOUNDS and sound_key(row) == original_sound:
            shared_sound += 1
    return dict(replay_sha256=digest, support_frames=dict(counts), sound_descriptors_matching_ten=shared_sound)


def generate(source, selections, references):
    old, raw = game(source, SOURCE, 41810)
    dst = load_protocol(96477)
    original = list(opening(raw, old))
    if encode_game_events([e for e,_,_ in original], old) != b"".join(f for _,_,f in original):
        raise ValueError("Original game input prefix differs")
    sound, = {sound_key(e) for e,_,_ in original if e["_eventid"] == SOUNDS}
    reference_rows = [control(path, digest, sound) for digest,path in sorted(references.items())]
    if len(reference_rows) < 2 or sum(r["sound_descriptors_matching_ten"] > 0 for r in reference_rows) < 2:
        raise ValueError("Insufficient independent evidence for the original sound definitions")
    if sha256(selections).hexdigest() != SELECTION_DIGEST:
        raise ValueError("Unrecognized grounded hero selection stream")
    commands, _ = point_commands(source, SOURCE, 41810, 64)
    streams = {28: deque(dst.decode_replay_game_events(selections)), 27: deque(dst.decode_replay_game_events(commands))}
    generated = []
    for e, _, _ in original:
        kind = e["_eventid"]
        if kind in SUPPORT:
            row = support_event(e, 41810)
        else:
            key = 27 if kind == 104 else kind
            if key not in streams or not streams[key]:
                raise ValueError("Source input lacks a target prediction")
            row = streams[key].popleft()
            if (row["_eventid"], row["_gameloop"], row["_userid"]) != (kind, e["_gameloop"], e["_userid"]):
                raise ValueError("Input prediction belongs to a different command, loop or user")
        generated.append(row)
    if any(streams.values()):
        raise ValueError("Unclaimed predictions")
    payload = encode_game_events(generated, dst)
    decoded = list(dst.decode_replay_game_events(payload))
    def values(rows):
        return [{k:v for k,v in e.items() if k != "_bits"} for e in rows]
    if (values(generated) != values(decoded) or sum(e["_bits"] for e in decoded) != len(payload)*8
            or len(decoded) != 30 or decoded[-1]["_gameloop"] != 64):
        raise ValueError("Target game input prefix did not reproduce")
    return payload, dict(source_sha256=SOURCE, target_build=98348, records=len(decoded), bytes=len(payload),
                         sha256=sha256(payload).hexdigest(), counts=dict(Counter(e["_eventid"] for e in decoded)),
                         source_sync_options_preserved=True, checksum_value_verified=False,
                         references=reference_rows)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("source", type=Path)
    cli.add_argument("selections", type=Path)
    cli.add_argument("--native-case", nargs=2, action="append", required=True, metavar=("SHA256","REPLAY"))
    cli.add_argument("--private-output", type=Path)
    a = cli.parse_args()
    payload, result = generate(a.source,a.selections.read_bytes(),{h:Path(p) for h,p in a.native_case})
    if a.private_output:
        with a.private_output.open("xb") as f:
            f.write(payload)
    print(json.dumps(result, indent=2))
