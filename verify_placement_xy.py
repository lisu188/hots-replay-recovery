"""Verify the native build-98348 position reader's calls, literal table and finite map input."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from

from placement_xy import generate
from verify_dispatch_group_native import PE, TEXT, TEXT_RVA, pinned


WINDOWS = (
    (0xA2EA30, 0xA2EAF6, "bc44d798569c7e38f7c17937"),
    (0xA30AEF, 0xA30B3C, "72bb96b78ff1eadb708c4784"),
    (0xA316C7, 0xA31714, "8f20bed2ec40df77a07f79d1"),
    (0xA297C0, 0xA2986D, "1f2bb611225b556157e116c7"),
    (0xA29B50, 0xA29B95, "d7e4949e99dcd55fec5a404a"),
    (0x28A310, 0x28A3DE, "5838a916db0544ca87d65c1b"),
    (0x2D14E0, 0x2D184B, "ec9c562d565ebc665250436f"),
    (0xA2E3DB, 0xA2E3ED, "76dd17bc3c0d00af6593cb6a"),
)

CALLS = {
    0xA2EAAD: 0xA30A80, 0xA2EAF1: 0xA31680, 0xA3170F: 0xA297C0,
    0xA29815: 0x16000D0, 0xA29826: 0x28A310, 0xA29849: 0xA29B50,
    0xA29B73: 0x16000D0, 0xA29B8A: 0x28A310, 0x28A376: 0x284100,
    0x28A38F: 0x2D14E0,
}


def verify(exe, verified_text, package):
    pe = pinned(exe, PE)
    text = pinned(verified_text, TEXT)
    nt, = unpack_from("<I", pe, 60)
    table = nt + 24 + unpack_from("<H", pe, nt+20)[0]
    sections = [unpack_from("<III", pe, table+40*i+12)
                for i in range(unpack_from("<H", pe, nt+6)[0])]

    def data(rva, length):
        offset, = [raw+rva-base for base, size, raw in sections
                   if base <= rva and rva+length <= base+size]
        return pe[offset:offset+length]

    for start, end, expected in WINDOWS:
        if sha256(text[start-TEXT_RVA:end-TEXT_RVA]).hexdigest()[:24] != expected:
            raise ValueError("Native instructions changed")
    for addr, target in CALLS.items():
        off = addr - TEXT_RVA
        opcode = 0xe9 if addr == 0xa2eaf1 else 0xe8
        if text[off] != opcode or addr+5+unpack_from("<i",text,off+1)[0] != target:
            raise ValueError("Native reader call changed")
    for addr, word in ((0x2f70140,b"ObjectUnit"), (0x2f70370,b"position"),
                       (0x2f70380,b"Position")):
        ptr, length = unpack_from("<QI", data(addr,12))
        if length != len(word) or data(ptr-0x140000000,length) != word:
            raise ValueError("Native map key changed")
    divisors = unpack_from("<13Q",data(0x2f2f7e0,104))
    if divisors != tuple(10**i for i in range(12,-1,-1)) or data(0x2641f1c,2) != b",\0":
        raise ValueError("Decimal weights or vector delimiter changed")
    return dict(
        build=98348, native_windows=len(WINDOWS), native_calls_and_tail_jumps=len(CALLS),
        decimal_weights_verified=len(divisors), max_fractional_digits=12,
        scriptable_fractional_expressions_supported=False,
        fixed_unit_denominator=4096, map=generate(package),
    )


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("exe","text","map"):
        parser.add_argument(name,type=Path)
    a=parser.parse_args()
    print(json.dumps(verify(a.exe,a.text,a.map),indent=2))
