"""Check the first file input, observer sentinel and recorded sync cadence on held replays."""

from collections import Counter
from contextlib import closing
import argparse
import json
from pathlib import Path

from check_dispatch_inputs import advance, components, native_tables
from first_sync_game import game, opening
from mpq_reader import MPQArchive
from portable_sync_98348 import decode_sync


def compare(replays, table):
    counts = Counter()
    for digest, name in replays.items():
        path = Path(name)
        protocol, raw = game(path, digest, 98348)
        events = list(opening(raw, protocol))
        _, _, first = events[0]
        kind, user, loop, length, crc = next(components(first))
        if (kind, user, loop, length, crc) == (5, 16, 0, 0, 0):
            counts["first_empty_sentinel_event"] += 1
            if advance(0xffffffff, loop, user, crc, table) == 0x79167cd3:
                counts["clean_seed_first_update_matches"] += 1
        with closing(MPQArchive(path)) as archive:
            sync = decode_sync(archive.read_file("replay.sync.events"))
            slots = protocol.decode_replay_initdata(archive.read_file("replay.initData"))["m_syncLobbyState"]["m_lobbyState"]["m_slots"]
            tracker = protocol.decode_replay_tracker_events(archive.read_file("replay.tracker.events"))
            observed = []
            for event in tracker:
                if event["_gameloop"] != 0:
                    break
                if event["_event"].endswith(".SPlayerSetupEvent"):
                    observed.append(event)
        counts["controls"] += 1
        counts["records"] += len(sync)
        counts["complete_64_loop_cadence"] += bool(sync) and all(
            r.event_id == 2 and r.gameloop == i * 64 for i, r in enumerate(sync, 1))
        for e in observed:
            if e["m_type"] != 1:
                continue
            slot, user = e["m_slotId"], e["m_userId"]
            counts["human_joins_examined"] += 1
            if (slot is not None and 0 <= slot < len(slots) and slots[slot]["m_control"] == 2
                    and slots[slot]["m_userId"] == user):
                counts["human_lobby_tracker_joins"] += 1
                counts["user_differs_from_slot"] += user != slot
                counts["player_id_differs_from_slot_plus_one"] += e["m_playerId"] != slot + 1
    return dict(sorted(counts.items()))


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("controls", type=Path, help="Local JSON map of the 24 pinned SHA-256 values to replay paths")
    cli.add_argument("pe", type=Path)
    a = cli.parse_args()
    cases = json.loads(a.controls.read_bytes())
    import first_sync_game
    pins = Path(first_sync_game.__file__).resolve().parent / "observations" / "first-sync-game.json"
    if len(cases) != 24 or set(cases) != {r["replay_sha256"] for r in json.loads(pins.read_bytes())["references"]}:
        raise ValueError("Expected the 24 pinned target recordings")
    print(json.dumps(compare(cases, native_tables(a.pe.read_bytes())), indent=2))
