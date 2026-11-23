"""Check the 98348 constructor, import paths and exact TEN lookup state against pinned artifacts."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import struct

from check_dispatch_inputs import components
from dispatch_group_source import player_groups
from dispatch_lookup_tail import audit, lookup_state
from mpq_reader import MPQArchive
from protocol_loader import load_protocol
from verify_dispatch_admission import GAME, R8, SOURCE
from verify_dispatch_group_native import check, pinned, TEXT, TEXT_RVA


WINDOWS = {
    "empty_groups": (0x97C0DD, 0x97C110, "5c77fc4972f0e7a7ae7c85e4a5484480901da690eff09eef9ed96ca1495eed98"),
    "group_count_loop": (0x97C1D9, 0x97C20D, "a2836cd7f8c8055efec1ea6193e5688cca7b53383e1a6e105bcdb0e4232c1273"),
    "special_groups": (0x97CE8D, 0x97CEF9, "4ae74fa8db06044df068415ad4f4b7714d1e4dfff78723116d7da29827eda7fb"),
    "leftover_slots": (0x97CFE2, 0x97D02A, "f6e6070522736faa250a60d75caff888a97d111013ba7c37c5d64794dab5c04d"),
    "tandem_guard": (0x97D112, 0x97D149, "73ff6c0f623cd25adb212738cdda6fd098013b96668b991b7558384c419166a4"),
    "import_groups": (0x133BEE0, 0x133BF4B, "443a1f46589cca4be2ceaaeb1d79f8ac1c2ca2e70806d4aa3b738cb875e7339f"),
    "active_mask": (0x133B9D0, 0x133BA1F, "653e5c9c982f3de1fe295f591db3bf073f1f5e9e856854f00e02f9a6be8d0ba3"),
    "roster_updates": (0x132E4EB, 0x132E57F, "fffe73759d31202ac11cbc7a41cef992f9b0b8a1650129a6007f7c497c69895f"),
    "feed_lookups": (0x131CF35, 0x131CF7E, "792b767b36555fd83469c6c8e90fbea68f732b586494fd47ae5cbe3364246dc0"),
    "feed_mask": (0x131CE2C, 0x131CE41, "963a56920078f86e8c7ce8db8a002856203b8b910780f8eeb910fc5a6efa9e4a"),
}


def verify(pe, text, original, r8, map_file, game_file):
    identity = check(pe, text)
    code = pinned(text, TEXT)
    def at(start, end):
        return code[start - TEXT_RVA:end - TEXT_RVA]
    if at(0x13239DB, 0x13239E4) != bytes.fromhex("33c0668987b8130a00"):
        raise ValueError("Clean mask initialization")
    stores = b"".join(b"\xc7\x87" + struct.pack("<II", offset, 0x10101010)
                      for offset in range(0xA13C8, 0xA13F8, 4))
    if at(0x1323EC4, 0x1323F3C) != stores:
        raise ValueError("Clean 48-byte initialization")
    for name, (start, end, expected) in WINDOWS.items():
        if sha256(at(start, end)).hexdigest() != expected:
            raise ValueError(f"Unexpected {name}")
    historical = audit(original, SOURCE, 41810, map_file)
    if sha256(r8.read_bytes()).hexdigest() != R8:
        raise ValueError("Unexpected R8")
    with closing(MPQArchive(r8)) as archive:
        lobby = load_protocol(96477).decode_replay_initdata(archive.read_file("replay.initData"))["m_syncLobbyState"]["m_lobbyState"]
    active, tail, writes = lookup_state(player_groups(map_file, 41810), lobby["m_slots"])
    tail_sha = sha256(tail).hexdigest()
    if (active, writes, tail_sha) != (0x3FF, (0x3FF,)*3, historical["lookup_tail_sha256"]):
        raise ValueError("R8 target-format input differs from TEN source projection")
    raw = game_file.read_bytes()
    if sha256(raw).hexdigest() != GAME:
        raise ValueError("Unexpected opening game member")
    events = list(components(raw))
    kinds = sorted({k for k, *_ in events})
    if len(events) != 30 or events[-1][2] != 64 or kinds != [5, 7, 27, 28, 56, 104]:
        raise ValueError("Unexpected target opening path")
    return dict(target_build=identity["build"], pe_sha256=identity["pe_sha256"],
                decoded_text_sha256=identity["text_sha256"], constructor_dword_stores=12,
                mask_initially_zero=True, verified_native_windows=list(WINDOWS),
                clean_setup=historical, r8_sha256=R8, r8_state_matches=True,
                projected_game_member_sha256=GAME, projected_records=len(events), projected_kinds=kinds,
                scope="Clean context and ordinary TEN setup. The recorded and regenerated prefixes have no user join or leave through loop 64; unrecorded producers and state restoration are outside this check.")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for arg in ("pe", "decoded_text", "original", "r8", "map", "game_prefix"):
        cli.add_argument(arg, type=Path)
    args = cli.parse_args()
    print(json.dumps(verify(args.pe, args.decoded_text, args.original, args.r8, args.map, args.game_prefix), indent=2))
