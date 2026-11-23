"""Read back every stored 72-bit slice with the independently named protocol codec."""

import argparse
from collections import Counter
import csv
from hashlib import sha256
import json
from pathlib import Path

from protocol_loader import load_protocol
from encoders import BitPackedEncoder
from decoders import BitPackedDecoder
from snapshot_wire import fragment


def verify(directory):
    proto = load_protocol(96477)
    if proto.recovery_schema_sha256 != "e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84":
        raise ValueError("Named projection profile differs")
    fields = lambda tid: {name: child for name, child, _ in proto.typeinfos[tid][1][0]}
    target_branch = proto.typeinfos[fields(proto.game_event_types[27][0])["m_data"]][1][1][2]
    update_target = fields(proto.game_event_types[105][0])["m_target"]
    if target_branch != ("TargetUnit", update_target):
        raise ValueError("Named command target wrappers differ")
    tid = fields(update_target)["m_snapshotPoint"]
    raw = (directory / "historical-98348-snapshot-points.bin").read_bytes()
    index = (directory / "historical-98348-snapshot-index.tsv").read_bytes()
    summary = json.loads((directory / "source-wire-summary.json").read_bytes())
    if (
        sha256(raw).hexdigest() != summary["binary_sha256"]
        or sha256(index).hexdigest() != summary["index_sha256"]
    ):
        raise ValueError("Artifact or index digest changed")
    counts = Counter()
    previous = -1
    for i, row in enumerate(csv.DictReader(index.decode("ascii").splitlines(), delimiter="\t")):
        ordinal, offset, bits = (
            int(row[k]) for k in ("game_ordinal", "binary_byte_offset", "subrecord_bits")
        )
        if ordinal <= previous or offset != i * 72 or bits != 72:
            raise ValueError("Inconsistent index")
        previous = ordinal
        xyz = {k: int(row[k]) for k in ("x", "y", "z")}
        for phase in range(8):
            block = raw[offset + phase * 9 : offset + phase * 9 + 9]
            writer = BitPackedEncoder(proto.typeinfos)
            writer._buffer.write_bits((1 << phase) - 1, phase)
            writer.instance(tid, xyz)
            if block != fragment(writer.getvalue(), phase, 72):
                raise ValueError((ordinal, phase, "independent encoded bytes differ"))
            # Independently pack a nonzero prefix, the artifact and a suffix. Neither
            # neighboring fragment is part of the 72-bit subrecord.
            prefix = (1 << phase) - 1
            suffix_width = (-phase) % 8
            suffix = (1 << suffix_width) - 1
            wrapped = prefix | (int.from_bytes(block, "little") << phase) | (suffix << (phase + 72))
            decoder = BitPackedDecoder(
                wrapped.to_bytes((phase + 72 + suffix_width) // 8, "little"), proto.typeinfos
            )
            if decoder._buffer.read_bits(phase) != prefix or decoder.instance(tid) != xyz:
                raise ValueError((ordinal, phase, "independent decoded point differs"))
            if (
                decoder.used_bits() != phase + 72
                or decoder._buffer.read_bits(suffix_width) != suffix
                or not decoder.done()
            ):
                raise ValueError((ordinal, phase, "neighboring bits changed"))
            counts[phase] += 1
    if set(counts.values()) != {2179} or len(raw) != 2179 * 72:
        raise ValueError("Phase coverage incomplete")
    return dict(
        named_profile_sha256=proto.recovery_schema_sha256,
        named_point_type=tid,
        verified_phase_variants=sum(counts.values()),
        verified_per_phase=dict(counts),
        nonzero_adjacent_bits_preserved=True,
        native_writer_matches_independent_encoder_and_decoder=True,
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("directory", type=Path, help="Output directory produced by snapshot_wire.py generate.")
    print(json.dumps(verify(cli.parse_args().directory), indent=2, sort_keys=True))
