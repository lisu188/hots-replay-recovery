"""Verify the build-98348 command issuer and lookup-only update handlers in pinned files."""
import argparse
import json
from pathlib import Path
from struct import unpack_from

from verify_dispatch_group_native import PE, TEXT, TEXT_RVA, pinned


def verify(executable, decoded_text):
    pe, text = pinned(executable, PE), pinned(decoded_text, TEXT)
    nt, = unpack_from("<I", pe, 60)
    sections = nt + 24 + unpack_from("<H", pe, nt + 20)[0]
    count, = unpack_from("<H", pe, nt + 6)
    image, = unpack_from("<Q", pe, nt + 24 + 24)

    def pointer(rva):
        for i in range(count):
            start, size, offset = unpack_from("<III", pe, sections + 40*i + 12)
            if start <= rva and rva + 8 <= start + size:
                return unpack_from("<Q", pe, offset + rva - start)[0] - image
        raise ValueError(f"Missing PE pointer at {rva:#x}")

    def instruction(rva, expected):
        raw = bytes.fromhex(expected)
        if text[rva-TEXT_RVA:rva-TEXT_RVA+len(raw)] != raw:
            raise ValueError(f"Unexpected instruction at {rva:#x}")

    def direct(rva, target):
        instruction(rva, "e8")
        if rva + 5 + unpack_from("<i", text, rva+1-TEXT_RVA)[0] != target:
            raise ValueError(f"Unexpected call at {rva:#x}")

    if pointer(0x2f73050) != 0x26ec238 or pointer(0x26ec238+8) != 0xb58e70:
        raise ValueError("Listener vtable or callback differs")
    for event, site in ((103,0xb60219), (104,0xb6023c), (105,0xb6025f)):
        # Read the listener address, message ID, and common registration call.
        lea = site + 7
        instruction(lea, "4c8d05")
        if lea+7+unpack_from("<i",text,lea+3-TEXT_RVA)[0] != 0x2f73050:
            raise ValueError("Registration names another listener")
        instruction(lea+7, "41b9" + (0x30000+event).to_bytes(4,"little").hex())
        direct(lea+23, 0x1330160)
    instruction(0xb5f718, "05f2fffcff83f862")
    instruction(0xb5f726, "4898410fb6840160fab500418b8c81ecf9b5004903c9ffe1")
    for event, branch, offset, handler in (
        (27,0xb5f799,11,0xb60920), (103,0xb5f96d,11,0xb60c00),
        (104,0xb5f981,11,0xb60a80), (105,0xb5f995,11,0xb60b30)
    ):
        index = text[0xb5fa60-TEXT_RVA+event-14]
        if unpack_from("<I",text,0xb5f9ec-TEXT_RVA+4*index)[0] != branch:
            raise ValueError(f"Unexpected dispatch case {event}")
        direct(branch+offset, handler)
    # The issuer copies the explicit sequence from the event into a temporary
    # descriptor; its +0x48 lies at stack+0x68 in the caller.
    instruction(0x202a897, "8b476c894648")
    instruction(0xb609ca,"8b542468")
    direct(0xb609d4,0x2031640)
    instruction(0x2031678,"395950")
    instruction(0x203169a,"488bceff5038")
    direct(0x20316a7,0x2032290)
    # Target and manager handlers read the optional payload's numeric word.
    for site, op in ((0xb60ac5,"8b7b34"),(0xb60b91,"8b7b34"),(0xb60c2c,"8b5638")):
        instruction(site,op)
    for site in (0xb60ae5,0xb60bb1,0xb60c37):
        direct(site,0x2031bf0)
    instruction(0xb60aea,"4885c0740f")
    instruction(0xb60bb6,"4885c0740f")
    instruction(0xb60c3f,"4885c07435")
    instruction(0xb60c44,"8b463085c0741a83e801740a83f801751b0fb6d0eb0d488b07b201488bcfff502833d2")
    instruction(0x2031bf0,"4c8b4110488b410849c1e0044c03c0")
    instruction(0x2031c04,"488b084885c9740539515074064883c010ebe8488bc1c333c0c3")
    for site in (0xb60afa,0xb60bc6):
        instruction(site,"41ff5030")
    for site in (0xb60c62,0xb60c6d):
        instruction(site,"ff5028")
    instruction(0x6d45ab,"488d7908")
    instruction(0x6d460f,"8b4748894638c6463401")
    instruction(0x6d462e,"8b470c488bd7c1e81383e001ffc0894630")
    return dict(build=98348, exe_sha256=PE[1], static_text_sha256=TEXT[1],
                listener="0xb58e70", issue_find_or_create="0x2031640", lookup_only="0x2031bf0",
                object_sequence_offset=80, manager_state_argument_sequences={"0":[0],"1":[1,0],"2":[1]},
                target_handler_vtable_offset=48, manager_handler_vtable_offset=40)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("exe", type=Path)
    cli.add_argument("decoded_text", type=Path)
    args = cli.parse_args()
    print(json.dumps(verify(args.exe,args.decoded_text),indent=2))
