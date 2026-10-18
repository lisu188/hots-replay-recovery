"""Hash private upstream text and publish only provenance/manual source facts.

Does not import, compile or execute upstream C++, and never reads a client image.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRIVATE = HERE.parent / "bsn-primary-source-private"
COMMIT = "b1c71b8bd108823bca952f16c6f83a7ad33b9648"
PREFIX = "WoW/Source/Battlenet/BSN/"
BASE = "https://github.com/SatyPardus/wowdecomp/blob/" + COMMIT + "/" + PREFIX
EXPECTED = {
    "Types.h": "58671489cb7c0d8831506443e33cdf33cb6b93fc",
    "Protocol.h": "1f884571dbec47298265d4784b004079ec3e353b",
    "Protocol.cpp": "6308f2814054cebc917e8e2e3a9274698b1e4a88",
    "ProtocolMeta.cpp": "9edbe0b937aab834ffd6dccd03ae6569795b99b0",
    "ProtocolType.cpp": "420dc2de0722d10d2ff3970c303c245a19515965",
}

def ref(file, first, last):
    return {"file": file, "first_line": first, "last_line": last,
            "url": BASE + file + "#L" + str(first) + "-L" + str(last)}

FACTS = [
    {"id": "container-header", "source": [ref("Protocol.cpp", 17, 53)],
     "fact": "The constructor consumes five big-endian 32-bit words: version, an unnamed value stored as unk_0014, typeIdCount, typeInfoSize, dumpInfoSize. It stores bytecodeSize and separate codeInfo parameters. The constructor does not itself assert version5 or interpret the second word."},
    {"id": "table-order", "source": [ref("Protocol.cpp", 55, 68)],
     "fact": "After the 20-byte header is a typeIdCount-by-4 type-offset table, then typeInfoSize type-information bytes. If that end equals bytecode+bytecodeSize, dump state is cleared; otherwise a typeIdCount-by-4 dump-offset table precedes the dump-information pointer. This is pointer setup in the reference, not a complete bounds validator."},
    {"id": "absolute-offsets", "source": [ref("Protocol.cpp", 5, 12), ref("Protocol.cpp", 73, 98)],
     "fact": "TypeInfo reads the indexed four-byte big-endian type-offset entry and returns bytecode+offset. DumpInfo reads the indexed four-byte big-endian dump-offset entry and also returns bytecode+offset; no dump data or a zero offset returns null. These entries are absolute relative to the container bytecode base, not relative to the type/dump payload pointers."},
    {"id": "dump-string-offsets", "source": [ref("Protocol.cpp", 103, 115)],
     "fact": "DumpString reads a four-byte big-endian entry at dumpInfo+4*index and returns a char pointer at bytecode+offset. Missing dump state returns an empty string; a zero entry returns null. This routine does not identify what each caller's index denotes, validate a terminal NUL, or bind a member name to a replay field."},
    {"id": "meta-enumeration", "source": [ref("Types.h", 11, 28), ref("ProtocolMeta.cpp", 5, 21)],
     "fact": "MetaType declares IDs1..16 for Array, AsciiString, BitArray, Blob, Bool, Choice, Enum, FourCC, Int, Null, Optional, Real32, Real64, Struct, String, User respectively. PeekHeaderEnum masks the type-information byte with0x3f. Base consumes this first header byte and initializes type/dump pointers. The purpose of bit6 is not established by these cited routines."},
    {"id": "external-code-info", "source": [ref("Protocol.h", 19, 38), ref("ProtocolMeta.cpp", 11, 21), ref("ProtocolMeta.cpp", 220, 235)],
     "fact": "Base reads a codeInfo[typeId+1] entry as an index into a separate native codeInfo array. Struct::GetMember reads native member offset from m_codeInfo[index+1]. The native offset is not decoded from the serialized type-information stream. Protocol.h's annotated native member offsets describe this WoW reference layout and do not establish the 64-bit HotS object ABI."},
    {"id": "integer-encoding", "source": [ref("ProtocolType.cpp", 5, 35), ref("ProtocolType.cpp", 69, 75)],
     "fact": "Int::Get uses byte width1<<(intType>>1) and big-endian accumulation. Its uint64 variant sign-extends when the intType low bit is0 and the first byte has its high bit set; low bit1 is treated unsigned. GetSize consumes an intType byte followed by that width of integer. GetTypeId always consumes four big-endian bytes. The reference does not explicitly validate the intType domain or available input extent."},
    {"id": "bounds-encoding", "source": [ref("ProtocolType.cpp", 40, 65), ref("Protocol.h", 44, 52)],
     "fact": "Bounds::Get first consumes intType. For fixed=true it sets variable=false, bits=0 and consumes one integer used as both min and max. Otherwise it consumes a flags/bits byte (high bit variable, lower7 bits m_bits) and then min and max integers. Contains uses unsigned comparisons for odd intType and signed int64 comparisons for even intType. These metadata bits are not by themselves proof of any selected HotS replay bit width."},
    {"id": "array-and-blob-bounds", "source": [ref("ProtocolMeta.cpp", 26, 40)],
     "fact": "Array, BitArray and Blob pass header>>7 to Bounds::Get, so the high header bit chooses fixed-bound parsing for these types. Array then consumes a four-byte element type ID."},
    {"id": "struct-count-and-type-references", "source": [ref("ProtocolMeta.cpp", 208, 235)],
     "fact": "Struct always parses non-fixed Bounds. When the header high bit is clear it then reads an explicit GetSize count; when set it computes count from uint32(max)-uint32(min)+1. For member index i the type-ID pointer skips count*(1<<(intType>>1)) bytes in the high-bit-clear form, then advances4*i bytes; the high-bit-set form advances4*i directly. GetMember does not interpret the skipped prefix entries in this function. It returns the BE32 type ID and a separate native codeInfo member offset."},
    {"id": "choice-and-enum", "source": [ref("ProtocolMeta.cpp", 45, 105), ref("ProtocolMeta.cpp", 110, 130), ref("ProtocolMeta.cpp", 184, 203)],
     "fact": "Choice and Enum use non-fixed Bounds and the same explicit-count versus contiguous-range count branch. Their high-bit-clear variants compare explicit integer entries; high-bit-set variants relate the index/tag by the minimum bound. Choice type IDs follow its explicit-entry prefix, or begin directly in the range form. These functions name Choice tag values, whereas the Struct skipped prefix is not named here."},
    {"id": "other-meta-payloads", "source": [ref("ProtocolMeta.cpp", 135, 179), ref("ProtocolMeta.cpp", 241, 245)],
     "fact": "Int and AsciiString parse non-fixed Bounds; User and Optional read one four-byte referenced type ID. Bool, FourCC, Null, Real32 and Real64 constructors add no payload reads after Base. String parses character Bounds, copies them to byte Bounds, adds2 to the byte bit count and multiplies the byte maximum by4."},
]

def record():
    rows = []
    for name, expected in EXPECTED.items():
        data = (PRIVATE / name).read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
        if blob != expected:
            raise ValueError("upstream Git blob differs: " + name)
        lines = data.decode("utf-8").splitlines()
        for fact in FACTS:
            for source in fact["source"]:
                if source["file"] == name and not 1 <= source["first_line"] <= source["last_line"] <= len(lines):
                    raise ValueError("source line reference out of bounds")
        rows.append({"file": name, "relative_upstream_path": PREFIX + name, "url": BASE + name,
                     "bytes": len(data), "git_blob_sha1": blob, "expected_git_blob_matches": True,
                     "sha256": hashlib.sha256(data).hexdigest(), "lines": len(lines),
                     "CRLF_pairs": data.count(b"\r\n")})
    result = {
        "format": "bsn-primary-source-provenance-and-manual-facts-v1",
        "source_repository": "SatyPardus/wowdecomp", "source_commit": COMMIT,
        "source_role": "Pinned community WoW decompilation implementation; not an official Blizzard protocol specification or proof of HotS implementation identity.",
        "producer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "verification": {"all_five_expected_git_blob_SHA1s_match": True, "total_private_source_bytes": sum(r["bytes"] for r in rows),
                         "Git_blob_hash_formula": "SHA1(ASCII('blob '+decimal_byte_length)+NUL+exact_file_bytes)",
                         "all_source_line_references_within_actual_files": True},
        "sources": rows, "manual_code_facts": FACTS,
        "unproven": ["No cited constructor check requires version5; a version5 HotS table is a separate artifact observation.",
                     "The unknown second container word and header bit6 remain unnamed.",
                     "DumpString's index-to-member-name or type-name convention is not established by these five files alone.",
                     "The native codeInfo table and WoW annotated offsets do not establish HotS ABI or replay bit layout.",
                     "No current HotS byte range, table boundary, 174-to198-bit block, availability meaning or DataMod namespace is established by this source-only receipt."],
        "safe_parser_requirements": ["Add explicit bounds and integer/type/count/offset validation rather than copying unchecked native pointer operations.",
                                     "Keep decoded source grammar, a matching PE container and replay-field semantics as separate evidence stages.",
                                     "Do not infer names or type identity from adjacent strings without validating the actual tables and caller convention."],
        "operations": {"network_requests": 0, "client_or_PE_reads": 0, "upstream_code_imported_compiled_or_executed": False,
                       "raw_upstream_bodies_published_or_copied_to_report_directory": False, "repo_or_cloud_writes": False},
    }
    return result

if __name__ == "__main__":
    output = HERE / "bsn-primary-source-provenance.json"
    if output.exists():
        raise FileExistsError("refuse existing provenance report")
    report = record()
    encoded = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with output.open("xb") as stream:
        stream.write(encoded)
    print(json.dumps({"report_bytes": len(encoded), "report_sha256": hashlib.sha256(encoded).hexdigest(),
                      "producer_sha256": report["producer_sha256"], "verified_private_source_bytes": report["verification"]["total_private_source_bytes"]}))
