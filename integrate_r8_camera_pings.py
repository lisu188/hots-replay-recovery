"""Put the recorded-tracker camera and ping corrections into a private copy of R8."""

import argparse
from contextlib import closing
import ctypes
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import native_game_events as native
from convert_historical_pings import (
    FIELDS, PING, generate_for_retained_tracker, native_frame, target_protocol,
)
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from portable_sync_98348 import decode_sync, encode_sync
from repair_startup import v4_profile
from runtime_catalog_probe import Storm
from smartcam_tags import generate_r8, R8, SOURCE

GAME = "replay.game.events"
CAMERA = "replay.smartcam.events"
SYNC = "replay.sync.events"
PING_STREAM = "7da30d2ca6ca4444b5c5fb976640697ff3b94872d41dfba7e9a6a039fedf3234"
CAMERA_STREAM = "c3dd2875353f18c2cf62ee2a79e1641eb6a800aba88a6b45bd50287884043f35"


def digest(raw):
    return sha256(raw).hexdigest()


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def patch_game(original, corrected_stream):
    protocol = target_protocol()
    pings = list(protocol.decode_replay_game_events(corrected_stream))
    require(len(pings) == 81 and all(e["_eventid"] == PING for e in pings), "Unexpected sparse stream")
    edited = bytearray(original)
    offset = previous = seen = changes = total = 0
    for e in protocol.decode_replay_game_events(original):
        require(e["_bits"] > 0 and e["_bits"] % 8 == 0, "Non-byte-aligned event")
        end = offset + e["_bits"] // 8
        loop = e["_gameloop"]
        if e["_eventid"] == PING:
            dst = pings[seen]
            require(all(e[k] == dst[k] for k in ("_gameloop", "_userid", *FIELDS)
                        if k != "m_unit"), "Ping sequence or field mismatch")
            delta = loop - previous
            old = native.encode_game_events([native_frame(e, e["m_unit"], delta)])
            require(old == original[offset:end], "Cannot reproduce original physical ping frame")
            if dst["m_unit"] != e["m_unit"]:
                new = native.encode_game_events([native_frame(e, dst["m_unit"], delta)])
                require(len(new) == len(old), "Ping frame length changed")
                edited[offset:end] = new
                changes += 1
            seen += 1
        offset, previous = end, loop
        total += 1
    require(offset == len(original) and seen == len(pings) and changes == 25,
            "Incomplete traversal or unexpected ping count")
    new_raw = bytes(edited)
    checked = 0
    for before, after in zip(protocol.decode_replay_game_events(original),
                             protocol.decode_replay_game_events(new_raw), strict=True):
        if before["_eventid"] == PING:
            before = {**before, "m_unit": pings[checked]["m_unit"]}
            checked += 1
        require(before == after, "Unexpected event, payload, position or length change")
    return new_raw, dict(full_game_events=total, ping_frames=checked, changed_ping_fields=changes,
                         length=len(new_raw), differing_bytes=sum(x != y for x, y in zip(original, new_raw)),
                         original=digest(original), corrected=digest(new_raw))


def inventory(path, storm):
    v4 = v4_profile(path)
    with closing(MPQArchive(path)) as arc:
        listed = read_member(arc, "(listfile)").decode("ascii").splitlines()
        names = listed + ["(listfile)", "(attributes)"]
        require(len(names) == len(set(names)) == 14, "Unexpected archive inventory")
        indices = {arc.get_hash_table_entry(n).block_table_index for n in names}
        require(indices == {i for i, b in enumerate(arc.block_table) if b.flags & 0x80000000}
                and len(indices) == len(names), "Unaccounted active block")
        members = {name: read_member(arc, name) for name in names}
        header = arc.header["user_data_header"]["content"]
    lib = storm.lib
    lib.SFileVerifyRawData.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p]
    lib.SFileVerifyRawData.restype = ctypes.c_int
    lib.SFileVerifyFile.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
    lib.SFileVerifyFile.restype = ctypes.c_uint32
    handle = storm.open(path)
    try:
        for name, data in members.items():
            require(storm.read(handle, name) == data, "Independent reader disagrees")
        tables = [lib.SFileVerifyRawData(handle, k, None) for k in range(1, 7)]
        flags = [lib.SFileVerifyFile(handle, n.encode("ascii"), 15) for n in names]
        require(not any(tables) and not any(f & 0x02AB for f in flags), "Archive integrity failure")
    finally:
        require(lib.SFileCloseArchive(handle), "Failed to close verification archive")
    return header, members, v4


def integrate(source, r8, output, stormlib=None):
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    baseline = r8.read_bytes()
    require(len(baseline) == 2438570 and digest(baseline) == R8, "Unexpected R8")
    require(source.stat().st_size == 635140 and digest(source.read_bytes()) == SOURCE, "Unexpected source")
    storm = Storm(stormlib)
    header, before, old_v4 = inventory(r8, storm)
    camera, camera_info = generate_r8(source, r8)
    pings, ping_info = generate_for_retained_tracker(source, r8)
    require(digest(camera) == CAMERA_STREAM and digest(pings) == PING_STREAM, "Sparse evidence mismatch")
    game, context = patch_game(before[GAME], pings)
    with closing(MPQArchive(source)) as arc:
        original_sync = read_member(arc, SYNC)
    records = decode_sync(original_sync)
    require(len(records) == 308 and encode_sync(records) == before[SYNC] == original_sync,
            "Original synchronization data differs")
    with TemporaryDirectory(dir=output.parent) as tmp:
        stage = Path(tmp) / "candidate.StormReplay"
        stage.write_bytes(baseline)
        storm.replace(stage, {GAME: game, CAMERA: camera})
        header2, after, new_v4 = inventory(stage, storm)
        require(header == header2 and before.keys() == after.keys(), "Changed header or member list")
        changed = {n for n in before if before[n] != after[n]}
        require(changed == {GAME, CAMERA, "(attributes)"}, "Unexpected set of member differences")
        require(after[GAME] == game and after[CAMERA] == camera and decode_sync(after[SYNC]) == records,
                "Written streams differ from the verified data")
        require(old_v4["raw_chunk_size"] == new_v4["raw_chunk_size"], "Archive layout changed")
        require(digest(r8.read_bytes()) == R8 and digest(source.read_bytes()) == SOURCE, "Inputs changed")
        image = stage.read_bytes()
        os.link(stage, output)
    return dict(format="partial-r8-recorded-tracker-camera-ping-integration-v1", source=SOURCE,
                parent=R8, output_sha256=digest(image), output_bytes=len(image),
                retained_header_build=98285, tracker_sha256=ping_info["tracker_sha256"],
                sync_records=len(records), sync_sha256=digest(original_sync),
                camera_rows=camera_info["fields"] // 2, camera_sha256=digest(camera),
                sparse_ping_sha256=digest(pings), game=context, changed_members=sorted(changed),
                unchanged_members=len(before)-len(changed), independent_readers_agree=True,
                all_available_archive_checksums_verified=True, original_and_r8_preserved=True,
                destination_simulation_allocation_verified=False, native_playback_verified=False)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "r8", "output"):
        cli.add_argument("--" + name, required=True, type=Path)
    cli.add_argument("--stormlib")
    args = cli.parse_args()
    print(json.dumps(integrate(args.source, args.r8, args.output, args.stormlib), indent=2))
