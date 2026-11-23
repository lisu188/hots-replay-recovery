"""Verify the unit-pass contribution to the first 98348 fast-sync operand."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from struct import pack, unpack_from
from zlib import crc32

from verify_sync_vector_source import TEXT_BASE, need, verify


def check(exe, static_text):
    pinned = verify(exe, static_text)
    pe, text = exe.read_bytes(), static_text.read_bytes()
    def code(rva, length):
        return text[rva-TEXT_BASE:rva-TEXT_BASE+length]
    windows = [(0x99a1cc,0x99a1d9,"44454a8e7b932bef0b0ae26b"),
               (0x986940,0x986970,"3ca26de2dd652726f8bb0a2e"),
               (0x9a9760,0x9a97e1,"8656734b02aa2a0c61d4d080"),
               (0x9a9bc0,0x9a9bda,"43e4d59a3d56d405a6650bde"),
               (0x9a8f80,0x9a8f9a,"224a248d7da4f329ee3a5b6e"),
               (0x9a90e0,0x9a9182,"a011bfd373a834f0471abfa2"),
               (0x9aa400,0x9aa4fc,"a62ccf26249d89b2ccc6c87b"),
               (0x986970,0x986af7,"a85ea02299ffa9cfece151f8"),
               (0x99a2f5,0x99a31d,"fb37488cacbac050de3e6bba")]
    for start,end,digest in windows:
        need(sha256(code(start,end-start)).hexdigest().startswith(digest),f"window {start:#x}")
    def ref(rva, operand, target):
        prefix = bytes.fromhex(operand)
        actual = code(rva,len(prefix)+4)
        need(actual.startswith(prefix) and rva+len(actual)+unpack_from("<i",actual,len(prefix))[0]==target,
             f"target at {rva:#x}")
    for site,target in [(0x985a60,0x999690),(0x99a1d4,0x986940),(0x985b88,0x987d10),
                        (0x99a0e4,0x9aa400),(0x99270b,0x9a9760),(0x9bbb89,0x9a90e0),
                        (0x9a8f86,0x9a9bc0),(0x97b2fa,0x9a8f80),(0x99a2fd,0x986970)]:
        ref(site,"e8",target)
    ref(0x99a1cc,"8b0d",0x2f3d5b4)
    ref(0x9a977f,"448b15",0x2f3d5b4)
    ref(0x9a97c5,"44890d",0x2f3d5b4)
    ref(0x9a9778,"4c8d1d",0x2648210)
    need(code(0x99a1d2,2)==bytes.fromhex("f7d1")
         and code(0x98696c,4)==bytes.fromhex("89480cc3"),"complement into world+12")
    nt, = unpack_from("<I",pe,60)
    sec = nt+24+unpack_from("<H",pe,nt+20)[0]
    secs = [unpack_from("<8sIIII",pe,sec+i*40) for i in range(unpack_from("<H",pe,nt+6)[0])]
    def pe_offset(rva, length):
        pos, = [raw+rva-base for _,_,base,size,raw in secs if base<=rva and rva+length<=base+size]
        return pos
    initial, = unpack_from("<I",pe,pe_offset(0x2f3d5b4,4))
    need(initial==0xffffffff,"file-backed unit accumulator seed")
    tables = unpack_from("<1024I",pe,pe_offset(0x2648210,4096))
    for state in [0,1,0xffffffff,0x70129ab3]:
        for word in [0,42,0xffffffff,0x14252383]:
            x = state ^ word
            update = tables[x>>24] ^ tables[256+((x>>16)&255)] ^ tables[512+((x>>8)&255)] ^ tables[768+(x&255)]
            need((update^0xffffffff)==crc32(pack("<I",word),state^0xffffffff),"raw CRC32 update")
    return dict(build=98348,pe=pinned["pe_sha256"],static_text=pinned["static_text_sha256"],
                field="+0x0c",unit_pass_store="~u32(RVA 0x2f3d5b4)",
                initial_raw=hex(initial),release_crc_input="le32(unit+0x2b4)",
                update_crc_inputs_after_descriptor_helper=["le32(old unit+0x2b4)","le32(new helper return)"],
                initialize_enables_updates=True,synthetic_native_crc_comparisons=16,
                native_986970="reads/decodes world+0x14",
                actual_ten_loop64_first_operand=None, actual_ten_loop64_slot0=None)


if __name__=="__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("exe",type=Path)
    cli.add_argument("text",type=Path)
    args = cli.parse_args()
    print(json.dumps(check(args.exe,args.text),indent=2))
