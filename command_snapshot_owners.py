"""Recover command target owner fields from independently recorded tracker history."""

import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
from contextlib import closing
from dataclasses import dataclass, replace
from hashlib import sha256
import json
from pathlib import Path

from migrate_replay import decode_events, encode_events
from mpq_reader import MPQArchive
from protocol_loader import load_protocol
from repair_unit_tags import components, u32

SCHEMAS_AND_SHIFTS = {41810: (41810, 18), 98348: (96477, 22)}
OWNER_FIELDS = ("m_snapshotControlPlayerId", "m_snapshotUpkeepPlayerId")
PREFIX = "NNet.Replay.Tracker."
SPAWNS = {PREFIX + "SUnitInitEvent", PREFIX + "SUnitBornEvent"}
CHANGE = PREFIX + "SUnitOwnerChangeEvent"
DEATH = PREFIX + "SUnitDiedEvent"
REVIVE = PREFIX + "SUnitRevivedEvent"
TYPE_CHANGE = PREFIX + "SUnitTypeChangeEvent"
BOUNDARIES = SPAWNS | {CHANGE, DEATH, REVIVE, TYPE_CHANGE}


@dataclass(frozen=True)
class Ownership:
    recycle: int
    pair: tuple[int, int]
    alive: bool = True
    transferred: tuple[bool, bool] = (False, False)
    revived: bool = False


class OwnerHistory:
    """Use each role while the known tag generation is alive and that role has never changed."""

    def __init__(self, tracker):
        self.times = defaultdict(list)
        self.states = defaultdict(list)
        self.invariant = {}
        retired = defaultdict(set)
        last = -1
        for event in tracker:
            loop = u32(event["_gameloop"])
            if loop < last:
                raise ValueError("Tracker events must be chronological")
            last = loop
            kind = event["_event"]
            if kind not in BOUNDARIES:
                continue
            index, recycle = (u32(event[k]) for k in ("m_unitTagIndex", "m_unitTagRecycle"))
            prior = self.states[index][-1] if self.states[index] else None
            if prior is not None and prior.recycle != recycle:
                if kind not in SPAWNS or recycle in retired[index]:
                    raise ValueError("Contradictory tracker tag generation")
                retired[index].add(prior.recycle)
                prior = None
            if kind in SPAWNS or kind == CHANGE:
                pair = u32(event["m_controlPlayerId"]), u32(event["m_upkeepPlayerId"])
                if max(pair) > 15:
                    raise ValueError("Tracker owner exceeds its four-bit range")
                if prior is None:
                    state = Ownership(recycle, pair) if kind in SPAWNS else None
                else:
                    transferred = tuple(
                        changed or old != new
                        for changed, old, new in zip(prior.transferred, prior.pair, pair)
                    )
                    state = replace(
                        prior, pair=pair, alive=prior.alive or kind in SPAWNS, transferred=transferred
                    )
            elif prior is None or kind == TYPE_CHANGE:
                state = prior
            elif kind == DEATH:
                state = replace(prior, alive=False)
            else:
                state = replace(prior, alive=True, revived=True)
            self.times[index].append(loop)
            self.states[index].append(state)
            if state is not None:
                # Monotone transfer flags summarize every observed assignment in this generation.
                self.invariant[index, recycle] = tuple(
                    None if changed else owner for owner, changed in zip(state.pair, state.transferred)
                )

    def lookup(self, tag, loop, shift):
        index, recycle = components(tag, shift)
        u32(loop)
        if tag in (0, 0xFFFFFFFF):
            return None, "sentinel"
        times = self.times.get(index, ())
        pos = bisect_right(times, loop) - 1
        if pos < 0:
            return None, "unknown_generation"
        state = self.states[index][pos]
        if state is None or state.recycle != recycle:
            return None, "unknown_generation"
        if times[pos] == loop or not state.alive:
            reason = "transition_loop" if times[pos] == loop else "dead"
            pair = self.invariant[index, recycle]
            # A queued command may describe an earlier snapshot. Accept only values which
            # agree at every recorded ownership assignment for this entire generation.
            if pair == (None, None):
                return None, reason
            return pair, "constant_lifetime_role_" + reason
        if all(state.transferred):
            return None, "ownership_changed"
        if any(state.transferred):
            return (
                tuple(None if changed else value for changed, value in zip(state.transferred, state.pair)),
                "one_stable_role",
            )
        return state.pair, "revived" if state.revived else "alive"


def command_target(event):
    if event["_event"] == "NNet.Game.SCmdEvent":
        return event["m_data"].get("TargetUnit")
    if event["_event"] == "NNet.Game.SCmdUpdateTargetUnitEvent":
        return event["m_target"]
    return None


def recover_replay(path, build):
    """Erase eligible owner fields in memory and compare the fully re-encoded game member."""
    schema, shift = SCHEMAS_AND_SHIFTS[build]
    p = load_protocol(schema)
    with closing(MPQArchive(path)) as archive:
        header = p.decode_replay_header(archive.header["user_data_header"]["content"])
        version = header["m_version"]
        if (version["m_build"], version["m_baseBuild"], header["m_dataBuildNum"]) != (build,) * 3:
            raise ValueError("Unexpected physical build")
        tracker = archive.read_file("replay.tracker.events")
        game = archive.read_file("replay.game.events")
    history = OwnerHistory(p.decode_replay_tracker_events(tracker))
    events = list(decode_events(game, p, "game"))
    counts = Counter()
    missing = []
    recovered = Counter()
    full_pairs = 0
    for event in events:
        target = command_target(event)
        if target is None:
            continue
        pair, reason = history.lookup(target["m_tag"], event["_gameloop"], shift)
        counts[reason] += 1
        if pair is None:
            continue
        for key, value in zip(OWNER_FIELDS, pair):
            if value is not None:
                del target[key]
        missing.append((event, target))
    for event, target in missing:
        pair, _ = history.lookup(target["m_tag"], event["_gameloop"], shift)
        for key, value in zip(OWNER_FIELDS, pair):
            if value is not None:
                target[key] = value
                recovered[key] += 1
        full_pairs += None not in pair
    if encode_events(events, p, "game") != game:
        raise ValueError("Restored owner fields did not reproduce full game member")
    return dict(
        build=build,
        schema=schema,
        replay_sha256=sha256(path.read_bytes()).hexdigest(),
        game_sha256=sha256(game).hexdigest(),
        tracker_sha256=sha256(tracker).hexdigest(),
        game_bytes=len(game),
        command_targets=counts.total(),
        recovered_pairs=full_pairs,
        recovered_fields=recovered.total(),
        recovered_by_field=dict(sorted(recovered.items())),
        outcomes=dict(sorted(counts.items())),
        full_game_bytes_equal=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("replay", type=Path)
    parser.add_argument("--build", required=True, type=int, choices=sorted(SCHEMAS_AND_SHIFTS))
    args = parser.parse_args()
    print(json.dumps(recover_replay(args.replay, args.build), indent=2))
