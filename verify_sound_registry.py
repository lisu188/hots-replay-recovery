"""Bind the class-15 ordinary allocator, release, and initialization to build 98348."""

import argparse
import json
from pathlib import Path
import struct
from sound_object_registry import ObjectRegistry, minimum_allocations
from verify_dispatch_group_native import PE, TEXT, TEXT_RVA, pinned


def verify(exe_path, text_path):
    pe, code=pinned(exe_path,PE),pinned(text_path,TEXT)
    nt=struct.unpack_from("<I",pe,60)[0]
    optional=nt+24
    image_base=struct.unpack_from("<Q",pe,optional+24)[0]
    sh=optional+struct.unpack_from("<H",pe,nt+20)[0]
    def ptr(rva):
        for i in range(struct.unpack_from("<H",pe,nt+6)[0]):
            va,length,off=struct.unpack_from("<III",pe,sh+40*i+12)
            if va<=rva and rva+8<=va+length:
                return struct.unpack_from("<Q",pe,off+rva-va)[0]-image_base
        raise ValueError("Unbacked pointer")
    def op(rva,data):
        raw=bytes.fromhex(data)
        if code[rva-TEXT_RVA:rva-TEXT_RVA+len(raw)]!=raw:
            raise ValueError(f"Unexpected instructions at {rva:x}")
    def rel(rva,disp,n,expected):
        if rva+n+struct.unpack_from("<i",code,rva+disp-TEXT_RVA)[0]!=expected:
            raise ValueError(f"Unexpected target at {rva:x}")
    vtable=0x26b4e98
    if {ofs:ptr(vtable+ofs) for ofs in (0x18,0x20,0x28,0x50)}!={0x18:0xae4390,0x20:0xae8140,0x28:0xae8260,0x50:0xac6280}:
        raise ValueError("Unexpected sound class table")
    sites={
        0xae8140:"b80f000000c3",0xae8260:"b8d8000000c3",0x1ff6397:"c7410800000000",
        0x20d62dc:"e85f0ff2ff488b13488bcbff5250",0x1ff72ad:"488b01ff50208844dd060fb744dd0066ffc0668944dd00",
        0x1ff72ce:"0fb7c80fb7c6488b742440c1e1100bc8894f08",0x1ff7213:"0fb70566971202668944de02488b742430893d56971202",
        0x1ff7273:"488bc64803c00fb744c5028905fc961202eb17",0x1ff7286:"8b35f896120281fe000001007d538d46018905e7961202",
        0x1ff71f7:"48c744c60800000000c644c606ff",0x1ff750f:"896bfc66892bc64302ff48896b04",
        0x1ff755f:"c7870400100002000000",0x1ff7307:"c7470800000000",0x1ff7353:"0fb7d68bce4803d2c1e9100fb7c6663b4cd50066410f45c0",
        0x1ff7392:"897708",0xac62d5:"8b7b08",0xac6388:"897c88fc"
    }
    for site,data in sites.items():
        op(site,data)
    for a,b in [(0x20d409d,0x20d60f0),(0x20d62dc,0x1ff7240),(0x20d40b3,0xac6750),
                (0x20d54e3,0xac64b0),(0xae7f7f,0x1ff7320),(0x1ff740d,0x1ff7240),(0x1ff719b,0x1ff74d0)]:
        op(a,"e8")
        rel(a,1,5,b)
    for a,disp,size,b in [(0x20d6276,3,7,vtable),(0x229e79,3,7,0x4020980),(0x229e8b,3,7,0x4020970),
                          (0x1ff725c,3,7,0x4020980),(0x1ff7268,3,7,0x4120980),
                          (0x1ff7286,2,6,0x4120984),(0x1ff71e3,3,7,0x4020980),
                          (0x1ff7213,3,7,0x4120980),(0x1ff7224,2,6,0x4120980)]:
        rel(a,disp,size,b)
    model=ObjectRegistry()
    a,b=model.allocate(15),model.allocate(19)
    model.retire_slot(a&65535)
    model.retire_slot(b&65535)
    c,d=model.allocate(15),model.allocate(15)
    if (a,b,c,d)!=(0x10002,0x10003,0x20003,0x20002) or minimum_allocations((c,d))!=4:
        raise ValueError("Wrong allocation/retirement order")
    for _ in range(65534):
        model.retire_slot(d&65535)
        d=model.allocate(15)
    if d!=2 or minimum_allocations((d,))!=65536:
        raise ValueError("16-bit generation wrap failed")
    return dict(build=98348,pe_sha256=PE[1],text_sha256=TEXT[1],sound_class=15,class_vtable=hex(vtable),
                pool=hex(0x4020980),free_head=hex(0x4120980),next_virgin=hex(0x4120984),first_slot=2,capacity=65534,
                stride=16,generation_bits=16,generation_increment_on_allocation=True,reuse_order="last retired first",
                generation_wraps=True,ordinary_exhaustion_result=0,explicit_restore_uses_supplied_word=True,
                tested_native_ten_word=None)


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("pe",type=Path)
    cli.add_argument("decoded_text",type=Path)
    args=cli.parse_args()
    print(json.dumps(verify(args.pe,args.decoded_text),indent=2))
