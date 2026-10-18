"""One-PE-read independent metadata/type-graph conformance review.

No upstream/game code is loaded. The reviewed Python decoder is executed only
after exact source capture/hash verification; all PE processing is ordinary bytes.
"""
import collections
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys
import types
import unittest

HERE = Path(__file__).resolve().parent
TARGET = HERE.parent / "native-embedded-schema-98348"
IMAGE = Path("C:/Program Files (x86)/Heroes of the Storm/Versions/Base98348/HeroesOfTheStorm_x64.exe")
PE_SIZE = 53573840
PE_SHA = "efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9"
START, END = 43169040, 43560673
BLOB_SHA = "ce3b1f764575730f2c08c89eed73ea843ec4cc702b727c9577ca071ce610e741"
REPORT_NAME = "native-BSN-metadata-98348-v2.json"
sha = lambda data: hashlib.sha256(data).hexdigest()

def require(value, message):
    if not value:
        raise ValueError(message)

def independently_parse(blob):
    """Separate cursor/record implementation from the pinned source grammar."""
    version, unknown, total, tsize, dsize = struct.unpack_from(">5I", blob)
    require((version, unknown, total, tsize, dsize) == (7, 0, 8330, 67244, 257729), "framing differs")
    first = 20 + 4 * total
    tend = first + tsize
    dstart = tend + 4 * total
    require(dstart + dsize == len(blob), "extent differs")
    offsets = struct.unpack_from(">" + str(total) + "I", blob, 20)
    dumps = struct.unpack_from(">" + str(total) + "I", blob, tend)
    require(offsets[0] == first and list(offsets) == sorted(set(offsets)), "type ordering")
    require(all(first <= p < tend for p in offsets), "type sections")
    require(all(not p or dstart <= p < len(blob) for p in dumps), "dump sections")
    records, materialized = [], 0
    for i, (a, b) in enumerate(zip(offsets, offsets[1:] + (tend,))):
        cursor = a
        def get(n, signed=False):
            nonlocal cursor
            require(0 <= n <= b - cursor, "record truncated")
            result = int.from_bytes(blob[cursor:cursor + n], "big", signed=signed)
            cursor += n
            return result
        def number(t):
            require(0 <= t <= 7, "integer width")
            return get(1 << (t // 2), not bool(t & 1))
        def bounds(fixed=False):
            t = get(1)
            flags = 0 if fixed else get(1)
            lo = number(t)
            hi = lo if fixed else number(t)
            return {"int_type": t, "variable": bool(flags & 128), "bits": flags & 127, "min": lo, "max": hi}
        header = get(1)
        kind = header & 63
        require(1 <= kind <= 16, "unknown kind")
        rec = {"id": i, "header": header, "offset": a, "bytes": b - a}
        if kind in (1, 3, 4):
            rec["bounds"] = bounds(bool(header & 128))
            if kind == 1:
                rec["element_type"] = get(4)
        elif kind in (2, 9, 15):
            rec["bounds"] = bounds()
        elif kind in (6, 7, 14):
            limits = rec["bounds"] = bounds()
            if header & 128:
                count = limits["max"] - limits["min"] + 1
            else:
                t = get(1)
                require(t <= 5, "count width")
                count = get(1 << (t // 2))
            materialized += count
            require(0 <= count <= 20000 and materialized <= 200000, "aggregate count")
            rec["count"] = count
            rec["tags"] = list(range(limits["min"], limits["max"] + 1)) if header & 128 else [number(limits["int_type"]) for _ in range(count)]
            if kind != 7:
                require(len(set(rec["tags"])) == count, "duplicate structure/choice tags")
            if kind in (6, 14):
                rec["field_types"] = [get(4) for _ in range(count)]
        elif kind in (11, 16):
            rec["element_type"] = get(4)
        if cursor != b:
            require(i == total - 1 and b - cursor <= 3 and blob[cursor:b] == b"\0" * (b - cursor), "record trailing data")
            rec["trailing_zero_alignment_bytes"] = b - cursor
        limits = rec.get("bounds")
        if limits and limits["min"] > limits["max"]:
            require(kind in (6, 7, 14) and header & 128 and limits["min"] == limits["max"] + 1, "reversed bounds")
        for child in rec.get("field_types", []) + ([rec["element_type"]] if "element_type" in rec else []):
            require(0 <= child < total, "child type ID")
        records.append(rec)
    name_sizes = [1 + (r.get("count", 0) if r["header"] & 63 in (6, 7, 14) else 0) for r in records]
    pool = max(p + 4 * n for p, n in zip(dumps, name_sizes) if p)
    require(dstart <= pool < len(blob) and (pool - dstart) % 4 == 0 and blob[-1] == 0, "name boundary")
    words = struct.unpack_from(">" + str((pool - dstart) // 4) + "I", blob, dstart)
    tokens = {pool + m.start() for m in re.finditer(rb"[^\x00]+", blob[pool:])}
    require(all(not p or p in tokens for p in words), "name token reference")
    def name(i, index):
        if not dumps[i]:
            return None
        p = dumps[i] + 4 * index
        require(dstart <= p and p + 4 <= pool, "dump record boundary")
        offset = struct.unpack_from(">I", blob, p)[0]
        if not offset:
            return None
        require(offset in tokens, "name token start")
        stop = blob.find(b"\0", offset, min(len(blob), offset + 513))
        require(offset < stop and all(32 <= c < 127 for c in blob[offset:stop]), "bounded name")
        return blob[offset:stop].decode("ascii")
    for i, rec in enumerate(records):
        rec["name"] = name(i, 0)
        if rec["header"] & 63 in (6, 7, 14):
            rec["field_names"] = [name(i, j + 1) for j in range(rec["count"])]
    return records, {"materialized_tags": materialized, "name_pool_offset": pool, "name_tokens": len(tokens),
                     "dump_words": len(words), "zero_dump_words": words.count(0), "name_reference_count": sum(name_sizes)}

def captured_module(name, path):
    raw = path.read_bytes()
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module, raw

def independent_negatives(decoder, fixture):
    """Small synthetic fixtures; never use real PE/player values as mutations."""
    passes = []
    def reject(label, raw):
        try:
            decoder.Protocol(raw)
        except decoder.MetadataError:
            passes.append(label)
            return
        raise ValueError("independent malformed fixture accepted: " + label)
    n = 32
    record = b"\x87\x01\x05\x00\x1f"
    tstart = 20 + 4 * n
    body = record * n
    dstart = tstart + len(body) + 4 * n
    pool = dstart + 4 * 33
    dump = struct.pack(">33I", *([pool] * 33)) + b"SyntheticEnum\0"
    dense = struct.pack(">5I", 7, 0, n, len(body), len(dump)) + struct.pack(">32I", *[tstart + len(record) * i for i in range(n)]) + body + struct.pack(">32I", *([dstart] * n)) + dump
    old_limit = decoder.MAX_FIELDS
    try:
        decoder.MAX_FIELDS = 1000
        reject("aggregate_dense_enums_with_shared_dump_records", dense)
    finally:
        decoder.MAX_FIELDS = old_limit
    base = decoder.Protocol(fixture())
    zero = bytearray(base.raw)
    zero[base.dump_offsets:base.dump_start] = b"\0" * (4 * base.count)
    reject("all_zero_dump_records_controlled_error", bytes(zero))
    for suffix, label in ((b"UNTERMINATED", "unreferenced_unterminated_name"), (b"\xff\0", "unreferenced_nonASCII_name")):
        changed = bytearray(base.raw + suffix)
        struct.pack_into(">I", changed, 16, base.dump_size + len(suffix))
        reject(label, bytes(changed))
    primitive = [b"\x10" + struct.pack(">I", 1), b"\x09\x05\xa0" + b"\0" * 4 + b"\xff" * 4,
                 None, b"\x05"]
    # Sparse enum aliases are legal; analogous duplicate Struct/Choice tags reject.
    duplicate = b"\x01\x02\x00\x03\x01\x02\x01\x01"
    primitive[2] = b"\x07" + duplicate
    enum = decoder.Protocol(fixture(primitive))
    require(enum.records[2]["tags"] == [1, 1], "enum aliases not preserved")
    passes.append("sparse_enum_aliases_preserved")
    for kind, label in ((6, "duplicate_choice_tags"), (14, "duplicate_struct_tags")):
        primitive[2] = bytes((kind,)) + duplicate + struct.pack(">II", 0, 3)
        reject(label, fixture(primitive))
    primitive[2] = b"\x8e\x01\x00\x01\x00"
    empty = decoder.Protocol(fixture(primitive))
    require(empty.records[2]["count"] == 0 and empty.records[2]["tags"] == [], "dense empty struct")
    passes.append("dense_empty_struct_min1_max0_preserved")
    invalid = bytearray(base.raw)
    invalid[base.type_offsets[0]] = 0
    reject("unknown_zero_type_kind", bytes(invalid))
    return passes

def review(expected_parser_sha, expected_inspector_sha, expected_test_sha, expected_report_sha):
    pins = {"parse_bsn_metadata.py": expected_parser_sha, "inspect_bsn_schema.py": expected_inspector_sha,
            "test_parse_bsn_metadata.py": expected_test_sha, REPORT_NAME: expected_report_sha}
    for name, expected in pins.items():
        require(sha((TARGET / name).read_bytes()) == expected, "frozen pin differs: " + name)
    decoder, source = captured_module("parse_bsn_metadata", TARGET / "parse_bsn_metadata.py")
    tests, test_source = captured_module("test_parse_bsn_metadata", TARGET / "test_parse_bsn_metadata.py")
    suite = unittest.defaultTestLoader.loadTestsFromModule(tests)
    result = unittest.TestResult()
    suite.run(result)
    require(result.wasSuccessful() and not result.skipped, "focused parser suite failed/skipped")
    extra_checks = independent_negatives(decoder, tests.capsule)
    require(not IMAGE.is_symlink(), "PE symlink")
    with IMAGE.open("rb") as stream:
        before = os.fstat(stream.fileno())
        require(before.st_size == PE_SIZE, "PE size differs")
        raw = stream.read(PE_SIZE + 1)
        after = os.fstat(stream.fileno())
    require(len(raw) == PE_SIZE and sha(raw) == PE_SHA, "whole PE pin differs")
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), "PE changed")
    blob = raw[START:END]
    require(sha(blob) == BLOB_SHA, "embedded blob pin differs")
    independent, stats = independently_parse(blob)
    protocol = decoder.Protocol(blob)
    require(len(protocol.records) == len(independent) == 8330, "record count differs")
    for own, record in zip(independent, protocol.records):
        for key, value in own.items():
            require(record.get(key) == value, "independent record mismatch: " + str(own["id"]) + "/" + key)
    require(protocol.name_start == stats["name_pool_offset"] and len(protocol.name_starts) == stats["name_tokens"], "name pool mismatch")
    require(protocol.name_reference_count == stats["name_reference_count"], "name reference mismatch")
    static_report = json.loads((TARGET / REPORT_NAME).read_bytes())
    require(static_report["source_hashes"]["parse_bsn_metadata.py"] == sha(source), "report parser binding")
    require(static_report["source_hashes"]["test_parse_bsn_metadata.py"] == sha(test_source), "report test binding")
    require(static_report["container"]["sha256"] == BLOB_SHA, "report blob binding")
    histogram = dict(collections.Counter(r["kind"] for r in protocol.records))
    require(static_report["meta_type_counts"] == histogram, "report kind histogram")
    require(stats["dump_words"] == static_report["container"]["dump_words"], "dump word report")
    named = [r for r in protocol.records if r["name"] == "Battlenet::Client::S2GameDefines::ClientInfo"]
    require(len(named) == 1 and named[0]["id"] == 1768 and named[0]["count"] == 18, "selected ClientInfo graph differs")
    for name, expected in pins.items():
        require(sha((TARGET / name).read_bytes()) == expected, "source changed after review")
    return {"format": "native-BSN-parser-independent-review-v1", "verdict": "PASS", "material_findings_remaining": [],
            "reviewer_source_sha256": sha(Path(__file__).read_bytes()), "reviewed_input_pins": pins,
            "source_PE_sha256": PE_SHA, "PE_read_passes": 1, "actual_PE_bytes_read": len(raw), "embedded_blob_sha256": BLOB_SHA,
            "independent_all_type_records_and_graph_edges_exact": True, "records_compared": len(independent),
            "independent_statistics": stats, "meta_type_counts": histogram,
            "focused_tests_run": result.testsRun, "focused_tests_failures": len(result.failures), "focused_tests_errors": len(result.errors), "focused_tests_skipped": len(result.skipped),
            "independent_synthetic_positive_negative_checks": extra_checks,
            "resolved_initial_findings": {"initial_parser_sha256": "026c81c53a8f47171eebe577bbbad06b267485784889c618ce9cb1303f43fb3e",
                 "aggregate_dense_enum_expansion_budget": "fixed before allocation; shared-dump32enum fixture now rejects at budget1000",
                 "all_zero_dump_records": "fixed to MetadataError", "unreferenced_unterminated_name_pool": "fixed to reject"},
            "manual_review": ["BE32 framing/offsets, integer sign and width, fixed/nonfixed bounds, dense/sparse counts and references match pinned source facts.",
                              "Enum duplicate values are preserved; structure/choice duplicate tags reject. Dense empty ranges and only final zero alignment are explicit.",
                              "All current8330 type records, child type IDs, dump names and member-name sequences independently agree.",
                              "Header bit6 and native codeInfo offsets remain uninterpreted; no ownership or old174-layout meaning follows."],
            "not_performed": ["No client/native code execution, replay read, network, raw binary/full schema output, repo/cloud write."],
            "scope_limit": "This verifies metadata grammar/type graph. Actual replay-to-native field binding is reviewed separately."}

if __name__ == "__main__":
    require(len(sys.argv) == 5, "supply exact parser, inspector, test and report SHA256 pins")
    output = HERE / "native-BSN-parser-independent-review.json"
    require(not output.exists(), "refuse existing review output")
    report = review(*sys.argv[1:])
    data = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    with output.open("xb") as stream:
        stream.write(data)
    print(json.dumps({"verdict": report["verdict"], "bytes": len(data), "sha256": sha(data),
                      "source_sha256": report["reviewer_source_sha256"], "tests": report["focused_tests_run"], "independent_statistics": report["independent_statistics"]}))
