"""Predict ordinary hero lifetimes and camera references from lobby and player statistics."""

import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import re
from struct import Struct

from check_roster import PROFILES, model
from mpq_reader import MPQArchive
from smartcam_tags import components, decode, identity, number, pack, phase, read_case
from protocol_loader import load_protocol
from predict_camp_captures import CONTROLS

HEROES = "15f0314a1c48a0391e76e22360847e7ef0c91b12a29da15d79453045c175a683"
GAME = "a6384749fbe8f676cbd6ccb9ec1aeac004815d37a8e1c2f8f9f8f176b2bfca09"
FIELD = Struct("<II")


def timers(heroes_path, game_path):
    heroes = heroes_path.read_bytes()
    game = game_path.read_bytes()
    if (sha256(heroes).hexdigest(), sha256(game).hexdigest()) != (HEROES, GAME):
        raise ValueError("Unexpected target Galaxy library")
    start = heroes.index(b"bool libCore_gt_DataDeathTimes_Func")
    body = heroes[start:heroes.index(b"\n}", start)]
    table = {int(a): int(b) for a, b in re.findall(
        rb"libCore_gv_bALDeathTimes\[(\d+)\] = (\d+)\.0;", body)}
    if set(table) != set(range(1, 31)):
        raise ValueError("Incomplete standard death timer table")
    return table


def lobby_predictions(path, build):
    schema, count, _ = PROFILES[build]
    p = load_protocol(schema)
    with closing(MPQArchive(path)) as archive:
        slots = p.decode_replay_initdata(archive.read_file("replay.initData"))[
            "m_syncLobbyState"]["m_lobbyState"]["m_slots"]
    roster = {i: s["m_hero"] for i, s in enumerate(slots, 1) if s.get("m_hero")}
    if set(roster) != set(range(1, 11)):
        return []
    teams = [[i for i in roster if slots[i - 1]["m_teamId"] == team] for team in (0, 1)]
    return model(roster, teams, count)


def independent_histories(predictions, tracker, table, horizon):
    # UnitBorn, UnitDied and UnitRevived carry unit tags and are deliberately excluded here.
    levels, deaths = defaultdict(list), defaultdict(list)
    for event in tracker:
        name = event.get("m_eventName")
        if name in (b"LevelUp", b"PlayerDeath"):
            slot = number(event, "m_intData", "PlayerID")
            tick = event["_gameloop"]
            if name == b"LevelUp":
                levels[slot].append((tick, number(event, "m_intData", "Level")))
            else:
                deaths[slot].append(tick - 1)
    result = {}
    for born, index, recycle, slot, _, unit in predictions:
        history = [(born, True)]
        for died in deaths[slot]:
            if died > horizon:
                continue
            pos = bisect_right(levels[slot], died, key=lambda r: r[0])
            if not pos:
                raise ValueError("Player death precedes initial level")
            history.append((died, False))
            revived = died + table[levels[slot][pos - 1][1]] * 16
            if revived <= horizon:
                history.append((revived, True))
        result[(index, recycle)] = (slot, unit, sorted(history))
    return result


def recorded_histories(tracker):
    spawns = set()
    births = defaultdict(list)
    history = defaultdict(list)
    for event in tracker:
        tick = event["_gameloop"]
        if event.get("m_eventName") == b"PlayerSpawned":
            spawns.add((tick, number(event, "m_intData", "PlayerID"),
                        number(event, "m_stringData", "Hero")))
        kind = event["_event"].rsplit(".", 1)[-1]
        if kind in ("SUnitBornEvent", "SUnitInitEvent", "SUnitDiedEvent", "SUnitRevivedEvent"):
            key = identity(event)
            history[key].append((tick, kind != "SUnitDiedEvent"))
            if kind in ("SUnitBornEvent", "SUnitInitEvent"):
                births[tick, event["m_controlPlayerId"], event["m_unitTypeName"]].append(key)
    actual = {}
    for tick, slot, unit in sorted(spawns):
        keys = births[tick, slot, unit]
        if len(keys) == 1 and keys[0] not in actual:
            actual[keys[0]] = (slot, unit, history[keys[0]])
    return actual


def core_horizon(tracker, horizon):
    core = {identity(e) for e in tracker if e["_eventid"] in (1, 6)
            and e["_gameloop"] == 0 and e["m_unitTypeName"] == b"KingsCore"}
    ends = [e["_gameloop"] for e in tracker if e["_eventid"] == 2 and identity(e) in core]
    return ends[0] if len(core) == 2 and len(ends) == 1 else horizon


def reference_timers(references):
    """Recover the ordinary whole-second curve only where three other 41810 recordings support it."""
    if len(references) != len(CONTROLS) or {digest for _, digest in references} != set(CONTROLS):
        raise ValueError("Expected exactly the three independent 41810 references")
    support = defaultdict(Counter)
    residual = Counter()
    for path, digest in references:
        _, tracker, _, _, _ = read_case(path, digest, 41810)
        levels = defaultdict(list)
        for e in tracker:
            if e.get("m_eventName") == b"LevelUp":
                levels[number(e, "m_intData", "PlayerID")].append(
                    (e["_gameloop"], number(e, "m_intData", "Level")))
        for slot, unit, history in recorded_histories(tracker).values():
            for (death, was_alive), (birth, alive) in zip(history, history[1:]):
                if was_alive or not alive:
                    continue
                if unit in (b"HeroMurky", b"HeroTyrael"):
                    residual[unit.decode()] += 1
                    continue
                index = bisect_right(levels[slot], death, key=lambda r: r[0])
                if not index:
                    raise ValueError("Death before initial level")
                level = levels[slot][index - 1][1]
                seconds, remainder = divmod(birth - death, 16)
                if remainder:
                    residual["nonintegral_elapsed_loops"] += 1
                else:
                    support[level][seconds] += 1
    if not support or any(len(v) != 1 for v in support.values()):
        raise ValueError("Conflicting ordinary whole-second observations")
    table = {n: next(iter(v)) for n, v in sorted(support.items())}
    return table, dict(reference_sha256=sorted(CONTROLS),
                       seconds_by_level=table,
                       observations_by_level={n: sum(v.values()) for n,v in sorted(support.items())},
                       outside_ordinary_curve=dict(residual))


def analyze(path, digest, build, table):
    camera, tracker, _, horizon, _ = read_case(path, digest, build)
    rows = decode(camera, horizon)
    cutoff = core_horizon(tracker, horizon)
    proposed = independent_histories(lobby_predictions(path, build), tracker, table, cutoff)
    observed = recorded_histories(tracker)
    counts = Counter(total_camera_fields=2 * len(rows), opening_rows=len(proposed))
    valid = set()
    for key, (slot, unit, history) in proposed.items():
        actual = observed.get(key)
        if actual is None or actual[:2] != (slot, unit):
            continue
        counts["exact_opening_keys"] += 1
        observed_history = [item for item in actual[2] if item[0] <= cutoff]
        actual_changes = set(observed_history[1:])
        for at, alive in history[1:]:
            label = "revive" if alive else "death"
            counts["predicted_" + label] += 1
            counts["exact_" + label] += (at, alive) in actual_changes
        for _, alive in observed_history[1:]:
            counts["observed_" + ("revive" if alive else "death")] += 1
        if history == observed_history:
            valid.add(key)
    counts["heroes_with_exact_whole_lifetime"] = len(valid)
    fields = bytearray()
    shift = 18 if build == 41810 else 22
    for ordinal, (_, tick, *words) in enumerate(rows):
        for side, word in enumerate(words):
            key = components(word, shift)
            counts["observed_primary_fields"] += key in observed
            if key not in proposed:
                continue
            counts["predicted_primary_fields"] += 1
            if key not in valid or tick > cutoff:
                continue
            history = proposed[key][2]
            state = phase(history, tick)
            counts["qualified_primary_fields"] += 1
            counts["qualified_" + state] += 1
            counts["qualified_after_first_revive"] += any(t <= tick and alive for t, alive in history[1:])
            offset = ordinal * 13 + 5 + 4 * side
            if int.from_bytes(camera[offset:offset + 4], "little") != pack(*key, shift):
                raise ValueError("Original field mismatch")
            fields.extend(FIELD.pack(offset, pack(*key, 22)))
    return dict(build=build, sha256=digest, comparison_end_loop=cutoff,
                horizon_basis="KingsCore death" if cutoff != horizon else "archive horizon",
                **counts, span_sha256=sha256(fields).hexdigest()), bytes(fields)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--heroes-lib", type=Path, required=True)
    p.add_argument("--game-lib", type=Path, required=True)
    p.add_argument("--case", nargs=3, required=True, metavar=("REPLAY", "SHA256", "BUILD"))
    p.add_argument("--historical-reference", action="append", nargs=2,
                   metavar=("REPLAY", "SHA256"), help="Repeat for all three other 41810 recordings")
    p.add_argument("--output", type=Path, help="Exclusive-create sparse little-endian offset/value pairs")
    args = p.parse_args()
    path, digest, build = args.case
    table = timers(args.heroes_lib, args.game_lib)
    source = "stock_98348"
    timer_evidence = None
    if args.historical_reference:
        if int(build) != 41810 or digest in CONTROLS:
            raise ValueError("Historical validation requires a held-out source recording")
        table, timer_evidence = reference_timers([(Path(p), h) for p, h in args.historical_reference])
        source = "independent_41810_recordings"
    receipt, fields = analyze(Path(path), digest, int(build), table)
    receipt["timer_source"] = source
    if timer_evidence is not None:
        receipt["historical_timer_evidence"] = timer_evidence
    if args.output:
        with args.output.open("xb") as f:
            f.write(fields)
    print(json.dumps(receipt, indent=2))
