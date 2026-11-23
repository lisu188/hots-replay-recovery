"""Verify the 98348 recording source, mode-2 staging field and committed setup cache boundary."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import struct

import native_setup
from verify_dispatch_group_native import PE, TEXT, TEXT_RVA, pinned


# Headless IDA windows on the pinned PE text. No executable is mapped for execution.
WINDOWS = {
    "record_context_and_mode": (0x132B0F0, 0x132B137),
    "record_branch_and_temporary": (0x132B3C9, 0x132B410),
    "record_fifth_argument": (0x132B458, 0x132B483),
    "package_home_slots": (0x134FBF0, 0x134FC21),
    "package_to_member": (0x134FFAE, 0x134FFBA),
    "writer_root_copy": (0x1350F9D, 0x1350FAF),
    "writer_root_serializer": (0x1351096, 0x13510EF),
    "snapshot_input": (0xDB9A54, 0xDB9A62),
    "snapshot_copy_registers": (0xDB9AA7, 0xDB9AB8),
    "snapshot_copy": (0xDB9B99, 0xDB9BB9),
    "snapshot_global_select": (0xD04530, 0xD0456D),
    "snapshot_global_producer": (0xD03E90, 0xD03EE7),
    "snapshot_owner_save": (0xD01998, 0xD019C2),
    "startup_setup_getter": (0xD00F76, 0xD00FA5),
    "startup_owner_copy": (0xD01065, 0xD0108F),
    "reader_to_stored": (0xCFECCD, 0xCFECE0),
    "mode2_staging_preparation": (0xE02C2F, 0xE02C50),
    "staging_destination": (0xE0572A, 0xE05761),
    "staging_description_copy": (0x1343FC4, 0x1343FFF),
    "mode2_speed": (0xE02D87, 0xE02DEE),
    "mode4_only_copyback": (0xE02E82, 0xE02ECD),
    "final_setter_arguments": (0xE02F8A, 0xE02FAF),
    "setter_copy": (0x133B8B3, 0x133B8C8),
    "cache_compute": (0x133D0AC, 0x133D14C),
    "cache_root_serializer": (0x133D3A2, 0x133D3C6),
}

CALLS = {
    0xD00F9A: 0xD008C0, 0xD0108A: 0xCF96B0, 0xD019BD: 0xD03E90,
    0xD03EA5: 0xDB9A40, 0xD04560: 0xCF96B0, 0xDB9BA6: 0xCF96B0,
    0x132B3DD: 0xD04E60, 0x132B3F4: 0xD04530, 0x132B409: 0xDB9A40,
    0x132B47E: 0x134FBF0, 0x134FFB5: 0x1350F80, 0x1350FA7: 0xCF96B0,
    0x13510EA: 0x1A6F5E0, 0x134DF39: 0xCF96B0, 0xCFEC51: 0x134DD30, 0xCFECDB: 0xCF96B0,
    0xE02C4B: 0xE05180, 0xE0574D: 0x1343FB0, 0x1343FD9: 0xCF8310,
    0xE02DB7: 0x13308E0, 0xE02E8C: 0x133E410, 0xE02EC6: 0xCF96B0,
    0x133B8C3: 0x133E420, 0x133D3C1: 0x1A6F5E0,
}


def verify(image_path, text_path):
    image, code = pinned(image_path, PE), pinned(text_path, TEXT)
    nt = struct.unpack_from("<I", image, 60)[0]
    optional = nt + 24
    section_table = optional + struct.unpack_from("<H", image, nt + 20)[0]
    base = struct.unpack_from("<Q", image, optional + 24)[0]
    def physical(rva, size):
        for i in range(struct.unpack_from("<H", image, nt + 6)[0]):
            addr, length, raw = struct.unpack_from("<III", image, section_table + 40 * i + 12)
            if addr <= rva and rva + size <= addr + length:
                pos = raw + rva - addr
                return image[pos:pos+size]
        raise ValueError("Range outside physical sections")
    def u32(rva):
        return struct.unpack("<I", physical(rva, 4))[0]
    def at(rva, size):
        return code[rva-TEXT_RVA:rva-TEXT_RVA+size]
    def rel(insn, off, size):
        return insn + size + struct.unpack("<i", at(insn + off, 4))[0]

    for site, target in CALLS.items():
        if at(site, 1) != b"\xe8" or rel(site, 1, 5) != target:
            raise ValueError(f"Unexpected call at {site:x}")
    for slot, target in ((0xE0, 0x1324B70), (0xF0, 0x133B890), (0x1B0, 0x133B790),
                         (0x1A8, 0x1324B80), (0x200, 0x132B820), (0x358, 0x1327C00)):
        if struct.unpack("<Q", physical(0x27BC518 + slot, 8))[0] != base + target:
            raise ValueError("Unexpected base table")
    probes = {
        0x1324B70: "488d81783f0800c3", 0x1324B80: "488d81d8030000c3",
        0x1327C00: "8b8110d90100c3",
        0xD04E60: "0fb605", 0xD019B6: "488d8ff8650300",
        0x132B3FB: "4c8d86783f0800", 0x132B402: "4588b83cd40100",
        0x132B466: "4889442420", 0x134FFAE: "488b557f",
        0x13510AB: "4c8d8f78de0000", 0xE02DD1: "8985e89a0200",
        0xE02E99: "4981c660940100", 0x133E420: "c6813cd4010000e9",
    }
    for site, op in probes.items():
        if at(site, len(op)//2).hex() != op:
            raise ValueError(f"Unexpected instruction at {site:x}")
    if rel(0xD04E60, 3, 7) != 0x379BC88 or rel(0xD04556, 3, 7) != 0x377E7C8:
        raise ValueError("Unexpected snapshot selector")
    if rel(0x133E427, 1, 5) != 0xCF96B0:
        raise ValueError("Unexpected cache-invalidating copy")
    if (u32(0x27C9F24), u32(0x27BEC74)) != (888, 775):
        raise ValueError("Wrong physical schema roots")
    desc = physical(0x27C4428, 232)
    if sha256(desc).hexdigest() != "dea2828a3589e6de24d022538897895ec0b2d99d0069e1c292a292257da63ba9":
        raise ValueError("Unexpected game description offsets")
    game_speed, = struct.unpack_from("<Q", desc, 8 * (1 + 3))
    if 0x29AE8 - 0x1D3A0 != 0xC308 + game_speed or 0x25768 - 0x19460 != 0xC308:
        raise ValueError("Staging field mismatch")
    schema = Path(native_setup.__file__).with_name("test_native_setup_official_schema.json").read_bytes()
    if sha256(schema).hexdigest() != native_setup.OFFICIAL_TYPES_SHA256:
        raise ValueError("Unexpected official setup field declarations")
    if json.loads(schema)[60][1][0][3] != ["m_gameSpeed", 12, -25]:
        raise ValueError("Unexpected index 3 in Blizzard's game-description schema")
    fingerprints = {name: sha256(at(lo, hi - lo)).hexdigest() for name, (lo, hi) in WINDOWS.items()}
    return dict(build=98348, pe_sha256=PE[1], static_text_sha256=TEXT[1],
                functions_called=len(CALLS), base_vtable_bindings=6, window_sha256=fingerprints,
                cache_root="G+0x83f78", file_writer_root="file+0xde78", file_writer_type=888, cache_type=775,
                flag_zero_snapshot="committed root at packaging", flag_nonzero_snapshot="owner+0x365f8 cached through global 0x377e7c8",
                startup_owner_source="base getter +0xe0 returns G+0x83f78",
                staging_speed=dict(root_offset="0xc748", description_field=3, description_offset=hex(game_speed),
                                   tag=-25, official_name="m_gameSpeed"),
                mode2_setter_source="owner+0x19460", mode4_only_staging_copyback=True,
                cache_validity_reset_by_setter=True, actual_frame64_cache_observed=False)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("pe", type=Path)
    cli.add_argument("decoded_text", type=Path)
    args = cli.parse_args()
    print(json.dumps(verify(args.pe, args.decoded_text), indent=2))
