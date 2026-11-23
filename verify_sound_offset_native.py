"""Verify build 98348's event-46 producer, registration, codec, and two consumer comparisons."""

import argparse
import json
from pathlib import Path
import struct
from native_game_events import PROFILE, _profile
from verify_dispatch_group_native import PE, TEXT, TEXT_RVA, pinned


def verify(exe_path, text_path):
    exe, code = pinned(exe_path, PE), pinned(text_path, TEXT)
    nt = struct.unpack_from("<I", exe, 60)[0]
    optional = nt + 24
    base = struct.unpack_from("<Q", exe, optional + 24)[0]
    header = optional + struct.unpack_from("<H", exe, nt + 20)[0]
    sections = [struct.unpack_from("<III", exe, header + 40*i + 12)
                for i in range(struct.unpack_from("<H", exe, nt + 6)[0])]
    def pe(rva, fmt):
        size = struct.calcsize(fmt)
        for start, length, raw in sections:
            if start <= rva and rva+size <= start+length:
                return struct.unpack_from(fmt, exe, raw+rva-start)[0]
        raise ValueError("Unbacked PE address")
    def relative(site, displacement, end):
        return site+end+struct.unpack_from("<i", code, site+displacement-TEXT_RVA)[0]
    def op(site, hex_bytes):
        data = bytes.fromhex(hex_bytes)
        if code[site-TEXT_RVA:site-TEXT_RVA+len(data)] != data:
            raise ValueError(f"Unexpected native instructions at {site:x}")
    def branch(site, target, opcode):
        op(site, opcode)
        if relative(site,1,5) != target:
            raise ValueError(f"Unexpected native branch at {site:x}")

    root = pe(0x27BEBD8, "<I")
    types, roots = _profile(PROFILE)
    if root != roots[46] or root != 441 or types[root]["field_types"] != [442]:
        raise ValueError("Schema root disagreement")
    for slot, target in ((0x2665958,0x77AB10),(0x26EEF68,0xC27FC0)):
        if pe(slot, "<Q") != base+target:
            raise ValueError("Unexpected listener or serializer")
    if pe(0x26EEED0 + 5*4, "<I") != 0x3002E:
        raise ValueError("Unexpected event-to-listener binding")
    if struct.unpack_from("<I", code, 0xC286D8+5*4-TEXT_RVA)[0] != 0xC28157:
        raise ValueError("Unexpected listener dispatch")
    for loc,disp,size,target in [
            (0x77BB95,3,7,0x2665950),(0x1353484,3,7,0x2665950),
            (0x77AB10,3,7,0x27BEBD8),(0xAC60BD,3,7,0x4020970),
            (0xAC60AC,3,7,0x2F71A08),(0xC27F40,3,7,0x26EEF60),
            (0xC27F4F,3,7,0x26EEED0),(0xC28161,3,7,0x4020970)]:
        if relative(loc,disp,size) != target:
            raise ValueError(f"Unexpected native global at {loc:x}")
    for site,target in [(0xAC6110,0x6899E0),(0xAC64ED,0x6899E0),(0xAC67B5,0x6899E0),
                        (0x689AB4,0x77BB60),(0xC27F76,0x1330160),
                        (0xC2817E,0xAC61B0),(0xC2818C,0xA8F5B0)]:
        branch(site,target,"e8")
    branch(0x77AB28,0x1A74220,"e9")
    sites = {
        0x77BB66:"488bd9", 0x77BB81:"c741102e000300", 0x1353470:"c740102e000300",
        0x77BBAE:"8b4308894130", 0x77AB17:"4c8d4930", 0x689AAF:"488b4c2460",
        0xAC62D5:"8b7b08", 0xAC6388:"897c88fc", 0xAC60B5:"0fb73c8848c1e704",
        0xAC60C4:"807f060f",0xAC60CE:"488b7f08",0xAC610B:"48897c2420",
        0xC27F67:"448bcb8b17",0xC27F7B:"ffc3488d7f0483fb24",
        0xC28157:"8b4b300fb7c148c1e004",0xC28168:"8078060f75184c8b40084d85c0740f",
        0xC28183:"8b4b308bd10fb64b2a",0xAC61C7:"0fb6cad3e00987d0000000",
        0xA8F5BB:"448bd2",0xA8F630:"837828037516443950407510418bc9ba01000000d3e2099068010000",
    }
    for loc, data in sites.items():
        op(loc,data)
    return dict(build=98348, pe_bytes=PE[0], pe_sha256=PE[1], text_bytes=TEXT[0], text_sha256=TEXT[1],
                event=46, native_payload_root=root, listener_case=5, allocation_list_word_from_object=8,
                producer_payload_offset=48, object_table_index_mask=65535, slot_stride=16, required_class=15,
                object_mask_offset=208, pending_kind=3, pending_handle_offset=64, pending_mask_offset=360,
                pending_equality_bits=32, recovered_target_handle=None)


if __name__ == "__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("pe", type=Path)
    cli.add_argument("decoded_text", type=Path)
    args=cli.parse_args()
    print(json.dumps(verify(args.pe,args.decoded_text),indent=2))
