"""Combine original-layout camera references with qualified primary hero references."""

import argparse
from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from dragonshire_packages import historical_package_digest
from hero_camera_lifetimes import analyze, FIELD, reference_timers
from predict_camp_captures import SOURCE
from smartcam_startup import project
from smartcam_tags import RECORD


def generate(source, original_map, historical_map, references):
    package = historical_package_digest(historical_map)
    base = project(source, original_map, historical_map)
    timers, _ = reference_timers(references)
    hero, sparse = analyze(source, SOURCE, 41810, timers)
    if base["fields"] != hero["total_camera_fields"] or base["fields"] % 2:
        raise ValueError("Camera member lengths disagree")
    rows = base["fields"] // 2
    fields = [(r["member_byte_offset"], r["target_packed_value"]) for r in base["projections"]]
    fields.extend(FIELD.iter_unpack(sparse))
    locations = set()
    known = Counter()
    for offset, _ in fields:
        ordinal, pos = divmod(offset, RECORD.size)
        if ordinal >= rows or pos not in (5, 9) or offset in locations:
            raise ValueError("Invalid or overlapping camera field")
        locations.add(offset)
        known[ordinal] += 1
    output = b"".join(FIELD.pack(*field) for field in sorted(fields))
    counts = Counter(known[i] for i in range(rows))
    return output, dict(source_sha256=SOURCE, package_sha256=package, rows=rows,
                        map_fields=len(base["projections"]), hero_fields=hero["qualified_primary_fields"],
                        emitted_fields=len(fields), missing_fields=2 * rows - len(fields),
                        complete_rows=counts[2], one_known_endpoint=counts[1], neither_known=counts[0],
                        sparse_bytes=len(output), sparse_sha256=sha256(output).hexdigest(),
                        destination_simulation_verified=False)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "original-map", "historical-map", "output"):
        cli.add_argument("--" + name, required=True, type=Path)
    cli.add_argument("--reference", nargs=2, action="append", required=True, metavar=("REPLAY", "SHA256"))
    args = cli.parse_args()
    raw, report = generate(args.source, args.original_map, args.historical_map,
                           [(Path(p), h) for p, h in args.reference])
    with TemporaryDirectory(dir=args.output.parent) as tmp:
        staged = Path(tmp) / "fields.bin"
        staged.write_bytes(raw)
        os.link(staged, args.output)
    print(json.dumps(report, indent=2))
