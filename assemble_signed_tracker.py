"""Assemble attributable 98348 tracker frames in their original match order."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
from itertools import groupby
import json
from pathlib import Path

import blocker_spatial_order
import clocked_objective_stats as objectives
import dragon_reset_wire as resets
import hero_revive_wire as revives
from camp_owner_wire import read_tracker
from convert_historical_pings import placements
from dragon_loop_zero import upgrade
from dragon_mastery_ring_history import historical
from dragonshire_packages import MERC_CAPTURE, SIGNED_ANNOUNCER
from encoders import encode_tracker_events
from first_sync_tracker import ZERO, camp_flags, stat
from merc_capture_tracker import generate as mercenary_owners
from opening_birth_wire import model, target_protocol
from predict_camp_captures import SOURCE
from team_level_frames import project as team_levels
from tracker_player_prefix import generate as setup_prefix


def require(condition, message):
    if not condition:
        raise ValueError(message)


def clean(row):
    return {k: v for k, v in row.items() if k != "_bits"}


def source_view(row):
    """Undo only the two modeled tracker schema/value changes when locating a source frame."""
    if row.get("m_eventName") in (objectives.CAMP, objectives.DRAGON):
        fixed = row["m_fixedData"]
        require(fixed[-1]["m_key"] == b"GameTime", "Missing target objective time")
        return {**row, "m_fixedData": fixed[:-1]}
    if row["_eventid"] == 2:
        require(row["m_killerPlayerId"] == 0, "Unexpected blocker removal source")
        return {**row, "m_killerPlayerId": None}
    return row


def opening_heroes(path, build, protocol, package, folder):
    library = folder / "mapmechanicslib.galaxy"
    placed, heroes, _ = model(path, build, protocol, package, library)
    require(
        len(heroes) == 10 and len({h["m_controlPlayerId"] for h in heroes}) == 10,
        "Incomplete hero roster",
    )
    rows = camp_flags(package, library, placed)
    pairs = [
        (tick, list(group))
        for tick, group in groupby(heroes, key=lambda h: h["_gameloop"])
    ]
    require(
        [tick for tick, _ in pairs] == [50, 58, 66, 74, 82],
        "Unmodeled hero startup schedule",
    )
    for _, pair in pairs:
        require(len(pair) == 2, "Incomplete hero pair")
        for hero in pair:
            rows.extend((hero, stat(b"PlayerSpawned", hero)))
        rows.extend(stat(b"LevelUp", h) for h in reversed(pair))
    return rows


def check_sequence(rows, observed):
    require(
        len(rows) == len(observed), "Additional or missing physical events in opening"
    )
    for row, (_, native) in zip(rows, observed, strict=True):
        require(row == clean(native), "Opening hero event or order differs")


def generate(source, package, folder, timers, initial_talents=None):
    target = target_protocol()
    digest = lambda data: sha256(data).hexdigest()
    map_hash = digest(package.read_bytes())
    require(
        digest(source.read_bytes()) == SOURCE
        and map_hash in (SIGNED_ANNOUNCER, MERC_CAPTURE),
        "Expected original TEN replay and supported historical map",
    )
    mechanics = folder / "mapmechanicslib.galaxy"
    objectives.read_clocks(folder)
    source_protocol, raw, end = read_tracker(source, 41810)
    original = list(source_protocol.decode_replay_tracker_events(raw))
    require(
        sum(e["_bits"] for e in original) == 8 * len(raw), "Incomplete source tracker"
    )
    setup, _ = setup_prefix(source, SOURCE, 41810)
    map_body, _ = historical(
        source, SOURCE, package, mechanics, folder / "supportlib.galaxy"
    )
    zero = setup + map_body
    require(
        digest(zero) == ZERO,
        "Actual map opening differs from the qualified queue candidate",
    )
    zero_rows = [clean(e) for e in target.decode_replay_tracker_events(zero)]
    require(
        len(zero_rows) == 235 and all(e["_gameloop"] == 0 for e in zero_rows),
        "Wrong loop-zero block",
    )

    by_tick = defaultdict(list)
    for ordinal, e in enumerate(original):
        by_tick[e["_gameloop"]].append((ordinal, e))
    used = {}

    def admit(producer, rows):
        last = -1
        for row in rows:
            projected_source = source_view(row)
            hits = [
                idx
                for idx, native in by_tick[row["_gameloop"]]
                if clean(native) == projected_source
            ]
            require(
                len(hits) == 1,
                f"{producer}: missing or ambiguous source frame at {row['_gameloop']}",
            )
            (idx,) = hits
            require(
                idx > last and idx not in used,
                f"{producer}: duplicate or misordered frame",
            )
            used[idx] = producer, row
            last = idx

    opening = opening_heroes(source, 41810, source_protocol, package, folder)
    check_sequence(
        opening, [(i, e) for i, e in enumerate(original) if 0 < e["_gameloop"] <= 84]
    )
    admit("hero_startup", opening)
    if initial_talents is not None:
        packet = initial_talents.read_bytes()
        require(
            digest(packet)
            == "641010b8498a0e4faf25ab206cc6df3f41aa7d85b13db22a2ec5fcbb8288e91b",
            "Unexpected initial talent evidence",
        )
        require(
            digest(encode_tracker_events(zero_rows + opening, target))
            == "1073a5bdbffca7d6c50fd4ffe7dcedfe150ea4d2ba4152b4db7b04b357259d86",
            "Talent startup evidence differs",
        )
        admit(
            "initial_talent_requires_award_state",
            [clean(e) for e in target.decode_replay_tracker_events(packet)],
        )
    (gate,) = {
        e["_gameloop"]
        for e in original
        if e.get("m_upgradeTypeName") == b"GatesAreOpen"
    }
    admit("gates_open", [objectives.stat(gate, b"GatesOpen", None, None)])
    for name, delay in ((b"GatesAreOpen", 0), (b"MinionsAreSpawning", 80)):
        admit(
            name.decode(),
            [{**upgrade(i, name), "_gameloop": gate + delay} for i in range(1, 11)],
        )
    blocker_spatial_order.verify_trigger(folder / "gamelib.galaxy")
    admit(
        "gate_blocker_removal",
        blocker_spatial_order.predict(placements(package, map_hash), gate),
    )
    _, revive_data = revives.analyze(
        source, SOURCE, 41810, package, revives.source_curve(timers)
    )
    admit(
        "ordinary_revival",
        [clean(e) for e in target.decode_replay_tracker_events(revive_data)],
    )
    camps = objectives.camps(package, mechanics, map_hash)
    stats, _ = objectives.compare(source, SOURCE, 41810, camps)
    admit("clocked_objective", stats)
    level_rows, reason = team_levels(source, source_protocol, raw)
    require(
        reason is None and len(level_rows) == 210,
        "Incomplete historical team-level clock",
    )
    admit("team_level_requires_recorded_xp_clock", level_rows)
    tags = resets.actors(package, mechanics, map_hash)
    activations = [
        e["_gameloop"] for e in stats if e["m_eventName"] == objectives.DRAGON
    ]
    owners, _ = resets.project(gate, activations, tags, 16, SOURCE)
    admit("objective_owner", owners)
    if map_hash == MERC_CAPTURE:
        captures, _, _ = mercenary_owners(source, package, mechanics)
        for role in ("beacon", "flag"):
            admit(
                "merc_capture_" + role,
                [row for kind, row in captures.values() if kind == role],
            )

    postzero = [i for i, e in enumerate(original) if e["_gameloop"]]
    missing = [i for i in postzero if i not in used]
    require(bool(missing), "Unexpected full conversion")
    first_missing = original[missing[0]]
    ordered = sorted(used)
    rows = zero_rows + [used[i][1] for i in ordered]
    wire = encode_tracker_events(rows, target)
    decoded = list(target.decode_replay_tracker_events(wire))
    require(
        [clean(e) for e in decoded] == rows
        and sum(e["_bits"] for e in decoded) == len(wire) * 8,
        "Target readback differs from assembled tracker",
    )
    require(wire.startswith(zero), "Loop-zero prefix differs after assembly")
    cut = next(
        i for i, e in enumerate(decoded) if e["_gameloop"] >= first_missing["_gameloop"]
    )
    nbits = sum(e["_bits"] for e in decoded[:cut])
    prefix = wire[: nbits // 8]
    require(
        nbits % 8 == 0 and prefix == encode_tracker_events(rows[:cut], target),
        "Invalid prefix boundary",
    )
    counts = Counter(producer for producer, _ in used.values())
    report = dict(
        target_build=98348,
        target_map_sha256=map_hash,
        source_replay_sha256=SOURCE,
        source_tracker_frames=len(original),
        source_postzero_frames=len(postzero),
        target_loop_zero_candidate=len(zero_rows),
        covered_postzero=len(ordered),
        omitted_postzero=len(missing),
        match_end_loop=end,
        sparse_frames=len(rows),
        sparse_bytes=len(wire),
        sparse_sha256=digest(wire),
        continuous_candidate_frames=cut,
        continuous_candidate_bytes=len(prefix),
        continuous_candidate_sha256=digest(prefix),
        last_contiguous_event_loop=rows[cut - 1]["_gameloop"],
        first_missing_loop=first_missing["_gameloop"],
        first_missing_source_ordinal=missing[0],
        first_missing_event=first_missing.get("m_eventName", b"").decode(),
        per_producer=dict(counts),
        native_playback_verified=False,
        verified_target_syncs=0,
    )
    ledger = [
        dict(source_ordinal=i, target_ordinal=n + len(zero_rows), producer=used[i][0])
        for n, i in enumerate(ordered)
    ]
    return wire, prefix, ledger, report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("source", "package", "folder", "timers"):
        parser.add_argument(arg, type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        help="Create a fresh private directory for wire streams and ordinal ledger",
    )
    parser.add_argument(
        "--initial-talents",
        type=Path,
        help="Include the separately reproduced first-purchase tracker stream",
    )
    args = parser.parse_args()
    stream, prefix, ledger, report = generate(
        args.source, args.package, args.folder, args.timers, args.initial_talents
    )
    if args.output:
        args.output.mkdir()
        (args.output / "TEN.tracker.sparse.bin").write_bytes(stream)
        (args.output / "TEN.tracker.prefix.bin").write_bytes(prefix)
        (args.output / "tracker-ordinals.json").write_text(
            json.dumps(ledger), encoding="utf-8"
        )
    print(json.dumps(report, indent=2))
