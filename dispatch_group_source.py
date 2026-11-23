"""Project normal Dragon Shire dispatch groups from MapInfo and the lobby, then check the physical setup prefix."""

import argparse
import json
import struct
from contextlib import closing
from hashlib import sha256
from pathlib import Path

from camp_owner_wire import read_tracker, STOCK, TARGET_SCHEMA_SHA
from encoders import encode_tracker_events
from hero_revive_wire import MEMBERS, GATE_MAP
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from protocol_loader import load_protocol
from tracker_player_prefix import SETUP


def digest(data):
    return sha256(data).hexdigest()


def player_groups(path, build):
    if digest(path.read_bytes()) != {41810: GATE_MAP, 98348: STOCK}[build]:
        raise ValueError("Unknown map package")
    with closing(MPQArchive(path)) as archive:
        info = read_member(archive, "MapInfo")
    expected, _, offset = MEMBERS[build]
    if digest(info) != expected or info[:4] != b"IpaM":
        raise ValueError("Unexpected MapInfo")
    count, = struct.unpack_from("<I", info, offset)
    offset += 4
    groups = []
    for _ in range(count):
        group, control, _color = struct.unpack_from("<BII", info, offset)
        offset = info.index(b"\0", offset + 9) + 1
        offset = info.index(b"\0", offset + 12) + 1
        if control == 1:
            groups.append(group)
        elif control not in (3, 4):
            raise ValueError("Unmodeled map control")
    if len(groups) != 10 or len(set(groups)) != 10 or max(groups) >= 16:
        raise ValueError("Expected ten distinct human groups")
    return groups


def predict(groups, slots):
    playing = [(i, s) for i, s in enumerate(slots) if s["m_observe"] == 0]
    if len(slots) != 16 or [i for i, _ in playing] != list(range(10)):
        raise ValueError("Expected ten leading playing slots")
    if any(s["m_control"] != 2 or not s["m_hero"] or s["m_tandemLeaderUserId"] not in (None, 16)
           for _, s in playing):
        raise ValueError("Requires ordinary human players without tandem leaders")
    users = [s["m_userId"] for _, s in playing]
    bound = [s["m_userId"] for s in slots if s["m_userId"] is not None]
    if any(type(u) is not int or not 0 <= u < 16 for u in users) or len(set(bound)) != len(bound):
        raise ValueError("Missing or repeated participant binding")
    return [(user, i, group) for user, (i, _), group in zip(users, playing, groups, strict=True)]


def verify(path, replay_sha, build, groups):
    if digest(path.read_bytes()) != replay_sha:
        raise ValueError("Unexpected replay")
    source, raw, _ = read_tracker(path, build)
    with closing(MPQArchive(path)) as archive:
        slots = source.decode_replay_initdata(archive.read_file("replay.initData"))["m_syncLobbyState"]["m_lobbyState"]["m_slots"]
    rows = predict(groups, slots)
    # The independent physical tracker enters only after producing every assignment.
    expected = [dict(_event=SETUP, _eventid=9, _gameloop=0, m_type=1,
                     m_userId=user, m_slotId=slot, m_playerId=group) for user, slot, group in rows]
    target = load_protocol(96477)
    if target.recovery_schema_sha256 != TARGET_SCHEMA_SHA:
        raise ValueError("Unexpected target schema")
    slot_fields = target.typeinfos[67][1][0]
    used = [(slot_fields[i][0], slot_fields[i][2]) for i in (0, 1, 8, 16)]
    if used != [("m_control", -26), ("m_userId", -25), ("m_observe", -18), ("m_tandemLeaderUserId", -10)]:
        raise ValueError("Unexpected target slot field declarations")
    payload = encode_tracker_events(expected, target)
    observed = source.decode_replay_tracker_events(raw)
    bits = 0
    for prediction in expected:
        event = next(observed)
        bits += event.pop("_bits")
        if event != prediction:
            raise ValueError("Physical setup row disagrees with map/lobby")
    if bits != len(payload) * 8 or not raw.startswith(payload) or next(observed)["_event"] == SETUP:
        raise ValueError("Physical setup block differs")
    return dict(build=build, replay_sha256=replay_sha, user_slot_group=rows,
                physical_setup_bytes=len(payload), physical_setup_sha256=digest(payload),
                differing_user_slot=sum(u != i for u, i, _ in rows),
                differing_working_set_slot=sum(slots[i]["m_workingSetSlotId"] != i for _, i, _ in rows))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map", type=Path)
    parser.add_argument("replay", type=Path)
    parser.add_argument("build", type=int, choices=(41810, 98348))
    parser.add_argument("replay_sha256")
    args = parser.parse_args()
    print(json.dumps(verify(args.replay, args.replay_sha256, args.build,
                            player_groups(args.map, args.build)), indent=2))


if __name__ == "__main__":
    main()
