"""Measure camp beacon, defender-death and reward transitions from original HotS archives."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import re
from xml.etree import ElementTree

from dragon_startup_births import indexed, xy as authored_xy
from mpq_reader import MPQArchive
from protocol_loader import load_protocol

# Frozen on TEN_GREYMANE before examining the three independent 41810 fixtures.
STAT_LAG = 1
RESET_AFTER_STAT = {41810: 16, 98348: 48}


def require(test, message):
    if not test:
        raise ValueError(message)


def map_points(map_path):
    with closing(MPQArchive(map_path)) as a:
        xml = ElementTree.fromstring(a.read_file("Objects"))
        script = a.read_file("MapScript.galaxy").decode("utf-8-sig")
    require(xml.tag == "PlacedObjects", "Expected the map Objects member")
    points = indexed(xml, "ObjectPoint", "Id")

    def projected(point):
        require(int(point) in points, "Missing referenced camp point")
        return tuple(map(int, authored_xy(points[int(point)])))

    captains = {}
    defenders = {}
    types = {
        "SiegeGiants": ("MercDefenderSiegeGiant",) * 2,
        "Knights": ("MercDefenderMeleeKnight",) * 3 + ("MercDefenderRangedMage",),
    }
    blocks = script.split("lv_junglecamp += 1;")[1:]
    require(len(blocks) == 5, "Expected five camps")
    for camp, b in enumerate(blocks, 1):
        (p,) = re.findall(r"lv_mapDataCampCaptainSpawnPoint = PointFromId\((\d+)\);", b)
        xy = projected(p)
        require(xy not in captains, "Duplicate captain position")
        captains[xy] = camp
        (k,) = re.findall(
            r"lv_mapDataCampDefenderType = libMapM_ge_JungleCampDefenderTypes_(\w+);", b
        )
        slots = re.findall(
            r"lv_mapDataDefenderSpawnPoints\[(\d+)\] = PointFromId\((\d+)\);", b
        )
        require(
            k in types
            and [int(i) for i, _ in slots] == list(range(1, len(types[k]) + 1)),
            "Unexpected defender slots",
        )
        for name, (_, point) in zip(types[k], slots):
            key = name, *projected(point)
            require(key not in defenders, "Ambiguous defender birth")
            defenders[key] = camp
    return captains, defenders


def named_value(e, field, key):
    (value,) = [x["m_value"] for x in e[field] if x["m_key"] == key]
    return value


def ownership_forecast(changes, stats, build, horizon):
    """Predict stat and reset events from team-owner transitions alone; compare full multisets."""
    teams = [
        (camp, t, o)
        for camp, events in changes.items()
        for t, o in events
        if o in (11, 12)
    ]
    extra_owners = sum(
        o not in (0, 11, 12) for events in changes.values() for _, o in events
    )
    expected_stats = Counter(
        (camp, t + STAT_LAG, o) for camp, t, o in teams if t + STAT_LAG <= horizon
    )
    actual_stats = Counter((camp, t, o) for camp, t, o, _ in stats)
    reset_lag = STAT_LAG + RESET_AFTER_STAT[build]
    expected_resets = Counter(
        (camp, t + reset_lag) for camp, t, _ in teams if t + reset_lag <= horizon
    )
    actual_resets = Counter(
        (camp, t) for camp, events in changes.items() for t, o in events if o == 0
    )

    def compare(predicted, observed):
        return dict(
            predicted=predicted.total(),
            observed=observed.total(),
            matches=(predicted & observed).total(),
            missing_observations=(predicted - observed).total(),
            unexpected_observations=(observed - predicted).total(),
        )

    return dict(
        team_ownership_events=len(teams),
        other_ownership_events=extra_owners,
        team_to_stat_loops=STAT_LAG,
        stat_to_reset_loops=RESET_AFTER_STAT[build],
        stats_beyond_replay_end=len(teams) - expected_stats.total(),
        resets_beyond_replay_end=len(teams) - expected_resets.total(),
        capture_stats=compare(expected_stats, actual_stats),
        neutral_resets=compare(expected_resets, actual_resets),
    )


def measure(events, captains, defenders, build, horizon):
    beacon_camps = {}
    by_tag = {}
    live = defaultdict(set)
    last_dead = {}
    changes = defaultdict(list)
    stats = []
    previous_loop = -1
    for e in events:
        kind = e["_event"].rsplit(".", 1)[-1]
        loop = e["_gameloop"]
        require(
            previous_loop <= loop <= horizon,
            "Nonmonotonic tracker or event beyond replay end",
        )
        previous_loop = loop
        tag = e.get("m_unitTagIndex"), e.get("m_unitTagRecycle")
        if kind == "SUnitBornEvent":
            name = e["m_unitTypeName"].decode()
            xy = e["m_x"], e["m_y"]
            if loop == 0 and name == "TownMercCampCaptureBeacon":
                require(
                    xy in captains and tag not in beacon_camps, "Invalid camp beacon"
                )
                beacon_camps[tag] = captains[xy]
            elif (e["m_controlPlayerId"], e["m_upkeepPlayerId"]) == (15, 15) and (
                name,
                *xy,
            ) in defenders:
                camp = defenders[name, *xy]
                require(tag not in by_tag, "Duplicate live defender tag")
                by_tag[tag] = camp
                if not live[camp]:
                    last_dead.pop(camp, None)
                live[camp].add(tag)
        elif kind == "SUnitDiedEvent" and tag in by_tag:
            camp = by_tag.pop(tag)
            live[camp].remove(tag)
            if not live[camp]:
                last_dead[camp] = loop
        elif kind == "SUnitOwnerChangeEvent" and tag in beacon_camps:
            require(
                e["m_controlPlayerId"] == e["m_upkeepPlayerId"], "Beacon roles differ"
            )
            changes[beacon_camps[tag]].append((loop, e["m_controlPlayerId"]))
        elif e.get("m_eventName") == b"JungleCampCapture":
            camp = named_value(e, "m_intData", b"CampID")
            team = named_value(e, "m_fixedData", b"TeamID")
            require(team in (4096, 8192), "Unknown capturing team")
            stats.append((camp, loop, 10 + team // 4096, last_dead.get(camp)))
    require(
        len(beacon_camps) == len(set(beacon_camps.values())) == 5,
        "Missing authored camp beacon",
    )
    intervals = []
    consumed = set()
    for camp, stat, owner, last in stats:
        before = [(i, t) for i, (t, _) in enumerate(changes[camp]) if t <= stat]
        if not before:
            continue
        i, team_loop = before[-1]
        if (
            changes[camp][i][1] != owner
            or (camp, i) in consumed
            or i + 1 >= len(changes[camp])
            or changes[camp][i + 1][1] != 0
        ):
            continue
        reset = changes[camp][i + 1][0]
        if reset <= stat:
            continue
        consumed.add((camp, i))
        # A tracked last death must precede the actual ownership transfer to establish its interval.
        intervals.append(
            dict(
                camp=camp,
                last_tracked_defender_death=(
                    last if last is not None and last <= team_loop else None
                ),
                team_beacon=team_loop,
                capture_stat=stat,
                neutral_beacon=reset,
            )
        )
    coverage = ownership_forecast(changes, stats, build, horizon)
    coverage["capture_stats_without_adjacent_owner_and_reset"] = len(stats) - len(
        intervals
    )
    return intervals, coverage


def inspect(map_path, build, replays):
    source_points = map_points(map_path)
    map_sha = sha256(map_path.read_bytes()).hexdigest()
    proto = load_protocol({41810: 41810, 98348: 96477}[build])
    cases = []
    for path in replays:
        with closing(MPQArchive(path)) as a:
            header = proto.decode_replay_header(a.header["user_data_header"]["content"])
            require(
                (
                    header["m_version"]["m_build"],
                    header["m_version"]["m_baseBuild"],
                    header["m_dataBuildNum"],
                )
                == (build,) * 3,
                "Incorrect physical build",
            )
            handles = proto.decode_replay_details(a.read_file("replay.details"))[
                "m_cacheHandles"
            ]
            init = proto.decode_replay_initdata(a.read_file("replay.initData"))
            require(
                handles
                and len(handles[-1]) == 40
                and handles[-1][:4] == b"s2ma"
                and handles[-1][8:].hex() == map_sha
                and handles
                == init["m_syncLobbyState"]["m_gameDescription"]["m_cacheHandles"],
                "Map binding disagrees",
            )
            wire = a.read_file("replay.tracker.events")
        intervals, coverage = measure(
            proto.decode_replay_tracker_events(wire),
            *source_points,
            build,
            header["m_elapsedGameLoops"],
        )

        def counts(values):
            return dict(sorted(Counter(values).items()))

        result = dict(
            replay_sha256=sha256(path.read_bytes()).hexdigest(),
            tracker_sha256=sha256(wire).hexdigest(),
            captures=coverage["capture_stats"]["observed"],
            frozen_rule=coverage,
            team_beacon_to_stat=counts(
                r["capture_stat"] - r["team_beacon"] for r in intervals
            ),
            stat_to_neutral=counts(
                r["neutral_beacon"] - r["capture_stat"] for r in intervals
            ),
        )
        if build == 41810:
            result["death_to_team_beacon"] = counts(
                r["team_beacon"] - r["last_tracked_defender_death"]
                for r in intervals
                if r["last_tracked_defender_death"] is not None
            )
            result["intervals"] = intervals
        cases.append(result)
    require(
        cases and len(cases) == len({r["replay_sha256"] for r in cases}),
        "Expected distinct recordings",
    )
    return dict(build=build, map_sha256=map_sha, cases=cases)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("map", type=Path)
    ap.add_argument("replays", type=Path, nargs="+")
    ap.add_argument("--build", type=int, required=True, choices=(41810, 98348))
    ap.add_argument(
        "--historical-cohort",
        action="store_true",
        help="require TEN_GREYMANE and the three pinned independent build-41810 cases",
    )
    args = ap.parse_args()
    report = inspect(args.map, args.build, args.replays)
    if args.historical_cohort:
        from predict_camp_captures import CONTROLS, MAP, SOURCE

        files = {r["replay_sha256"]: r for r in report["cases"]}
        require(
            args.build == 41810
            and report["map_sha256"] == MAP
            and set(files) == {SOURCE, *CONTROLS},
            "Expected the four pinned recordings of the original Dragon Shire map",
        )
        report["development_replay_sha256"] = SOURCE
        report["independent_control_sha256"] = list(CONTROLS)
        report["cases"] = [files[h] for h in (SOURCE, *CONTROLS)]
    print(json.dumps(report, indent=2))
