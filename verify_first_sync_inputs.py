"""Cross-check the TEN target game and tracker prefixes at the first original sync marker."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from audit_native_game_fidelity import _anonymous
from first_sync_game import game, opening
from mpq_reader import MPQArchive
from native_game_events import GameEvent, encode_game_events as encode_native, iter_game_events
from portable_sync_98348 import decode_sync
from predict_camp_captures import SOURCE
from protocol_loader import load_protocol

TRACKER = "4fb2990a2c35b1199fca861e86bbc98ed4e1d1abd01d1791d8d06ad6e462efce"
GAME = "68def0020f334b543ed6e1be6aed1fd57bfbdc284c933372298a3e96cc69efc5"


def verify(source, target_tracker, target_game):
    if (sha256(target_tracker).hexdigest(), sha256(target_game).hexdigest()) != (TRACKER, GAME):
        raise ValueError("Unexpected game or tracker input")
    old, original_game = game(source, SOURCE, 41810)
    with closing(MPQArchive(source)) as archive:
        slots = old.decode_replay_initdata(archive.read_file("replay.initData"))["m_syncLobbyState"]["m_lobbyState"]["m_slots"]
        sync = archive.read_file("replay.sync.events")
    if sha256(sync).hexdigest() != "62a68b50c8cf0c94da98403dad8cda0f92e02580ec9590b2b32815ee32f8d8ae":
        raise ValueError("Original sync member differs")
    records = decode_sync(sync)
    if len(records) != 308 or records[0].gameloop != 64:
        raise ValueError("Unexpected first original sync marker")
    players = {s["m_userId"]: i for i, s in enumerate(slots, 1) if s.get("m_hero")}
    target = load_protocol(96477)
    tr = list(target.decode_replay_tracker_events(target_tracker))
    inputs = list(target.decode_replay_game_events(target_game))
    if (len(tr),len(inputs),sum(e["_bits"] for e in tr),sum(e["_bits"] for e in inputs)) != (
            247,30,len(target_tracker)*8,len(target_game)*8):
        raise ValueError("Incomplete pair of target prefixes")
    native = list(iter_game_events(target_game))
    prior = 0
    for named, physical in zip(inputs, native, strict=True):
        event_id = named["_eventid"]
        type_id, _ = target.game_event_types[event_id]
        fields = {k:v for k,v in named.items() if not k.startswith("_")}
        expected = GameEvent(named["_gameloop"] - prior, named["_userid"]["m_userId"], event_id,
                             _anonymous(fields, target.typeinfos, type_id))
        if physical.event != expected or physical.aligned_end_bit - physical.start_bit != named["_bits"]:
            raise ValueError("Native-derived input frame disagrees with the named target protocol")
        prior = named["_gameloop"]
    if encode_native([row.event for row in native]) != target_game:
        raise ValueError("Native-derived input writer disagrees")
    births = {(e["m_unitTagIndex"],e["m_unitTagRecycle"]):e for e in tr if e["_eventid"] == 1}
    selected, issued, hits = {}, {}, []
    source_events = [e for e,_,_ in opening(original_game, old)]
    for e, historic in zip(inputs, source_events, strict=True):
        tick, kind, user = e["_gameloop"], e["_eventid"], e["_userid"]["m_userId"]
        if (historic["_gameloop"],historic["_eventid"],historic["_userid"]["m_userId"]) != (tick, kind, user):
            raise ValueError("Target input order differs from TEN")
        if kind == 28:
            tag, = e["m_delta"]["m_addUnitTags"]
            original_tag, = historic["m_delta"]["m_addUnitTags"]
            key = tag >> 22, tag & ((1 << 22) - 1)
            if key != (original_tag >> 18, original_tag & ((1 << 18) - 1)):
                raise ValueError("Historical and target tag identify different units")
            birth = births[key]
            if birth["_gameloop"] >= tick or birth["m_controlPlayerId"] != players[user] or birth["m_upkeepPlayerId"] != players[user]:
                raise ValueError("Selected hero is absent or belongs to a different player")
            selected[user] = key
            hits.append(dict(loop=tick, hero=birth["m_unitTypeName"].decode()))
        elif kind == 27:
            if user not in selected or historic["m_data"] != e["m_data"] or historic["m_sequence"] != e["m_sequence"]:
                raise ValueError("Movement command disagrees with the source or its selection")
            issued[user] = e["m_sequence"]
        elif kind == 104:
            if user not in issued or issued[user] != e["m_sequence"] or e["m_target"] != historic["m_target"]:
                raise ValueError("Point update does not match the original destination and issued command")
    if len(hits) != 4 or len(issued) != 2:
        raise ValueError("Incomplete input-to-unit joins")
    return dict(target_build=98348, first_sync_loop=64, tracker_events=len(tr), tracker_bytes=len(target_tracker),
                tracker_sha256=TRACKER, source_game_inputs_represented=len(inputs), game_bytes=len(target_game),
                game_sha256=GAME, selected_heroes=hits, distinct_command_issuers=len(issued),
                native_game_values_and_physical_extents_equal=len(native), native_reencoded_bytes=len(target_game),
                source_sync_records_preserved=len(records), target_state_checksum_computed=False)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("original", "target_tracker", "target_game"):
        cli.add_argument(name, type=Path)
    a = cli.parse_args()
    print(json.dumps(verify(a.original, a.target_tracker.read_bytes(), a.target_game.read_bytes()), indent=2))
