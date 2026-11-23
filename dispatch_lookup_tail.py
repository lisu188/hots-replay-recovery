"""Project the clean 98348 dispatch mask and lookup tables from a Dragon Shire map and lobby."""

import argparse
from contextlib import closing
from hashlib import sha256
from itertools import takewhile
import json
from pathlib import Path

from dispatch_group_source import player_groups, predict, verify
from mpq_reader import MPQArchive
from protocol_loader import load_protocol


def lookup_state(groups, slots):
    """Return mask, three consecutive 16-byte tables, and the membership-write masks."""
    rows = predict(groups, slots)
    active = 0
    for slot in slots:
        if slot["m_control"] == 2:
            user = slot["m_userId"]
            if type(user) is not int or not 0 <= user < 16:
                raise ValueError("Unmodeled controlled slot")
            active |= 1 << user
    user_group, slot_group, user_slot = (bytearray([16] * 16) for _ in range(3))
    user_writes = slot_writes = 0
    for user, slot, group in rows:
        user_group[user] = slot_group[slot] = group
        user_slot[user] = slot
        user_writes |= 1 << user
        slot_writes |= 1 << slot
    return active, bytes(user_group + slot_group + user_slot), (user_writes, slot_writes, user_writes)


def audit(path, digest, build, map_file):
    groups = player_groups(map_file, build)
    prefix = verify(path, digest, build, groups)
    proto = load_protocol(41810 if build == 41810 else 96477)
    with closing(MPQArchive(path)) as arc:
        setup = proto.decode_replay_initdata(arc.read_file("replay.initData"))
        game = arc.read_file("replay.game.events")
    slots = setup["m_syncLobbyState"]["m_lobbyState"]["m_slots"]
    active, tail, writes = lookup_state(groups, slots)
    # The mask includes controlled observers as well as playing users. Cross-check their
    # physical input envelopes independently of both the lobby and the tracker setup rows.
    options = set()
    lobby_updates = []
    for event in takewhile(lambda e: e["_gameloop"] <= 64, proto.decode_replay_game_events(game)):
        if event["_eventid"] in (101, 102):
            lobby_updates.append((event["_gameloop"], event["_eventid"]))
        if event["_eventid"] == 7:
            if event["_event"].rsplit(".", 1)[-1] != "SUserOptionsEvent":
                raise ValueError("Unexpected event 7")
            options.add(event["_userid"]["m_userId"])
    if options != {user for user in range(16) if active & (1 << user)}:
        raise ValueError("Physical opening options disagree with projected active users")
    return dict(build=build, replay_sha256=digest, active_hex=f"{active:04x}",
                mask_little_endian=active.to_bytes(2, "little").hex(),
                group_member_write_masks=[f"{mask:04x}" for mask in writes],
                groups_without_members=[i for i in range(16) if i not in groups],
                user_to_group=tail[:16].hex(), slot_to_group=tail[16:32].hex(),
                user_to_slot=tail[32:].hex(), lookup_tail_sha256=sha256(tail).hexdigest(),
                complete_physical_setup_bytes=prefix["physical_setup_bytes"],
                physical_options_users=sorted(options), recorded_membership_updates_through_loop64=lobby_updates)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("replay", type=Path)
    cli.add_argument("replay_sha256")
    cli.add_argument("build", choices=(41810, 98348), type=int)
    cli.add_argument("map", type=Path)
    args = cli.parse_args()
    print(json.dumps(audit(args.replay, args.replay_sha256, args.build, args.map), indent=2))
