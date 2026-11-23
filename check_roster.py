"""Test the historical opening hero birth order without using observed tracker tags as inputs."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from mpq_reader import MPQArchive
from protocol_loader import load_protocol

TEN_HEROES = (
    "Abathur",
    "Anubarak",
    "Barbarian",
    "FaerieDragon",
    "Greymane",
    "Kaelthas",
    "Nova",
    "Tyrande",
)
PROFILES = {
    41810: (
        41810,
        172,
        "e0a58745837b3b5351015c933560dbffb178d747009d2d57b4153ef425cf7250",
    ),
    98348: (
        96477,
        170,
        "f557190f8aaab160789272ce086b8b69d6a8037b152de150332603dae3dc098f",
    ),
}


def model(heroes, teams, count):
    """Propose a normal two-team opening, with optional additional allocations unresolved."""
    a, b = teams
    if (
        len(a) != 5
        or len(b) != 5
        or type(count) is not int
        or count < 0
        or sorted([*a, *b]) != list(range(1, 11))
        or set(heroes) != set(range(1, 11))
    ):
        raise ValueError("Unsupported team structure")
    order = [a[0], b[0], *(who for pair in zip(b[1:], a[1:]) for who in pair)]
    return [
        (
            50 + 8 * (slot // 2),
            count + slot,
            1,
            controller,
            controller,
            b"Hero" + heroes[controller],
        )
        for slot, controller in enumerate(order)
    ]


def audit(path, digest, build):
    if sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("Digest")
    schema, count, map_sha = PROFILES[build]
    p = load_protocol(schema)
    with closing(MPQArchive(path)) as a:
        v = p.decode_replay_header(a.header["user_data_header"]["content"])
        if (
            v["m_version"]["m_build"],
            v["m_version"]["m_baseBuild"],
            v["m_dataBuildNum"],
        ) != (build,) * 3:
            raise ValueError("Version")
        lobby = p.decode_replay_initdata(a.read_file("replay.initData"))[
            "m_syncLobbyState"
        ]
        dependencies = lobby["m_gameDescription"]["m_cacheHandles"]
        if (
            not dependencies
            or dependencies
            != p.decode_replay_details(a.read_file("replay.details"))["m_cacheHandles"]
            or dependencies[-1][:4] != b"s2ma"
            or dependencies[-1][8:].hex() != map_sha
        ):
            raise ValueError("Map")
        slots = lobby["m_lobbyState"]["m_slots"]
        roster = {i: s["m_hero"] for i, s in enumerate(slots, 1) if s.get("m_hero")}
        teams = [
            [i for i, s in enumerate(slots, 1) if i in roster and s["m_teamId"] == team]
            for team in (0, 1)
        ]
        if set(roster) != set(range(1, 11)):
            return {
                "build": build,
                "sha256": digest,
                "lobby_hero_slots": len(roster),
                "all_ten_in_order_with_no_extras": False,
                "exact_rows": 0,
                "excluded": "incomplete hero slots in initial lobby",
            }
        pred = model(roster, teams, count)
        wire = a.read_file("replay.tracker.events")
    bits = 0
    actual = []
    opening = []
    initial = 0
    for e in p.decode_replay_tracker_events(wire):
        bits += e["_bits"]
        if e["_eventid"] not in (1, 6):
            continue
        unit = (
            e["m_unitTypeName"]
            if e["_eventid"] == 1
            else b"INIT:" + e["m_unitTypeName"]
        )
        if e["_eventid"] in (1, 6) and e["_gameloop"] == 0:
            initial += 1
        if e["_eventid"] in (1, 6) and 0 < e["_gameloop"] <= 82:
            actual.append(
                (
                    e["_gameloop"],
                    e["m_unitTagIndex"],
                    e["m_unitTagRecycle"],
                    e["m_controlPlayerId"],
                    e["m_upkeepPlayerId"],
                    unit,
                )
            )
        if e["_eventid"] in (1, 6) and 0 < e["_gameloop"] < 90:
            opening.append((e["_gameloop"], e["m_controlPlayerId"], unit))
    if bits != 8 * len(wire) or initial != count:
        raise ValueError("Tracker")
    missing = Counter(pred) - Counter(actual)
    extra = Counter(actual) - Counter(pred)
    hero_evidence = []
    for p0 in pred:
        tick, _, _, owner, _, unit = p0
        births = [r for r in opening if r[1:] == (owner, unit)]
        witnessed = any(r[0] == tick for r in births)
        other = [r for r in opening if r[1] == owner and tick <= r[0] < tick + 8]
        if witnessed:
            other.remove((tick, owner, unit))
        hero_evidence.append(
            dict(
                hero=roster[owner].decode(),
                exact_rank=p0 in actual,
                observed_timed_birth=witnessed,
                other_owned_births_within_eight_loops=[r[2].decode() for r in other],
            )
        )
    return {
        "build": build,
        "sha256": digest,
        "layout_startup_count": count,
        "all_ten_in_order_with_no_extras": pred == actual,
        "exact_rows": sum((Counter(actual) & Counter(pred)).values()),
        "hero_evidence": hero_evidence,
        "miss": [(*k[:-1], k[-1].decode()) for k in missing.elements()],
        "extra": [(*k[:-1], k[-1].decode()) for k in extra.elements()],
    }


def summarize(cases):
    if len({r["sha256"] for r in cases}) != len(cases):
        raise ValueError("Duplicate case")
    out = {
        "format": "dragon-shire-initial-hero-rank-hypothesis-v1",
        "cases": [],
        "profiles": {},
    }
    for case in sorted(cases, key=lambda r: r["sha256"]):
        out["cases"].append(
            {
                k: case[k]
                for k in (
                    "build",
                    "sha256",
                    "all_ten_in_order_with_no_extras",
                    "exact_rows",
                )
            }
        )
    for build in sorted({r["build"] for r in cases}):
        rows = [r for r in cases if r["build"] == build]
        by_hero = {}
        for hero in TEN_HEROES:
            appearances = [
                e for r in rows for e in r.get("hero_evidence", []) if e["hero"] == hero
            ]
            by_hero[hero] = dict(
                appearances=len(appearances),
                exact_rows=sum(e["exact_rank"] for e in appearances),
                expected_type_owner_tick=sum(
                    e["observed_timed_birth"] for e in appearances
                ),
                additional_same_owner_births_in_eight_loops=sum(
                    len(e["other_owned_births_within_eight_loops"]) for e in appearances
                ),
            )
        out["profiles"][str(build)] = dict(
            replays=len(rows),
            expected_rows=10 * len(rows),
            exact_rows=sum(r["exact_rows"] for r in rows),
            all_ten_in_order_with_no_extras=sum(
                r["all_ten_in_order_with_no_extras"] for r in rows
            ),
            excluded_rosters=sum("excluded" in r for r in rows),
            source_hero_coverage=by_hero,
        )
    return out


if __name__ == "__main__":
    cmd = argparse.ArgumentParser(description=__doc__)
    cmd.add_argument(
        "--case",
        action="append",
        nargs=3,
        required=True,
        metavar=("REPLAY", "SHA", "BUILD"),
    )
    cases = [audit(Path(p), h, int(b)) for p, h, b in cmd.parse_args().case]
    print(json.dumps(summarize(cases), indent=2))
