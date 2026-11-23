"""Check standalone 98348 event payloads independently of dispatch admission."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import struct
from zlib import crc32

from encoders import BitPackedEncoder
import first_sync_game
from first_sync_game import game, opening
from native_game_events import PROFILE, _profile, _Writer, iter_game_events
from opening_birth_wire import target_protocol


def components(raw):
    """Read the physical user, absolute loop and CRC of each standalone payload."""
    protocol = target_protocol()
    records, roots = _profile(PROFILE)
    loop = 0
    for named, frame in zip(protocol.decode_replay_game_events(raw), iter_game_events(raw), strict=True):
        event = frame.event
        writer = _Writer(records)
        writer.write(event.payload, roots[event.event_id])
        writer.align()
        wire = bytes(writer.raw)
        encoder = BitPackedEncoder(protocol.typeinfos)
        type_id, _ = protocol.game_event_types[named["_eventid"]]
        encoder.instance(type_id, named)
        loop += event.delta
        if ((event.event_id, event.user_id, loop) !=
                (named["_eventid"], named["_userid"]["m_userId"], named["_gameloop"])
                or wire != encoder.getvalue()):
            raise ValueError("Standalone payload mismatch")
        yield event.event_id, event.user_id, loop, len(wire), crc32(wire)


def advance(previous, loop, mapped, payload_crc, table):
    """Update the raw dispatch CRC for one admitted event, in native input order."""
    packed = struct.pack("<IBI", loop, mapped, payload_crc)
    def dword(state, value):
        x = state ^ value
        return (table[768 + (x & 255)] ^ table[512 + ((x >> 8) & 255)]
                ^ table[256 + ((x >> 16) & 255)] ^ table[x >> 24])
    state = dword(previous, loop)
    state = table[(state ^ mapped) & 255] ^ (state >> 8)
    state = dword(state, payload_crc)
    if state != crc32(packed, previous ^ 0xffffffff) ^ 0xffffffff:
        raise ValueError("Native tables disagree with the nine-byte CRC recurrence")
    return state


def check(raw, table):
    counts = Counter()
    lengths = []
    digest = sha256()
    for kind, _, _, length, payload_crc in components(raw):
        # Exercise the nine-byte projection with synthetic operands only.
        # Neither dispatcher admission nor the native mapped user is assumed.
        for previous, word, mapped in [(0xffffffff, 0, 16), (0x456789ab, 0xfedcba98, 3)]:
            advance(previous, word, mapped, payload_crc, table)
        digest.update(struct.pack("<III", kind, length, payload_crc))
        counts[kind] += 1
        lengths.append(length)
    return dict(events=sum(counts.values()), types=dict(sorted(counts.items())), standalone_bytes=sum(lengths),
                maximum_bytes=max(lengths, default=0), payload_sequence_sha256=digest.hexdigest())


def native_tables(binary):
    if (len(binary), sha256(binary).hexdigest()) != (53573840, "efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9"):
        raise ValueError("Unexpected target executable")
    pe = struct.unpack_from("<I", binary, 60)[0]
    sections = pe + 24 + struct.unpack_from("<H", binary, pe + 20)[0]
    for i in range(struct.unpack_from("<H", binary, pe + 6)[0]):
        va, size, pos = struct.unpack_from("<III", binary, sections + 40 * i + 12)
        if va <= 0x2648210 and 0x2648210 + 4096 <= va + size:
            return struct.unpack_from("<1024I", binary, pos + 0x2648210 - va)
    raise ValueError("CRC table absent")


def controls(paths, table):
    evidence = Path(first_sync_game.__file__).resolve().parent / "observations" / "first-sync-game.json"
    expected = {r["replay_sha256"] for r in json.loads(evidence.read_bytes())["references"]}
    if len(expected) != 24 or set(paths) != expected:
        raise ValueError("Expected exactly the 24 previously pinned controls")
    _, roots = _profile(PROFILE)
    totals, outside = Counter(), Counter()
    size = largest = 0
    for digest, path in sorted(paths.items()):
        protocol, raw = game(Path(path), digest, 98348)
        frames = []
        for event, _, wire in opening(raw, protocol):
            if event["_eventid"] in roots:
                frames.append(wire)
            else:
                outside[event["_eventid"]] += 1
        row = check(b"".join(frames), table)
        totals.update(row["types"])
        size += row["standalone_bytes"]
        largest = max(largest, row["maximum_bytes"])
    if (totals.total(), size, largest, outside) != (1507, 19243, 106, {58: 8}):
        raise ValueError("Control cohort regression")
    return dict(controls=len(paths), events=totals.total(), standalone_bytes=size, maximum_bytes=largest,
                types=dict(sorted(totals.items())), outside_profile=dict(sorted(outside.items())))


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("pe", type=Path)
    cli.add_argument("prefix", type=Path)
    cli.add_argument("--controls", type=Path, help="Private JSON object mapping pinned replay hashes to local paths")
    args = cli.parse_args()
    raw = args.prefix.read_bytes()
    if sha256(raw).hexdigest() != "68def0020f334b543ed6e1be6aed1fd57bfbdc284c933372298a3e96cc69efc5":
        raise ValueError("Unexpected TEN input prefix")
    tables = native_tables(args.pe.read_bytes())
    result = check(raw, tables)
    if (result["events"], result["standalone_bytes"], result["payload_sequence_sha256"]) != (
        30, 593, "3fbe83b84771036331379ea05a3dc228d3d57939297484fae7d5aaba2a1c9330"
    ):
        raise ValueError("TEN standalone payload regression")
    if args.controls:
        result["cohort"] = controls(json.loads(args.controls.read_bytes()), tables)
    print(json.dumps(result, indent=2))
