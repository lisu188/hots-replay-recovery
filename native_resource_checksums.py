"""Check the 98348 replay map/mod comparison and serialize explicit type-815 inputs."""

import argparse
from collections.abc import Sequence
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from struct import pack, unpack_from
from zlib import crc32

from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from portable_sync_98348 import _spec, _Writer, PROGRAM_SHA256
from verify_dispatch_group_native import PE, TEXT, TEXT_RVA, pinned


def mod_checksum(words):
    """Compute the mod DWORD from an ordered 98348 history entry supplied by the caller."""
    if not isinstance(words, Sequence) or isinstance(words, (str, bytes, bytearray, memoryview)) or len(words) > 255:
        raise ValueError("Expected an ordered sequence of at most 255 unsigned words")
    words = tuple(words)
    if len(words) > 255 or any(type(n) is not int or not 0 <= n <= 0xffffffff for n in words):
        raise ValueError("Expected at most 255 unsigned 32-bit words")
    wire = bytes([len(words)]) + b"".join(pack(">I", n) for n in words)
    return crc32(wire + bytes(4))


def serialized_mod_vector_crc(advertised):
    """Undo the four appended zero bytes to recover the CRC of the serialized vector."""
    if type(advertised) is not int or not 0 <= advertised <= 0xffffffff:
        raise ValueError("Expected an unsigned 32-bit checksum")
    table = {}
    for low in range(256):
        v = low
        for _ in range(8):
            v = (v >> 1) ^ (0xedb88320 if v & 1 else 0)
        table[v >> 24] = (v, low)
    state = advertised ^ 0xffffffff
    for _ in range(4):
        value, low = table[state >> 24]
        state = ((state ^ value) << 8) | low
    result = state ^ 0xffffffff
    if crc32(bytes(4),result) != advertised:
        raise ValueError("CRC inverse failed")
    return result


def map_word(package):
    with closing(MPQArchive(package)) as archive:
        header = read_member(archive,"DocumentHeader")
    if len(header) < 32 or header[:12] != b"oreH\x08\0\0\0oreH":
        raise ValueError("Expected a recorded Heroes version-8 DocumentHeader")
    return unpack_from("<I",header,0x1c)[0]


WINDOWS = {
    "validation_condition": (0xcfa3d0,0xcfa469,"8842730ed608d98d27fb"),
    "document_name": (0x193190,0x1931cf,"bcb2dd483e5b31792041"),
    "map_slot_walk": (0x7bda68,0x7bdaae,"72b5a9b226bcd780e845"),
    "document_stream": (0x7bd8d8,0x7bd968,"d1191cb8647755d30763"),
    "member_reader": (0x7bd172,0x7bd28a,"b79e60bd82b4453c4f32"),
    "version8_subfields": (0x271380,0x27140d,"2e9818600a01c5fe89a7"),
    "cursor": (0x271833,0x271847,"1059ae188e680e8bc0f7"),
    "compare_mod": (0xcfa471,0xcfa48f,"e284ba4060a9bdfbc641"),
    "compare_map": (0xcfa577,0xcfa5d9,"9db76bed2869df0d5eac"),
    "setup_map_load": (0xe05b55,0xe05b69,"176aeb32f3640537cefc"),
    "setup_map_store": (0xe05dc9,0xe05dd3,"3f0f3db4e7c8e2cabf8e"),
    "setup_mod_store": (0xe06006,0xe06024,"df3597a84d86d5ce344e"),
    "second_mod_store": (0xe06cb1,0xe06cbc,"a0fbd4ce1abaa8b1378f"),
    "mod_crc": (0xe04850,0xe04982,"d160c5a08de76105b196"),
    "mod_entry_selector": (0x980570,0x9805a1,"69c5d3fcb05b2500f511"),
    "gameplay_entry_selector": (0x986f20,0x986f5a,"73261e3f2a285d6534c1"),
    "index_update_a": (0x97dad1,0x97dae3,"8d1e080c065961a93245"),
    "index_update_b": (0x987767,0x987779,"7e1317ca4107f0a4572e"),
}


def verify(pe_path,text_path):
    image, text = pinned(pe_path,PE), pinned(text_path,TEXT)
    def code(r,n):
        return text[r-TEXT_RVA:r-TEXT_RVA+n]
    nt, = unpack_from("<I",image,60)
    nsec, = unpack_from("<H",image,nt+6)
    sh = nt + 24 + unpack_from("<H",image,nt+20)[0]
    def phys(r,n):
        for i in range(nsec):
            va,size,pos = unpack_from("<III",image,sh+40*i+12)
            if va <= r and r+n <= va+size:
                return image[pos+r-va:pos+r-va+n]
        raise ValueError("Unbacked physical input")
    def reference(r,opcode,target):
        n = len(opcode)
        if code(r,n)!=opcode or r+n+4+unpack_from("<i",code(r+n,4))[0]!=target:
            raise ValueError(f"Instruction reference differs at {r:x}")
    for k,(a,b,h) in WINDOWS.items():
        if not sha256(code(a,b-a)).hexdigest().startswith(h):
            raise ValueError(f"Unexpected native window {k}")
    if phys(0x26ab0a0,15)!=b"DocumentHeader\0" or unpack_from("<I",phys(0x27bec98,4))[0]!=815:
        raise ValueError("File member name or root type differs")
    for field,offset in [(14,0x454),(17,0x960)]:
        if unpack_from("<Q",phys(0x27c4428+8*(field+1),8))[0]!=offset:
            raise ValueError("Active description offsets changed")
    program = phys(0x27c6960,13744)
    if sha256(program).hexdigest()!=PROGRAM_SHA256:
        raise ValueError("Physical type program differs")
    _spec()
    for off,expected in [(10795,"8e0000ffff00000330"),(10804,"01018800ff00000331"),
                         (10813,"100000015c"),(7348,"1000000003"),(4805,"0905a000000000ffffffff")]:
        blob=bytes.fromhex(expected)
        if program[off:off+len(blob)]!=blob:
            raise ValueError("Physical type-815 declaration changed")
    reference(0x193194,b"\x48\x8d\x05",0x26ab0a0)
    reference(0xe048af,b"\x44\x8b\x05",0x27bec98)
    reference(0x980580,b"\x8b\x05",0x34f0200)
    reference(0x986f30,b"\x8b\x05",0x2f3d318)
    if code(0xcfa447,16) != bytes.fromhex("8b87e800010083e80283f801410f96c6"):
        raise ValueError("Validation predicate differs")
    for site,target in [(0x7bda9e,0x7bd8b0),(0x7bd943,0x7bd160),(0x7bd9dc,0x7bd160),
                        (0x7bd24e,0x271370),(0x7bd27b,0x2717e0),(0xcfa47c,0xe04850),
                        (0xcfa588,0x7bda30),(0xe05b62,0x7bda30),(0xe06006,0xe04850),
                        (0xe06cb1,0xe04850),(0xe0486b,0x980570),(0xe048d3,0x1a6f5e0),
                        (0x98057b,0x989810),(0x986f2b,0x989810)]:
        reference(site,b"\xe8",target)
    table=unpack_from("<1024I",phys(0x2648210,4096))
    cases=[[],[0],[0x12345678],[0,0xffffffff],[i*0x01010101 for i in range(72)],
           [i*0x01010101 for i in range(255)]]
    for words in cases:
        writer = _Writer()
        writer.bits(len(words),8)
        for n in words:
            writer.bits(n,32)
        state = crc32(writer.raw)^0xffffffff
        state = (table[768+(state&255)]^table[512+((state>>8)&255)]^
                 table[256+((state>>16)&255)]^table[state>>24])^0xffffffff
        if state!=mod_checksum(words) or crc32(writer.raw)!=serialized_mod_vector_crc(state):
            raise ValueError("Native table/bit writer disagrees with mod CRC")
    return dict(build=98348,pe_sha256=PE[1],text_sha256=TEXT[1],windows=len(WINDOWS),
                map_member="DocumentHeader",map_version=8,map_declared_le32_offset=28,
                description_offsets=dict(map=0x454,mod=0x960),type_program_sha256=PROGRAM_SHA256,
                mod_wire_type_chain=[815,816,817,348,3],mod_crc_input="u8 count followed by BE32 words and four zero bytes",
                maximum_words=255,synthetic_checks=len(cases),mod_history_index_global_rva=0x34f0200,
                validation_owner_field_0x100e8=[2,3],compared_mismatch_codes=dict(mod=16,map=17),historical_target_mod_words_known=False,
                gameplay_vector_identity_at_comparison_verified=False)


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("pe",type=Path)
    cli.add_argument("static_text",type=Path)
    cli.add_argument("--map",type=Path)
    args=cli.parse_args()
    report=verify(args.pe,args.static_text)
    if args.map:
        report["map_package_sha256"]=sha256(args.map.read_bytes()).hexdigest()
        report["map_advertised_word"]=f"{map_word(args.map):08x}"
    print(json.dumps(report,indent=2))
