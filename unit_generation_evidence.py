"""Compare physical unit generations, player inputs and blocker-slot reuse on Dragon Shire."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from mpq_reader import MPQArchive
from protocol_loader import load_protocol
from smartcam_tags import SRC_SCHEMA, DST_SCHEMA, MAP, TARGET_MAP, components

BLOCKER_TYPES = {b"StormGameStartPathingBlocker", b"StormGameStartPathingBlockerDiagonal"}


def game_tags(event):
    kind = event["_event"].rsplit(".", 1)[-1]
    if kind == "SCmdEvent":
        if "TargetUnit" in event["m_data"]:
            yield "command_target", event["m_data"]["TargetUnit"]["m_tag"]
        yield "command_other_unit", event.get("m_otherUnit")
    elif kind == "SCmdUpdateTargetUnitEvent":
        yield "updated_target", event["m_target"]["m_tag"]
    elif kind == "SSelectionDeltaEvent":
        for tag in event["m_delta"]["m_addUnitTags"]:
            yield "selection", tag
    elif kind == "STriggerPingEvent":
        yield "ping", event["m_unit"]


def audit(replay, digest, build):
    schema, schema_sha, map_sha, shift = {
        41810: (41810, SRC_SCHEMA, MAP, 18), 98348: (96477, DST_SCHEMA, TARGET_MAP, 22)
    }[build]
    if sha256(replay.read_bytes()).hexdigest() != digest:
        raise ValueError("Unexpected replay")
    p = load_protocol(schema)
    if p.recovery_schema_sha256 != schema_sha:
        raise ValueError("Unexpected protocol")
    with closing(MPQArchive(replay)) as archive:
        h = p.decode_replay_header(archive.header["user_data_header"]["content"])
        if (h["m_version"]["m_build"], h["m_version"]["m_baseBuild"], h["m_dataBuildNum"]) != (build,) * 3:
            raise ValueError("Unexpected build")
        handles = p.decode_replay_details(archive.read_file("replay.details"))["m_cacheHandles"]
        lobby = p.decode_replay_initdata(archive.read_file("replay.initData"))["m_syncLobbyState"]
        if handles != lobby["m_gameDescription"]["m_cacheHandles"] or handles[-1][:4] != b"s2ma" or handles[-1][8:].hex() != map_sha:
            raise ValueError("Unexpected map")
        tracker_wire = archive.read_file("replay.tracker.events")
        game_wire = archive.read_file("replay.game.events")
    allocations = {}
    previous = {}
    blocker_tags = set()
    released = []
    first_nonconsecutive = None
    gaps = Counter()
    first_wave = []
    minion_types = {b"FootmanMinion", b"RangedMinion", b"WizardMinion"}
    born_info = {}
    wave_tick = None
    extent = 0
    for e in p.decode_replay_tracker_events(tracker_wire):
        extent += e["_bits"]
        if "m_unitTagIndex" not in e or "m_unitTagRecycle" not in e:
            continue
        index, generation = key = (e["m_unitTagIndex"], e["m_unitTagRecycle"])
        kind, tick = e["_eventid"], e["_gameloop"]
        if kind == 2 and key in blocker_tags:
            released.append((tick, index))
        if kind not in (1, 6):
            continue
        if key in allocations:
            raise ValueError("Duplicate birth/init generation")
        last = previous.get(index, 0)
        if generation <= last:
            raise ValueError("Non-monotone recorded generation")
        delta = generation - last
        if delta != 1 and first_nonconsecutive is None:
            first_nonconsecutive = dict(loop=tick, index=index, previous_generation=last,
                                        observed_generation=generation, unit=e["m_unitTypeName"].decode())
        previous[index] = generation
        gaps[delta] += 1
        allocations[key] = tick
        born_info[key] = (e["m_unitTypeName"], last)
        if tick == 0 and generation == 1 and e["m_unitTypeName"] in BLOCKER_TYPES:
            blocker_tags.add(key)
        if e["m_unitTypeName"] in minion_types:
            if wave_tick is None:
                wave_tick = tick
            if tick < wave_tick + 9:
                first_wave.append((tick, e["m_unitTypeName"].decode(), index, generation))
    if extent != 8 * len(tracker_wire) or not first_wave or not released:
        raise ValueError("Incomplete tracker, first wave or blocker release")
    if len(set(k for _, k in released)) != len(released):
        raise ValueError("Repeated blocker death")
    extent = 0
    physical = Counter()
    missing = defaultdict(set)
    pre_birth = Counter()
    dynamic_pings = Counter()
    for e in p.decode_replay_game_events(game_wire):
        extent += e["_bits"]
        for field, raw in game_tags(e):
            if raw in (None, 0, 0xFFFFFFFF):
                continue
            key = components(raw, shift)
            physical[field] += 1
            if key not in allocations:
                missing[field].add(key)
            elif allocations[key] > e["_gameloop"]:
                pre_birth[field] += 1
            elif field == "ping" and build == 41810 and allocations[key] > 82:
                dynamic_pings[key] += 1
    if extent != 8 * len(game_wire):
        raise ValueError("Incomplete game stream")
    free = [i for tick, i in released if tick <= wave_tick]
    ranks = {k: i for i, k in enumerate(free)}
    high = max(i for (i, generation), born in allocations.items() if born < wave_tick)
    first_six = [(i,g) for _,_,i,g in first_wave[:6]]
    return dict(build=build, sha256=digest, recorded_generation_count=len(allocations),
                distinct_indices=len(previous), unrecorded_numbers_below_max_per_index=sum(previous.values())-len(allocations),
                first_nonconsecutive=first_nonconsecutive, nonconsecutive_births=sum(n for delta,n in gaps.items() if delta>1),
                game_non_sentinel_fields=dict(physical), distinct_missing={k:len(v) for k,v in missing.items()},
                input_before_tracker_birth=dict(pre_birth), first_wave_loop=wave_tick,
                pre_wave_tracker_highest_index=high,
                six_fresh_indices=first_six == [(high+step,1) for step in range(1,7)],
                six_sequential_new_indices=[i for i,_ in first_six] == list(range(high+1,high+7)),
                blocker_deaths_before_wave=len(free), wave_births=len(first_wave),
                blocker_release_order_sha256=sha256(bytes(free)).hexdigest(),
                wave_reuse_count=sum(i in ranks and gen==2 for _,_,i,gen in first_wave),
                wave_released_indices=sum(i in ranks for _,_,i,gen in first_wave),
                first_wave_tags=[[i,gen] for _,_,i,gen in first_wave],
                first_wave_released_slot_ranks=[ranks.get(i) if gen==2 else None for _,_,i,gen in first_wave],
                first_wave_order=[[tick-wave_tick,unit] for tick,unit,_,_ in first_wave],
                dynamic_ping_generations=[dict(unit=born_info[k][0].decode(), born=allocations[k], pings=n,
                    previous_visible_generation=born_info[k][1], observed_generation=k[1],
                    missing_intervening_numbers=k[1]-born_info[k][1]-1) for k,n in dynamic_pings.items()])


def summarize(cases):
    if not cases or len({r["sha256"] for r in cases}) != len(cases):
        raise ValueError("Missing or duplicated recording")
    from predict_camp_captures import SOURCE
    out = {"cases": [], "builds": {}}
    for r in sorted(cases, key=lambda r: r["sha256"]):
        out["cases"].append({k:r[k] for k in (
            "build", "sha256", "recorded_generation_count", "distinct_indices",
            "unrecorded_numbers_below_max_per_index", "first_nonconsecutive",
            "nonconsecutive_births", "blocker_deaths_before_wave", "blocker_release_order_sha256",
            "wave_births", "first_wave_loop", "wave_released_indices", "wave_reuse_count",
            "six_fresh_indices", "six_sequential_new_indices")})
        if r["sha256"] == SOURCE:
            out["source_dynamic_pings"] = r["dynamic_ping_generations"]
    for b in sorted({r["build"] for r in cases}):
        group = [r for r in cases if r["build"] == b]
        inputs = Counter()
        misses = Counter()
        early = Counter()
        for r in group:
            inputs.update(r["game_non_sentinel_fields"])
            misses.update(r["distinct_missing"])
            early.update(r["input_before_tracker_birth"])
        out["builds"][str(b)] = dict(cases=len(group), non_sentinel_fields=dict(inputs),
            sum_missing_distinct_by_recording=dict(misses), pre_birth_input_fields=dict(early),
            missing_numbers=sum(r["unrecorded_numbers_below_max_per_index"] for r in group),
            witnessed_generation_count=sum(r["recorded_generation_count"] for r in group),
            release_order_variants=len({r["blocker_release_order_sha256"] for r in group}),
            first_wave_tag_order_variants=len({tuple(map(tuple,r["first_wave_tags"])) for r in group}),
            first_six_sequential_new_indices=sum(r["six_sequential_new_indices"] for r in group),
            first_six_sequential_new_generation_one=sum(r["six_fresh_indices"] for r in group),
            first_wave_births=sum(r["wave_births"] for r in group),
            first_wave_reusing_a_blocker_index=sum(r["wave_released_indices"] for r in group))
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", nargs=3, action="append", required=True, metavar=("REPLAY", "SHA256", "BUILD"))
    args = parser.parse_args()
    print(json.dumps(summarize([audit(Path(p), h, int(b)) for p,h,b in args.case]), indent=2))
