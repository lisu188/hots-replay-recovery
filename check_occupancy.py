"""Measure what build-41810 Dragon Shire records about heroes near camp captures."""

import argparse
from bisect import bisect_left
from collections import Counter, defaultdict
from contextlib import closing
from hashlib import sha256
import json
from math import hypot
from pathlib import Path

from mpq_reader import MPQArchive
from predict_camp_captures import MAP, SOURCE, CONTROLS, map_camps, birth_keys, number
from protocol_loader import load_protocol


def unit(e):
    return e["m_unitTagIndex"], e["m_unitTagRecycle"]


def events_near(points, xy, start, stop, radius):
    return {
        pid
        for loop, pid, x, y in points
        if start <= loop <= stop and hypot(x - xy[0], y - xy[1]) <= radius
    }


def analyze(path, expected, camps):
    if sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError("Replay SHA differs")
    p = load_protocol(41810)
    with closing(MPQArchive(path)) as arc:
        header = p.decode_replay_header(arc.header["user_data_header"]["content"])
        details = p.decode_replay_details(arc.read_file("replay.details"))
        if (
            header["m_version"]["m_build"] != 41810
            or details["m_cacheHandles"][-1][8:].hex() != MAP
        ):
            raise ValueError("Wrong build or map")
        twire = arc.read_file("replay.tracker.events")
        gwire = arc.read_file("replay.game.events")
    t = list(p.decode_replay_tracker_events(twire))
    centers = {cid: tuple(map(float, record[1])) for cid, record in camps.items()}
    stats = defaultdict(list)
    for e in t:
        if "m_eventName" in e:
            stats[e["m_eventName"].decode()].append(e)
    teams = {
        number(e, "m_intData", "PlayerID"): number(e, "m_intData", "Team")
        for e in stats["PlayerInit"]
    }
    users = {
        e["m_userId"]: e["m_playerId"]
        for e in t
        if e["_event"].endswith("SPlayerSetupEvent")
    }
    spawns = {
        (
            e["_gameloop"],
            number(e, "m_intData", "PlayerID"),
            number(e, "m_stringData", "Hero"),
        )
        for e in stats["PlayerSpawned"]
    }
    births = [e for e in t if e["_event"].endswith("SUnitBornEvent")]
    heroes = {
        unit(e): e["m_controlPlayerId"]
        for e in births
        if (e["_gameloop"], e["m_controlPlayerId"], e["m_unitTypeName"]) in spawns
    }
    hero_names = {pid: name.decode() for _, pid, name in spawns}
    matched_spawns = {
        (e["_gameloop"], e["m_controlPlayerId"], e["m_unitTypeName"])
        for e in births
        if unit(e) in heroes
    }
    if matched_spawns != spawns or Counter(heroes.values()) != {
        pid: 1 for pid in teams
    }:
        raise ValueError("Expected one matching primary hero tracker tag per player")
    active = {}
    cycle = defaultdict(list)
    samples = defaultdict(list)
    packets = []
    defenders = {}
    by_wave = defaultdict(list)
    defender_deaths = {}
    dummies = []
    fixed = defaultdict(list)
    beacon = birth_keys(
        t,
        b"TownMercCampCaptureBeacon",
        dict((i, v[1]) for i, v in camps.items()),
        initial=True,
    )
    marker_types = set()
    for e in t:
        kind = e["_event"].rsplit(".", 1)[-1]
        loop = e["_gameloop"]
        if "m_unitTagIndex" in e:
            key = unit(e)
            if kind in ("SUnitBornEvent", "SUnitInitEvent", "SUnitRevivedEvent"):
                active[key[0]] = key
                if key in heroes:
                    cycle[key].append((loop, 1))
                    samples["hero_birth_revive"].append(
                        (loop, heroes[key], e["m_x"], e["m_y"])
                    )
            if (
                key in beacon
                and kind == "SUnitOwnerChangeEvent"
                and e["m_controlPlayerId"] == e["m_upkeepPlayerId"] in (11, 12)
            ):
                fixed[beacon[key]].append((loop, e["m_controlPlayerId"] - 10))
            name = e.get("m_unitTypeName", b"").decode()
            if kind == "SUnitBornEvent" and name == "MercCoweringDefenderOrientDummy":
                dummies.append((loop, e["m_x"], e["m_y"], e["m_controlPlayerId"]))
            if kind == "SUnitBornEvent" and name.startswith("MercDefender"):
                nearby = [
                    i
                    for i, xy in centers.items()
                    if hypot(e["m_x"] - xy[0], e["m_y"] - xy[1]) <= 8
                ]
                if len(nearby) != 1:
                    raise ValueError("Unmatched defender")
                defenders[key] = nearby[0]
                by_wave[nearby[0], loop].append(key)
            if kind == "SUnitDiedEvent":
                if key in heroes:
                    cycle[key].append((loop, 0))
                    samples["hero_unit_death"].append(
                        (loop, heroes[key], e["m_x"], e["m_y"])
                    )
                if active.get(key[0]) == key:
                    active.pop(key[0])
                if key in defenders:
                    defender_deaths[key] = e
            if name and any(
                w in name.lower()
                for w in ("camp", "merc", "capture", "channel", "occup")
            ):
                marker_types.add(name)
        if kind == "SUnitPositionsEvent":
            packets.append(loop)
            idx = e["m_firstUnitIndex"]
            a = e["m_items"]
            if len(a) % 3:
                raise ValueError("Incomplete position packet")
            for j in range(0, len(a), 3):
                idx += a[j]
                key = active.get(idx)
                x, y = a[j + 1 : j + 3]
                if key in heroes:
                    samples["hero_tracker_sample"].append((loop, heroes[key], x, y))
        if e.get("m_eventName") == b"PlayerDeath":
            samples["hero_death_stat"].append(
                (
                    loop,
                    number(e, "m_intData", "PlayerID"),
                    number(e, "m_fixedData", "PositionX") / 4096,
                    number(e, "m_fixedData", "PositionY") / 4096,
                )
            )

    def active_hero(key, loop):
        history = cycle.get(key, ())
        i = bisect_left(history, (loop, -1)) - 1
        return (
            key in heroes
            and i >= 0
            and history[i][1]
            and (i + 1 == len(history) or history[i + 1][0] > loop)
        )

    marked_game_kinds = set()
    for e in p.decode_replay_game_events(gwire):
        kind = e["_event"].rsplit(".", 1)[-1]
        if any(
            word in kind.lower() for word in ("camp", "capture", "occup", "channel")
        ):
            marked_game_kinds.add(kind)
        loop = e["_gameloop"]
        if kind == "SCmdEvent":
            data = e["m_data"]
        elif kind == "SCmdUpdateTargetUnitEvent":
            data = {"TargetUnit": e["m_target"]}
        elif kind == "SCmdUpdateTargetPointEvent":
            data = {"TargetPoint": e["m_target"]}
        else:
            continue
        pid = users.get(e["_userid"]["m_userId"])
        if pid not in teams:
            continue
        if "TargetPoint" in data:
            s = data["TargetPoint"]
            samples["command_destination"].append(
                (loop, pid, s["x"] / 4096, s["y"] / 4096)
            )
        if "TargetUnit" in data:
            s = data["TargetUnit"]
            tag = s["m_tag"]
            key = tag >> 18, tag & ((1 << 18) - 1)
            x, y = s["m_snapshotPoint"]["x"] / 4096, s["m_snapshotPoint"]["y"] / 4096
            samples["unit_target_location_by_issuer"].append((loop, pid, x, y))
            if active_hero(key, loop):
                samples["targeted_live_hero_snapshot"].append((loop, heroes[key], x, y))
    at_loop = defaultdict(list)
    for loop, pid, x, y in samples["targeted_live_hero_snapshot"]:
        at_loop[loop, pid].append((x, y))
    scale = Counter()
    for loop, pid, x, y in samples["hero_tracker_sample"]:
        positions = at_loop.get((loop, pid))
        if positions:
            scale["same_loop_same_main_body_position_comparisons"] += 1
            scale["raw_within_two_units"] += (
                min(hypot(x - a, y - b) for a, b in positions) <= 2
            )
            scale["times_four_within_two_units"] += (
                min(hypot(x * 4 - a, y * 4 - b) for a, b in positions) <= 2
            )
    rows = []
    for e in stats["JungleCampCapture"]:
        capture = e["_gameloop"]
        cid = number(e, "m_intData", "CampID")
        team = number(e, "m_fixedData", "TeamID") // 4096
        if (capture - 1, team) not in fixed[cid]:
            raise ValueError("Missing direct beacon marker")
        wave = max(loop for (i, loop) in by_wave if i == cid and loop < capture)
        keys = by_wave[cid, wave]
        want = 2 if camps[cid][0] == "SiegeGiants" else 4
        if len(keys) != want or not all(k in defender_deaths for k in keys):
            raise ValueError("Incomplete defender wave")
        last = max(defender_deaths[k]["_gameloop"] for k in keys)
        if last >= capture:
            raise ValueError("Unexpected defender lifetime")
        last_events = [
            defender_deaths[k] for k in keys if defender_deaths[k]["_gameloop"] == last
        ]
        killers = set(d["m_killerPlayerId"] for d in last_events)
        kill_player_body = all(
            heroes.get((d.get("m_killerUnitTagIndex"), d.get("m_killerUnitTagRecycle")))
            == d.get("m_killerPlayerId")
            and active_hero(
                (d.get("m_killerUnitTagIndex"), d.get("m_killerUnitTagRecycle")), last
            )
            for d in last_events
        )
        dummy_same = any(
            dl == last
            and hypot(x - centers[cid][0], y - centers[cid][1]) <= 8
            and owner == 15
            for dl, x, y, owner in dummies
        )
        killer_evidence = {}
        positive_tracker_samples = [
            dict(
                loop=l,
                hero=hero_names[p],
                team=teams[p],
                x=x,
                y=y,
                credited_killer=p in killers,
            )
            for l, p, x, y in samples["hero_tracker_sample"]
            if last <= l <= capture
            and hypot(x - centers[cid][0], y - centers[cid][1]) <= 4
        ]
        for label in ("hero_tracker_sample", "targeted_live_hero_snapshot"):
            at_capture = [
                (p, hypot(x - centers[cid][0], y - centers[cid][1]))
                for l, p, x, y in samples[label]
                if l == capture and p in killers
            ]
            close = events_near(samples[label], centers[cid], last, capture - 1, 4)
            killer_evidence[label] = dict(
                credited_killer_inside_four_between_death_and_beacon=bool(
                    close & killers
                ),
                another_winning_body_inside_four_between_death_and_beacon=any(
                    p not in killers and teams[p] == team for p in close
                ),
                credited_killer_seen_outside_eight_at_capture=any(
                    dist > 8 for _, dist in at_capture
                ),
            )
        observed = {}
        for label, items in samples.items():
            observed[label] = {}
            for window, a, b in (
                ("death_exact", last, last),
                ("beacon_exact", capture - 1, capture - 1),
                ("capture_exact", capture, capture),
                ("death_to_beacon", last, capture - 1),
                ("prior_second", capture - 16, capture),
                ("prior_15_seconds", capture - 240, capture),
            ):
                observed[label][window] = {}
                for radius in (2, 4, 8):
                    pids = events_near(items, centers[cid], a, b, radius)
                    observed[label][window][str(radius)] = sorted(
                        {teams[pid] for pid in pids}
                    )
        rows.append(
            dict(
                camp=cid,
                team=team,
                capture_loop=capture,
                beacon_loop=capture - 1,
                last_defender_death=last,
                delay_to_capture=capture - last,
                dying_defender_killer_teams=sorted(
                    {teams[k] for k in killers if k in teams}
                ),
                killer_live_primary_body_matches_credited_player=kill_player_body,
                hostile_orientation_dummy_at_last_death=dummy_same,
                credited_killer_position=killer_evidence,
                tracker_hero_samples_within_four_from_death_through_stat=positive_tracker_samples,
                events=observed,
            )
        )
    names = sorted(
        k
        for k in stats
        if any(w in k.lower() for w in ("camp", "merc", "capture", "occup", "channel"))
    )
    return dict(
        replay_sha256=expected,
        tracker_sha256=sha256(twire).hexdigest(),
        game_sha256=sha256(gwire).hexdigest(),
        heroes_matched=len(heroes),
        matched_spawn_labels=len(matched_spawns),
        spawn_labels=len(spawns),
        packets=len(packets),
        packet_intervals=dict(Counter(b - a for a, b in zip(packets, packets[1:]))),
        sample_counts={k: len(v) for k, v in samples.items()},
        camp_stat_names=names,
        other_marker_types=sorted(marker_types),
        unit_position_scale_control=scale,
        game_event_names_matching_camp_capture_channel_occupancy=sorted(
            marked_game_kinds
        ),
        hostile_dummy_births=len(dummies),
        rows=rows,
    )


def summarize(cases):
    groups = [
        ("source", cases[0]["rows"]),
        ("three_controls", sum((d["rows"] for d in cases[1:]), [])),
        ("all", sum((d["rows"] for d in cases), [])),
    ]
    output = {}
    for name, rows in groups:

        def covered(sample, window, rad, selected=rows):
            return sum(
                r["team"] in r["events"][sample][window][str(rad)] for r in selected
            )

        counts = {}
        for label in rows[0]["events"]:
            counts[label] = {
                w: {rad: covered(label, w, rad) for rad in (2, 4, 8)}
                for w in (
                    "death_exact",
                    "beacon_exact",
                    "capture_exact",
                    "death_to_beacon",
                    "prior_second",
                    "prior_15_seconds",
                )
            }
        camps = {}
        for i in range(1, 6):
            selected = [r for r in rows if r["camp"] == i]
            camps[i] = {
                "captures": len(selected),
                **{
                    w: covered("hero_tracker_sample", w, 4, selected)
                    for w in (
                        "death_exact",
                        "beacon_exact",
                        "capture_exact",
                        "death_to_beacon",
                        "prior_15_seconds",
                    )
                },
            }
        output[name] = dict(
            captures=len(rows),
            by_camp_within_four=camps,
            capturing_team_position_or_command_counts=counts,
            last_defender_credits_same_team=sum(
                r["dying_defender_killer_teams"] == [r["team"]] for r in rows
            ),
            exactly_credited_live_primary_body=sum(
                r["killer_live_primary_body_matches_credited_player"] for r in rows
            ),
            hostile_dummy_at_final_death_by_camp=dict(
                sorted(
                    Counter(
                        r["camp"]
                        for r in rows
                        if r["hostile_orientation_dummy_at_last_death"]
                    ).items()
                )
            ),
            delay_from_final_death_to_stat_loop=dict(
                sorted(Counter(r["delay_to_capture"] for r in rows).items())
            ),
            killer_position={
                sensor: {
                    k: sum(r["credited_killer_position"][sensor][k] for r in rows)
                    for k in rows[0]["credited_killer_position"][sensor]
                }
                for sensor in rows[0]["credited_killer_position"]
            },
        )
    return dict(
        format="legacy-camp-hero-presence-coverage-v1",
        map_sha256=MAP,
        diagnostic_radii_map_units=[2, 4, 8],
        historical_capture_radius_verified=False,
        complete_hero_occupancy_verified=False,
        input_evidence=[{k: v for k, v in d.items() if k != "rows"} for d in cases],
        groups=output,
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--map", type=Path, required=True)
    cli.add_argument("--replays", nargs=4, type=Path, required=True)
    cli.add_argument(
        "--details",
        action="store_true",
        help="Emit per-capture results instead of compact group counts.",
    )
    args = cli.parse_args()
    by_sha = {sha256(p.read_bytes()).hexdigest(): p for p in args.replays}
    if set(by_sha) != {SOURCE, *CONTROLS}:
        raise ValueError("Expected original and three exact 41810 controls")
    camps = map_camps(args.map)
    cases = [analyze(by_sha[h], h, camps) for h in (SOURCE, *CONTROLS)]
    print(json.dumps(cases if args.details else summarize(cases), indent=1))
