"""Prove two numerical words directly from the build-98348 native vector builder."""

import argparse
import json
from contextlib import closing
from hashlib import sha256
from pathlib import Path
from struct import iter_unpack, pack, unpack_from
from zlib import crc32

from verify_sync_vector_source import verify as verify_vector

BASE = 0xBA000
SCALAR = 0x34EF5C0


def require(ok, message):
    if not ok:
        raise ValueError(message)


def constant_slot(text, first_instruction, initial_crc):
    """Evaluate just the checked builder instructions and leaf calls; no native code runs."""

    def code(site, n):
        return text[site - BASE : site - BASE + n]

    site = first_instruction
    accumulator = initial_crc
    eax = None
    callees = []
    for _ in range(14):
        opcode = code(site, 10)
        if opcode[:2] == b"\xc7\x03":
            (accumulator,) = unpack_from("<I", opcode, 2)
            site += 6
        elif opcode[0] == 0xE8:
            (disp,) = unpack_from("<i", opcode, 1)
            target = site + 5 + disp
            callee = code(target, 8)
            if callee[:3] == b"\xc2\x00\x00":
                kind = "return_without_writing"
            elif callee[:3] == b"\x48\x8d\x05" and callee[7] == 0xC3:
                kind = "return_address_without_writing"
            else:
                raise ValueError("Call has unsupported effects")
            callees.append(dict(rva=hex(target), action=kind))
            site += 5
        elif opcode[:2] == b"\x8b\x03":
            eax = accumulator
            site += 2
        elif opcode[:3] in (b"\x48\x8b\xd3", b"\x48\x8b\xc8"):
            site += 3
        elif opcode[:2] == b"\xf7\xd0" and eax is not None:
            eax ^= 0xFFFFFFFF
            site += 2
        elif opcode[:2] in (b"\x89\x47", b"\x89\x87") and eax is not None:
            fmt = "<b" if opcode[1] == 0x47 else "<i"
            (offset,) = unpack_from(fmt, opcode, 2)
            slot, rem = divmod(offset - 8, 4)
            require(not rem and 0 <= slot < 72, "Invalid store")
            return dict(
                slot=slot,
                value=eax,
                little_endian_hex=pack("<I", eax).hex(),
                entry_offset=hex(offset),
                start_rva=hex(first_instruction),
                store_rva=hex(site),
                callees=callees,
            )
        else:
            raise ValueError(f"Unknown delta at {site:#x}")
    raise ValueError("No direct store")


def rel32_field_candidates(text):
    """Find all four-byte displacement positions spanning a target byte with 0..8 trailing bytes."""
    hits = set()
    view = memoryview(text)
    for align in range(4):
        end = align + (len(view) - align) // 4 * 4
        offset = BASE + align
        for (delta,) in iter_unpack("<i", view[align:end]):
            # For a RIP relative operand, the reference is offset+4+delta plus trailing operands.
            skew = SCALAR - (offset + 4 + delta)
            if -3 <= skew <= 8:
                hits.add(offset)
            offset += 4
    return hits


def scalar_boundary(pe, text):
    (nt,) = unpack_from("<I", pe, 60)
    tbl = nt + 24 + unpack_from("<H", pe, nt + 20)[0]
    (count,) = unpack_from("<H", pe, nt + 6)
    sections = [unpack_from("<8sIIII", pe, tbl + 40 * i) for i in range(count)]
    ((name, virtual, base, raw, _),) = [
        s for s in sections if s[2] <= SCALAR and SCALAR + 4 <= s[2] + s[1]
    ]
    require(
        name.rstrip(b"\0") == b".data" and base + raw <= SCALAR,
        "Expected loader-zeroed .data",
    )
    refs = {
        0x970DC4: "primary vector read",
        0x972301: "write if input stream yielded a DWORD",
        0x973425: "pass address to a read-only formatting helper",
        0x975162: "write value to output stream",
        0x97B101: "write zero",
        0x985E05: "aggregate checksum read",
        0x9874E5: "write zero",
    }
    require(rel32_field_candidates(text) == set(refs), "Unexpected nearby displacement")
    for pointer in (pack("<I", SCALAR), pack("<Q", 0x140000000 + SCALAR)):
        require(
            pointer not in pe and pointer not in text, "Unexpected absolute reference"
        )

    def match(site, hexbytes):
        raw = bytes.fromhex(hexbytes)
        require(
            text[site - BASE : site - BASE + len(raw)] == raw,
            f"Unrecognized instruction {site:#x}",
        )

    match(0x97B0F2, "33f6")  # ESI=0 before the first store
    match(0x97B0FF, "8935")
    match(0x9873B9, "33ff")  # EDI=0 before the second store
    match(0x9874E3, "893d")
    match(0x9722F8, "4885c074088b008905")
    match(
        0x2D62F2, "488bfa"
    )  # sole address-taking wrapper only reads the pointed-to DWORD
    match(0x2D62FE, "8b17")
    return dict(
        scalar_rva=hex(SCALAR),
        direct_rip_reference_count=len(refs),
        static_data_loader_value=0,
        code_paths_with_nonconstant_direct_write=1,
        no_restore_candidate_value=crc32(pack("<I", 0)),
        loop64_slot1_admitted=False,
    )


def verify(executable, static_text):
    profile = verify_vector(executable, static_text)
    text = static_text.read_bytes()
    rows = []
    for site, slot in ((0x970858, 7), (0x970BED, 37)):
        results = [
            constant_slot(text, site, seed) for seed in (0, 1, 0xA5A55A5A, 0xFFFFFFFF)
        ]
        require(
            len({r["value"] for r in results}) == 1
            and (results[0]["slot"], results[0]["value"]) == (slot, 0),
            "Unexpected native word",
        )
        rows.append(results[0])
    return dict(
        build=profile["build"],
        pe_sha256=profile["pe_sha256"],
        static_text_sha256=profile["static_text_sha256"],
        vector_words=profile["selected_vector_words"],
        primary_builder_rva="0x9707a0",
        exact_on_primary_builder_path=rows,
        scalar_slot_one=scalar_boundary(executable.read_bytes(), text),
        ten_loop64_vector_observed=False,
        ten_loop64_final_word_recovered=False,
    )


def ten_recording(path):
    from mpq_reader import MPQArchive
    from portable_sync_98348 import decode_sync
    from protocol_loader import load_protocol

    digest = sha256(path.read_bytes()).hexdigest()
    require(
        digest == "e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824",
        "Expected TEN",
    )
    p = load_protocol(41810)
    with closing(MPQArchive(path)) as arc:
        desc = p.decode_replay_details(arc.read_file("replay.details"))
        records = decode_sync(arc.read_file("replay.sync.events"))
    first = records[0]
    require(
        (first.gameloop, first.event_id, first.words) == (64, 2, None),
        "Unexpected first recorded sync form",
    )
    require(
        desc["m_miniSave"] is False and desc["m_restartAsTransitionMap"] is False,
        "Unexpected source replay flags",
    )
    return dict(
        source_build=41810,
        source_sha256=digest,
        source_first_sync_loop=first.gameloop,
        source_first_sync_event_id=first.event_id,
        source_first_sync_vector_recorded=False,
        source_mini_save=desc["m_miniSave"],
        source_restart_as_transition_map=desc["m_restartAsTransitionMap"],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("static_text", type=Path)
    parser.add_argument("--ten", type=Path)
    a = parser.parse_args()
    receipt = verify(a.executable, a.static_text)
    if a.ten:
        receipt["source_recording"] = ten_recording(a.ten)
    print(json.dumps(receipt, indent=2))
