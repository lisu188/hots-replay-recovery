"""Independent BSN framing geometry check, one pinned PE read, no game loading.

Uses only documented BE32 constructor geometry. Does not import other producers,
parse complete type records, interpret replay fields, or export any binary body.
"""
import collections
import hashlib
import json
import os
from pathlib import Path
import stat
import struct

HERE = Path(__file__).resolve().parent
PE_PATH = Path("C:/Program Files (x86)/Heroes of the Storm/Versions/Base98348/HeroesOfTheStorm_x64.exe")
PE_BYTES = 53573840
PE_SHA256 = "efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9"
START = 43169040
EXPECTED_HEADER = (7, 0, 8330, 67244, 257729)
EXPECTED_END = 43560673
EXPECTED_FINAL_STRING = 43560668
EXPECTED_FINAL_STRING_POINTER = 43363800
PRIMARY_PROVENANCE_SHA = "10a65095b099f71ae69c225a7dc9842adb110ce9243d80bfe79229a3533112ea"
ANCHORS = {
    "m_licenseCatalog": 43393499,
    "m_licenseInstance": 43396498,
    "m_clientLicensesList": 43426603,
    "m_mapNamespace": 43476303,
}
sha = lambda raw: hashlib.sha256(raw).hexdigest()

def require(condition, message):
    if not condition:
        raise ValueError(message)

def analyze():
    provenance = (HERE.parent / "bsn-primary-provenance" / "bsn-primary-source-provenance.json").read_bytes()
    require(sha(provenance) == PRIMARY_PROVENANCE_SHA, "documented source facts changed")
    require(not PE_PATH.is_symlink(), "refuse PE final symlink")
    with PE_PATH.open("rb") as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_size == PE_BYTES, "PE size/type differs")
        raw = stream.read(PE_BYTES + 1)
        after = os.fstat(stream.fileno())
    require(len(raw) == PE_BYTES and sha(raw) == PE_SHA256, "whole PE SHA/size differs")
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), "PE changed during read")
    require(raw[:2] == b"MZ", "DOS magic")
    pe_offset = struct.unpack_from("<I", raw, 0x3c)[0]
    require(raw[pe_offset:pe_offset + 4] == b"PE\0\0", "PE magic")
    machine, count = struct.unpack_from("<HH", raw, pe_offset + 4)
    optional = pe_offset + 24
    optional_size = struct.unpack_from("<H", raw, pe_offset + 20)[0]
    require(machine == 0x8664 and struct.unpack_from("<H", raw, optional)[0] == 0x20b, "AMD64 PE32+ required")
    require(0 < count <= 64 and optional_size >= 240, "section/header count bound")
    sections = []
    for index in range(count):
        p = optional + optional_size + 40 * index
        require(p + 40 <= len(raw), "truncated section table")
        name = raw[p:p + 8].rstrip(b"\0").decode("ascii")
        virtual_size, rva, size, offset = struct.unpack_from("<IIII", raw, p + 8)
        require(offset + size <= len(raw), "section outside physical PE")
        sections.append({"name": name, "file_start": offset, "file_end_exclusive": offset + size,
                         "rva_start": rva, "virtual_size": virtual_size})
    def locate(offset, length=1):
        hits = [s for s in sections if s["file_start"] <= offset and offset + length <= s["file_end_exclusive"]]
        require(len(hits) == 1, "byte extent lacks one physical PE section")
        section = hits[0]
        return {"file_offset": offset, "rva": section["rva_start"] + offset - section["file_start"],
                "section": section["name"]}
    header = struct.unpack_from(">5I", raw, START)
    require(header == EXPECTED_HEADER, "five-word BE header differs")
    version, unknown, n, type_size, dump_size = header
    type_offsets_start = 20
    type_offsets_end = type_offsets_start + 4 * n
    type_info_start = type_offsets_end
    type_info_end = type_info_start + type_size
    dump_offsets_start = type_info_end
    dump_offsets_end = dump_offsets_start + 4 * n
    dump_info_start = dump_offsets_end
    dump_info_end = dump_info_start + dump_size
    end = START + dump_info_end
    require(dump_info_end == 391633 and end == EXPECTED_END, "derived blob length/end differs")
    require(end <= len(raw), "framed blob beyond PE")
    container_location = locate(START, dump_info_end)
    require(container_location["section"] == ".rdata", "container not completely in .rdata")
    intervals = {
        "header": (0, 20), "type_offset_table": (type_offsets_start, type_offsets_end),
        "type_info": (type_info_start, type_info_end),
        "dump_offset_table": (dump_offsets_start, dump_offsets_end),
        "dump_info": (dump_info_start, dump_info_end),
    }
    interval_report = []
    for name, (start, stop) in intervals.items():
        location = locate(START + start, stop - start)
        interval_report.append({"name": name, "relative_start": start, "relative_end_exclusive": stop,
                                "file_start": START + start, "file_end_exclusive": START + stop,
                                "bytes": stop - start, "section": location["section"], "rva_start": location["rva"]})
    types = struct.unpack_from(">" + str(n) + "I", raw, START + type_offsets_start)
    dumps = struct.unpack_from(">" + str(n) + "I", raw, START + dump_offsets_start)
    require(all(type_info_start <= value < type_info_end for value in types), "type offset outside type-info")
    require(all(value == 0 or dump_info_start <= value < dump_info_end for value in dumps), "dump offset outside dump-info")
    type_sections = collections.Counter(locate(START + value)["section"] for value in types)
    dump_sections = collections.Counter(locate(START + value)["section"] for value in dumps if value)
    require(set(type_sections) == {".rdata"} and set(dump_sections) <= {".rdata"}, "table referenced section differs")
    require(raw[EXPECTED_FINAL_STRING:end] == b"GGCP\0", "final GGCP NUL anchor differs")
    final_pointer_value = struct.unpack_from(">I", raw, EXPECTED_FINAL_STRING_POINTER)[0]
    require(final_pointer_value == EXPECTED_FINAL_STRING - START == 391628, "final dump-string pointer differs")
    require(START + dump_info_start <= EXPECTED_FINAL_STRING_POINTER < EXPECTED_FINAL_STRING, "final pointer outside dump payload")
    require(raw[end:end + 3] == b"\0\0\0" and (end + 3) % 4 == 0, "three alignment NULs differ")
    anchor_rows = []
    for name, offset in ANCHORS.items():
        literal = name.encode("ascii")
        require(raw[offset:offset + len(literal) + 1] == literal + b"\0", "named anchor bytes/NUL differ")
        require(START + dump_info_start <= offset < end, "named anchor outside dump-info")
        anchor_rows.append({"name": name, **locate(offset, len(literal) + 1),
                            "relative_container_offset": offset - START, "NUL_terminated_literal_verified": True})
    final = PE_PATH.stat()
    require((final.st_size, final.st_mtime_ns) == (before.st_size, before.st_mtime_ns), "PE metadata changed after analysis")
    return {
        "format": "native-bsn-independent-framing-v1", "verdict": "PASS", "material_findings": [],
        "producer_sha256": sha(Path(__file__).read_bytes()),
        "documented_source_provenance_sha256": PRIMARY_PROVENANCE_SHA,
        "source_PE": {"sha256": PE_SHA256, "bytes": len(raw), "read_passes": 1,
                      "actual_PE_bytes_read": len(raw), "size_and_mtime_unchanged": True},
        "container": {**container_location, "bytes": dump_info_end, "file_end_exclusive": end,
                      "sha256": sha(raw[START:end]), "version_word": version, "unknown_second_word": unknown,
                      "type_count": n, "declared_type_info_bytes": type_size, "declared_dump_info_bytes": dump_size,
                      "header_and_intervals_are_contiguous": True, "intervals": interval_report},
        "table_checks": {
            "type_entries_checked": len(types), "type_offsets_inside_declared_type_info": True,
            "type_offset_min": min(types), "type_offset_max": max(types), "type_offset_unique_count": len(set(types)),
            "type_target_section_counts": dict(type_sections),
            "dump_entries_checked": len(dumps), "zero_dump_entries": dumps.count(0),
            "nonzero_dump_offsets_inside_declared_dump_info": True,
            "nonzero_dump_offset_min": min(v for v in dumps if v),
            "nonzero_dump_offset_max": max(v for v in dumps if v),
            "nonzero_dump_offset_unique_count": len({v for v in dumps if v}), "dump_target_section_counts": dict(dump_sections),
            "last_top_level_dump_offset_word_file_position": START + dump_offsets_end - 4,
        },
        "anchors": {"literal_names": anchor_rows, "final_NUL_terminated_string": "GGCP",
                    "final_string_file_offset": EXPECTED_FINAL_STRING, "final_string_ends_at_container_end": True,
                    "final_dump_string_pointer_word_file_offset": EXPECTED_FINAL_STRING_POINTER,
                    "final_dump_string_pointer_value": final_pointer_value,
                    "final_string_pointer_is_in_dump_info_not_top_level_dump_offset_table": True,
                    "immediately_following_alignment_NUL_bytes": 3, "aligned_following_boundary": end + 3},
        "limitations": ["Validates constructor geometry, all top-level table target bounds and four literal anchors, not complete type-record grammar.",
                        "Dump-info pointers are not automatically string pointers; the one final-string pointer is separately checked.",
                        "The reference source does not mandate version7 or name its second header word; those are observed current PE values.",
                        "Framing and label presence do not establish HotS replay field layouts, serialization bit widths or availability semantics."],
        "operations": {"imported_agent_producer": False, "upstream_native_or_client_code_loaded_or_executed": False,
                       "raw_blob_or_binary_body_saved": False, "network_requests": 0, "repo_or_cloud_writes": False},
    }

if __name__ == "__main__":
    output = HERE / "native-bsn-independent-framing.json"
    require(not output.exists(), "refuse existing independent framing receipt")
    result = analyze()
    body = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf8")
    with output.open("xb") as stream:
        stream.write(body)
    print(json.dumps({"verdict": result["verdict"], "receipt_bytes": len(body), "receipt_sha256": sha(body),
                      "source_sha256": result["producer_sha256"], "container": result["container"],
                      "table_checks": result["table_checks"], "actual_PE_bytes_read": len(result["source_PE"]) and PE_BYTES}))
