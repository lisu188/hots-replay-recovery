"""Check the static build 98348 MapInfo/lobby -> group import against pinned local inputs."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import struct


PE = (53573840, "efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9")
TEXT = (36581376, "3ef739d3cda2f8c592fcbeb3a2fdb690224458c13916f1abc8d525191a32df83")
TEXT_RVA = 0xBA000
# Confirm the sites interpreting the data in addition to the two whole-input pins.
INSTRUCTIONS = {
    0x6D0646: "3d4970614d", 0x6D090D: "4c69c8b00100004c038e58080000",
    0x6CF3DA: "8806", 0x6CF424: "895e04", 0x97BD9C: "4981c4f0090000",
    0x97C28E: "440fb6a5d0010000", 0x97C29C: "4969f4f00b0000", 0x97C2A6: "4803b5f0610000",
    0x97C3A5: "83bd4c42000000", 0x97C3AE: "80bd0849000000", 0x97C3B7: "80bd0949000010",
    0x97C59D: "4488bb59ffffff", 0x97C5A4: "41fec7", 0x97C5B3: "3c02",
    0x97C5BB: "0fb68582030000", 0x97C5DA: "888358ffffff",
    0x97D12C: "80bdf819000000", 0x97D139: "0fb695f9190000",
    0xD0121D: "498d9de0a60200", 0xD0122C: "48895c2420",
    0xD01252: "488bd3", 0xD0125F: "ff9060030000",
    0x133BF04: "46888c11d8130a00", 0x133BF17: "46888c11c8130a00",
    0x133BF26: "42888c12e8130a00", 0x133BF2E: "4805b0000000",
    0x133BF3D: "4981c3f00b0000", 0x133BF44: "4180f910",
}
CALLS = {0x6AA97A: 0x6D05C0, 0x6D091B: 0x6CF390, 0x6CF3CD: 0x2717E0,
         0x6CF3FA: 0x2717E0, 0x97C1F5: 0x6CE240, 0x97C289: 0x6CE2C0,
         0x97C2FD: 0x645A90, 0x97C58C: 0x988DE0, 0xD00F9A: 0xD008C0,
         0xD0123E: 0x97BCA0}


def pinned(path, identity):
    data = path.read_bytes()
    if (len(data), sha256(data).hexdigest()) != identity:
        raise ValueError("Unexpected whole input")
    return data


def check(image_path, text_path):
    image = pinned(image_path, PE)
    text = pinned(text_path, TEXT)
    nt = struct.unpack_from("<I", image, 60)[0]
    sections = struct.unpack_from("<H", image, nt + 6)[0]
    optional_size = struct.unpack_from("<H", image, nt + 20)[0]
    optional = nt + 24
    base = struct.unpack_from("<Q", image, optional + 24)[0]
    table = optional + optional_size

    def physical(rva, size):
        for i in range(sections):
            start, length, raw = struct.unpack_from("<III", image, table + i * 40 + 12)
            if start <= rva and rva + size <= start + length:
                offset = raw + rva - start
                return image[offset:offset + size]
        raise ValueError("Range outside physical PE")

    pointer = struct.pack("<Q", base + 0x133BEE0)
    if physical(0x27BC518 + 0x360, 8) != pointer or image.count(pointer) != 1:
        raise ValueError("Base vtable group-import slot mismatch")
    native = physical(0x27C4748, 216)
    if sha256(native).hexdigest() != "2ed7a05e7188e90e96e761a90430f567163373efd4241a3bc76352dea93238f8":
        raise ValueError("Native slot field table")
    stride, *offset = struct.unpack("<27Q", native)
    if (stride, offset[0], offset[1], offset[8], offset[16]) != (0xF28, 0, 1, 12, 0x6C8):
        raise ValueError("Native slot shape")
    for rva, encoded in INSTRUCTIONS.items():
        instruction = bytes.fromhex(encoded)
        if text[rva-TEXT_RVA:rva-TEXT_RVA+len(instruction)] != instruction:
            raise ValueError(f"Instruction mismatch at {rva:x}")
    for site, target in CALLS.items():
        offset = site - TEXT_RVA
        disp, = struct.unpack_from("<i", text, offset + 1)
        if text[offset] != 0xE8 or site + 5 + disp != target:
            raise ValueError(f"Direct call mismatch at {site:x}")
    return dict(build=98348, pe_bytes=PE[0], pe_sha256=PE[1], text_bytes=TEXT[0],
                text_sha256=TEXT[1], matched_sites=len(INSTRUCTIONS), matched_direct_calls=len(CALLS),
                vtable_rva="0x27bc518", slot="0x360", import_function_rva="0x133bee0",
                lobby_slot_type=730, slot_bytes=stride, optional_tandem_offset="0x6c8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pe", type=Path)
    parser.add_argument("decoded_text", type=Path)
    args = parser.parse_args()
    print(json.dumps(check(args.pe, args.decoded_text), indent=2))
