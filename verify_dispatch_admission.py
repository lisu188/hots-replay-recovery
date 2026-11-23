"""Verify clean-roster dispatch admission for the first TEN game inputs in 98348."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import struct
from zlib import crc32

from mpq_reader import MPQArchive
from native_game_events import iter_game_events
from protocol_loader import load_protocol


BASE = 0x140000000
TEXT = 0xba000
EXE_HASH = "efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9"
TEXT_HASH = "3ef739d3cda2f8c592fcbeb3a2fdb690224458c13916f1abc8d525191a32df83"
SOURCE = "e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824"
R8 = "4f2435e8cd678aeac16c0b1403cfdf67ab8e513b04f0f93e22d504c187bbaf19"
GAME = "68def0020f334b543ed6e1be6aed1fd57bfbdc284c933372298a3e96cc69efc5"
VTABLES = {5:(0x13527e0,0x27bbc20,7), 7:(0x1352703,0x271e5b8,7),
           27:(0x1352cd8,0x2657c78,1), 28:(0x1352d3a,0x26643a0,7),
           56:(0x135334c,0x26658b0,1), 104:(0x1351287,0x2657db8,1)}

# IDA-decoded windows indexed by image-relative address, end exclusive.
WINDOWS = {
    "file_reader_and_queue": (0x132d989,0x132da09,"e5fefbddf63d867e1695cf79992429eea4820fe49f908cabbd2b9e3a36a0f08f"),
    "dispatcher_filters": (0x132e2c2,0x132e350,"650c6c7d2ad8a65e431c94a8dd2fac7aa8320167ac4d12ee70ef5e1d84916383"),
    "dispatch_crc": (0x132e350,0x132e41c,"ab008a4341397e6e2e03d2cb58f316a28eeb99e4a45311cdf31e2bbc506b5345"),
    "setup_user_mask": (0x133b890,0x133ba10,"7db061ab1b0fc0555d55e975619cbd8fa6210601f1286741ca7cb6feabe47444"),
    "slot_field_copy": (0x645aa4,0x645b0c,"cdb6350ac4ba0ad9d6c0c30ebdd133ba32db886076c1016164dc2ea28eb16409"),
    "find_controlled_slot_by_user": (0x133dd60,0x133df22,"766ac1e3c4c851a46c41713774e9268e05f2f820963bcc0b21e672500b789733"),
    "setup_choose_user": (0x97d33e,0x97d42e,"2d2afb006006a8ca28870b88d194d2a21d0d6326cf097255e03b30d308a30fe5"),
    "setup_find_and_copy": (0x97d42e,0x97d487,"061485a71cfc685a4b63df0c6893d007469ec087d9fb690e455896726e5beff9"),
    "setup_class_write": (0x97d529,0x97d5e2,"42b6bbffea5916fd477a14ee3a6217713988400693cde5b0fd6771d92711f035"),
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def pinned(path, digest):
    data = path.read_bytes()
    require(sha256(data).hexdigest() == digest, f"Unexpected {path.name}")
    return data


def native(exe, code):
    require(len(exe) == 53573840 and len(code) == 36581376, "Native size mismatch")
    nt, = struct.unpack_from("<I", exe, 60)
    count, = struct.unpack_from("<H", exe, nt + 6)
    optional_size, = struct.unpack_from("<H", exe, nt + 20)
    sections = [struct.unpack_from("<III", exe, nt + 24 + optional_size + i * 40 + 12)
                for i in range(count)]

    def rdata(rva, size):
        for start, length, raw in sections:
            if start <= rva and rva + size <= start + length:
                offset = raw + rva - start
                return exe[offset:offset + size]
        raise ValueError("Missing PE bytes")

    def at(rva, count):
        return code[rva - TEXT:rva - TEXT + count]

    def vmethod(vtable, offset):
        return struct.unpack("<Q", rdata(vtable + offset, 8))[0] - BASE

    for label, (start, end, expected) in WINDOWS.items():
        require(sha256(at(start, end - start)).hexdigest() == expected, label)
    methods = {}
    for event_id, (lea, tab, mask) in VTABLES.items():
        case, = struct.unpack("<I", at(0x1353a78 + 4 * event_id, 4))
        start = case
        type_store = bytes.fromhex("c74010")
        if event_id == 104:
            call = case + 22
            require(at(call, 1) == bytes([0xe8]), "Separate event constructor call")
            start = call + 5 + struct.unpack("<i", at(call + 1, 4))[0]
            type_store = bytes.fromhex("c74110")
        require(0 < lea - start <= 96 and
                (type_store + struct.pack("<I", 0x30000 + event_id)) in at(start, lea - start),
                "Physical event ID to constructor")
        ins = at(lea, 10)
        pair = ("488d05", "488901") if event_id == 104 else ("488d0d", "488908")
        require(ins[:3].hex() == pair[0] and ins[7:].hex() == pair[1], "Constructor vptr assignment")
        require(lea + 7 + struct.unpack_from("<i", ins, 3)[0] == tab, "Constructor vptr target")
        cls, roles = vmethod(tab, 0x40), vmethod(tab, 0x58)
        require(at(cls, 6) == bytes.fromhex("b802000000c3"), "Queue class leaf")
        require(at(roles, 3) == bytes((0xb0, mask, 0xc3)), "Admission mask leaf")
        methods[event_id] = dict(case=hex(case), vtable=hex(tab), class_leaf=hex(cls), file_class=2,
                                 mask_leaf=hex(roles), role_mask=mask)
    require(vmethod(0x27bc518, 0x110) == 0x1327810 and
            at(0x1327810, 8).hex() == "80fa107203b010c3", "Sentinel mapping")
    require(at(0x13239e4, 11).hex() == "48c787c0130a00ffffffff", "Clean seed")

    # Compare complete getter bodies including all 16 jump cases after fixing their relocations.
    def normalized_manager(rva):
        body = bytearray(at(rva, 0x224))
        for off in [0x15, 0x1c, 0x23, 0x83] + [0xa7 + 0x14*i for i in range(16)]:
            target = rva + off + 4 + struct.unpack_from("<i", body, off)[0]
            struct.pack_into("<I", body, off, target)
        for off in [0x98] + [0x1e4 + 4*i for i in range(16)]:
            address, = struct.unpack_from("<I", body, off)
            require(rva <= address < rva + len(body), "Jump table refers outside getter")
            struct.pack_into("<I", body, off, address - rva)
        return body

    for wrapper, target in [(0x9d1df0, 0xb67ef0), (0x9d1e00, 0xb68120)]:
        require(at(wrapper, 12).hex() == "80f910720333c0c30fb6c9e9", "User bounds wrapper")
        require(wrapper + 16 + struct.unpack("<i", at(wrapper + 12, 4))[0] == target, "Getter tail")
    manager = normalized_manager(0xb67ef0)
    require(manager == normalized_manager(0xb68120), "User getter bodies disagree")
    # Table header is the size, followed by one qword offset per schema field.
    offsets = struct.unpack("<27Q", rdata(0x27c4748, 216))
    require((offsets[0], offsets[1], offsets[2], offsets[9]) == (0xf28, 0, 1, 12), "Slot layout")
    return methods, sha256(manager).hexdigest()


def roster(path, build, expected):
    pinned(path, expected)
    proto = load_protocol(build)
    with closing(MPQArchive(path)) as archive:
        setup = proto.decode_replay_initdata(archive.read_file("replay.initData"))
    slots = setup["m_syncLobbyState"]["m_lobbyState"]["m_slots"]
    rows = [(s["m_control"], s["m_userId"], s["m_observe"]) for s in slots]
    require(rows == [(2, user, 0) for user in range(10)] + [(1, None, 1)] * 6, "TEN setup")
    return {user: role for control, user, role in rows if control == 2 and user is not None}


def admitted(kind, user, enabled, role, mask):
    if kind not in (5, 43, 102) and not (0 <= user < 16 and (enabled & (1 << user))):
        return False
    return role is None or bool((1 << (role & 31)) & mask & 255)


def verify(args):
    methods, manager_hash = native(pinned(args.exe, EXE_HASH), pinned(args.text, TEXT_HASH))
    roles = roster(args.original, 41810, SOURCE)
    require(roles == roster(args.r8, 96477, R8), "R8 changed source roster")
    declared = load_protocol(96477).typeinfos[67][1][0]
    require([(declared[i][0], declared[i][2]) for i in (0,1,8)] ==
            [("m_control",-26), ("m_userId",-25), ("m_observe",-18)], "Schema roles")
    enabled = sum(1 << user for user in roles)
    physical = [f.event for f in iter_game_events(pinned(args.game_prefix, GAME))]
    require(len(physical) == 30 and sum(e.delta for e in physical) == 64, "Opening inputs")
    sentinels = [i + 1 for i,e in enumerate(physical) if e.user_id == 16]
    require(sentinels == [1,22] and all(physical[i-1].event_id == 5 for i in sentinels), "System inputs")
    require(physical[0].delta == 0 and physical[0].payload == (), "System payload")
    accepted = [admitted(e.event_id,e.user_id,enabled,roles.get(e.user_id),methods[e.event_id]["role_mask"])
                for e in physical]
    require(all(accepted), "Opening admission")
    require(not admitted(56,16,enabled,None,1) and not admitted(27,0,enabled,1,1)
            and not admitted(27,0,0,None,1) and admitted(28,0,enabled,1,7), "Filter distinctions")
    state = crc32(struct.pack("<IBI", 0, 16, crc32(b""))) ^ 0xffffffff
    require(state == 0x79167cd3, "First CRC")
    return dict(build=98348, original_sha256=SOURCE, r8_sha256=R8, game_prefix_sha256=GAME,
                exe_sha256=EXE_HASH, text_sha256=TEXT_HASH, methods=methods,
                normalized_user_getters_sha256=manager_hash, clean_enabled_mask=hex(enabled),
                real_users=list(roles), real_user_classes=list(roles.values()), class2_queue="G+0xbfdd8",
                physical_events=len(physical), admitted_on_clean_ten_roster=sum(accepted),
                sentinel_ordinals=sentinels, first_dispatch_crc_from_clean_seed=hex(state),
                limits="Requires the clean TEN roster committed to native setup, and file dispatch in order. A resumed process may have different state. Overall sync word uncomputed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("exe", "text", "original", "r8", "game_prefix"):
        parser.add_argument(field, type=Path)
    print(json.dumps(verify(parser.parse_args()), indent=2) + "\n", end="")
