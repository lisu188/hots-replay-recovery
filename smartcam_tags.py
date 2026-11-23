"""Inspect Dragon Shire smart-camera records against independent tracker unit lifetimes."""

import argparse
from bisect import bisect_left
from collections import Counter, defaultdict
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from struct import Struct

from mpq_reader import MPQArchive
from predict_camp_captures import MAP, SOURCE, number
from protocol_loader import load_protocol
from repair_unit_tags import components, pack

RECORD = Struct("<BIII")
TARGET_MAP = "f557190f8aaab160789272ce086b8b69d6a8037b152de150332603dae3dc098f"
R8 = "4f2435e8cd678aeac16c0b1403cfdf67ab8e513b04f0f93e22d504c187bbaf19"
SRC_SCHEMA = "879d228d9d8acd21d63563538dd15841aaf49259ee0bb468b8a46b6a4ef866fd"
DST_SCHEMA = "e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84"


def decode(raw, horizon):
    if len(raw) % RECORD.size:
        raise ValueError("Partial smartcam frame")
    rows = list(RECORD.iter_unpack(raw))
    previous = 0
    for kind, tick, left, right in rows:
        if kind != 8 or not previous <= tick <= horizon:
            raise ValueError("Unknown frame kind or loop")
        previous = tick
    return rows


def read_case(path, expected, build):
    if sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError("Incorrect replay digest")
    if build not in (41810, 98348) and (build, expected) != (98285, R8):
        raise ValueError("Unsupported replay")
    p = load_protocol(41810 if build == 41810 else 96477)
    if p.recovery_schema_sha256 != (SRC_SCHEMA if build == 41810 else DST_SCHEMA):
        raise ValueError("Unexpected tracker schema")
    with closing(MPQArchive(path)) as arc:
        h = p.decode_replay_header(arc.header["user_data_header"]["content"])
        if (
            h["m_version"]["m_build"],
            h["m_version"]["m_baseBuild"],
            h["m_dataBuildNum"],
        ) != (build,) * 3:
            raise ValueError("Header build mismatch")
        details = p.decode_replay_details(arc.read_file("replay.details"))[
            "m_cacheHandles"
        ]
        init = p.decode_replay_initdata(arc.read_file("replay.initData"))[
            "m_syncLobbyState"
        ]["m_gameDescription"]["m_cacheHandles"]
        if details != init or not details or details[-1][:4] != b"s2ma":
            raise ValueError("Inconsistent details/init map")
        map_sha = details[-1][8:].hex()
        if map_sha != (MAP if build == 41810 else TARGET_MAP):
            raise ValueError("Unexpected map")
        raw = arc.read_file("replay.smartcam.events")
        tracker = list(
            p.decode_replay_tracker_events(arc.read_file("replay.tracker.events"))
        )
        messages = list(
            p.decode_replay_message_events(arc.read_file("replay.message.events"))
        )
    return raw, tracker, messages, h["m_elapsedGameLoops"], map_sha


def identity(e):
    return e["m_unitTagIndex"], e["m_unitTagRecycle"]


def lifetimes(tracker):
    births = {}
    live = defaultdict(list)
    credited = set()
    players = {}
    spawn = set()
    for e in tracker:
        kind = e["_event"].rsplit(".", 1)[-1]
        t = e["_gameloop"]
        if kind == "SPlayerSetupEvent":
            players[e["m_playerId"]] = e["m_userId"]
        if e.get("m_eventName") == b"PlayerSpawned":
            spawn.add(
                (
                    t,
                    number(e, "m_intData", "PlayerID"),
                    number(e, "m_stringData", "Hero"),
                )
            )
        if kind in (
            "SUnitBornEvent",
            "SUnitInitEvent",
            "SUnitRevivedEvent",
            "SUnitDiedEvent",
        ):
            k = identity(e)
            if kind in ("SUnitBornEvent", "SUnitInitEvent"):
                births.setdefault(k, e)
            live[k].append((t, kind != "SUnitDiedEvent"))
            if kind == "SUnitDiedEvent" and e.get("m_killerUnitTagIndex") is not None:
                credited.add(
                    (t, (e["m_killerUnitTagIndex"], e["m_killerUnitTagRecycle"]), k)
                )
    heroes = {
        k: players.get(e["m_controlPlayerId"])
        for k, e in births.items()
        if (e["_gameloop"], e["m_controlPlayerId"], e["m_unitTypeName"]) in spawn
    }
    return births, live, heroes, credited


def phase(history, tick):
    if not history:
        return "missing"
    prior = bisect_left(history, tick, key=lambda row: row[0])
    if prior < len(history) and history[prior][0] == tick:
        return "boundary"
    if prior == 0:
        return "pre_birth"
    return "live" if history[prior - 1][1] else "dead"


def analyze(raw, tracker, messages, horizon):
    rows = decode(raw, horizon)
    births, live, heroes, credited = lifetimes(tracker)
    message_loops = Counter(e["_gameloop"] for e in messages)
    tracker_loops = Counter(e["_gameloop"] for e in tracker)
    candidate = []
    for column in (2, 3):
        tags = Counter(r[column] for r in rows)
        scores = {
            s: sum(n for v, n in tags.items() if components(v, s) in births)
            for s in range(1, 32)
        }
        candidate.append(scores)
    combined = {s: sum(c[s] for c in candidate) for s in range(1, 32)}
    score = max(combined.values())
    best = [s for s, n in combined.items() if n == score]
    if not rows or len(best) != 1:
        raise ValueError("Empty or ambiguous observed tag packing")
    if score != 2 * len(rows):
        raise ValueError(
            "One or more camera endpoints have no known tracker birth; sentinel semantics unresolved"
        )
    shift = best[0]
    sides = []
    for side, column in enumerate((2, 3)):
        counts = Counter()
        for r in rows:
            k = components(r[column], shift)
            b = births.get(k)
            counts["phase_" + phase(live.get(k), r[1])] += 1
            if b:
                if k in heroes:
                    counts["primary_hero"] += 1
                    counts["assigned_user"] += heroes[k] is not None
                elif b["_gameloop"] == 0:
                    counts["initial_other"] += 1
                else:
                    counts["later_other"] += 1
        sides.append(
            dict(
                **counts,
                zero=sum(r[column] == 0 for r in rows),
                all_ones=sum(r[column] == 2**32 - 1 for r in rows),
                compatible_shifts=[
                    s for s, n in candidate[side].items() if n == len(rows)
                ],
                shift18_hits=candidate[side][18],
                shift22_hits=candidate[side][22],
            )
        )
    pairs = Counter()
    deaths = defaultdict(list)
    for tick, a, b in credited:
        deaths[tick].append((a, b))
    for _, t, left, right in rows:
        a, b = components(left, shift), components(right, shift)
        pairs["at_least_one_primary_hero"] += a in heroes or b in heroes
        pairs["both_primary_hero"] += a in heroes and b in heroes
        pairs["same_actor"] += a == b
        pairs["left_killed_right_same_loop"] += (t, a, b) in credited
        pairs["right_killed_left_same_loop"] += (t, b, a) in credited
        pairs["any_message_at_loop"] += t in message_loops
        pairs["any_message_previous_loop"] += t - 1 in message_loops
        pairs["any_tracker_at_loop"] += t in tracker_loops
        pairs["any_tracker_previous_loop"] += t - 1 in tracker_loops
        for offset in (-1, 0, 1):
            candidates = deaths.get(t + offset, ())
            if len(candidates) == 1:
                pair = candidates[0]
                pairs[f"unique_death_offset_{offset}"] += 1
                pairs[f"unique_death_pair_matches_offset_{offset}"] += pair == (a, b)
    # The intermediate carries the same tracker references at the other observed packing.
    # Endpoints are selected by the physical input; this validates serialization and lookup only.
    other = 18 if shift == 22 else 22
    projected, _ = transpose(rows, tracker, tracker, shift, other)
    return_rows, _ = transpose(projected, tracker, tracker, other, shift)
    by_birth = born_by_signature(births)
    ambiguous = sum(
        len(by_birth[birth_signature(births[components(word, shift)])]) > 1
        for r in rows
        for word in r[2:]
    )
    return dict(
        bytes=len(raw),
        sha256=sha256(raw).hexdigest(),
        records=len(rows),
        constant_prefix_byte=8,
        horizon=horizon,
        min_tick=rows[0][1],
        max_tick=rows[-1][1],
        same_loop_neighbors=sum(a[1] == b[1] for a, b in zip(rows, rows[1:])),
        best_shift=shift,
        matched_fields=score,
        fields=2 * len(rows),
        whole_member_byte_equal=b"".join(RECORD.pack(*r) for r in rows) == raw,
        shift_hits={s: n for s, n in combined.items() if n},
        columns=sides,
        pair_evidence=pairs,
        repeated_birth_signatures_disambiguated_by_lifetime=ambiguous,
        full_reciprocal_packing_equal=b"".join(RECORD.pack(*r) for r in return_rows)
        == raw,
    )


def birth_signature(event):
    return tuple(
        event[k]
        for k in (
            "_gameloop",
            "_event",
            "m_unitTypeName",
            "m_controlPlayerId",
            "m_upkeepPlayerId",
            "m_x",
            "m_y",
        )
    )


def born_by_signature(births):
    index = defaultdict(list)
    for key, event in births.items():
        index[birth_signature(event)].append(key)
    return index


def match_tracker_identities(keys, source_tracker, destination_tracker):
    """Map full (index, recycle) pairs by unique birth payload and matching live/dead history."""
    source, src_live, _, _ = lifetimes(source_tracker)
    destination, dst_live, _, _ = lifetimes(destination_tracker)
    src_index = born_by_signature(source)
    dst_index = born_by_signature(destination)
    identity_map = {}
    for old in dict.fromkeys(keys):
        if old not in source:
            raise ValueError("Referenced endpoint missing from source tracker")
        signature = birth_signature(source[old])
        origin = src_index[signature]
        target = dst_index[signature]
        if len(origin) > 1 or len(target) > 1:
            origin = [k for k in origin if src_live[k] == src_live[old]]
            target = [k for k in target if dst_live[k] == src_live[old]]
        if len(origin) != 1 or len(target) != 1:
            raise ValueError("Missing or ambiguous recorded birth correspondence")
        new = target[0]
        if src_live[old] != dst_live[new]:
            raise ValueError("Different recorded endpoint lifetime")
        identity_map[old] = new
    if len(set(identity_map.values())) != len(identity_map):
        raise ValueError("Non-injective recorded endpoint correspondence")
    return identity_map


def transpose(rows, source_tracker, destination_tracker, old_shift, new_shift):
    """Resolve the entire recorded endpoint sequence against a supplied destination tracker."""
    decoded = [
        (kind, tick, components(left, old_shift), components(right, old_shift))
        for kind, tick, left, right in rows
    ]
    keys = (key for r in decoded for key in r[2:])
    identity_map = match_tracker_identities(keys, source_tracker, destination_tracker)
    out = []
    for kind, tick, left, right in decoded:
        tags = [pack(*identity_map[key], new_shift) for key in (left, right)]
        out.append((kind, tick, *tags))
    return out, identity_map


def generate_r8(source_path, r8_path):
    source, s, m, h, _ = read_case(source_path, SOURCE, 41810)
    carry, d, m2, h2, _ = read_case(r8_path, R8, 98285)
    if source != carry or h != h2:
        raise ValueError("Unexpected R8 smart-camera member or horizon")
    rows = decode(source, h)
    generated, mapping = transpose(rows, s, d, 18, 22)
    raw = b"".join(RECORD.pack(*r) for r in generated)
    restored, _ = transpose(decode(raw, h), d, s, 22, 18)
    if b"".join(RECORD.pack(*r) for r in restored) != source:
        raise ValueError("Inverse failed")
    checks = analyze(raw, d, m2, h)
    if any(side["compatible_shifts"] != [22] for side in checks["columns"]) or checks[
        "matched_fields"
    ] != 2 * len(rows):
        raise ValueError("Result does not fully resolve in destination tracker")
    return raw, dict(
        original_source_sha256=SOURCE,
        partial_input_sha256=R8,
        original_member_sha256=sha256(source).hexdigest(),
        member_sha256=sha256(raw).hexdigest(),
        bytes=len(raw),
        distinct_endpoint_correspondences=len(mapping),
        fields=2 * len(rows),
        fields_changed=sum(
            v != w for a, b in zip(rows, generated) for v, w in zip(a[2:], b[2:])
        ),
        endpoint_pairs_changed=sum(k != v for k, v in mapping.items()),
        byte_differences=sum(a != b for a, b in zip(raw, source)),
        unique_destination_packing=checks["best_shift"],
        destination_tracker_matched_fields=checks["matched_fields"],
        record_sequence_and_loops_preserved=True,
        full_inverse_equal=True,
        target_match_simulation_verified=False,
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="mode", required=True)
    audit = sub.add_parser("audit")
    audit.add_argument("--replay", type=Path, required=True)
    audit.add_argument("--sha256", required=True)
    audit.add_argument("--build", type=int, required=True)
    repair = sub.add_parser("generate-r8-tracker-member")
    repair.add_argument("--source", type=Path, required=True)
    repair.add_argument("--r8", type=Path, required=True)
    repair.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.mode == "audit":
        raw, t, m, h, mp = read_case(args.replay, args.sha256, args.build)
        result = dict(
            replay_sha256=args.sha256,
            build=args.build,
            map_sha256=mp,
            **analyze(raw, t, m, h),
        )
    else:
        raw, result = generate_r8(args.source, args.r8)
        with args.output.open("xb") as f:
            f.write(raw)
    print(json.dumps(result, sort_keys=True, indent=2))
