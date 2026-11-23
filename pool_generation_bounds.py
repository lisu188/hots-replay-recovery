"""Derive same-slot operation lower bounds for ordinary unit-pool generations."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from camp_owner_wire import read_tracker
from mpq_reader import MPQArchive
from predict_camp_captures import SOURCE
from repair_unit_tags import components
from unit_slot_pool import GENERATION_MASK, SLOT_LIMIT, UnitSlotPool


def single_slot_witness(slot, previous, current):
    """Construct a minimal history for an isolated slot; other live slots are held."""
    if not (0 <= slot < SLOT_LIMIT and 0 < previous < current < GENERATION_MASK):
        raise ValueError("Outside the ordinary target pool")
    pool = UnitSlotPool()
    for _ in range(slot + 1):
        tag = pool.allocate()
    if tag != (slot, 1):
        raise ValueError("Fresh pool mismatch")
    while tag[1] < previous:
        pool.retire(tag)
        pool.drain()
        tag = pool.allocate()
    if tag != (slot, previous):
        raise ValueError("Previous generation mismatch")
    hidden = []
    while tag[1] < current:
        pool.retire(tag)
        pool.drain()
        tag = pool.allocate()
        if tag != (slot, current):
            hidden.append(tag)
    if tag != (slot, current) or hidden != [(slot, n) for n in range(previous + 1, current)]:
        raise ValueError("Isolated slot history mismatch")
    return len(hidden)


def audit(path, digest, build):
    if sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("Replay SHA-256 mismatch")
    p, raw, horizon = read_tracker(path, build)
    pings = Counter()
    if digest == SOURCE:
        with closing(MPQArchive(path)) as arc:
            game = arc.read_file("replay.game.events")
        game_bits = 0
        for e in p.decode_replay_game_events(game):
            game_bits += e["_bits"]
            if e["_eventid"] == 36 and e["m_unit"]:
                pings[components(e["m_unit"],18)] += 1
        if game_bits != len(game) * 8:
            raise ValueError("Incomplete game member")

    last = {}
    last_death = {}
    counts = Counter()
    earliest = None
    targets = []
    bits = 0
    for e in p.decode_replay_tracker_events(raw):
        bits += e["_bits"]
        kind, loop = e["_eventid"], e["_gameloop"]
        if kind not in (1, 2, 6):
            continue
        idx, gen = key = e["m_unitTagIndex"], e["m_unitTagRecycle"]
        if not 0 <= idx < SLOT_LIMIT or not 0 < gen < GENERATION_MASK or loop > horizon:
            raise ValueError("Observed value outside tested pool range")
        if kind == 2:
            last_death[key] = loop
            continue
        prev, prev_loop, prev_type = last.get(idx, (0, None, None))
        if gen <= prev:
            raise ValueError("Nonmonotone slot, reset or duplicate")
        hidden = gen - prev - 1
        name = e["m_unitTypeName"].decode()
        counts["visible_births"] += 1
        reason = "between_observed_births" if prev else "before_first_visible_birth_if_clean"
        counts[reason] += hidden
        if prev and hidden:
            counts["between_birth_intervals_with_gap"] += 1
            counts["gaps_with_prior_recorded_death"] += (idx, prev) in last_death
        is_target = key in pings and loop > 82
        if prev and ((earliest is None and hidden) or is_target):
            rule = single_slot_witness(idx, prev, gen)
            item = dict(index=idx, previous_generation=prev, previous_type=prev_type,
                        previous_birth_loop=prev_loop, previous_last_recorded_death=last_death.get((idx,prev)),
                        next_generation=gen, next_type=name, next_birth_loop=loop,
                        missing_complete_lifetimes=rule, minimum_retires_between_allocations=gen-prev,
                        isolated_reallocation_witness=True)
            if hidden and earliest is None:
                earliest = item
            if is_target:
                targets.append({**item, "pings":pings[key]})
        last[idx] = gen, loop, name
    if bits != len(raw) * 8:
        raise ValueError("Incomplete tracker member")
    rec = dict(build=build, sha256=digest, ordinary_rule_verified_for_image=(build==98348),
               counts=dict(counts), first_gap_with_two_recorded_births=earliest)
    if digest == SOURCE:
        rec["dynamic_ping_intervals_if_target_rule_applies"] = targets
    return rec


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, action="append", nargs=3, metavar=("REPLAY","SHA256","BUILD"))
    args = parser.parse_args()
    if len({h for p,h,b in args.case}) != len(args.case):
        raise ValueError("Duplicate recording")
    print(json.dumps([audit(Path(p), h, int(b)) for p,h,b in args.case],indent=2))
