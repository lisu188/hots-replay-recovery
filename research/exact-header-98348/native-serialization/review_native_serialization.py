"""Independent byte-only review. Reads one pinned PE once, never loads client code."""
from __future__ import annotations
import collections
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
INPUT = HERE.parent / "native-serialization-98348"
IMAGE = Path("C:/Program Files (x86)/Heroes of the Storm/Versions/Base98348/HeroesOfTheStorm_x64.exe")
EXPECTED_PE = "efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9"
EXPECTED_RECEIPT = "92a619233605f0cc54d39c9c1e61f4d88237a0ff4b9b2535f480f1d0c3bf0cca"
EXPECTED_SIZE = 53573840
TARGETS = ("m_licenseInstance", "m_licenseCatalog", "m_clientLicensesList", "m_mapNamespace")
SAFE = re.compile(r"[A-Za-z0-9_@?$:.<>(), \[\]*=+!~-]{4,192}\Z")
sha = lambda b: hashlib.sha256(b).hexdigest()

def check(condition, message):
    if not condition:
        raise ValueError(message)

def category(label):
    low = label.lower()
    if "mapnamespace" in low or "map_namespace" in low:
        return "map-namespace-label"
    if low.startswith("replay.") or "battlelobby" in low or "battle_lobby" in low:
        return "replay-stream-or-battlelobby-label"
    if label.startswith(".?A") or label.startswith("??_R"):
        return "MSVC-RTTI-type-name-candidate"
    if re.fullmatch(r"CReward[A-Za-z0-9_]*", label):
        return "reward-catalog-type-label"
    if label.startswith(("m_", "s_")):
        return "field-spelling-candidate"
    if "serializ" in low:
        return "serialization-word-label"
    return "other-target-keyword-label"

def import_research(name, path):
    # Only reviewed stdlib research source is imported, never the PE or a game DLL.
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def review():
    receipt_raw = (INPUT / "native-serialization-frozen-receipt.json").read_bytes()
    check(sha(receipt_raw) == EXPECTED_RECEIPT, "frozen receipt changed")
    receipt = json.loads(receipt_raw)
    check(len(receipt["allowlisted_files"]) == 5, "five-file allowlist differs")
    inputs = []
    for row in receipt["allowlisted_files"]:
        name = row["name"]
        check(Path(name).name == name, "allowlist path is not a filename")
        data = (INPUT / name).read_bytes()
        check(len(data) == row["bytes"] and sha(data) == row["sha256"], "allowlist input changed")
        inputs.append({"name": name, "bytes": len(data), "sha256": sha(data)})
    labels_raw = (INPUT / "native-serialization-labels-98348.json").read_bytes()
    contexts_raw = (INPUT / "native-descriptor-contexts-98348.json").read_bytes()
    labels, contexts = json.loads(labels_raw), json.loads(contexts_raw)
    file_pins = {r["name"]: r["sha256"] for r in inputs}
    check(labels["producer_sha256"] == file_pins["inspect_native_serialization_labels.py"], "first producer binding")
    check(contexts["producer_sha256"] == file_pins["inspect_native_descriptor_contexts.py"], "context producer binding")
    check(contexts["PE_parser_source_sha256"] == labels["producer_sha256"], "parser-source binding")
    check(contexts["initial_report_sha256"] == sha(labels_raw), "report-to-report binding")
    check(len(labels_raw) + len(contexts_raw) == receipt["JSON_report_bytes"] == 156753, "report byte total")
    check(not IMAGE.is_symlink(), "final PE symlink")
    with IMAGE.open("rb") as stream:
        before = os.fstat(stream.fileno())
        check(stat.S_ISREG(before.st_mode) and before.st_size == EXPECTED_SIZE, "PE size/type")
        raw = stream.read(EXPECTED_SIZE + 1)
        after = os.fstat(stream.fileno())
    check(len(raw) == EXPECTED_SIZE and sha(raw) == EXPECTED_PE, "whole PE SHA/size")
    check((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), "PE changed during read")

    # Independent physical section mapping, without loading the Windows image.
    u16 = lambda p: struct.unpack_from("<H", raw, p)[0]
    u32 = lambda p: struct.unpack_from("<I", raw, p)[0]
    u64 = lambda p: struct.unpack_from("<Q", raw, p)[0]
    check(raw[:2] == b"MZ", "MZ")
    pe = u32(0x3c)
    check(raw[pe:pe + 4] == b"PE\0\0" and u16(pe + 4) == 0x8664, "AMD64 PE")
    optional = pe + 24
    check(u16(optional) == 0x20b, "PE32+")
    sections = []
    for index in range(u16(pe + 6)):
        p = optional + u16(pe + 20) + index * 40
        virtual, rva, size, offset = struct.unpack_from("<IIII", raw, p + 8)
        check(offset + size <= len(raw), "physical section bounds")
        sections.append({"name": raw[p:p + 8].rstrip(b"\0").decode("ascii"),
                         "rva": rva, "virtual_size": virtual, "raw_size": size,
                         "raw_offset": offset, "characteristics": u32(p + 36)})
    check(sections == labels["sections"], "independent section table differs")
    def location(p):
        matches = [s for s in sections if s["raw_offset"] <= p < s["raw_offset"] + s["raw_size"]]
        check(len(matches) <= 1, "overlapping physical sections")
        s = matches[0] if matches else None
        return {"file_offset": p, "section": s["name"] if s else None,
                "rva": s["rva"] + p - s["raw_offset"] if s else p if p < u32(optional + 60) else None}
    def physical(rva, size=1):
        matches = [s for s in sections if s["rva"] <= rva and rva + size <= s["rva"] + s["raw_size"]]
        check(len(matches) == 1, "RVA extent lacks unique physical section")
        return matches[0]["raw_offset"] + rva - matches[0]["rva"]
    resource_rva, resource_size = struct.unpack_from("<II", raw, optional + 112 + 16)
    resource = physical(resource_rva, resource_size)
    def resource_entries(relative):
        p = resource + relative
        check(resource <= p and p + 16 <= resource + resource_size, "resource directory")
        count = u16(p + 12) + u16(p + 14)
        check(count <= 4096 and p + 16 + 8 * count <= resource + resource_size, "resource entries")
        return [struct.unpack_from("<II", raw, p + 16 + 8 * i) for i in range(count)]
    roots = [v & 0x7fffffff for k, v in resource_entries(0) if k == 16 and v & 0x80000000]
    check(len(roots) == 1, "RT_VERSION root")
    pending = [(roots[0], 0)]
    version_blobs = []
    while pending:
        relative, depth = pending.pop()
        check(depth <= 4, "resource depth")
        for _, value in resource_entries(relative):
            if value & 0x80000000:
                pending.append((value & 0x7fffffff, depth + 1))
            else:
                p = resource + value
                check(p + 16 <= resource + resource_size, "resource leaf")
                rva, size = struct.unpack_from("<II", raw, p)
                check(size <= 65536, "version leaf bound")
                offset = physical(rva, size)
                version_blobs.append(raw[offset:offset + size])
    fixed_versions, textual_versions = [], []
    for blob in version_blobs:
        pending = [(0, len(blob), 0)]
        while pending:
            p, bound, depth = pending.pop()
            check(depth <= 8 and p + 6 <= bound, "version node")
            length, value_len, kind = struct.unpack_from("<HHH", blob, p)
            stop = p + length
            check(length >= 6 and stop <= bound, "version node length")
            key_end = p + 6
            while blob[key_end:key_end + 2] != b"\0\0":
                key_end += 2
                check(key_end + 2 <= stop, "version node key")
            key = blob[p + 6:key_end].decode("utf-16le")
            v = (key_end + 2 + 3) & ~3
            size = value_len * (2 if kind == 1 else 1)
            check(v + size <= stop, "version node value")
            if key == "VS_VERSION_INFO":
                check(size == 52, "fixed fileinfo size")
                f = struct.unpack_from("<13I", blob, v)
                check(f[0] == 0xfeef04bd, "fixed signature")
                fixed_versions.append([f[2] >> 16, f[2] & 65535, f[3] >> 16, f[3] & 65535])
            elif key == "FileVersion":
                check(kind == 1, "text FileVersion kind")
                textual_versions.append(blob[v:v + size].decode("utf-16le").rstrip("\0"))
            child = (v + size + 3) & ~3
            while child + 6 <= stop:
                child_size = struct.unpack_from("<H", blob, child)[0]
                if not child_size:
                    break
                pending.append((child, stop, depth + 1))
                child = (child + child_size + 3) & ~3
    check(textual_versions == ["2.57.0.98348"] and fixed_versions == [[2, 57, 0, 32812]], "independent version values")
    check(labels["source"]["version_resources"][0]["fixed"]["file_version_words"] == fixed_versions[0], "reported fixed version")
    check(labels["source"]["version_resources"][0]["strings"]["FileVersion"] == textual_versions[0], "reported text version")

    # Verify every reported literal at its physical offset and independently mapped RVA.
    for row in labels["selected_labels"]:
        encoded = row["label"].encode("ascii" if row["encoding"] == "ASCII" else "utf-16le")
        p = row["file_offset"]
        check(raw[p:p + len(encoded)] == encoded, "selected literal bytes")
        check({k: row[k] for k in ("file_offset", "section", "rva")} == location(p), "selected literal location")
        check(category(row["label"]) == row["category"], "selected literal family")
    check(len(labels["selected_labels"]) == 320, "selected label count")
    matched, exclusions, families = [], collections.Counter(), collections.Counter()
    keywords = re.compile(r"replay|battle.?lobby|licen[cs]e|reward|collection|serializ|availability|player|map_?namespace", re.I)
    for encoding, pattern in (("ASCII", rb"[\x20-\x7e]{4,2048}"), ("UTF-16LE", rb"(?:[\x20-\x7e]\x00){4,2048}")):
        for match in re.finditer(pattern, raw):
            name = match.group().decode("ascii" if encoding == "ASCII" else "utf-16le")
            if not keywords.search(name):
                continue
            loc = location(match.start())
            if not SAFE.fullmatch(name):
                exclusions["non-label-or-long-" + encoding] += 1
                continue
            if loc["section"] is None:
                exclusions["outside-PE-section-" + encoding] += 1
                continue
            family = category(name)
            families[family] += 1
            matched.append({"label": name, "encoding": encoding, "category": family, **loc})
    check(dict(families) == labels["safe_label_counts"] and dict(exclusions) == labels["excluded_non_label_counts"], "full scan counts")
    priority = {"map-namespace-label": 0, "replay-stream-or-battlelobby-label": 0, "MSVC-RTTI-type-name-candidate": 1, "field-spelling-candidate": 2, "serialization-word-label": 3, "reward-catalog-type-label": 4, "other-target-keyword-label": 5}
    caps = {"map-namespace-label": 48, "replay-stream-or-battlelobby-label": 64, "MSVC-RTTI-type-name-candidate": 112, "field-spelling-candidate": 48, "serialization-word-label": 48, "reward-catalog-type-label": 48, "other-target-keyword-label": 48}
    selected, saved = [], collections.Counter()
    for row in sorted(matched, key=lambda r: (priority[r["category"]], r["file_offset"])):
        if len(selected) < 320 and saved[row["category"]] < caps[row["category"]]:
            selected.append(row)
            saved[row["category"]] += 1
    check(selected == labels["selected_labels"] and dict(saved) == labels["saved_label_counts"], "selected inventory exact")

    # Recompute bounded contexts independently; reuse only reviewed pure wire grammar.
    grammar = import_research("review_context_grammar", INPUT / "inspect_native_descriptor_contexts.py")
    occurrences = [(term, match.start()) for term in TARGETS for match in re.finditer(re.escape(term.encode()), raw)]
    check(len(occurrences) == 11, "target count")
    intervals = sorted((max(0, p - 1024), min(len(raw), p + 2048)) for _, p in occurrences)
    merged = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    union = sum(end - start for start, end in merged)
    check(union == contexts["context_union_bytes"] == receipt["descriptor_context_union_bytes"] == 33666, "context union")
    reproduced, containers = [], {}
    for term, p in occurrences:
        start, end = next((s, e) for s, e in merged if s <= p < e)
        names = []
        for match in re.finditer(rb"[\x20-\x7e]{4,256}", raw[start:end]):
            value = match.group().decode()
            if SAFE.fullmatch(value):
                names.append({"label": value, **location(start + match.start())})
        nearest = sorted(names, key=lambda row: abs(row["file_offset"] - p))[:32]
        row = {"target": term, **location(p), "neighbor_label_window_start": start,
               "neighbor_label_window_end": end, "nearest_allowlisted_labels": sorted(nearest, key=lambda r: r["file_offset"]),
               "protobuf_name_key_length_prefix_matches": raw[p - 2:p] == bytes((10, len(term)))}
        fields = []
        if row["protobuf_name_key_length_prefix_matches"]:
            for frame, key, a, b in grammar.framed_payloads(raw, start, end, p - 2):
                try:
                    desc = grammar.field_descriptor(raw[a:b])
                except ValueError:
                    continue
                if desc["name"] == term:
                    fields.append({"enclosing_field_number": key, "field_descriptor_start": a, "field_descriptor_end": b,
                                   "complete_contiguous_payload_sha256": sha(raw[a:b]), "descriptor": desc})
        row["complete_protobuf_FieldDescriptorProto_candidates"] = fields
        for match in re.finditer(rb"\x0a[\x01-\x7f][A-Za-z_]", raw[start:end]):
            for frame, key, a, b in grammar.framed_payloads(raw, start, end, start + match.start()):
                if not a <= p < b:
                    continue
                try:
                    wire = grammar.wire(raw, a, b)
                    names2 = [v for n, k, v in wire if n == 1 and k == 2]
                    if len(names2) != 1 or not grammar.IDENTIFIER.fullmatch(names2[0]):
                        continue
                    body = [grammar.field_descriptor(v) for n, k, v in wire if n == 2 and k == 2]
                    if not body or len(body) > 128 or not any(d["name"] == term for d in body):
                        continue
                    if len({d["name"] for d in body}) != len(body) or len({d["number"] for d in body}) != len(body):
                        continue
                    containers[(a, b)] = body
                except ValueError:
                    continue
        reproduced.append(row)
    check(reproduced == contexts["target_occurrences"], "all context families/locations/nearest labels exact")
    check(not containers and contexts["complete_protobuf_DescriptorProto_candidates"] == [], "bounded complete descriptor results")
    check(all(not r["complete_protobuf_FieldDescriptorProto_candidates"] for r in reproduced), "bounded field descriptor results")
    rtti_count = 0
    for row in labels["RTTI_data_structure_candidates"]:
        for candidate in row["validated_data_structure_candidates"]:
            loc = candidate["complete_object_locator"]
            check(location(loc["file_offset"]) == loc, "COL location")
            signature, offset, cd, typed, hierarchy, itself = struct.unpack_from("<6I", raw, loc["file_offset"])
            check(signature == 1 and itself == loc["rva"] and typed == candidate["type_descriptor_rva"], "COL structural fields")
            check((offset, cd, hierarchy) == (candidate["offset_in_complete_object"], candidate["constructor_displacement_offset"], candidate["class_hierarchy_rva"]), "COL remaining fields")
            physical(hierarchy)
            rtti_count += 1
    hints = []
    target_rvas = {r["rva"] for r in selected if r["rva"] is not None}
    for section in sections:
        if section["characteristics"] & 0x20000000:
            view = raw[section["raw_offset"]:section["raw_offset"] + section["raw_size"]]
            for match in re.finditer(rb"[\x48\x4c][\x8b\x8d][\x05\x0d\x15\x1d\x25\x2d\x35\x3d]....", view, re.S):
                target = section["rva"] + match.start() + 7 + struct.unpack_from("<i", match.group(), 3)[0]
                if target in target_rvas:
                    hints.append(target)
    check(hints == labels["raw_RIP_relative_byte_hints"] == [], "narrow RIP byte scan negative")
    check(not labels["serializer_field_semantics_proven"] and not labels["old174_to_new198_mapping_proven"] and not labels["availability32byte_record_meaning_proven"], "semantics remain unproven")
    check(not contexts["opaque174_to198_or_32byte_layout_bound"] and not contexts["new_header_candidate"], "context conclusions")
    final = IMAGE.stat()
    check((final.st_size, final.st_mtime_ns) == (before.st_size, before.st_mtime_ns), "PE metadata changed")
    for row in inputs:
        check(sha((INPUT / row["name"]).read_bytes()) == row["sha256"], "frozen input changed after review")
    return {
        "format": "hots-native-serialization-independent-review-v1", "verdict": "PASS", "material_findings": [],
        "reviewer_source_sha256": sha(Path(__file__).read_bytes()), "frozen_receipt_sha256": EXPECTED_RECEIPT,
        "allowlisted_inputs": inputs, "source_PE": {"sha256": EXPECTED_PE, "bytes": len(raw), "read_passes": 1,
        "actual_PE_bytes_read": len(raw), "source_size_and_mtime_unchanged": True},
        "verified": {"five_file_pins_and_producer_report_bindings": True, "independent_PE_section_table_and_RVA_mapping": True,
        "resource_FileVersion": textual_versions[0], "fixed_file_version_16bit_words": fixed_versions[0],
        "fixed_last_word_is_98348_mod65536": fixed_versions[0][-1] == 98348 % 65536,
        "all_selected_literal_bytes_and_locations": len(selected), "full_scan_family_counts": dict(sorted(families.items())),
        "selected_inventory_exact": True, "target_occurrences": dict(collections.Counter(t for t, _ in occurrences)),
        "all_context_rows_exact": True, "context_union_bytes": union, "bounded_complete_FieldDescriptorProto_candidates": 0,
        "bounded_complete_DescriptorProto_candidates": 0, "reported_RTTI_type_rows": len(labels["RTTI_data_structure_candidates"]),
        "validated_COL_structures": rtti_count, "narrow_raw_RIP_byte_hints": len(hints), "combined_JSON_report_bytes": len(labels_raw) + len(contexts_raw)},
        "manual_source_review": ["Both research mains refuse an existing report and read the pinned PE as data only.",
        "Physical offsets, RVAs and version-resource text are distinct; the fixed 16-bit version cannot carry build98348 directly.",
        "Context-family observations are literal adjacency, without asserting descriptor membership or replay-field semantics.",
        "The protobuf result is restricted to the implemented contiguous framed grammar and bounded contexts.",
        "Raw RIP forms lack established instruction boundaries; zero hits cannot prove absence of references.",
        "No serialization bit widths, availability meaning, opaque player mapping or missing namespace value is inferred."],
        "not_performed": ["No client/game DLL import, executable load, execution, debugger, Ghidra, disassembly, network, repo/cloud write or raw binary export."],
        "limitations": ["Reuses reviewed pure protobuf grammar helpers for negative candidate reproduction; PE/version/literal/location/union checks are separately implemented.",
        "No complete protobuf schema, serializer function or runtime field correspondence is identified."]}

if __name__ == "__main__":
    output = HERE / "native-serialization-independent-review.json"
    check(not output.exists(), "refuse existing independent receipt")
    result = review()
    encoded = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    with output.open("xb") as stream:
        stream.write(encoded)
    print(json.dumps({"verdict": result["verdict"], "receipt_bytes": len(encoded), "receipt_sha256": sha(encoded),
                      "source_sha256": result["reviewer_source_sha256"], "verified": result["verified"], "PE_bytes_read": result["source_PE"]["actual_PE_bytes_read"]}))
