"""Encode the 98348 command snapshot point at each possible start-bit phase."""

import argparse
from collections import Counter
from contextlib import closing
import csv
from functools import lru_cache
from hashlib import sha256
import io
import json
from pathlib import Path

from command_authored_xy import analyze
from historical_layout_xy import profile, HISTORICAL_PACKAGE, MAPS, SOURCE
from map_startup_identity import SCHEMAS
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
import native_game_events as native
from protocol_loader import load_protocol
from terrain_snapshot_height import SyncTerrain


def fragment(raw, start, size):
    """Copy physical bits in little-position-within-byte order into a tight slice."""
    if (
        type(start) is not int
        or type(size) is not int
        or min(start, size) < 0
        or start + size > len(raw) * 8
    ):
        raise ValueError("Invalid physical bit span")
    offset = start % 8
    block = raw[start // 8 : (start + size + 7) // 8]
    if len(block) * 8 < offset + size:
        raise ValueError("Truncated physical bit span")
    return ((int.from_bytes(block, "little") >> offset) & ((1 << size) - 1)).to_bytes(
        (size + 7) // 8, "little"
    )


@lru_cache(maxsize=1)
def point_graph():
    records, roots = native._profile(native.PROFILE)
    if {27, 105} - roots.keys():
        raise ValueError("Missing native command root")
    # Follow the SCmdEvent TargetUnit union and SCmdUpdateTargetUnitEvent direct field.
    cmd = records[roots[27]]["field_types"][2]
    choice = records[records[cmd]["element_type"]]
    unit_branch = choice["field_types"][choice["tags"].index(2)]
    target = records[unit_branch]["element_type"]
    update_field = records[roots[105]]["field_types"][1]
    if records[update_field]["element_type"] != target:
        raise ValueError("Different target records for the two command events")
    point_field = records[target]["field_types"][6]
    point = records[point_field]["element_type"]
    bounds = []
    for child in records[point]["field_types"]:
        while records[child]["kind"] == "USER":
            child = records[child]["element_type"]
        bounds.append(tuple(records[child]["bounds"][k] for k in ("bits", "min", "max")))
    if (point_field, point) != (152, 157) or bounds != [
        (20, 0, 1048575),
        (20, 0, 1048575),
        (32, -2147483648, 2147483647),
    ]:
        raise ValueError("Unexpected native point definition")
    return records, roots, point_field, point


@lru_cache(maxsize=8192, typed=True)
def encode_point(x, y, z, phase):
    if type(phase) is not int or phase not in range(8):
        raise ValueError("Start-bit phase must be 0 through 7")
    records, _, _, point = point_graph()
    writer = native._Writer(records)
    writer.bits(0, phase)
    writer.write((x, y, z), point)
    if writer.bit != phase + 72:
        raise ValueError("Unexpected native point width")
    return fragment(writer.raw, phase, 72)


def terrain(path):
    with closing(MPQArchive(path)) as archive:
        return SyncTerrain(read_member(archive, "t3SyncHeightMap"))


def source_artifact(original, package, replay):
    source = profile(original, package, replay, rows=True)
    if source["package_sha256"] != HISTORICAL_PACKAGE:
        raise ValueError("Unexpected historical talent map")
    plane = terrain(package)
    with closing(MPQArchive(replay)) as arc:
        raw = arc.read_file("replay.game.events")
    events = load_protocol(41810).decode_replay_game_events(raw)
    positions = {r[0]: r for r in source["rows"]}
    index = []
    payload = bytearray()
    for ordinal, e in enumerate(events):
        if ordinal not in positions:
            continue
        _, loop, ident, x, y = positions[ordinal]
        if loop != e["_gameloop"] or e["_eventid"] not in (27, 105):
            raise ValueError("Source ordinal does not have the expected command shape")
        z, r = plane.sample(x, y)
        if r:
            raise ValueError("Inexact terrain sample")
        index.append([ordinal, loop, ident, e["_eventid"], x, y, z, len(payload), 72])
        for phase in range(8):
            payload.extend(encode_point(x, y, z, phase))
    if len(index) != 2179 or len(payload) != len(index) * 8 * 9:
        raise ValueError("Source point inventory differs")
    return bytes(payload), index


class PointReader(native._Reader):
    """Capture only the snapshot field, excluding TargetPoint choices and command vector fields."""

    def read(self, type_id, depth=0):
        if type_id != 152:
            return super().read(type_id, depth)
        start = self.bit
        value = super().read(type_id, depth)
        self.spans.append((start, self.bit, value))
        return value


def target_control(map_path, replay, expected_digest):
    if sha256(map_path.read_bytes()).hexdigest() != MAPS[98348]:
        raise ValueError("Unexpected stock 98348 Dragon Shire map")
    if sha256(replay.read_bytes()).hexdigest() != expected_digest:
        raise ValueError("Unexpected genuine recording")
    info = analyze(map_path, replay, 98348, observations=True)
    if not info["full_game_byte_equal"] or info["counts"].get("mismatches"):
        raise ValueError("Unverified authored coordinate scope")
    positions = {r["ordinal"]: r for r in info["projected_rows"]}
    with closing(MPQArchive(replay)) as arc:
        raw = arc.read_file("replay.game.events")
    plane = terrain(map_path)
    records, roots, _, _ = point_graph()
    reader = PointReader(raw, records)
    official = load_protocol(SCHEMAS[98348])
    start = 0
    recovered = bytearray(raw)
    counts = Counter()
    phases = Counter()
    kinds = Counter()
    phase_event = Counter()
    examples = []
    event_count = 0
    for ordinal, e in enumerate(official.decode_replay_game_events(raw)):
        event_count += 1
        stop = start + e["_bits"]
        if ordinal in positions:
            row = positions[ordinal]
            x, y = row["xy"]
            z, r = plane.sample(x, y)
            if r:
                raise ValueError("Fractional final terrain sample")
            reader.bit = start
            reader.spans = []
            reader.read(50)
            reader.read(890)
            eid = reader.read(138)
            if eid not in (27, 105) or eid != e["_eventid"] or row["loop"] != e["_gameloop"]:
                raise ValueError("Native and independently framed event identities differ")
            reader.read(roots[eid])
            reader.align()
            if reader.bit != stop or len(reader.spans) != 1:
                raise ValueError("Event boundary or snapshot field count differs")
            begin, end, observed = reader.spans[0]
            phase = begin % 8
            wire = encode_point(x, y, z, phase)
            if end - begin != 72 or observed != (x, y, z) or fragment(raw, begin, 72) != wire:
                raise ValueError("Native encoding differs from genuine point span")
            # Patch only the recovered 72 bits into a separate copy. Preserve both neighboring bit fragments.
            if phase:
                size = 10
            else:
                size = 9
            offset = begin // 8
            prior = int.from_bytes(recovered[offset : offset + size], "little")
            mask = ((1 << 72) - 1) << phase
            updated = (prior & ~mask) | (int.from_bytes(wire, "little") << phase)
            recovered[offset : offset + size] = updated.to_bytes(size, "little")
            counts["matched"] += 1
            counts["naive_phase_zero_would_differ"] += encode_point(x, y, z, 0) != wire
            phases[phase] += 1
            kinds[eid] += 1
            if not phase_event[eid, phase]:
                examples.append(
                    dict(
                        ordinal=ordinal,
                        event_id=eid,
                        loop=e["_gameloop"],
                        start_bit=begin,
                        end_bit=end,
                        phase=phase,
                        xyz=[x, y, z],
                        wire_hex=wire.hex(),
                    )
                )
            phase_event[eid, phase] += 1
        start = stop
    if start != len(raw) * 8 or recovered != raw or counts["matched"] != len(positions):
        raise ValueError("Full-stream or snapshot count mismatch")
    return dict(
        replay_sha256=expected_digest,
        member_sha256=sha256(raw).hexdigest(),
        member_bytes=len(raw),
        upstream_framing_schema_sha256=official.recovery_schema_sha256,
        native_schema_sha256=native.SCHEMA_SHA256,
        all_framed_events=event_count,
        counts=dict(counts),
        by_phase=dict(sorted(phases.items())),
        by_event_id=dict(sorted(kinds.items())),
        full_game_equal_after_generated_span_write=True,
        observed_cursor_examples=examples,
    )


def generate(original, package, replay, destination):
    """Write the private binary, per-command index and digest receipt to a new directory."""
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("A new output directory is required")
    raw, index = source_artifact(original, package, replay)
    table = io.StringIO()
    writer = csv.writer(table, delimiter="\t", lineterminator="\n")
    writer.writerow(
        (
            "game_ordinal",
            "loop",
            "object_id",
            "event_id",
            "x",
            "y",
            "z",
            "binary_byte_offset",
            "subrecord_bits",
        )
    )
    writer.writerows(index)
    index_blob = table.getvalue().encode("ascii")
    summary = dict(
        format="target-98348-command-snapshot-point-phase-slices-v1",
        source_replay=SOURCE,
        historical_map_sha256=HISTORICAL_PACKAGE,
        field_bits_per_ordinal=72,
        phases_per_point=8,
        bytes_per_phase_variant=9,
        point_count=len(index),
        artifact_bytes=len(raw),
        binary_sha256=sha256(raw).hexdigest(),
        index_sha256=sha256(index_blob).hexdigest(),
        breakdown=dict(sorted(Counter(row[3] for row in index).items())),
        full_event_emitted=False,
        storage="For phase p, read 9 packed physical bytes at binary_byte_offset+9*p. "
        "Copy physical bits least significant bit first into a destination cursor whose modulus is p.",
    )
    files = (
        ("historical-98348-snapshot-points.bin", raw),
        ("historical-98348-snapshot-index.tsv", index_blob),
        ("source-wire-summary.json", (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode("ascii")),
    )
    destination.mkdir()
    created = []
    try:
        for name, body in files:
            path = destination / name
            with path.open("xb") as output:
                created.append(path)
                output.write(body)
    except OSError:
        for path in created:
            path.unlink(missing_ok=True)
        destination.rmdir()
        raise
    return summary


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    sub = cli.add_subparsers(dest="action", required=True)
    make = sub.add_parser(
        "generate", help="Generate source-derived snapshot subrecords using the target wire format."
    )
    for name in ("original-map", "historical-map", "source-replay", "output-dir"):
        make.add_argument("--" + name, type=Path, required=True)
    check = sub.add_parser(
        "verify-control", help="Check generated point bits against one genuine build-98348 replay."
    )
    check.add_argument("--target-map", type=Path, required=True)
    check.add_argument("--target-replay", type=Path, required=True)
    check.add_argument("--replay-sha256", required=True)
    args = cli.parse_args()
    if args.action == "generate":
        result = generate(args.original_map, args.historical_map, args.source_replay, args.output_dir)
    else:
        result = target_control(args.target_map, args.target_replay, args.replay_sha256)
        del result["observed_cursor_examples"]
    print(json.dumps(result, indent=2, sort_keys=True))
