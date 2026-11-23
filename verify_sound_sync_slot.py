"""Recover the full 98348 sync slot 42 from a complete, ordered class-15 sound handle list."""

from argparse import ArgumentParser
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from struct import pack, unpack, unpack_from
from zlib import crc32

from build_gate_order_map import definition
from first_sound_timing import verify_manifest
from first_sync_game import game
from initial_talent_tracker import GAME
from mpq_reader import MPQArchive
from portable_sync_98348 import decode_sync, encode_sync
from predict_camp_captures import SOURCE
from verify_dispatch_group_native import PE, TEXT, TEXT_RVA, pinned

WINDOWS = ((0x970c85,0x970c9d),(0xac5d80,0xac5deb),(0x2d71a0,0x2d7229),
           (0x20d625c,0x20d6289),(0x20d62d9,0x20d62ea),(0xae8140,0xae8146),
           (0xac6280,0xac6392),(0xac6420,0xac6494),(0xac6098,0xac60e9),
           (0xac5eff,0xac5f26))
WINDOW_HASH = "afd458fae6f42c02605883bcae358ff9f0f90e23c06b90cd155ff6b5ea7bee3f"
EXTRA_CASE_COUNTS = "1028f1d99ad6a5a83ff4a166808aacbcb6d7cd28af6073187d3d42d735f06389"


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sound_list_crc(handles):
    """Full-builder CRC over count and each full slot/generation word in list order."""
    return crc32(pack(f"<{len(handles) + 1}I", len(handles), *handles))


def inspect_native(executable, section):
    image, code = pinned(executable, PE), pinned(section, TEXT)
    def data(a, b):
        return code[a-TEXT_RVA:b-TEXT_RVA]
    require(sha256(b"".join(data(a,b) for a,b in WINDOWS)).hexdigest() == WINDOW_HASH, "Native code differs")
    nt, = unpack_from("<I",image,60)
    sh = nt + 24 + unpack_from("<H",image,nt+20)[0]
    sections = [unpack_from("<III",image,sh+40*i+12) for i in range(unpack_from("<H",image,nt+6)[0])]
    def read(rva, length):
        pos, = (offset+rva-base for base,size,offset in sections if base<=rva and rva+length<=base+size)
        return image[pos:pos+length]
    def relative(site, opcode, destination):
        head = bytes.fromhex(opcode)
        operand = site+len(head)
        require(data(site,operand) == head and operand+4+unpack("<i",data(operand,operand+4))[0] == destination,
                f"Reference differs at {site:#x}")
    for site, opcode, dest in ((0x970c8e,"e8",0xac5d80),(0xac5d8a,"8b05",0x2f719f8),
            (0xac5dd8,"448b05",0x2f719f8),(0xac5ddf,"488b15",0x2f71a08),
            (0xac5de6,"e9",0x2d71a0),(0xac5d83,"4c8d1d",0x2648210),
            (0x2d71bc,"488d1d",0x2648210),(0x20d6276,"488d05",0x26b4e98),
            (0x20d62dc,"e8",0x1ff7240),(0xac6382,"890d",0x2f719f8),
            (0xac647b,"e8",0x1a2b250),(0xac6488,"8915",0x2f719f8)):
        relative(site, opcode, dest)
    require(data(0x970c93,0x970c9d) == bytes.fromhex("8b03f7d08987b0000000") and (0xb0-8)//4 == 42,
            "Changed vector destination")
    require(data(0x20d62e7,0x20d62ea) == bytes.fromhex("ff5250") and
            unpack("<Q",read(0x26b4e98+0x50,8)) == (0x140ac6280,) and
            unpack("<Q",read(0x26b4e98+0x20,8)) == (0x140ae8140,), "Different sound vtable")
    require(unpack("<I",read(0x2f719f8,4))==(0,) and unpack("<Q",read(0x2f71a08,8))==(0,),
            "Initial count or list pointer differs")
    table = unpack("<1024I",read(0x2648210,4096))
    def native_crc(handles):
        state = 0xffffffff
        for operand in (len(handles), *handles):
            w = state ^ operand
            state = table[w>>24] ^ table[256+(w>>16 & 255)] ^ table[512+(w>>8 & 255)] ^ table[768+(w & 255)]
        return state ^ 0xffffffff
    for test in ([], [0x10001], [0x10002], [0x10001,0x10002], [0x10002,0x10001], [0xffff0001]):
        require(native_crc(test) == sound_list_crc(test),"Native CRC differs from zlib")
    require(sound_list_crc([]) == 0x2144df1c and sound_list_crc([0x10001,0x10002]) != sound_list_crc([0x10002,0x10001]),
            "Unexpected empty or order-sensitive CRC")
    return native_crc


def collect(cases, native_crc):
    totals = {}
    ten = None
    for path, h, build in verify_manifest(json.loads(cases.read_bytes())):
        protocol, raw = game(Path(path), h, build)
        with closing(MPQArchive(path)) as arc:
            sync_raw = arc.read_file("replay.sync.events")
            tracker = arc.read_file("replay.tracker.events")
        sync = decode_sync(sync_raw)
        require(sync and sync[0].gameloop==64 and sync[0].event_id==2 and encode_sync(sync)==sync_raw,
                "Unexpected physical sync marker")
        report_count = 0
        first = None
        births = []
        for row in protocol.decode_replay_tracker_events(tracker):
            if row["_gameloop"] > 64:
                break
            if row["_event"].endswith(".SUnitBornEvent") and row.get("m_unitTypeName",b"").startswith(b"Hero") and row.get("m_controlPlayerId") in range(1,11):
                births.append(row["_gameloop"])
        for row in protocol.decode_replay_game_events(raw):
            if row["_gameloop"]>150 and first is None:
                break
            if row["_eventid"]==46:
                if first is None:
                    first = row["_gameloop"]
                h_word = row["m_sound"]
                require(native_crc([h_word])==sound_list_crc([h_word]),"Control handle CRC differs")
                if row["_gameloop"]<=64:
                    report_count += 1
            if row["_gameloop"]>64 and first is not None:
                break
        stats = totals.setdefault(build,Counter())
        stats["replays"] += 1
        stats["first_sync_type2"] += 1
        stats["offset_reports_through_64"] += report_count
        stats["replays_with_pre64_hero_birth_and_no_offset_through_64"] += bool(births and min(births)<64 and not report_count)
        if h == SOURCE:
            require(first == 68 and report_count == 0 and sorted(births) == [50,50,58,58], "Unexpected source evidence")
            ten = dict(hero_birth_loops=births, first_offset_loop=first, first_sync_loop=64, observed_type=2)
    require(ten is not None and totals[98348]["replays"]==24 and totals[41810]["replays"]==5,"Incomplete corpus")
    return ten, totals


def extra_sync_records(path_map, cases):
    refs = json.loads(path_map.read_bytes())
    original_pins = {h for _, h, _ in verify_manifest(json.loads(cases.read_bytes()))}
    require(isinstance(refs,dict) and len(refs)==28 and not (set(refs)&original_pins), "Unexpected extra controls")
    lengths = []
    for h, path in sorted(refs.items()):
        game(Path(path),h,98348)
        with closing(MPQArchive(path)) as archive:
            raw = archive.read_file("replay.sync.events")
        rows = decode_sync(raw)
        require(rows and rows[0].gameloop==64 and encode_sync(rows)==raw and
                all(r.event_id==2 and r.words is None for r in rows), "Different extra sync shape")
        lengths.append((h,len(rows)))
    aggregate = sha256(json.dumps(lengths,separators=(",",":")).encode("ascii")).hexdigest()
    require(aggregate == EXTRA_CASE_COUNTS, "Unexpected extra build-98348 control set or record counts")
    return dict(replays=len(lengths), physical_type2_records=sum(n for _,n in lengths),
                type1_records=0, identity_and_record_counts_sha256=aggregate)


def run(executable, section, gamelib, cases, extra_manifest=None):
    native_crc = inspect_native(executable, section)
    raw = gamelib.read_bytes()
    require(sha256(raw).hexdigest() == GAME, "Unexpected GameLib")
    start = definition(raw.decode("utf-8-sig").replace("\r\n","\n"), "bool", "libGame_gt_StartGame_Func")
    tutorial = start.index("if ((libCore_gv_sYSGameMode == libCore_ge_GameModes_Tutorial1))")
    spawn = start.index("libGame_gf_SpawnHeroesForBothTeams();",tutorial)
    require('else {\n        SoundPlayForPlayer(SoundLink("Gen_HeroRespawn_GameStart", -1), c_maxPlayers, PlayerGroupAll(), 100.0, 0.0);\n        Wait(libGame_gv_heroSpawnDelay_C, c_timeGame);' in start[tutorial:spawn],
            "Unexpected initial ordinary sound call")
    ten, totals = collect(cases, native_crc)
    result = dict(build=98348, slot=42, unit="ordered class-15 sound handle DWORDs",
                fresh_file_initialized_full_crc32=f"{native_crc([]):08x}", fast_mode4_bit6_clear_word=0,
                native_windows_sha256=WINDOW_HASH, native_tables_and_zlib_agree=True, gamelib_sha256=GAME,
                ordinary_pre_spawn_call="Gen_HeroRespawn_GameStart", source=ten, corpus=totals,
                ten_full_slot_at_64=None, ten_selected_slot_at_64=None)
    if extra_manifest:
        result["additional_distinct_98348_controls"] = extra_sync_records(extra_manifest, cases)
    return result


if __name__ == "__main__":
    cli = ArgumentParser(description=__doc__)
    for name in ("executable","section","gamelib","cases"):
        cli.add_argument(name,type=Path)
    cli.add_argument("--extra-manifest",type=Path)
    print(json.dumps(run(**vars(cli.parse_args())),indent=2))
