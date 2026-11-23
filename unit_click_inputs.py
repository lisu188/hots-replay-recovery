"""Generate original-ordinal TEN unit-click inputs on the GateOrder Dragon Shire layout."""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import first_sync_game

from camp_owner_wire import read_tracker
from dragon_vehicle_cycles import RESPAWN_LOOPS, activation_owners, vehicle_cycles
from encoders import encode_game_events as named_encode
from first_sync_game import game
from hero_camera_lifetimes import core_horizon, independent_histories, lobby_predictions, recorded_histories
from hero_revive_wire import GATE_MAP, source_curve, team_slots
from match_selections import at, timeline
from mpq_reader import MPQArchive
from native_game_events import GameEvent, encode_game_events, iter_game_events
from opening_birth_wire import FIELDS, model, target_protocol
from predict_camp_captures import SOURCE
from project_rank_targets import lifetime_ends
from repair_unit_tags import components, pack
from smartcam_tags import phase

ID = 39
NAME = "NNet.Game.SUnitClickEvent"


def reference_keys(reference_list):
    refs = sorted(r["replay_sha256"] for r in json.loads(reference_list.read_bytes())["references"])
    pin = "ecf4ad00b6c16fb075971d6ab03a15cbe6040d03f8e7d0eefd110e0334b55545"
    if len(set(refs)) != 24 or sha256(" ".join(refs).encode()).hexdigest() != pin:
        raise ValueError("Unexpected first-sync reference list")
    return set(refs)


def validate_cohort(controls, expected):
    if len(controls) != 24 or {r["replay_sha256"] for r in controls} != expected:
        raise ValueError("Expected 24 distinct original 98348 recordings")
    for row in controls:
        if (
            row["build"] != 98348
            or row["best_tag_shifts"] != [22]
            or row["frames"] < 1
            or row["frames"] != row["nonzero_frames"]
            or row["frames"] != row["best_tracker_matches"]
        ):
            raise ValueError("Incomplete independent 98348 click or tag crosscheck")
    totals = sum(c["frames"] for c in controls), sum(c["enclosing_bytes"] for c in controls)
    if totals != (41988, 293916):
        raise ValueError("Unexpected physical click totals")
    return totals


def clicks(protocol, raw):
    tid, name = protocol.game_event_types[ID]
    kind, args = protocol.typeinfos[tid]
    if name != NAME or kind != "_struct" or len(args[0]) != 1:
        raise ValueError("Unexpected click root")
    ((field, child, label),) = args[0]
    if (field, label) != ("m_unitTag", -1) or protocol.typeinfos[child] != ("_int", [(0, 32)]):
        raise ValueError("Expected a mandatory uint32 unit tag")
    prior = offset = 0
    for ordinal, event in enumerate(protocol.decode_replay_game_events(raw)):
        tick = event["_gameloop"]
        size, rem = divmod(event["_bits"], 8)
        if rem or not size or offset + size > len(raw) or tick < prior:
            raise ValueError("Invalid enclosing frame")
        if event["_eventid"] == ID:
            if event["_event"] != NAME:
                raise ValueError("Click kind mismatch")
            yield ordinal, prior, event, raw[offset : offset + size]
        prior, offset = tick, offset + size
    if offset != len(raw):
        raise ValueError("Incomplete enclosing member")


def analyze_physical(path, digest, build):
    p, raw = game(path, digest, build)
    with closing(MPQArchive(path)) as arc:
        tracker = list(p.decode_replay_tracker_events(arc.read_file("replay.tracker.events")))
    changes = timeline(tracker)
    shift = 18 if build == 41810 else 22
    states, live_types, tags = Counter(), Counter(), Counter()
    wire, expected, rows = [], bytearray(), []
    for ordinal, prior, event, physical in clicks(p, raw):
        tick, user, tag = event["_gameloop"], event["_userid"]["m_userId"], event["m_unitTag"]
        pair = components(tag, shift)
        state = at(changes.get(pair, ()), tick)
        if tag == 0:
            states["zero"] += 1
        else:
            tags[tag] += 1
            if state is None:
                states["untracked"] += 1
            elif state[0] == tick:
                states["transition_tick"] += 1
            elif not state[3]:
                states["after_death"] += 1
            else:
                states["prior_live"] += 1
                live_types[state[1]] += 1
        rows.append((ordinal, event))
        expected.extend(physical)
        wire.append(GameEvent(tick - prior, user, ID, (tag,)))
    if encode_game_events(wire) != expected:
        raise ValueError("Native event writer disagrees with physical frame bytes")
    scores = {w: sum(n for tag, n in tags.items() if components(tag, w) in changes) for w in range(1, 32)}
    best = max(scores.values())
    return (
        tracker,
        rows,
        dict(
            build=build,
            replay_sha256=digest,
            frames=len(wire),
            states=dict(sorted(states.items())),
            enclosing_bytes=len(expected),
            enclosing_sha256=sha256(expected).hexdigest(),
            nonzero_frames=tags.total(),
            best_tracker_matches=best,
            best_tag_shifts=[w for w, n in scores.items() if n == best],
        ),
        live_types,
    )


def control(case):
    path, digest = case
    _, _, receipt, types = analyze_physical(path, digest, 98348)
    return receipt, types


def generate(source, gate_map, mechanics, curve):
    """Return {zero-based source game ordinal: target named event}, sparse bytes and aggregate report."""
    tracker, clicks_in, observed, _ = analyze_physical(source, SOURCE, 41810)
    old, _, end = read_tracker(source, 41810)
    cutoff = core_horizon(tracker, end)
    placed, heroes, digest = model(source, 41810, old, gate_map, mechanics)
    if (
        digest != GATE_MAP
        or len(clicks_in) != 2756
        or observed["best_tag_shifts"] != [18]
        or observed["nonzero_frames"] != len(clicks_in)
    ):
        raise ValueError("Unexpected source click cohort or layout")
    starts = {(e["m_unitTagIndex"], e["m_unitTagRecycle"]): e for e in placed + heroes}
    actual = {
        (e["m_unitTagIndex"], e["m_unitTagRecycle"]): e
        for e in tracker
        if e["_eventid"] == 1 and e["_gameloop"] <= 82
    }
    # The GateOrder allocator supplies the target pairs independently of historical click tags.
    if starts.keys() != actual.keys() or any(
        tuple(e[k] for k in ("_gameloop", *FIELDS)) != tuple(actual[key][k] for k in ("_gameloop", *FIELDS))
        for key, e in starts.items()
    ):
        raise ValueError("Historical births and independent map/roster allocation disagree")
    changes = timeline(tracker)
    hero_keys = {(e["m_unitTagIndex"], e["m_unitTagRecycle"]) for e in heroes}
    hero_life = independent_histories(
        lobby_predictions(source, 41810), tracker, source_curve(curve), cutoff
    )
    recorded = recorded_histories(tracker)
    if set(hero_life) != hero_keys or any(
        key not in recorded
        or (slot, unit, life)
        != (recorded[key][0], recorded[key][1], [row for row in recorded[key][2] if row[0] <= cutoff])
        for key, (slot, unit, life) in hero_life.items()
    ):
        raise ValueError("Historical primary hero life disagrees with independent timer and roster")
    ends = lifetime_ends(tracker, starts.keys() - hero_keys)
    (statue,) = [row for row in placed if row["m_unitTypeName"] == b"VehicleDragon"]
    teams = {owner: (slot - 1) // 5 + 1 for owner, slot in team_slots(source, old).items()}
    cycles = vehicle_cycles(tracker, (statue["m_x"], statue["m_y"]), teams, end)
    first = cycles[0]
    if (
        first.born != 0
        or first.tag != (statue["m_unitTagIndex"], statue["m_unitTagRecycle"])
        or first.activated is None
        or first.died is None
        or len(cycles) < 2
        or cycles[1].born - RESPAWN_LOOPS != first.died
        or activation_owners(cycles, tracker, 41810)["different"]
    ):
        raise ValueError(
            "First Dragon Knight objective disagrees with placement, owner or next statue timer"
        )
    projected, categories, accepted_types, withheld_types = {}, Counter(), Counter(), Counter()
    for ordinal, event in clicks_in:
        loop = event["_gameloop"]
        pair = components(event["m_unitTag"], 18)
        state = at(changes.get(pair, ()), loop)
        unit = state[1] if state else "untracked"
        if loop > cutoff:
            reason = "after_core_horizon"
        elif pair not in starts:
            reason = "postopening_allocation"
        elif state is None or not state[3] or state[0] == loop:
            reason = "historical_lifetime_boundary_or_inactive"
        elif pair in hero_keys:
            reason = (
                "primary_hero" if phase(hero_life[pair][2], loop) == "live" else "unconfirmed_hero_life"
            )
        elif (
            not (0 < loop < ends.get(pair, cutoff + 1))
            or state[1] != starts[pair]["m_unitTypeName"].decode()
        ):
            reason = "after_initial_placement_life"
        elif unit == "VehicleDragon":
            expected_owner = first.pilot if loop > first.activated else 0
            reason = (
                "first_dragon_vehicle"
                if pair == first.tag
                and first.active_at(loop)
                and loop != first.activated
                and state[2] == expected_owner
                else "vehicle_activation"
            )
        else:
            reason = "map_opening_generation"
        categories[reason] += 1
        if reason in ("primary_hero", "map_opening_generation", "first_dragon_vehicle"):
            target = starts[pair]
            word = pack(target["m_unitTagIndex"], target["m_unitTagRecycle"], 22)
            projected[ordinal] = {**event, "m_unitTag": word}
            accepted_types[unit] += 1
        else:
            withheld_types[unit] += 1
    previous = 0
    frames = []
    for event in projected.values():
        frames.append(
            GameEvent(
                event["_gameloop"] - previous, event["_userid"]["m_userId"], ID, (event["m_unitTag"],)
            )
        )
        previous = event["_gameloop"]
    raw = encode_game_events(frames)
    if raw != named_encode(list(projected.values()), target_protocol()) or any(
        f.event != e for f, e in zip(iter_game_events(raw), frames, strict=True)
    ):
        raise ValueError("Native reader and named target writer disagree")
    ledger = [[i, e["_gameloop"], e["_userid"]["m_userId"], e["m_unitTag"]] for i, e in projected.items()]
    reports = dict(
        source=observed,
        target_build=98348,
        map_sha256=digest,
        cutoff=cutoff,
        emitted=len(projected),
        withheld=len(clicks_in) - len(projected),
        categories=dict(sorted(categories.items())),
        accepted_types=dict(sorted(accepted_types.items())),
        withheld_types=dict(sorted(withheld_types.items())),
        bytes=len(raw),
        sha256=sha256(raw).hexdigest(),
        ledger_sha256=sha256(json.dumps(ledger, separators=(",", ":")).encode()).hexdigest(),
        target_simulation_verified=False,
    )
    return projected, raw, reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("source", "gate_map", "mechanics", "curve"):
        parser.add_argument(arg, type=Path)
    parser.add_argument(
        "--control-manifest", type=Path, help="JSON mapping reference digest to local recording"
    )
    parser.add_argument(
        "--reference-list",
        type=Path,
        default=Path(first_sync_game.__file__).parent / "observations/first-sync-game.json",
    )
    parser.add_argument("--jobs", type=int, default=2, choices=range(1, 5))
    parser.add_argument("--private-output", type=Path)
    parser.add_argument("--private-ledger", type=Path)
    args = parser.parse_args()
    events, raw, report = generate(args.source, args.gate_map, args.mechanics, args.curve)
    if args.control_manifest:
        manifest = json.loads(args.control_manifest.read_bytes())
        expected = reference_keys(args.reference_list)
        if set(manifest) != expected:
            raise ValueError("Control manifest differs from pinned 24-recording cohort")
        with ProcessPoolExecutor(args.jobs) as pool:
            results = list(
                pool.map(control, [(Path(path), digest) for digest, path in sorted(manifest.items())])
            )
        report["controls"] = [r for r, _ in results]
        report["target_physical_frames"], report["target_physical_bytes"] = validate_cohort(
            report["controls"], expected
        )
        counts = sum((t for _, t in results), Counter())
        report["target_prior_live_clicks_by_projected_type"] = {
            unit: counts[unit] for unit in report["accepted_types"]
        }
    if args.private_output:
        with args.private_output.open("xb") as out:
            out.write(raw)
    if args.private_ledger:
        rows = [[i, e["_gameloop"], e["_userid"]["m_userId"], e["m_unitTag"]] for i, e in events.items()]
        with args.private_ledger.open("xb") as out:
            out.write(json.dumps(rows, separators=(",", ":")).encode())
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
