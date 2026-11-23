"""Constrain successful 98348 announcer allocation pairs using the shared native registry."""

from argparse import ArgumentParser
from collections import Counter, defaultdict
from contextlib import closing
from pathlib import Path
import json

from first_sound_timing import verify_manifest
from first_sync_game import game
from mpq_reader import MPQArchive
from opening_sound_roles import COMMON, leave_one_out, role_order
from sound_object_registry import minimum_allocations


def allocation_constraints(sound_words):
    """Bounds from ordinary fresh reset, conditional on this producer's allocation order."""
    if len(sound_words) != 11 or len(set(w & 0xffff for w in sound_words)) != 11:
        raise ValueError("Expected eleven different live sound slots")
    previous = minimum_allocations(sound_words)
    # Every following successful play requires another SoundLink plus the sound itself.
    bound = max(minimum_allocations(sound_words[:i]) + 2*(len(sound_words)-i) for i in range(12))
    required_reuse = [role for role in range(1,11) if sound_words[role-1] >> 16 == 1 and
                      sound_words[role] >> 16 == 1 and sound_words[role] == sound_words[role-1]+1]
    common_generation = sound_words[0] >> 16
    return dict(old_bound=previous, allocation_lower_bound=bound, increase=bound-previous,
                common_slot_prior_generation=(common_generation-1)&0xffff,
                common_generation=common_generation, consecutive_generation_one_roles=required_reuse)


def first_round(path, sha):
    protocol, raw = game(path,sha,98348)
    with closing(MPQArchive(path)) as a:
        setup = {}
        for row in protocol.decode_replay_tracker_events(a.read_file("replay.tracker.events")):
            if row["_gameloop"] > 0:
                break
            if row["_eventid"] == 9 and row["m_userId"] is not None:
                uid,player = row["m_userId"],row["m_playerId"]
                if uid in setup or player in setup.values():
                    raise ValueError("Duplicate reporter mapping")
                setup[uid] = player
    if set(setup.values()) != set(range(1,11)):
        raise ValueError("Unexpected native cohort setup")
    groups = defaultdict(list)
    first_loop = None
    for row in protocol.decode_replay_game_events(raw):
        tick = row["_gameloop"]
        if first_loop is not None and tick > first_loop+100:
            break
        if row["_eventid"] != 46:
            continue
        if first_loop is None:
            first_loop=tick
        uid=row["_userid"]["m_userId"]
        if len(groups[setup[uid]]) < 10:
            groups[setup[uid]].append(row["m_sound"])
    if set(groups) != set(range(1,11)) or any(len(v)!=10 for v in groups.values()):
        return None
    hits, values = leave_one_out(groups,role_order(98348))
    if hits != 10:
        return None
    return [values[r] for r in [COMMON,*range(1,11)]]


def analyze(cases):
    rows = []
    for path, digest, build in verify_manifest(cases):
        if build == 98348:
            words = first_round(Path(path),digest)
            checks = allocation_constraints(words) if words else None
            rows.append(dict(sha256=digest, checks=checks))
    rows.sort(key=lambda r:r["sha256"])
    closed = [r["checks"] for r in rows if r["checks"]]
    bound = [r["allocation_lower_bound"] for r in closed]
    return dict(native_cases=len(rows), complete_roles=len(closed), conditional_allocation_range=[min(bound),max(bound)],
                improvement_histogram=dict(sorted(Counter(r["increase"] for r in closed).items())),
                intervening_link_reuses_if_generation_one_is_virgin=sum(len(r["consecutive_generation_one_roles"]) for r in closed),
                common_generations=[min(r["common_generation"] for r in closed),max(r["common_generation"] for r in closed)],
                target_first_sound_handle=None, cases=rows)


if __name__ == "__main__":
    parser=ArgumentParser(description=__doc__)
    parser.add_argument("manifest",type=Path)
    print(json.dumps(analyze(json.loads(parser.parse_args().manifest.read_bytes())), indent=2))
