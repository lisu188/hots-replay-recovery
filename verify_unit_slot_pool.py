"""Verify the 98348 unit-pool operation profile on the original PE and pinned static text."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from struct import iter_unpack, unpack_from

from unit_slot_pool import GENERATION_MASK, SLOT_LIMIT, UnitSlotPool

PE = (53573840, "efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9")
TEXT = (36581376, "3ef739d3cda2f8c592fcbeb3a2fdb690224458c13916f1abc8d525191a32df83")
TEXT_RVA = 0xBA000
MANAGER = 0x2F3D470


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def pinned(path, expected):
    data = path.read_bytes()
    need((len(data), sha256(data).hexdigest()) == expected, "Unexpected input size or SHA-256")
    return data


def verify(executable, transformed_text):
    pe = pinned(executable, PE)
    code = pinned(transformed_text, TEXT)
    nt, = unpack_from("<I", pe, 0x3C)
    optional = nt + 24
    section_table = optional + unpack_from("<H", pe, nt + 20)[0]
    sections = [unpack_from("<8sIIII", pe, section_table + 40*i)
                for i in range(unpack_from("<H", pe, nt + 6)[0])]
    text_section, = [row for row in sections if row[0].rstrip(b"\0") == b".text"]
    need(text_section[2] <= TEXT_RVA and TEXT_RVA + len(code) <= text_section[2] + text_section[1],
         "Static window outside the executable text section")

    def data(rva, length):
        offset, = [raw + rva - start for _, _, start, count, raw in sections
                   if start <= rva and rva + length <= start + count]
        return pe[offset:offset+length]

    def check(rva, expected):
        binary = bytes.fromhex(expected)
        off = rva - TEXT_RVA
        need(code[off:off+len(binary)] == binary, f"Instruction mismatch at {rva:#x}")

    def rel(rva, opcode, destination):
        check(rva, opcode)
        off = rva + len(bytes.fromhex(opcode))
        disp, = unpack_from("<i", code, off - TEXT_RVA)
        need(off + 4 + disp == destination, f"Reference mismatch at {rva:#x}")

    pdata, size = unpack_from("<II", pe, optional + 136)
    intervals = [(a,b) for a,b,_ in iter_unpack("<III",data(pdata,size))]
    for lo, hi in [(0x996D90,0x99703F), (0x990AF0,0x990C98), (0x9926C0,0x99284B),
                   (0x997400,0x997539), (0x9859A3,0x985B0F), (0x999690,0x999976)]:
        need(any(a == lo and hi < b for a,b in intervals), "Missing function extent")
    # Binding to unit creation, separately from adjacent ability/behavior limit diagnostics.
    check(0x996FAC, "ba01000000")
    rel(0x996FB1, "488d0d", MANAGER)
    rel(0x996FB8, "e8", 0x990AF0)
    check(0x996FBD, "488bd84885c00f858b000000")
    for site in (0x99702A,0x99703F):
        rel(site, "488d05", 0x26A8890)
    literal = b"GameDebug/UnitLimitReached\0"
    need(data(0x26A8890,len(literal)) == literal and pe.count(literal) == 1, "Unit identity")
    need(data(MANAGER,12) == b"\xff"*8 + b"\0"*4, "Unexpected initial list heads or count")
    # Pop ready first; only then allocate the next clean slot in a 16-entry chunk.
    check(0x990B0A,"4c8d4110448be241d1ef488d51044180e701")
    rel(0x990B1F,"e8",0x997C80)
    check(0x990B24,"488bd84885c00f8521010000")
    check(0x997C84,"0fb7024c8bd1b9ffff00004d8bc84c8bc2663bc1750733c0")
    rel(0x997CE7,"e8",0x997B80)
    rel(0x990B40,"8b35",0x34F02C0)
    check(0x990B46,"81feff0300000f83d7000000")
    check(0x990B58,"8d4e01")
    rel(0x990B5D,"890d",0x34F02C0)
    check(0x990B69,"4183e60f")
    check(0x990B73,"8bc648c1e804")
    check(0x990BCD,"4169def0020000")
    check(0x990BD9,"8b431025ffff3f00c1e6160bc68bc889431081e1ffff3f0081f9ffff3f007218")
    check(0x990C11,"85c9750b250100c0ff83c801894310")
    check(0x990C29,"4584ff74784c8d4712488bcf")
    # Increment only the generation; select pending or exhausted list and push its new head.
    rel(0x992775,"e8",0x997B80)
    rel(0x99277E,"4c8d0d",MANAGER+6)
    check(0x992791,"448d40014433c04181e0ffff3f004433c0")
    rel(0x9927A2,"488d05",MANAGER+2)
    check(0x9927A9,"458bd8458946104181e3ffff3f004181fbffff3f004c0f42c8")
    check(0x99281F,"66418946146641897e1666458901")
    # Drain pops pending head, prepends to ready, and repeats.
    check(0x997430,"410fb7460266413bc40f84ff000000")
    rel(0x997486,"e8",0x997B80)
    check(0x99748B,"4885db0f84aa000000448b4b104d8d4604410fb70041c1e916")
    check(0x9974E7,"410fb70066894314664489631666458908")
    rel(0x997539,"e9",0x997430)
    rel(0x997570,"488d0d",MANAGER)
    rel(0x997577,"e9",0x997400)
    rel(0x985A60,"e8",0x999690)
    rel(0x999976,"e8",0x9926C0)
    rel(0x985B0F,"e8",0x997570)

    pool = UnitSlotPool()
    opening = [pool.allocate() for _ in range(SLOT_LIMIT)]
    need(opening == [(i,1) for i in range(SLOT_LIMIT)] and pool.allocate() is None, "Fresh slots")
    pool.retire(opening[11])
    pool.retire(opening[3])
    need(pool.allocate() is None, "Pending reused too early")
    pool.drain()
    first = pool.allocate()
    pool.retire(opening[7])
    pool.drain()
    reuse = [first, pool.allocate(), pool.allocate()]
    need(reuse == [(11,2),(7,2),(3,2)], "Ready-list order")
    return dict(pe_bytes=PE[0], pe_sha256=PE[1], transformed_bytes=TEXT[0], transformed_sha256=TEXT[1],
                unit_manager_rva=hex(MANAGER), unit_create_call_rva="0x996fb8", unit_stride=0x2f0,
                chunk_slots=16, clean_slots=SLOT_LIMIT, unit_tag_offset=0x10, first_generation=1,
                ordinary_generation_max=GENERATION_MASK-1, quarantined_generation=GENERATION_MASK,
                pending_head_offset=2, ready_head_offset=4, exhausted_head_offset=6,
                actual_retire_rva="0x9926c0", drain_rva="0x997400",
                dispatch_release_then_drain=["0x985a60","0x985b0f"], model_batch_reuse=reuse,
                every_tracker_death_is_retirement=False, full_simulation_verified=False)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("executable", type=Path)
    p.add_argument("static_text", type=Path)
    args = p.parse_args()
    print(json.dumps(verify(args.executable,args.static_text), indent=2))
