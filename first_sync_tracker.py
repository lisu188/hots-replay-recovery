"""Generate and physically check the postzero Dragon Shire tracker window through loop 64."""

import argparse
from contextlib import closing
from hashlib import sha256
from itertools import groupby
import json
from pathlib import Path
from xml.etree import ElementTree

from camp_owner_wire import OWNER, read_tracker
from dragon_startup_births import predict
from encoders import encode_tracker_events
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from opening_birth_wire import model, target_protocol
from portable_sync_98348 import decode_sync
from predict_camp_captures import SOURCE

SYNC_LOOP = 64
STAT = "NNet.Replay.Tracker.SStatGameEvent"
GATE_MAP = "bda7aafd1d63c77b3b4d29ff2afee96da09a3104b54b4a1d625bb299607d9008"
ZERO = "575dc05ef76fa4c878fc45074c64e0cf94d7c658d3fd20d9b98d07fcf6c3bfee"
PINS = {
    "gamelib.galaxy": "a6384749fbe8f676cbd6ccb9ec1aeac004815d37a8e1c2f8f9f8f176b2bfca09",
    "mapmechanicslib.galaxy": "d49dbde21198963f953efa16c8d8bb6b035d2d8bd8f0d41b5989fecbb4e35b1f",
    "heroeslib.galaxy": "15f0314a1c48a0391e76e22360847e7ef0c91b12a29da15d79453045c175a683",
    "heroeslib_h.galaxy": "21d0147e00969baddb9e32e9d6bda3adc3bcb5c28f56fa52b4f4ba98e5cde891",
}


def digest(raw):
    return sha256(raw).hexdigest()


def stock_scripts(folder):
    scripts = {}
    for file, pin in PINS.items():
        raw = (folder / file).read_bytes()
        if digest(raw) != pin:
            raise ValueError("Unexpected library: " + file)
        scripts[file] = raw.decode("utf-8-sig").replace("\r\n", "\n")
    game, mech, core, header = (scripts[name] for name in PINS)

    def in_order(text, *terms):
        for term in terms:
            if term not in text:
                raise ValueError("Missing stock action: " + term)
            text = text.split(term, 1)[1]

    def body(text, signature):
        if text.count(signature) != 1:
            raise ValueError("Missing unique Galaxy body: " + signature)
        return text.split(signature, 1)[1].split("\n}", 1)[0]

    spawn = body(
        game,
        "bool auto_libGame_gf_SpawnHero_TriggerFunc (bool testConds, bool runActions) {",
    )
    dispatch = body(game, "void libGame_gf_LevelUpHero (unit lp_hero) {")
    in_order(dispatch, 'TriggerCreate("auto_libGame_gf_LevelUpHero_TriggerFunc");',
             "TriggerExecute(auto_libGame_gf_LevelUpHero_Trigger, false, false);")
    level = body(game, "bool auto_libGame_gf_LevelUpHero_TriggerFunc (bool testConds, bool runActions) {")
    camp = body(mech, "void libMapM_gf_JungleInitializeCreepCamp (int lp_camp) {")
    drop = body(
        mech,
        "void libMapM_gf_JungleDropLootBannerinMercCamp (int lp_campIndex, playergroup lp_creditPlayerGroup) {",
    )
    banner = body(
        game,
        "bool auto_libGame_gf_DropLootBannerinSconce_TriggerFunc (bool testConds, bool runActions) {",
    )
    in_order(
        spawn,
        'StatEventCreate("PlayerSpawned");',
        '"PlayerID", lp_player);',
        '"Hero", (libGame_gv_players[lp_heroIndex].lv_heroData.lv_unitType));',
        "StatEventSend(StatEventLastCreated());",
        "Wait(0.125, c_timeGame);",
        "libGame_gf_LevelUpHero(libGame_gv_players[lp_player].lv_heroUnit);",
    )
    in_order(
        level,
        "lv_player = UnitGetOwner(lp_hero);",
        "lv_level = libGame_gf_GetCustomValueLevelofHeroUnit(lp_hero);",
        'StatEventCreate("LevelUp");',
        '"PlayerID", lv_player);',
        '"Level", lv_level);',
        "StatEventSend(StatEventLastCreated());",
    )
    in_order(core, "libCore_gv_sYSHeroStartLevel = 1;")
    in_order(header, "libCore_gv_cOMPUTER_Hostile = 15;")
    in_order(
        camp,
        'UnitGroup("LootBannerSconce"',
        "lv_campOwnershipFlagUnit == null",
        "lv_stateIsEnabled = false;",
        "return ;",
        "libMapM_gf_JungleDropLootBannerinMercCamp(lp_camp, PlayerGroupSingle(libCore_gv_cOMPUTER_Hostile));",
    )
    in_order(
        drop,
        "lv_sconceUnit = libMapM_gv_jungleCreepCamps[lp_campIndex].lv_campOwnershipFlagUnit;",
        "libGame_gf_DropLootBannerinSconce(lv_sconceUnit,",
    )
    in_order(
        banner,
        "Wait(0.5, c_timeGame);",
        "UnitSetOwner(lp_sconceUnit, lp_owningPlayer, true);",
    )


def camp_flags(package, mechanics, placed):
    with closing(MPQArchive(package)) as a:
        parts = [read_member(a, k) for k in ("Objects", "Regions", "MapScript.galaxy")]
    _, meta = predict(*parts, mechanics.read_bytes())
    objects = sorted(
        ElementTree.fromstring(parts[0]).findall("ObjectUnit"),
        key=lambda e: int(e.get("Id")),
    )
    by_id = {
        int(e.get("Id")): birth
        for e, birth in zip(objects, placed[: meta["authored"]], strict=True)
    }
    result = []
    for camp in reversed(meta["camps"]):
        object_id = camp["sconce_object_id"]
        if object_id is None:
            continue
        b = by_id[object_id]
        if (b["m_unitTypeName"], b["m_controlPlayerId"], b["m_upkeepPlayerId"]) != (
            b"LootBannerSconce",
            0,
            0,
        ):
            raise ValueError("Unsupported initial camp ownership")
        result.append(
            dict(
                _eventid=3,
                _event=OWNER,
                _gameloop=8,
                m_unitTagIndex=b["m_unitTagIndex"],
                m_unitTagRecycle=b["m_unitTagRecycle"],
                m_controlPlayerId=15,
                m_upkeepPlayerId=15,
            )
        )
    if len(result) not in (0, 5):
        raise ValueError("Unsupported partial camp profile")
    return result


def stat(kind, hero):
    owner = dict(m_key=b"PlayerID", m_value=hero["m_controlPlayerId"])
    level = kind == b"LevelUp"
    return dict(
        _eventid=10,
        _event=STAT,
        _gameloop=hero["_gameloop"] + (2 if level else 0),
        m_eventName=kind,
        m_stringData=(
            None if level else [dict(m_key=b"Hero", m_value=hero["m_unitTypeName"])]
        ),
        m_intData=[owner, dict(m_key=b"Level", m_value=1)] if level else [owner],
        m_fixedData=None,
    )


def project(replay, build, protocol, package, folder):
    stock_scripts(folder)
    mechanics = folder / "mapmechanicslib.galaxy"
    placed, heroes, _ = model(replay, build, protocol, package, mechanics)
    rows = camp_flags(package, mechanics, placed)
    early = [h for h in heroes if 0 < h["_gameloop"] <= SYNC_LOOP]
    if len(early) != 4:
        return None, "unresolved lobby startup roles"
    if any(h["m_unitTypeName"] in {b"HeroNecromancer", b"HeroDVa"} for h in early):
        return None, "unmodeled Xul or D.Va startup allocations"
    for tick, group in groupby(early, key=lambda h: h["_gameloop"]):
        pair = list(group)
        if tick not in (50, 58) or len(pair) != 2:
            return None, "unsupported hero pair timing"
        for hero in pair:
            rows.extend((hero, stat(b"PlayerSpawned", hero)))
        rows.extend(stat(b"LevelUp", hero) for hero in reversed(pair))
    return rows, None


def physical(raw, protocol):
    start = None
    offset = prior = 0
    window = []
    for event in protocol.decode_replay_tracker_events(raw):
        tick = event["_gameloop"]
        if tick > SYNC_LOOP:
            if start is None:
                raise ValueError("Missing opening interval")
            return window, raw[start:offset], start, tick
        if tick < prior:
            raise ValueError("Unordered tracker")
        n, rem = divmod(event["_bits"], 8)
        if rem or not n or offset + n > len(raw):
            raise ValueError("Invalid frame bounds")
        if tick:
            if start is None:
                start = offset
            window.append({k: v for k, v in event.items() if k != "_bits"})
        prior, offset = tick, offset + n
    raise ValueError("Missing record after loop 64")


def inspect(replay, expected, build, package, folder):
    if digest(replay.read_bytes()) != expected:
        raise ValueError("Unexpected replay")
    with closing(MPQArchive(replay)) as arc:
        sync = decode_sync(arc.read_file("replay.sync.events"))
    if not sync or sync[0].gameloop != SYNC_LOOP:
        raise ValueError("Unexpected first physical sync gameloop")
    src, raw, _ = read_tracker(replay, build)
    predictions, reason = project(replay, build, src, package, folder)
    events, segment, offset, next_tick = physical(raw, src)
    result = dict(
        replay_sha256=expected,
        build=build,
        map_sha256=digest(package.read_bytes()),
        first_sync_loop=SYNC_LOOP,
        source_physical_frames=len(events),
        source_physical_bytes=len(segment),
        source_physical_sha256=digest(segment),
        first_following_tracker_loop=next_tick,
    )
    if reason is None:
        dst = target_protocol()
        stream = encode_tracker_events(predictions, dst)
        if predictions != events or stream != segment:
            reason = "unmatched complete interleaved tracker segment"
        else:
            decoded = list(dst.decode_replay_tracker_events(stream))
            if (
                sum(e["_bits"] for e in decoded) != len(stream) * 8
                or [{k: v for k, v in e.items() if k != "_bits"} for e in decoded]
                != predictions
            ):
                raise ValueError("Target decode does not cover segment")
            result.update(
                admitted=True,
                hero_births=4,
                spawn_statistics=4,
                level_statistics=4,
                early_flag_owners=len(predictions) - 12,
                last_tracker_loop=predictions[-1]["_gameloop"],
                target_bytes=len(stream),
                target_sha256=digest(stream),
            )
            return result, stream
    result.update(admitted=False, reason=reason)
    return result, None


def join_zero(prefix, tail, receipt):
    if (receipt["replay_sha256"], receipt["map_sha256"], receipt["admitted"]) != (
        SOURCE,
        GATE_MAP,
        True,
    ):
        raise ValueError("Only the pinned TEN/GateOrder combination is qualified")
    if digest(tail) != receipt["target_sha256"] or digest(prefix) != ZERO:
        raise ValueError("Unexpected loop-zero or postzero bytes")
    dst = target_protocol()
    result = prefix + tail
    rows = list(dst.decode_replay_tracker_events(result))
    if (
        len(rows) != 247
        or len([e for e in rows if not e["_gameloop"]]) != 235
        or sum(e["_bits"] for e in rows) != len(result) * 8
        or rows[-1]["_gameloop"] != 60
        or encode_tracker_events(rows, dst) != result
    ):
        raise ValueError("Incomplete combined tracker prefix")
    return result, dict(
        frames=len(rows),
        bytes=len(result),
        sha256=digest(result),
        loop_zero_candidate_sha256=ZERO,
        covered_through_loop=64,
        first_sync_checksum_verified=False,
        native_playback_verified=False,
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for arg in ("replay", "package", "scripts"):
        cli.add_argument(arg, type=Path)
    cli.add_argument("sha256")
    cli.add_argument("build", type=int, choices=(41810, 98348))
    cli.add_argument("--private-tail", type=Path)
    cli.add_argument("--loop-zero-candidate", type=Path)
    cli.add_argument("--private-prefix", type=Path)
    a = cli.parse_args()
    if bool(a.loop_zero_candidate) != bool(a.private_prefix):
        cli.error("Give both prefix arguments")
    record, stream = inspect(a.replay, a.sha256, a.build, a.package, a.scripts)
    if stream is None and (a.private_prefix or a.private_tail):
        raise ValueError("Unqualified opening")
    if a.private_prefix:
        combined, record["combined_candidate"] = join_zero(
            a.loop_zero_candidate.read_bytes(), stream, record
        )
        with a.private_prefix.open("xb") as f:
            f.write(combined)
    if a.private_tail:
        with a.private_tail.open("xb") as f:
            f.write(stream)
    print(json.dumps(record, indent=2))
