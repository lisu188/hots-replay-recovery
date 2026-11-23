"""Recover the clean computation and imported-value branches for build 98348 slot 69."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from

from verify_sync_vector_source import TEXT_BASE, verify as verify_vector


def need(condition, message):
    if not condition:
        raise ValueError(message)


def simd_fill_intervals(start, length):
    """Observable store extents for the SSE branch and the two native sizes >128."""
    end = start + length
    address = (start + 16) & ~15
    ranges = [(start,16)]
    blocks, remainder = divmod(end-address,128)
    for _ in range(blocks):
        ranges.extend((address+i,16) for i in range(0,128,16))
        address += 128
    blocks, tail = divmod(remainder,16)
    for _ in range(blocks):
        ranges.append((address,16))
        address += 16
    if tail:
        ranges.append((address+tail-16,16))
    return ranges


def verify(executable, static_text):
    parent = verify_vector(executable,static_text)
    text = static_text.read_bytes()
    need(parent["selected_vector_words"]==72 and parent["uncovered_slot"]==69
         and sha256(text).hexdigest()==parent["static_text_sha256"], "prior vector profile")

    def check(rva, expected):
        value = bytes.fromhex(expected)
        off = rva-TEXT_BASE
        need(text[off:off+len(value)] == value, f"instruction {rva:#x}")

    def reference(rva, target, opcode="e8"):
        check(rva,opcode)
        next_rva = rva + len(bytes.fromhex(opcode)) + 4
        disp, = unpack_from("<i", text, next_rva-4-TEXT_BASE)
        need(next_rva+disp == target,f"reference {rva:#x}")

    for start,length,digest in (
        (0x989cc0,51,"e3c5b1fbc14036143919f784"),   # both clear ranges
        (0x1a2b6a0,16,"44aa33320d91d4c7bf033c83"),  # REP STOSB
        (0x1a2b6c0,204,"ad0d07e0f8ecca8865b5c83c"),# SSE, block size and exact tail
        (0x987d10,84,"506f096b794040943bc5e1d4"),   # entry passed to reset before mode test
        (0x987db0,796,"73e1d91bbe404f5fcd8d0ae3"),  # mode 0, component output and trailer
        (0x9707a0,1860,"28a1af758d56a66113ae6355"), # entry stays in RDI for 70 stores
        (0x985bb0,74,"d6e2a12e7575a896e947decd"),   # incoming R8 overwritten before use
        (0x988d90,37,"f1946e0032d0ce411436412a"),   # new default entry
        (0x989810,184,"0ac04b775798fa3f220b35f4"),  # deferred compute or skip
        (0x977e40,162,"a6c0bfa9140275593d1adc68"),  # counted copy
        (0x9774bf,51,"b332c9c7394e03e2a16684e5"),   # alternative stream-fed words
    ):
        start -= TEXT_BASE
        need(sha256(text[start:start+length]).hexdigest().startswith(digest),"static code range")

    for site, dest in (
        (0x989cd5,0x1a2b6c0), (0x987d5a,0x989cc0), (0x988da4,0x989cc0),
        (0x985b88,0x987d10), (0x98987b,0x987d10), (0x9898b7,0x977ef0),
        (0x977f00,0x977e40), (0x9707b0,0x985bb0), (0x9774da,0x2717e0),
    ):
        reference(site,dest)
    reference(0x989cee,0x1a2b6c0,"e9")
    reference(0x97dd8d,0x9773c0,"e9")
    reference(0x977450,0x2f3d328,"488b1d")
    check(0x989cc9,"33d24883c10841b8fc030000")
    check(0x989cda,"488d8b0804000033d241b870010000")
    check(0x1a2b6a1,"8bc2488bf9498bc8f3aa")
    check(0x987da0,"894708")
    check(0x987df7,"4c8bc7")
    check(0x9707aa,"498bf8")
    check(0x985bf7,"448bc0")
    check(0x988065,"895f14")
    check(0x988082,"c6878005000001")
    check(0x989836,"4180bc008005000000757b")
    check(0x9774e4,"8b38893b4883c304")

    slot = 8 + 4*69
    for alignment in range(16):
        for displacement,length in ((8,0x3fc),(0x408,0x170)):
            start = alignment + displacement
            written = set()
            for address, size in simd_fill_intervals(start,length):
                written.update(range(address,address+size))
            need(written == set(range(start,start+length)),"SSE coverage")
            if displacement==8:
                need(set(range(alignment+slot,alignment+slot+4)) <= written,"slot coverage")
    need(parent["direct_main_stores"]==70 and parent["aggregate_slot"]==3
         and parent["component_storage_offset"]>=slot+4,"later direct stores")
    return dict(build=98348, pe_sha256=parent["pe_sha256"],
                static_text_sha256=parent["static_text_sha256"], slot=69, entry_offset=slot,
                initial_value_after_reset=0, clean_mode0_computation_value=0,
                clear_rva="0x989cc0", clear_ranges=[[8,1020],[1032,368]],
                sse_range_cases=32, default_entry_and_all_builder_modes_invoke_reset=True,
                serialized_if_vector_count_at_least=70, deferred_copy_preserves_source=True,
                input_stream_can_replace_word=True, actual_TEN_loop64_mode_or_value_observed=False)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("executable",type=Path)
    p.add_argument("static_text",type=Path)
    args=p.parse_args()
    print(json.dumps(verify(args.executable,args.static_text),indent=2))
