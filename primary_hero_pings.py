"""Project TEN's map-backed and ordinary opening-hero pings on the historical layout."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import native_game_events as native
from convert_historical_pings import PING, generate as map_pings, native_frame, target_protocol
from hero_camera_lifetimes import (
    core_horizon, independent_histories, lobby_predictions, recorded_histories, reference_timers,
)
from mpq_reader import MPQArchive
from predict_camp_captures import SOURCE
from protocol_loader import load_protocol
from repair_unit_tags import components, pack
from smartcam_tags import phase


def fields(e, unit):
    return (e["_gameloop"], e["_userid"]["m_userId"], e["m_point"]["x"], e["m_point"]["y"],
            unit, e["m_pingedMinimap"], e["m_option"])


def select_primary_pings(events, qualified, cutoff):
    tags = {}
    phases = Counter()
    for ordinal, e in enumerate(events):
        key = components(e["m_unit"], 18) if e["m_unit"] else None
        if key not in qualified or e["_gameloop"] > cutoff:
            continue
        history = qualified[key][2]
        state = phase(history, e["_gameloop"])
        if state != "live":
            phases["withheld_" + state] += 1
            continue
        tags[ordinal] = pack(*key, 22)
        phases["alive_after_revive" if any(t < e["_gameloop"] and alive for t, alive in history[1:])
               else "first_life"] += 1
    return tags, phases


def encode_selected(events, tags):
    frames = []
    previous = 0
    expected = []
    for n, tag in sorted(tags.items()):
        if type(n) is not int or not 0 <= n < len(events):
            raise ValueError("Ping ordinal outside the source sequence")
        e = events[n]
        frames.append(native_frame(e, tag, e["_gameloop"] - previous))
        previous = e["_gameloop"]
        expected.append(fields(e, tag))
    raw = native.encode_game_events(frames)
    actual = list(target_protocol().decode_replay_game_events(raw))
    if (sum(e["_bits"] for e in actual) != len(raw) * 8
            or any(e["_eventid"] != PING for e in actual)
            or [fields(e, e["m_unit"]) for e in actual] != expected):
        raise ValueError("Target decoder disagrees with ordered ping inputs")
    return raw


def locate_base(events, base):
    # The verified packages retain unit placement ordinals. Normalize word packing
    # for comparison only: each selected row must already exist in the map-only stream.
    ordinals = {}
    for n, e in enumerate(events):
        key = fields(e, pack(*components(e["m_unit"], 18), 22) if e["m_unit"] else 0)
        ordinals.setdefault(key, []).append(n)
    tags = {}
    for e in target_protocol().decode_replay_game_events(base):
        candidates = ordinals.get(fields(e, e["m_unit"]), [])
        if len(candidates) != 1 or candidates[0] in tags:
            raise ValueError("Map projection is missing, ambiguous or repeated")
        tags[candidates[0]] = e["m_unit"]
    if encode_selected(events, tags) != base:
        raise ValueError("Map projection failed its original byte comparison")
    return tags


def generate(source, original_map, historical_map, references):
    base, receipt = map_pings(source, original_map, historical_map)
    table, support = reference_timers(references)
    p = load_protocol(41810)
    with closing(MPQArchive(source)) as arc:
        head = p.decode_replay_header(arc.header["user_data_header"]["content"])
        tracker = list(p.decode_replay_tracker_events(arc.read_file("replay.tracker.events")))
        events = [e for e in p.decode_replay_game_events(arc.read_file("replay.game.events")) if e["_eventid"] == PING]
    cutoff = core_horizon(tracker, head["m_elapsedGameLoops"])
    proposed = independent_histories(lobby_predictions(source, 41810), tracker, table, cutoff)
    observed = recorded_histories(tracker)
    qualified = {k: v for k, v in proposed.items() if k in observed and v[:2] == observed[k][:2]
                 and v[2] == [row for row in observed[k][2] if row[0] <= cutoff]}
    if len(qualified) != 10:
        raise ValueError("Unexpected opening hero or independently reconstructed lifetime")
    hero, phases = select_primary_pings(events, qualified, cutoff)
    tags = locate_base(events, base)
    if hero.keys() & tags.keys():
        raise ValueError("Duplicate ping coverage")
    raw = encode_selected(events, tags | hero)
    return raw, dict(format="historical-layout-map-and-primary-hero-pings-v1", source=SOURCE,
                     historical_map=receipt["target_layout_sha256"], reference_digests=support["reference_sha256"],
                     cutoff=cutoff, full_ping_count=len(events), qualified_heroes=len(qualified),
                     base_pings=len(tags), base_sha256=sha256(base).hexdigest(),
                     projected_hero_pings=len(hero), hero_phases=dict(phases),
                     hero_unit_generations=len(set(hero.values())), withheld=len(events)-len(tags)-len(hero),
                     emitted=len(tags)+len(hero), bytes=len(raw), sha256=sha256(raw).hexdigest(),
                     target_simulation_verified=False)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "original-map", "historical-map", "output"):
        cli.add_argument("--" + name, required=True, type=Path)
    cli.add_argument("--reference", action="append", required=True, nargs=2, metavar=("REPLAY", "SHA256"))
    args = cli.parse_args()
    raw, report = generate(args.source, args.original_map, args.historical_map,
                           [(Path(path), digest) for path, digest in args.reference])
    with TemporaryDirectory(dir=args.output.parent) as tmp:
        stage = Path(tmp) / "pings.bin"
        stage.write_bytes(raw)
        os.link(stage, args.output)
    print(json.dumps(report, indent=2))
