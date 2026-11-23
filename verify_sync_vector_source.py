"""Verify the 98348 history-vector producer against the original PE and pinned static text."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from struct import pack, unpack_from
from zlib import crc32


TEXT_BASE = 0xba000
STORE_OFFSETS = (
    0x18,0x27,0x46,0x5b,0x73,0x8b,0xa0,0xb5,0xca,0x114,0x130,0x15a,0x176,
    0x18b,0x1a0,0x1b5,0x1ca,0x1ed,0x202,0x217,0x22c,0x244,0x259,0x26b,0x283,
    0x298,0x2b4,0x2c9,0x2e1,0x2f6,0x30b,0x320,0x338,0x34d,0x365,0x37d,0x392,
    0x3aa,0x3c2,0x3da,0x3f2,0x407,0x427,0x447,0x467,0x487,0x4a7,0x4ca,0x4df,
    0x4f7,0x51a,0x532,0x54a,0x562,0x57a,0x599,0x5b1,0x5c9,0x5de,0x601,0x616,
    0x672,0x688,0x6a0,0x6b8,0x6d0,0x6e8,0x700,0x718,0x72d,
)


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def verify(executable, static_text):
    pe = executable.read_bytes()
    text = static_text.read_bytes()
    pe_hash = sha256(pe).hexdigest()
    text_hash = sha256(text).hexdigest()
    need((len(pe), pe_hash) == (53573840, "efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9"), "original")
    need((len(text), text_hash) == (36581376, "3ef739d3cda2f8c592fcbeb3a2fdb690224458c13916f1abc8d525191a32df83"), "static text")

    def code(rva, length):
        start = rva - TEXT_BASE
        return text[start:start+length]

    def instruction(rva, expected):
        data = bytes.fromhex(expected)
        need(code(rva,len(data)) == data, f"instruction {rva:#x}")

    def reference(rva, target, opcode="e8"):
        instruction(rva, opcode)
        size = len(bytes.fromhex(opcode))
        disp, = unpack_from("<i", code(rva+size,4))
        need(rva+size+4+disp == target, f"reference {rva:#x}")

    for address, length, digest in (
        (0x97d9bd,114,"dfeb9412cf3d7b1185e6"), # last entry, zero-growth/shrink to 72
        (0x97da9f,50,"b15ebd1331605f2f7f98"),  # full previous -> last copy
        (0x9707a0,1860,"28a1af758d56a66113ae"),# main 70 direct vector stores
        (0x987f66,85,"b9058000cf4597ad6e3a"),  # component complement, combine, save
        (0x970dc2,84,"569377f5e4b762ae988b"),  # two complements, native CRC table, slot 1
    ):
        need(sha256(code(address,length)).hexdigest().startswith(digest), f"range {address:#x}")
    for site, dest in (
        (0x97d9b8,0x9889d0), (0x97da9a,0x9889d0), (0x97dacc,0x977ef0),
        (0x98987b,0x987d10), (0x9898b7,0x977ef0), (0x977f00,0x977e40),
        (0x986f2b,0x989810), (0x132f715,0x986f20), (0x132f728,0x977e40),
        (0x132f75b,0x131ce10), (0x132f7be,0x1a6f5e0), (0x132f7f1,0x1a750e0),
        (0x987dfe,0x9707a0), (0x9707b0,0x985bb0), (0x987f61,0x15fc810),
    ):
        reference(site,dest)
    reference(0x986f55,0x977e40,"e9")
    reference(0x970dc2,0x34ef5c0,"8b05")
    reference(0x970dd1,0x2648210,"4c8d15")
    reference(0x987f6a,0x2648210,"4c8d15")
    for rva, expected in (
        (0x97d88e,"418be8"), (0x97d995,"85ed0f85"),
        (0x987e1d,"bbffffffff"), (0x987e3d,"4c8daf08040000"),
        (0x987e5b,"c74587ffffffff"), (0x98802f,"4183fe5c"), (0x98803d,"f7d3"),
        (0x988065,"895f14"), (0x132fd36,"8b83c4130a00"), (0x132fd5d,"8bc8c1e9106633c8"),
    ):
        instruction(rva,expected)

    slots = set()
    for offset in STORE_OFFSETS:
        ins = code(0x9707a0+offset,7)
        if ins.startswith(b"\x44"):  # R8D
            ins = ins[1:]
        need(ins[:2] in (b"\x89\x47", b"\x89\x87"), f"store +{offset:#x}")
        dest = ins[2] if ins[1] == 0x47 else unpack_from("<I", ins, 2)[0]
        need(dest >= 8 and (dest-8) % 4 == 0, "vector store alignment")
        slots.add((dest-8)//4)
    need(slots == set(range(72)) - {3,69}, "direct slot coverage")

    # Read the exact four 256-cell PE tables referenced by both native reducers.
    nt, = unpack_from("<I", pe, 60)
    sections = nt + 24 + unpack_from("<H", pe, nt+20)[0]
    ranges = [unpack_from("<8sIIII", pe, sections+40*i)
              for i in range(unpack_from("<H", pe, nt+6)[0])]
    rva = 0x2648210
    raw, = [start+rva-base for _,_,base,size,start in ranges if base<=rva and rva+4096<=base+size]
    tables = [unpack_from("<256I", pe, raw+1024*i) for i in range(4)]

    def native_mix(words):
        value = 0xffffffff
        for word in words:
            x = value ^ word
            value = (tables[0][x>>24] ^ tables[1][(x>>16)&255] ^
                     tables[2][(x>>8)&255] ^ tables[3][x&255])
        return value ^ 0xffffffff

    comparisons = 0
    for seed in (0,1,0xf00dd00d,0xffffffff):
        for length in (1,92):
            words = [(seed+i*0x1234567) & 0xffffffff for i in range(length)]
            need(native_mix(words) == crc32(pack(f"<{length}I", *words)), "CRC equivalence")
            comparisons += 1
    return dict(build=98348, pe_sha256=pe_hash, static_text_sha256=text_hash,
                ring_entry_bytes=0x588, resize_function="0x97d870", resize_requires_r8d_zero=True,
                selected_vector_words=72, direct_main_stores=len(slots), aggregate_slot=3,
                aggregate_components=92, component_storage_offset=0x408,
                uncovered_slot=69, uncovered_entry_offset=0x11c, scalar_global_rva="0x34ef5c0",
                scalar_crc_slot=1, synthetic_crc_comparisons=comparisons,
                actual_replay_state_acquired=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("static_text", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.static_text), indent=2))
