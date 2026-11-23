"""Audit the normal hero respawn handle in GameLib and in full replay trackers."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from mpq_reader import MPQArchive
from protocol_loader import load_protocol


HEROES = {b"Abathur", b"Anubarak", b"Barbarian", b"FaerieDragon", b"Greymane",
          b"Kaelthas", b"Nova", b"Tyrande"}
LIB = "a6384749fbe8f676cbd6ccb9ec1aeac004815d37a8e1c2f8f9f8f176b2bfca09"
SCHEMAS = {
    41810: (41810, "879d228d9d8acd21d63563538dd15841aaf49259ee0bb468b8a46b6a4ef866fd"),
    98348: (96477, "e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84"),
}


def game_library(path):
    data = path.read_bytes()
    if len(data) != 1179642 or sha256(data).hexdigest() != LIB:
        raise ValueError("Unexpected build-98348 GameLib")
    lines = data.decode("utf-8-sig").splitlines()
    scopes = {
        "auto_libGame_gf_SpawnHero_TriggerFunc": (
            "lv_heroUnit != null", "libNtve_gf_CreateUnitsAtPoint2(1,",
            ".lv_heroUnit = UnitLastCreated();", "PlayerSetHeroUnit(lp_player,",
            'StatEventCreate("PlayerSpawned");'),
        "libGame_gt_HeroDeathHeroRespawnTimerExpires_Func": (
            "EventTimer() ==", ".lv_noRespawn == true", ".lv_heroRequiresCustomRespawn == false",
            "libGame_gf_HeroDeathRespawnHeroforPlayer(", "libGame_gf_SendEventRequestCustomRespawn("),
        "libGame_gf_HeroDeathRespawnHeroforPlayer": (
            "lv_heroUnit = libGame_gv_players[lp_player].lv_heroUnit;",
            'UnitHasBehavior2(lv_heroUnit, "AbnormalRespawn")', "return ;",
            'UnitBehaviorRemove(lv_heroUnit, "Dead", 1);', "UnitRevive(lv_heroUnit);",
            "libGame_gf_SendEventHeroRespawn(lp_player, lv_heroUnit);"),
    }
    anchors = {}
    for func, chain in scopes.items():
        start, = (i for i, line in enumerate(lines) if line.startswith(
            ("bool " + func + " (", "void " + func + " (")) and line.endswith("{"))
        end = next(i for i in range(start + 1, len(lines)) if lines[i] == "}")
        cursor = start
        anchors[func] = []
        for expression in chain:
            cursor = next(i for i in range(cursor + 1, end) if expression in lines[i])
            anchors[func].append(cursor + 1)
    return dict(bytes=len(data), sha256=LIB, anchor_lines=anchors)


def value(event, column, key):
    match, = (v["m_value"] for v in event[column] if v["m_key"] == key)
    return match


def audit(path, digest):
    if sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("Unexpected replay")
    with closing(MPQArchive(path)) as archive:
        header = load_protocol(41810).decode_replay_header(archive.header["user_data_header"]["content"])
        version = header["m_version"]
        build = version["m_build"]
        if build != version["m_baseBuild"] or build != header["m_dataBuildNum"]:
            raise ValueError("Version fields differ")
        schema, schema_sha = SCHEMAS[build]
        proto = load_protocol(schema)
        if proto.recovery_schema_sha256 != schema_sha:
            raise ValueError("Unexpected schema")
        lobby = proto.decode_replay_initdata(archive.read_file("replay.initData"))["m_syncLobbyState"]
        handles = proto.decode_replay_details(archive.read_file("replay.details"))["m_cacheHandles"]
        if not handles or handles != lobby["m_gameDescription"]["m_cacheHandles"] or handles[-1][:4] != b"s2ma":
            raise ValueError("Inconsistent map")
        roster = {i: s["m_hero"] for i, s in enumerate(lobby["m_lobbyState"]["m_slots"], 1)
                  if s.get("m_hero") in HEROES}
        raw = archive.read_file("replay.tracker.events")
    spawn = defaultdict(list)
    death_stats = defaultdict(Counter)
    births = defaultdict(list)
    history = defaultdict(list)
    all_borns = defaultdict(list)
    extent = 0
    for e in proto.decode_replay_tracker_events(raw):
        extent += e["_bits"]
        tick = e["_gameloop"]
        kind = e["_event"].rsplit(".", 1)[-1]
        if e.get("m_eventName") == b"PlayerSpawned":
            who = value(e, "m_intData", b"PlayerID")
            spawn[who].append((tick, value(e, "m_stringData", b"Hero")))
        elif e.get("m_eventName") == b"PlayerDeath":
            death_stats[value(e, "m_intData", b"PlayerID")][tick] += 1
        elif kind in ("SUnitBornEvent", "SUnitInitEvent", "SUnitDiedEvent", "SUnitRevivedEvent"):
            pair = e["m_unitTagIndex"], e["m_unitTagRecycle"]
            history[pair].append((kind, tick))
            if kind in ("SUnitBornEvent", "SUnitInitEvent"):
                all_borns[pair[0]].append((tick, pair))
            if kind == "SUnitBornEvent":
                births[e["m_controlPlayerId"], tick, e["m_unitTypeName"]].append(pair)
    if extent != len(raw) * 8:
        raise ValueError("Incomplete physical tracker")
    heroes = defaultdict(Counter)
    for who, hero in roster.items():
        counts = heroes[hero.decode()]
        counts["selected_slots"] += 1
        events = spawn[who]
        if len(events) != 1 or events[0][1] != b"Hero" + hero:
            counts["unmatched_spawn_stats"] += 1
            continue
        born = births[who, *events[0]]
        if len(born) != 1:
            counts["ambiguous_primary"] += 1
            continue
        pair, = born
        counts["registered_slots"] += 1
        lifecycle = history[pair]
        counts["later_births_same_index"] += sum(t > events[0][0] for t, _ in all_borns[pair[0]])
        actual_deaths = Counter(t for kind, t in lifecycle if kind == "SUnitDiedEvent")
        counts["death_stats"] += sum(death_stats[who].values())
        counts["died_on_registered_pair"] += sum(actual_deaths.values())
        actual_ticks = sorted(actual_deaths.elements())
        stat_ticks = sorted(death_stats[who].elements())
        if len(actual_ticks) == len(stat_ticks):
            for died, stat in zip(actual_ticks, stat_ticks):
                counts[f"death_stat_loop_minus_pair_death_{stat - died}"] += 1
        else:
            counts["different_death_counts"] += 1
        alive = True
        for kind, tick in lifecycle[1:]:
            if kind == "SUnitDiedEvent" and alive:
                alive = False
            elif kind == "SUnitRevivedEvent" and not alive:
                alive = True
                counts["revivals_on_registered_pair"] += 1
            else:
                counts["unexpected_lifecycle_transitions"] += 1
        counts["dead_at_end"] += int(not alive)
    return dict(build=build, sha256=digest, map_sha256=handles[-1][8:].hex(), heroes=heroes)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--library", type=Path, required=True)
    cli.add_argument("--case", nargs=2, action="append", required=True, metavar=("REPLAY", "SHA256"))
    args = cli.parse_args()
    cases = [audit(Path(p), s) for p, s in args.case]
    if len({r["sha256"] for r in cases}) != len(cases):
        raise ValueError("Duplicate replay")
    print(json.dumps(dict(library=game_library(args.library), cases=sorted(cases,key=lambda r:r["sha256"])),
                     indent=2))
