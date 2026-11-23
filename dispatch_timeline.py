"""Replay the first TEN dispatch CRC under explicit native user and admission inputs."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import struct
from zlib import crc32

from check_dispatch_inputs import advance, components, native_tables
from dispatch_group_source import player_groups, predict
from first_sync_game import game
from mpq_reader import MPQArchive
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE
from verify_first_sync_inputs import GAME, TRACKER


def trace(raw, table, mapped_users, admitted, seed=0xffffffff):
    """Return states of context+A13C0 after each event and at the end of each input loop."""
    if not 0 <= seed <= 0xffffffff:
        raise ValueError("Expected an unsigned 32-bit initial state")
    state = seed
    wire = bytearray()
    rows = []
    last = {}
    for (kind, user, loop, _, payload_crc), accept in zip(components(raw), admitted, strict=True):
        if type(accept) is not bool:
            raise ValueError("Expected a decision for each input")
        if accept:
            mapped = 16 if user >= 16 else mapped_users[user]
            if type(mapped) is not int or not 0 <= mapped <= 16:
                raise ValueError("Unresolved mapped user")
            state = advance(state, loop, mapped, payload_crc, table)
            wire.extend(struct.pack("<IBI", loop, mapped, payload_crc))
        rows.append(state)
        last[loop] = state
    independent = crc32(wire, seed ^ 0xffffffff) ^ 0xffffffff
    if state != independent:
        raise ValueError("Incremental and contiguous dispatch updates disagree")
    return rows, last, sha256(wire).hexdigest()


def ten(source, prefix, tracker, map_file, table):
    if (sha256(prefix).hexdigest(), sha256(tracker).hexdigest()) != (GAME, TRACKER):
        raise ValueError("Unexpected TEN target input pair")
    protocol, _ = game(source, SOURCE, 41810)
    with closing(MPQArchive(source)) as archive:
        lobby = protocol.decode_replay_initdata(archive.read_file("replay.initData"))["m_syncLobbyState"]["m_lobbyState"]["m_slots"]
    predicted = predict(player_groups(map_file, 41810), lobby)
    mapped = {user: group for user, _, group in predicted}
    roles = {user: lobby[slot]["m_observe"] for user, slot, _ in predicted}
    active_mask = sum(1 << s["m_userId"] for s in lobby if s["m_control"] == 2 and s["m_userId"] is not None)
    if active_mask != 0x03ff:
        raise ValueError("Unexpected set of active users")
    observed = []
    for event in target_protocol().decode_replay_tracker_events(tracker):
        if not event["_event"].endswith(".SPlayerSetupEvent"):
            continue
        slot, user, player = event["m_slotId"], event["m_userId"], event["m_playerId"]
        if (event["_gameloop"] != 0 or event["m_type"] != 1 or not 0 <= slot < len(lobby)
                or (lobby[slot]["m_control"], lobby[slot]["m_observe"], lobby[slot]["m_userId"]) != (2, 0, user)
                or mapped.get(user) != player):
            raise ValueError("Nonunique or unsupported participant setup")
        observed.append((user, slot, player))
    if observed != predicted:
        raise ValueError("Tracker and MapInfo/lobby assignments differ")
    data = list(components(prefix))
    if data[0] != (5, 16, 0, 0, 0) or len(data) != 30 or data[-1][2] != 64:
        raise ValueError("Unexpected boundary inputs")
    masks = {5: 7, 7: 7, 27: 1, 28: 7, 56: 1, 104: 1}
    allowed = []
    for kind, user, _, _, _ in data:
        if user == 16:
            if kind != 5:
                raise ValueError("Unbound sentinel event")
            allowed.append(True)
        elif user in mapped:
            allowed.append(bool((1 << user) & active_mask and masks[kind] & (1 << roles[user])))
        else:
            raise ValueError("Unbound source user")
    states, loops, digest = trace(prefix, table, mapped, allowed)
    if (states[0], digest) != (0x79167cd3, "4b01f15bd1931b326c562ed20e870dfe2b070be31c2f324f410255abd0394687"):
        raise ValueError("Opening dispatch regression")
    return dict(build=98348, inputs=len(states), wire_bytes=9 * sum(allowed), dispatch_input_sha256=digest,
                first_update_from_clean_seed=hex(states[0]), last_by_input_loop={t: hex(s) for t, s in loops.items()},
                scope="Clean start with TEN map, active mask and class-zero lobby participants committed, projected file inputs dispatched in recorded order",
                target_simulation_checksum_computed=False)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for field in ("original", "game_prefix", "tracker_prefix", "map", "pe"):
        cli.add_argument(field, type=Path)
    args = cli.parse_args()
    print(json.dumps(ten(args.original, args.game_prefix.read_bytes(), args.tracker_prefix.read_bytes(), args.map,
                         native_tables(args.pe.read_bytes())), indent=2))
