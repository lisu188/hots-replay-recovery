"""Restore the post-2019 mastery-ring records for Dragon Shire matches played before rings existed."""

import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from itertools import takewhile
import json
from pathlib import Path

from camp_owner_wire import read_tracker
from dragon_loop_zero import assemble, upgrade
from encoders import encode_tracker_events
from mpq_reader import MPQArchive
from opening_birth_wire import target_protocol

RING = b"HeroRingMasteryUpgrade"
INTRODUCTION = datetime(2019, 10, 15, tzinfo=timezone.utc)
SUPPORT = "b7578aac7284cbc6bed62b2b4fde267615f99bc0e3703fce31a32d5835a55a80"


def zero_rings():
    return [{**upgrade(i, RING), "m_count": 0} for i in range(1, 11)]


def check_support(path):
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != SUPPORT:
        raise ValueError("Unexpected SupportLib")
    code = raw.decode("utf-8-sig")
    begin = code.index("lv_playerMasteryLevel = PlayerHeroMasteryTier(")
    end = code.index('SetUpgradeLevelForPlayer(lp_player, "HeroRingMasteryUpgrade", lv_lastSuccessfulUpgradeLevel);', begin)
    body = code[begin:end]
    if ('if ((lv_playerMasteryLevel >= lv_iteratorString) && (PlayerHasReward(lp_player, '
        '(lv_combinedRewardArrayStringValue)) == true))' not in body
            or body.count("lv_lastSuccessfulUpgradeLevel = lv_iteratorString;") != 1):
        raise ValueError("Unrecognized mastery reward qualification")


def verify_native(replay, digest):
    if sha256(replay.read_bytes()).hexdigest() != digest:
        raise ValueError("Unexpected control")
    p, raw, _ = read_tracker(replay, 98348)
    target = target_protocol()
    rows = list(takewhile(lambda r:r["_gameloop"] == 0, p.decode_replay_tracker_events(raw)))
    tail = rows[-10:]
    if (rows[-11].get("m_eventName") != b"JungleCampInit"
            or [r.get("m_playerId") for r in tail] != list(range(1, 11))
            or any(r.get("m_upgradeTypeName") != RING for r in tail)):
        raise ValueError("Unexpected mastery initialization order")
    offset = sum(r["_bits"] for r in rows[:-10]) // 8
    levels = Counter()
    for r, expected in zip(tail, zero_rings()):
        size, rem = divmod(r["_bits"], 8)
        if rem or r["m_count"] not in range(4):
            raise ValueError("Unexpected mastery frame")
        levels[r["m_count"]] += 1
        if r["m_count"] == 0 and encode_tracker_events([expected], target) != raw[offset:offset+size]:
            raise ValueError("Zero-entitlement frame differs")
        offset += size
    return dict(replay_sha256=digest, levels=dict(levels))


def historical(replay, digest, package, mechanics, support):
    check_support(support)
    data, receipt = assemble(replay, digest, 41810, package, mechanics)
    p, _, _ = read_tracker(replay, 41810)
    with closing(MPQArchive(replay)) as arc:
        details = p.decode_replay_details(arc.read_file("replay.details"))
        slots = p.decode_replay_initdata(arc.read_file("replay.initData"))["m_syncLobbyState"]["m_lobbyState"]["m_slots"]
    epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
    played = epoch + timedelta(microseconds=details["m_timeUTC"] // 10)
    if not datetime(2015, 1, 1, tzinfo=timezone.utc) <= played < INTRODUCTION:
        raise ValueError("Match date outside the pre-mastery-ring era")
    if any(s.get("m_hero") in {b"Cho",b"Gall"} for s in slots):
        raise ValueError("Paired Cho/Gall mastery setter is outside this comparison")
    if receipt["subsequent_loop_zero_kinds"]:
        raise ValueError("Unexpected historical records after last camp")
    target = target_protocol()
    tail = encode_tracker_events(zero_rings(), target)
    full = data + tail
    decoded = list(target.decode_replay_tracker_events(full))
    if (len(decoded) != receipt["target_block_frames"] + 10 or sum(e["_bits"] for e in decoded) != 8 * len(full)
            or any(r["_gameloop"] != 0 for r in decoded)):
        raise ValueError("Projected post-draft block is incomplete")
    return full, dict(replay_sha256=digest, match_date=played.date().isoformat(),
                      post_draft_frames=len(decoded), bytes=len(full), sha256=sha256(full).hexdigest(),
                      tail_frames=10, tail_bytes=len(tail), tail_sha256=sha256(tail).hexdigest())


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("replay", type=Path)
    cli.add_argument("sha256")
    cli.add_argument("map", type=Path)
    cli.add_argument("mechanics", type=Path)
    cli.add_argument("support", type=Path)
    cli.add_argument("--private-output", type=Path)
    cli.add_argument("--native-case", action="append", nargs=2, default=[], metavar=("REPLAY", "SHA256"))
    args = cli.parse_args()
    data, result = historical(args.replay, args.sha256, args.map, args.mechanics, args.support)
    controls = [verify_native(Path(p), h) for p,h in args.native_case]
    if args.private_output:
        with args.private_output.open("xb") as stream:
            stream.write(data)
    print(json.dumps(dict(historical=result, native_controls=controls), indent=2))
