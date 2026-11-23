"""Regenerate the target camp and Dragon Knight statistics from physical ownership transitions."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from camp_owner_wire import STOCK, read_tracker
from dragon_reset_wire import COHORT
from dragon_startup_births import predict
from encoders import encode_tracker_events
from first_camp_event_order import layout
from first_sync_tracker import STAT, stock_scripts
from dragonshire_packages import MERC_CAPTURE, SIGNED_ANNOUNCER
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE
from verify_gate_order_map import function

CAMP = b"JungleCampCapture"
DRAGON = b"DragonKnightActivated"


def check(value, message):
    if not value:
        raise ValueError(message)


def item(key, value):
    return {"m_key": key, "m_value": value}


def stat(tick, name, integers, fixed, strings=None):
    return dict(
        _eventid=10,
        _event=STAT,
        _gameloop=tick,
        m_eventName=name,
        m_stringData=strings,
        m_intData=integers,
        m_fixedData=fixed,
    )


def read_clocks(folder):
    stock_scripts(folder)
    record = json.loads((folder / "member.json").read_bytes())
    check(
        sha256((folder / "member.json").read_bytes()).hexdigest()
        == "87b44ff3f91d9058f5001f926129a04d225f8a11fa05b99e1571362539ec3b7b",
        "Unexpected installed script inventory",
    )

    def script(name):
        (row,) = [r for r in record["members"] if r["saved_name"] == name]
        data = (folder / name).read_bytes()
        check(
            len(data) == row["bytes"] and sha256(data).hexdigest() == row["sha256"],
            "Changed script",
        )
        return data.decode("utf-8-sig").replace("\r\n", "\n")

    clock = function(script("uilib.galaxy"), "libUIUI_gf_HeroesGameTime")
    check(
        "TimerGetElapsed(libGame_gv_gameTimer)+libSprt_gf_DebugGameTimeDelta()*60"
        in clock,
        "UI clock changed",
    )
    mechanics = script("mapmechanicslib.galaxy")
    for fn, name in [
        ("libMapM_gf_JungleGrantCaptureRewards", CAMP),
        ("libMapM_gt_MMGardensDragonTransformChannelFinish_Func", DRAGON),
    ]:
        body = function(mechanics, fn)
        section = body.split('StatEventCreate("' + name.decode() + '");', 1)[1].split(
            "StatEventSend(StatEventLastCreated());", 1
        )[0]
        check(
            section.count('"GameTime", libUIUI_gf_HeroesGameTime()') == 1
            and '"TeamID"' in section,
            "Clock field changed",
        )
    gate = function(
        script("gamelib.galaxy"), "libGame_gt_OpenTheGatesOpenTheGatesTimerExpires_Func"
    )
    check(
        gate.index('StatEventCreate("GatesOpen");')
        < gate.index("TimerStart(libGame_gv_gameTimer, c_timerDurationInfinite"),
        "Gate timer start changed",
    )


def camps(package, library, expected):
    check(
        expected in (SIGNED_ANNOUNCER, MERC_CAPTURE, STOCK)
        and sha256(package.read_bytes()).hexdigest() == expected,
        "Wrong map profile",
    )
    with closing(MPQArchive(package)) as arc:
        parts = [
            read_member(arc, k) for k in ("Objects", "Regions", "MapScript.galaxy")
        ]
    births, _ = predict(*parts, library.read_bytes())
    positioned = {
        (b["m_x"], b["m_y"]): (b["m_unitTagIndex"], b["m_unitTagRecycle"])
        for b in births
        if b["m_unitTypeName"] == b"TownMercCampCaptureBeacon"
    }
    result = {}
    for i, (xy, _, defenders) in enumerate(layout(package), 1):
        units = {row[0] for row in defenders}
        if units == {"MercDefenderMeleeKnight", "MercDefenderRangedMage"}:
            kind = b"Bruiser Camp"
        elif units == {"MercDefenderSiegeGiant"}:
            kind = b"Siege Camp"
        else:
            raise ValueError("Unsupported defender composition")
        result[positioned[xy]] = (i, kind)
    check(len(result) == len(positioned) == 5, "Camp ambiguity")
    return result


def teams(replay, protocol, events):
    with closing(MPQArchive(replay)) as arc:
        slots = protocol.decode_replay_initdata(arc.read_file("replay.initData"))[
            "m_syncLobbyState"
        ]["m_lobbyState"]["m_slots"]
    setup = [e for e in events if e["_eventid"] == 9]
    check(
        len(setup) == 10 and {e["m_playerId"] for e in setup} == set(range(1, 11)),
        "Incomplete player setup",
    )
    result = {}
    playing = {
        i
        for i, s in enumerate(slots)
        if s["m_control"] in (2, 3) and s["m_observe"] == 0
    }
    check(
        {e["m_slotId"] for e in setup} == playing and len(playing) == 10,
        "Setup and lobby slots differ",
    )
    for e in setup:
        slot = slots[e["m_slotId"]]
        check(
            e["_gameloop"] == 0
            and e["m_userId"] == slot["m_userId"]
            and e["m_type"] == {2: 1, 3: 2}[slot["m_control"]],
            "Setup and lobby controllers differ",
        )
        result[e["m_playerId"]] = slot["m_teamId"] + 1
    check(Counter(result.values()) == {1: 5, 2: 5}, "Expected two five-player teams")
    return result


def project(events, tag_to_camp, player_teams, build):
    gate_rows = [
        e
        for e in events
        if e["_eventid"] == 5 and e["m_upgradeTypeName"] == b"GatesAreOpen"
    ]
    check(
        [e["m_playerId"] for e in gate_rows] == list(range(1, 11)),
        "Incomplete gate roster",
    )
    check(all(e["m_count"] == 1 for e in gate_rows), "Unexpected gate upgrade level")
    (gate,) = {e["_gameloop"] for e in gate_rows}
    dragons = set()
    result = []
    activations = 0
    for e in events:
        kind, tick = e["_eventid"], e["_gameloop"]
        if kind not in (1, 2, 3):
            continue
        tag = e["m_unitTagIndex"], e["m_unitTagRecycle"]
        if kind == 1 and e["m_unitTypeName"] == b"VehicleDragon":
            dragons.add(tag)
        elif kind == 2:
            dragons.discard(tag)
        elif kind == 3:
            owner = e["m_controlPlayerId"]
            if tag in tag_to_camp and owner in (11, 12):
                check(tick >= gate, "Camp transfer before gates opened")
                check(owner == e["m_upkeepPlayerId"], "Camp owner fields disagree")
                i, kind_name = tag_to_camp[tag]
                result.append(
                    stat(
                        tick + 1,
                        CAMP,
                        [item(b"CampID", i)],
                        [
                            item(b"TeamID", (owner - 10) * 4096),
                            item(b"GameTime", (tick - gate) * 256),
                        ],
                        [item(b"CampType", kind_name)],
                    )
                )
            elif tag in dragons and owner in player_teams:
                check(tick >= gate, "Pilot transfer before gates opened")
                team = player_teams[owner]
                check(
                    e["m_upkeepPlayerId"] == (owner if build == 41810 else 10 + team),
                    "Unknown pilot upkeep",
                )
                activations += 1
                result.append(
                    stat(
                        tick,
                        DRAGON,
                        [item(b"Event", activations)],
                        [
                            item(b"TeamID", team * 4096),
                            item(b"GameTime", (tick - gate) * 256),
                        ],
                    )
                )
    result.sort(key=lambda e: e["_gameloop"])
    check(
        len({e["_gameloop"] for e in result}) == len(result),
        "Unverified simultaneous objectives",
    )
    return result


def compare(replay, digest, build, tag_to_camp):
    check(sha256(replay.read_bytes()).hexdigest() == digest, "Replay identity")
    p, raw, _ = read_tracker(replay, build)
    events = list(p.decode_replay_tracker_events(raw))
    # No input statistic, event payload, or game time supplies the prediction.
    rows = project(
        [e for e in events if e["_eventid"] in (1, 2, 3, 5)],
        tag_to_camp,
        teams(replay, p, events),
        build,
    )
    target = target_protocol()
    source_ticks = []
    offset = prior = 0
    for ordinal, e in enumerate(events):
        size, rest = divmod(e["_bits"], 8)
        check(not rest, "Physical frame misaligned")
        if e.get("m_eventName") in (CAMP, DRAGON):
            expected = rows[len(source_ticks)].copy()
            if build == 41810:
                expected["m_fixedData"] = expected["m_fixedData"][:-1]
            check(
                expected == {k: v for k, v in e.items() if k != "_bits"},
                "Objective payload or order differs",
            )
            expected["_gameloop"] -= prior
            check(
                encode_tracker_events([expected], target)
                == raw[offset : offset + size],
                "Physical objective bytes differ",
            )
            source_ticks.append(ordinal)
        prior = e["_gameloop"]
        offset += size
    check(
        len(rows) == len(source_ticks) and offset == len(raw),
        "Incomplete objective scan",
    )
    return rows, source_ticks


def verify(legacy, current, evidence, signed, stock, folder, private=None):
    read_clocks(folder)
    report = json.loads(evidence.read_bytes())
    packed = json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    check(sha256(packed).hexdigest() == COHORT, "Unexpected Dragon cohort")
    counts = {}
    ten_rows = []
    map_hash = sha256(signed.read_bytes()).hexdigest()
    check(
        map_hash in (SIGNED_ANNOUNCER, MERC_CAPTURE),
        "Unknown historical map for objective checks",
    )
    for build, field, manifest, package, key in (
        (41810, "old_replays", legacy, signed, map_hash),
        (98348, "target_controls", current, stock, STOCK),
    ):
        paths = json.loads(manifest.read_bytes())
        actors = camps(package, folder / "mapmechanicslib.galaxy", key)
        totals = Counter()
        for rec in report[field]:
            digest = rec["sha256"]
            rows, ords = compare(Path(paths[digest]), digest, build, actors)
            totals.update(e["m_eventName"].decode() for e in rows)
            if digest == SOURCE:
                ten_rows = rows
        counts[build] = dict(totals)
    check(
        counts[98348] == {"DragonKnightActivated": 52, "JungleCampCapture": 260}
        and len(ten_rows) == 17,
        "Fixture counts changed",
    )
    target = target_protocol()
    data = encode_tracker_events(ten_rows, target)
    check(
        [
            {k: v for k, v in e.items() if k != "_bits"}
            for e in target.decode_replay_tracker_events(data)
        ]
        == ten_rows,
        "Target round trip",
    )
    if private:
        with private.open("xb") as f:
            f.write(data)
    return dict(
        target_map=map_hash,
        observed=counts,
        ten_rows=len(ten_rows),
        ten_bytes=len(data),
        ten_sha256=sha256(data).hexdigest(),
        camp_time_origin="team beacon ownership loop",
        dragon_time_origin="pilot transfer loop",
        source_objective_stats_used_for_prediction=False,
        uses_recorded_ownership=True,
        validated_syncs=0,
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("legacy", "current", "evidence", "signed", "stock", "folder"):
        cli.add_argument(name, type=Path)
    cli.add_argument("--private", type=Path)
    print(json.dumps(verify(**vars(cli.parse_args())), indent=2))
