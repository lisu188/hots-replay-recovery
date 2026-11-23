"""Test first and returning 41810 camp waves against strictly earlier inputs and independent flags."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from legacy_camp_wave_model import (
    CONTROLS,
    MAP,
    SOURCE,
    birth_keys,
    comparison,
    map_slots,
    need,
    read_case,
    run_clock,
    signals_and_targets,
)


def hostile_flag_waves(events, camps):
    flag_type = b"CampOwnershipFlag"
    flag_positions = {cid: record[2] for cid, record in camps.items()}
    by_tag = birth_keys(events, flag_type, flag_positions, initial=True)
    starting = [
        e
        for e in events
        if e["_gameloop"] == 0
        and e["_event"].endswith(".SUnitBornEvent")
        and e["m_unitTypeName"] == flag_type
    ]
    need(
        len(starting) == len(by_tag) == len(camps) and set(by_tag.values()) == set(camps),
        "Expected exactly one authored flag birth and one full tag per camp",
    )
    live = set()
    flags = Counter()
    for event in events:
        tag = event.get("m_unitTagIndex"), event.get("m_unitTagRecycle")
        if tag not in by_tag:
            continue
        tick = event["_gameloop"]
        kind = event["_event"].rsplit(".", 1)[-1]
        if kind == "SUnitBornEvent":
            need(
                tick == 0 and tag not in live and event["m_unitTypeName"] == flag_type,
                "Flag tag reused",
            )
            live.add(tag)
        elif kind in ("SUnitDiedEvent", "SUnitTypeChangeEvent", "SUnitInitEvent", "SUnitRevivedEvent"):
            raise ValueError("Unexpected original flag lifetime transition")
        elif kind == "SUnitOwnerChangeEvent":
            need(tag in live, "Ownership outside original flag lifetime")
            if (event["m_controlPlayerId"], event["m_upkeepPlayerId"]) == (15, 15):
                flags[tick + 2, by_tag[tag]] += 1
    need(len(live) == len(camps), "Missing original flag")
    return flags


def check(path, digest, camps, slots):
    events, horizon, tracker_sha = read_case(path, digest)
    kinds = {i: row[0] for i, row in camps.items()}
    full_signals, observed, _ = signals_and_targets(events, camps, slots)
    true_groups = Counter({(t, c): 1 for t, c, *_ in observed})
    full = run_clock(kinds, slots, full_signals, horizon)
    full_groups = Counter((t, c) for t, c, _ in full.waves)
    # Include false-positive full-stream forecast times as potential test boundaries.
    boundaries = sorted({t for t, _ in true_groups.keys() | full_groups.keys()})
    masked = [
        e
        for e in events
        if e.get("m_eventName") != b"JungleCampCapture"
        and not (
            e["_event"].endswith(".SUnitBornEvent") and e["m_unitTypeName"].startswith(b"MercDefender")
        )
    ]
    prefix_groups = Counter()
    for target_loop in boundaries:
        prefix = [e for e in masked if e["_gameloop"] < target_loop]
        drive, targets, _ = signals_and_targets(prefix, camps, slots)
        need(not targets, "Neutral births leaked into prefix")
        # The verifier supplies only earlier input. A projected +1 beacon effect may occur on the final tick.
        clock = run_clock(kinds, slots, drive, target_loop)
        prefix_groups.update((t, c) for t, c, _ in clock.waves if t == target_loop)
    flags = hostile_flag_waves(events, camps)
    wrong_offset = Counter({(t - 2, c): n for (t, c), n in flags.items()})
    return dict(
        replay_sha256=digest,
        tracker_sha256=tracker_sha,
        distinct_wave_ticks=len(boundaries),
        observed_waves=true_groups.total(),
        prefix_wave_scores=comparison(prefix_groups, true_groups),
        prefix_and_full_predictions_equal=prefix_groups == full_groups,
        hostile_flag_transitions=flags.total(),
        flag_plus_two_scores=comparison(flags, true_groups),
        negative_same_loop_flag=comparison(wrong_offset, true_groups),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, required=True)
    parser.add_argument("--replay", type=Path, nargs=4, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    camps, slots = map_slots(args.map)
    files = {sha256(p.read_bytes()).hexdigest(): p for p in args.replay}
    need(set(files) == {SOURCE, *CONTROLS}, "Expected all four original recordings")
    cases = [check(files[d], d, camps, slots) for d in (SOURCE, *CONTROLS)]
    doc = dict(
        map_sha256=MAP,
        mode="No neutral defender births, no capture stats, and no inputs on or after "
        "each scored wave tick. Hostile flag transitions are scored separately. Wave unit fields and "
        "lifetimes are scored in the companion cohort receipt.",
        cases=cases,
    )
    out = (json.dumps(doc, indent=2) + "\n").encode("utf-8")
    if args.output.exists():
        need(args.output.read_bytes() == out, "Existing receipt differs")
    else:
        with args.output.open("xb") as f:
            f.write(out)
    print(json.dumps([r["prefix_wave_scores"] for r in cases]))


if __name__ == "__main__":
    main()
