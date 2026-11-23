"""Recheck build 98348 retirement, tick-order and Galaxy bindings on pinned inputs."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from


PE = (53573840, "efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9")
TEXT = (36581376, "3ef739d3cda2f8c592fcbeb3a2fdb690224458c13916f1abc8d525191a32df83")
TEXT_RVA = 0xba000
MANAGER = 0x2f3d470
DESCRIPTORS = 0x4120b50


def need(condition, message):
    if not condition:
        raise ValueError(message)


def pinned(path, expected):
    data = path.read_bytes()
    need((len(data), sha256(data).hexdigest()) == expected, f"Unexpected input {path.name}")
    return data


def verify(executable, static_text):
    pe = pinned(executable, PE)
    text = pinned(static_text, TEXT)
    nt, = unpack_from("<I", pe, 60)
    sections = nt + 24 + unpack_from("<H", pe, nt + 20)[0]
    ranges = [unpack_from("<8sIIII", pe, sections + i*40)
              for i in range(unpack_from("<H", pe, nt + 6)[0])]

    def original(rva, size):
        offset, = [raw + rva - base for _, _, base, count, raw in ranges
                   if base <= rva and rva + size <= base + count]
        return pe[offset:offset+size]

    def instruction(rva, expected):
        value = bytes.fromhex(expected)
        offset = rva - TEXT_RVA
        need(text[offset:offset+len(value)] == value, f"Instruction at {rva:#x}")

    def reference(rva, opcode, target):
        instruction(rva, opcode)
        offset = rva + len(bytes.fromhex(opcode))
        disp, = unpack_from("<i", text, offset - TEXT_RVA)
        need(offset + 4 + disp == target, f"Static reference at {rva:#x}")

    # Check distinct sign/width predicates, delayed branch exits, and list order.
    for rva, length, signature in (
        (0x990c59, 13, "7989bfa11f0bbae6d85eac3b"),  # manager active-head arguments
        (0x990aa7, 18, "9342ae5a58eea6a794eef5bb"),  # set next to old head, prepend
        (0x999840, 103, "2211edb6bfe6cd868b60102e"), # save next before work on current
        (0x9998b3, 18, "c80fe883e64106d81896efaa"),  # unsigned due clock; update gate
        (0x9998dd, 21, "dd35f970c2461cec486da7ac"),  # flags after callback; signed timer
        (0x999905, 26, "36624c518b80f4c912a07929"),  # subtract and always exit; stage flag
        (0x999924, 71, "3750f04c2ca45a558a8e4511"),  # descriptor, sign, clamp, exit
        (0x99997b, 17, "bb9c7ca364d46ea2cd555d40"),  # resume saved next
        (0xaa9505, 71, "7016174b196a8e4582cd0407"),  # special and positive first-delay paths
        (0xaa9553, 57, "80dfa722426652e84760f658"),  # direct final mode; minimum countdown 1
        (0xaa95e2, 30, "dcae6c7a7dee47de87627fa4"),  # choose direct handling or state marker
        (0x99d2b0, 114, "a85dc0dec86a73cac597fc4f"), # stage hook only writes unit+0x30
        (0xb17b73, 25, "8f79b980449c32167b2501fe"),  # scale, shift 12, clamp nonnegative
        (0x1ffa99c, 27, "e24909277b17426e8c57184d"), # indexed VM jump
        (0x200e75d, 14, "d36f27485b72b343abc4ac76"), # descriptor stride
    ):
        run = text[rva-TEXT_RVA:rva-TEXT_RVA+length]
        need(sha256(run).hexdigest()[:24] == signature, f"Disassembly window at {rva:#x}")

    for site, target in (
        (0x990c66, 0x990a40), (0x985a60, 0x999690), (0x985b0f, 0x997570),
        (0x9997c1, 0xb3c030), (0x9998ae, 0x9804a0), (0x9998c8, 0x9992a0),
        (0x9998d8, 0xaa6bd0), (0x999900, 0xb17b30), (0x99991f, 0x99d2b0),
        (0x99996e, 0x9bcb40), (0x999976, 0x9926c0), (0xaa954c, 0x99d2b0),
        (0x2055426, 0x64bad0), (0x2055436, 0x99a770), (0xaab054, 0xaa91c0),
        (0x2053a54, 0x64bad0),
    ):
        reference(site, "e8", target)
    for site in (0x9996d3, 0x9997d2):
        reference(site, "440fb705", MANAGER)
    reference(0x9998f9, "488d0d", 0x2f72968)
    need(unpack_from("<I", original(0x2f72968, 4))[0] == 4096, "Fixed point debit seed")
    instruction(0x999829, "41be18000000")
    instruction(0x9998cd, "0fb64339a802740c")
    instruction(0xaa929a, "41be20000000")
    instruction(0xaa92ae, "41bc18000000")
    instruction(0xaa95fc, "804f3902")
    reference(0xaa95e2, "e8", 0x993180)
    reference(0x993180, "488b05", 0x34f0288)
    reference(0xaa95f5, "e8", 0xaa6bd0)

    reference(0x200e75d, "488d15", DESCRIPTORS)
    instruction(0x1ffa93a, "450fb77501")
    instruction(0x1ffa994, "4181fedf070000")
    instruction(0x1ffa9ab, "8b8c82ccac00024803caffe1")
    reference(0x2055445, "e9", 0xaaad70)
    reference(0x2053a67, "e9", 0xaa91c0)
    instruction(0x205543b, "b210")
    instruction(0xaab045, "c6809201000001")
    instruction(0x2051d10, "8b01c3")
    natives = {}
    for name, index, literal, name_ref, desc_ref, entry, call, handler in (
        ("UnitRemove", 1459, 0x29abbf8, 0x236ae7, 0x236aee, 0x2004dd4, 0x2004de4, 0x2055420),
        ("UnitKill", 1460, 0x29abc08, 0x236b05, 0x236b0c, 0x2004df3, 0x2004e03, 0x2053a50),
        ("UnitGetTag", 1466, 0x29abc50, 0x236bbe, 0x236bc5, 0x2004ed4, 0x2004ee4, 0x2051d10),
    ):
        need(original(literal, len(name)+1) == name.encode() + b"\0", name)
        reference(name_ref, "488d15", literal)
        reference(desc_ref, "488d0d", DESCRIPTORS+24*index)
        dest, = unpack_from("<I", text, 0x200accc - TEXT_RVA + 4*index)
        need(dest == entry, f"VM jump for {name}")
        reference(call, "e8", handler)
        natives[name] = dict(index=index, handler=hex(handler))
    return dict(build=98348, pe_bytes=PE[0], pe_sha256=PE[1],
                transformed_text_bytes=TEXT[0], transformed_text_sha256=TEXT[1],
                phase_rva="0x999690", actual_retire_site="0x999976", active_head=hex(MANAGER),
                next_link=20, clock_due_offset=148, countdown_offset=144, native_ids=natives,
                order="next link cached before each current unit; reverse activation on stable list",
                first_delay_offset=184, final_delay_offset=152, fixed_point_scale=4096,
                gate="unsigned clock >= due; post-update flags & 6; timer <= 0; !stage and final",
                native_state_inputs_bound_to_replay=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("static_text", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.static_text), indent=2))
