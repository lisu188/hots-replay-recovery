"""Check build-98348 spatial descriptor producers and compare the CRC model with the PE tables."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from struct import pack, unpack_from

from unit_spatial_descriptor import U32, advance, append_handle, descriptor, small_handle
from verify_dispatch_group_native import PE, TEXT, TEXT_RVA, pinned

WINDOWS = (
    (0x9a8660, 0x9a88e4, "01ed365e5b5db0a41709e072"),
    (0x9a89c0, 0x9a8ae7, "42960c2c7267f1da43c3c7ea"),
    (0x9a8b00, 0x9a8c0f, "04716f650eb24dfd76c14231"),
    (0x9a8fc0, 0x9a90d9, "a6d0be8ad9a47a921f96f634"),
    (0x9a90e0, 0x9a9182, "a011bfd373a834f0471abfa2"),
    (0x9aa200, 0x9aa3fa, "2fbcc2f14bf5bc9ec18deb6a"),
    (0x9aa400, 0x9aa4f7, "7dc4ea0ae5708317fce01a21"),
    (0x594626, 0x5946a2, "e9e26a3fc11e79e89008ecae"),
    (0x64bad0, 0x64bb2d, "f6a479aec6aab9d2231faa8c"),
    (0x9a9760, 0x9a97de, "0038e81773f544feeb344325"),
)


def verify(executable, decoded):
    image, text = pinned(executable, PE), pinned(decoded, TEXT)

    def code(rva,size):
        return text[rva-TEXT_RVA:rva-TEXT_RVA+size]

    def reference(rva, prefix):
        opcode = bytes.fromhex(prefix)
        if code(rva,len(opcode)) != opcode:
            raise ValueError(f"Unexpected instruction at {rva:#x}")
        size = len(opcode)+4
        return rva + size + int.from_bytes(code(rva+len(opcode),4),"little",signed=True)

    nt, = unpack_from("<I",image,60)
    section_table = nt + 24 + unpack_from("<H",image,nt+20)[0]
    sections = [unpack_from("<III", image, section_table+40*i+12)
                for i in range(unpack_from("<H",image,nt+6)[0])]

    def physical(rva,size):
        offset, = [raw+rva-base for base,length,raw in sections if base <= rva and rva+size <= base+length]
        return image[offset:offset+size]

    for start,end,digest in WINDOWS:
        if not sha256(code(start,end-start)).hexdigest().startswith(digest):
            raise ValueError(f"Changed native function at {start:#x}")
    for name,name_rva,opcode,offset_site,offset,call in (
        (b"Radius",0x594626,"488d0d",0x594645,0xf0,0x59465e),
        (b"DeadRadius",0x594679,"488d05",0x594673,0xf4,0x59469d),
    ):
        if (physical(reference(name_rva,opcode),len(name)+1) != name+b"\0" or
                code(offset_site,6) != b"\x41\xb9"+pack("<I",offset) or reference(call,"e8") != 0x1601160):
            raise ValueError("Catalog field registration changed")
    for table, call_offset in ((0x9a88e4,5),(0x20506ac,4)):
        arms = unpack_from("<16I",code(table,64))
        targets = [reference(arm+call_offset,"e8") for arm in arms]
        if table == 0x9a88e4:
            spatial = targets
        elif targets != spatial or len(set(spatial)) != 16:
            raise ValueError("Spatial and Galaxy unit position decoders differ")
    if code(0x2050358,4) != bytes.fromhex("0fb64044") or code(0x64bb29,4) != bytes.fromhex("443b4110"):
        raise ValueError("Owner/tag member mismatch")
    for pos,dest in ((0x9a9103,0x9a8660),(0x9a910d,0x9a8fc0),(0x9a9120,0x9a8b00),
                     (0x9aa428,0x9a8660),(0x9aa43a,0x9aa200),(0x9aa44d,0x9a8b00)):
        if reference(pos,"e8") != dest:
            raise ValueError("Spatial operation edge mismatch")
    base = reference(0x9a8b0d,"488d3d")
    tables = unpack_from("<1024I",physical(base,4096))
    if (small_handle(1,2,1,3), append_handle(17,deferred=True), append_handle(17,deferred=False)) != (
            0x240405, 0x230001, 0x230003):
        raise ValueError("Unexpected cell, bucket or list encoding")
    if code(0x9a9bda,6) != bytes.fromhex("41b800800000") or reference(0x9a9be0,"488d0d") != 0x35a2100:
        raise ValueError("Unexpected small grid extent")
    for cx,cy,depth,used in ((0,128,0,0),(1,1,0x3ff,0),(1,1,0,15)):
        try:
            small_handle(cx,cy,depth,used)
        except ValueError:
            continue
        raise ValueError("Accepted impossible ordinary insertion")
    for radius, flags, state3c, state41, expected in (
        (0x400,0x1000001,0,0,0x01000000),(0x401,0x1000000,0,0,0x12000000),
        (0,0,16,0,0x80000000),(0,0,0,16,0x80000000),(0x4000,0,0,0,0),
    ):
        raw = descriptor(0,0,0,0,radius,collision_flags=flags,state38=0,type_de=0,
                         state4c=0,state3c=state3c,state41=state41)
        if raw != pack("<IHHI",expected,0,0,radius):
            raise ValueError("Unexpected flags or radius quantization")

    def fold_u32(raw,word):
        z = raw ^ word
        return tables[z>>24] ^ tables[256+(z>>16 & 255)] ^ tables[512+(z>>8 & 255)] ^ tables[768+(z & 255)]

    def fold_raw(raw,entry,handles):
        if entry is not None:
            word, cx, cy, radius = unpack_from("<IHHI",entry)
            raw = fold_u32(raw,word)
            for sample in (cx,cy):
                for byte in (sample & 255, sample >> 8):
                    raw = (raw >> 8) ^ tables[(raw ^ byte) & 255]
            raw = fold_u32(raw,radius)
        for handle in handles:
            raw = fold_u32(raw,handle)
        return raw

    comparisons = 0
    for x,y,r in ((0,0,0),(0x21600,0x48000,14336),(-8193,-1,0x3c00),(0x7fffffff,-0x80000000,0x7fffffff)):
        for bits in range(16):
            entry = descriptor(0x11000001, 12, x, y, r, collision_flags=(1<<24 if bits&1 else 1),
                               state38=0x40 if bits&2 else 0, type_de=8 if bits&4 else 0,
                               state4c=1 if bits&8 else 255, state3c=0, state41=0)
            word,cx,cy,rad = unpack_from("<IHHI",entry)
            # Independent arithmetic for the two integer cells and upper flag nibble.
            cells = tuple((abs(v)//2 * (-1 if v < 0 else 1)) // 4096 & 65535 for v in (x,y))
            if word >> 28 != bits or (cx,cy) != cells or rad != (r & U32):
                raise ValueError("Descriptor field disagreement")
            # Use a valid ordinary handle for the CRC differential, including signed-coordinate descriptor tests.
            h = small_handle(1,2,1,3)
            pending = append_handle(17,deferred=True)
            large = append_handle(17,deferred=False)
            for seed in (U32,0,0x01234567):
                for desc,handles in ((entry,(h,)),(entry,(h,h)),(entry,(pending,large)),(None,(h,))):
                    if advance(seed,desc,*handles) != fold_raw(seed,desc,handles):
                        raise ValueError("PE table and CRC implementation differ")
                    comparisons += 1
    return dict(build=98348, executable_sha256=PE[1], static_text_sha256=TEXT[1], verified_code_ranges=len(WINDOWS),
                position_decoder_variants=len(spatial), catalog_fields={"Radius":240,"DeadRadius":244},
                crc_differential_cases=comparisons, crc_input_bytes_per_descriptor=12, target_fast_crc_verified=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe",type=Path)
    parser.add_argument("text",type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.exe,args.text),indent=2))
