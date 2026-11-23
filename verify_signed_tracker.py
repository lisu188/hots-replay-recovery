"""Join a private assembled tracker and ordinal ledger back to both physical byte streams."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from camp_owner_wire import read_tracker
from dragonshire_packages import MERC_CAPTURE, SIGNED_ANNOUNCER
from encoders import encode_tracker_events
from first_sync_tracker import ZERO
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE


def check(value, message):
    if not value:
        raise ValueError(message)


def digest(data):
    return sha256(data).hexdigest()


def frames(raw, protocol):
    rows = []
    offset = prev = 0
    for decoded in protocol.decode_replay_tracker_events(raw):
        n, rem = divmod(decoded.pop("_bits"), 8)
        loop = decoded["_gameloop"]
        check(
            not rem and n > 0 and loop >= prev and offset + n <= len(raw),
            "Invalid physical boundary",
        )
        rows.append((decoded, prev, offset, n))
        prev = loop
        offset += n
    check(offset == len(raw), "Unconsumed tracker data")
    return rows


def classify(e, types, gate):
    kind = e["_eventid"]
    name = e.get("m_eventName")
    if e["_gameloop"] <= 84 and (kind == 1 or name in (b"LevelUp", b"PlayerSpawned")):
        return "hero_startup"
    if kind == 3:
        actor = types[e["m_unitTagIndex"], e["m_unitTagRecycle"]]
        owner = e["m_controlPlayerId"]
        if actor == b"TownMercCampCaptureBeacon" and owner in (0, 11, 12):
            return "merc_capture_beacon"
        if actor == b"CampOwnershipFlag":
            if owner in (11, 12):
                return "merc_capture_flag"
            if owner == 15 and e["_gameloop"] == gate + 1920:
                return "objective_owner"
        if (
            actor
            in (
                b"DragonballCaptureBeacon",
                b"DragonShireShrineSun",
                b"DragonShireShrineMoon",
            )
            and owner == 0
        ):
            return "objective_owner"
    if (
        kind == 2
        and e["_gameloop"] == gate
        and types.get((e["m_unitTagIndex"], e["m_unitTagRecycle"]))
        in (b"StormGameStartPathingBlocker", b"StormGameStartPathingBlockerDiagonal")
    ):
        return "gate_blocker_removal"
    if kind == 5 and e["m_upgradeTypeName"] in (b"GatesAreOpen", b"MinionsAreSpawning"):
        return e["m_upgradeTypeName"].decode()
    if kind == 12:
        return "ordinary_revival"
    if kind == 10 and name in (
        b"GatesOpen",
        b"DragonKnightActivated",
        b"JungleCampCapture",
        b"TalentChosen",
        b"LevelUp",
    ):
        return {
            b"GatesOpen": "gates_open",
            b"DragonKnightActivated": "clocked_objective",
            b"JungleCampCapture": "clocked_objective",
            b"TalentChosen": "initial_talent_requires_award_state",
            b"LevelUp": "team_level_requires_recorded_xp_clock",
        }[name]
    raise ValueError("No eligible producer for tracker row")


def verify(source, package, directory, receipt):
    report = json.loads(receipt.read_bytes())
    check(
        digest(source.read_bytes()) == SOURCE == report["source_replay_sha256"],
        "Source replay differs",
    )
    m = digest(package.read_bytes())
    check(
        m in (MERC_CAPTURE, SIGNED_ANNOUNCER) and m == report["target_map_sha256"],
        "Target map differs",
    )
    check(
        report["target_build"] == 98348
        and report["native_playback_verified"] is False
        and type(report["verified_target_syncs"]) is int
        and report["verified_target_syncs"] == 0,
        "Invalid validation status",
    )
    p, old, horizon = read_tracker(source, 41810)
    native = frames(old, p)
    target = target_protocol()
    wire = (directory / "TEN.tracker.sparse.bin").read_bytes()
    prefix = (directory / "TEN.tracker.prefix.bin").read_bytes()
    mapping = json.loads((directory / "tracker-ordinals.json").read_bytes())
    new = frames(wire, target)
    zero = [r for r in new if r[0]["_gameloop"] == 0]
    zlen = sum(r[3] for r in zero)
    check(
        digest(wire[:zlen]) == ZERO and len(zero) == 235, "Queue or map startup differs"
    )
    post = [i for i, (e, *_) in enumerate(native) if e["_gameloop"] > 0]
    linked = [r["source_ordinal"] for r in mapping]
    check(
        linked == sorted(set(linked)) and set(linked) <= set(post),
        "Unordered or duplicate source ordinals",
    )
    check(
        [r["target_ordinal"] for r in mapping] == list(range(len(zero), len(new))),
        "Incomplete target ordinal coverage",
    )
    missing = sorted(set(post) - set(linked))
    first = native[missing[0]][0]
    contiguous = [r for r in new if r[0]["_gameloop"] < first["_gameloop"]]
    size = sum(r[3] for r in contiguous)
    check(
        prefix == wire[:size], "Prefix differs from target at the first uncovered loop"
    )
    counts = Counter()
    changed = Counter()
    opening_types = {
        (e["m_unitTagIndex"], e["m_unitTagRecycle"]): e["m_unitTypeName"]
        for e, *_ in native
        if e["_eventid"] == 1 and e["_gameloop"] == 0
    }
    (gate,) = {
        e["_gameloop"] for e, *_ in native if e.get("m_eventName") == b"GatesOpen"
    }
    for entry in mapping:
        src, previous, pos, n = native[entry["source_ordinal"]]
        actual, _, _, _ = new[entry["target_ordinal"]]
        expected = src.copy()
        check(
            entry["producer"] == classify(src, opening_types, gate),
            "Wrong producer for source tracker event",
        )
        delta = src["_gameloop"] - previous
        check(
            encode_tracker_events([{**src, "_gameloop": delta}], p)
            == old[pos : pos + n],
            "Original frame re-encoding changed",
        )
        if src.get("m_eventName") in (b"DragonKnightActivated", b"JungleCampCapture"):
            earlier = int(src["m_eventName"] == b"JungleCampCapture")
            expected["m_fixedData"] = [
                *src["m_fixedData"],
                dict(
                    m_key=b"GameTime", m_value=(src["_gameloop"] - earlier - gate) * 256
                ),
            ]
            changed["objective_time"] += 1
        elif src["_eventid"] == 2:
            check(
                src["m_killerPlayerId"] is None
                and entry["producer"] == "gate_blocker_removal",
                "Unexpected death translation",
            )
            expected["m_killerPlayerId"] = 0
            changed["gate_killer_encoding"] += 1
        check(actual == expected, "Source-to-target field accounting differs")
        counts[entry["producer"]] += 1
    wanted = dict(
        hero_startup=30,
        gates_open=1,
        GatesAreOpen=10,
        MinionsAreSpawning=10,
        gate_blocker_removal=54,
        ordinary_revival=45,
        clocked_objective=17,
        team_level_requires_recorded_xp_clock=210,
        objective_owner=21,
    )
    if m == MERC_CAPTURE:
        wanted.update(merc_capture_beacon=26, merc_capture_flag=13)
    if "initial_talent_requires_award_state" in counts:
        wanted["initial_talent_requires_award_state"] = 3
        check(
            [
                r["source_ordinal"]
                for r in mapping
                if r["producer"] == "initial_talent_requires_award_state"
            ]
            == [243, 250, 464],
            "Unexpected set of first-purchase awards",
        )
    check(dict(counts) == wanted, "Producer coverage does not match the map profile")
    derived = dict(
        source_tracker_frames=len(native),
        source_postzero_frames=len(post),
        target_loop_zero_candidate=len(zero),
        covered_postzero=len(mapping),
        omitted_postzero=len(missing),
        match_end_loop=horizon,
        sparse_frames=len(new),
        sparse_bytes=len(wire),
        sparse_sha256=digest(wire),
        continuous_candidate_frames=len(contiguous),
        continuous_candidate_bytes=size,
        continuous_candidate_sha256=digest(prefix),
        last_contiguous_event_loop=contiguous[-1][0]["_gameloop"],
        first_missing_loop=first["_gameloop"],
        first_missing_source_ordinal=missing[0],
        first_missing_event=first.get("m_eventName", b"").decode(),
        per_producer=dict(counts),
    )
    check(
        all(report[k] == v for k, v in derived.items()),
        "Tracker receipt differs from physical evidence",
    )
    return dict(
        physical_source_frames=len(native),
        physical_target_frames=len(new),
        joined_postzero=len(mapping),
        field_changes=dict(changed),
        ledger_sha256=digest((directory / "tracker-ordinals.json").read_bytes()),
        sparse_sha256=digest(wire),
        prefix_sha256=digest(prefix),
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "package", "directory", "receipt"):
        cli.add_argument(name, type=Path)
    print(json.dumps(verify(**vars(cli.parse_args())), indent=2))
