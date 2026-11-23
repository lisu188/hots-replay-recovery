"""Reconstruct explicit final-loop player departures and verify their recorded target form."""

import argparse
from collections import Counter
from contextlib import closing
import json
from pathlib import Path

from audit_native_game_fidelity import _anonymous
from encoders import encode_game_events as encode_named
from first_sync_game import game
from literal_chat_input import verify_chat
from mpq_reader import MPQArchive
from native_game_events import GameEvent, encode_game_events, iter_game_events
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE


def leaves(source, digest, build):
    p, data = game(source, digest, build)
    target = target_protocol()
    with closing(MPQArchive(source)) as archive:
        setup = p.decode_replay_initdata(archive.read_file("replay.initData"))
    slots = setup["m_syncLobbyState"]["m_lobbyState"]["m_slots"]
    initial = {s["m_userId"] for s in slots if s["m_control"] == 2 and s["m_userId"] is not None}
    touched = set()
    previous = offset = 0
    chat = 0
    candidates = []
    for ordinal, row in enumerate(p.decode_replay_game_events(data)):
        tick, user, kind = row["_gameloop"], row["_userid"]["m_userId"], row["_eventid"]
        size, extra = divmod(row["_bits"], 8)
        if extra or size == 0 or offset + size > len(data):
            raise ValueError("Invalid physical extent")
        if tick != previous:
            candidates.clear()
        if kind == 32:
            verify_chat(row,previous,data[offset:offset+size],p,target)
            chat += 1
        if kind in (101,102):
            if kind == 101 and user in initial and user not in touched and row["m_leaveReason"] == 0:
                candidates.append((ordinal, row, previous, data[offset:offset+size]))
            touched.add(user)
        offset += size
        previous = tick
    if offset != len(data):
        raise ValueError("Incomplete source stream")
    tid, name = target.game_event_types[101]
    source_tid, source_name = p.game_event_types[101]
    for proto, struct_id, width in ((p, source_tid, 4 if build == 41810 else 5),(target, tid, 5)):
        ((field, value_type, tag),) = proto.typeinfos[struct_id][1][0]
        if (field, tag) != ("m_leaveReason",-1) or proto.typeinfos[value_type] != ("_int",[(0,width)]):
            raise ValueError("Unexpected leave-reason declaration")
    if name != source_name:
        raise ValueError("Departure name differs")
    values = []
    target_bytes = 0
    for ordinal,row,prior,raw in candidates:
        fields = {k:v for k,v in row.items() if not k.startswith("_")}
        if name != row["_event"] or fields != {"m_leaveReason":0}:
            raise ValueError("Unexpected departure fields")
        dt = row["_gameloop"]-prior
        target_frame = GameEvent(dt,row["_userid"]["m_userId"],101,_anonymous(fields,target.typeinfos,tid))
        wire = encode_game_events([target_frame])
        decoded, = iter_game_events(wire)
        named = [{**row,"_gameloop":dt}]
        if (decoded.event != target_frame or encode_named(named,p) != raw
                or encode_named(named,target) != wire or (build == 98348 and raw != wire)):
            raise ValueError("Recorded departure or target encoding differs")
        target_bytes += len(wire)
        values.append((ordinal,row))
    return values, dict(build=build, last_game_loop=previous, terminal_departures=len(values),
                        physical_bytes=sum(len(raw) for _,_,_,raw in candidates), projected_bytes=target_bytes,
                        literal_chat_frames=chat)


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("original",type=Path)
    cli.add_argument("controls",type=Path)
    a=cli.parse_args()
    import first_sync_game
    refs=json.loads(a.controls.read_bytes())
    evidence=Path(first_sync_game.__file__).resolve().parent/"observations"/"first-sync-game.json"
    if len(refs)!=24 or set(refs)!={r["replay_sha256"] for r in json.loads(evidence.read_bytes())["references"]}:
        raise ValueError("Unexpected controls")
    actual,ten=leaves(a.original,SOURCE,41810)
    c=Counter()
    for digest,name in refs.items():
        _,info=leaves(Path(name),digest,98348)
        c["matching_departures"]+=info["terminal_departures"]
        c["matching_bytes"]+=info["physical_bytes"]
        c["controls_with_qualifying_departures"]+=bool(info["terminal_departures"])
        c["matching_literal_chat_frames"]+=info["literal_chat_frames"]
    print(json.dumps(dict(ten=ten,original_ordinals=[i for i,_ in actual],controls=len(refs),**c),indent=2))
