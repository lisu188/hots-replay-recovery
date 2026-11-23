"""Verify the private trigger-chat payload at its original game-event boundary."""

from encoders import encode_game_events as named_encode
from native_game_events import GameEvent, encode_game_events, iter_game_events


def verify_chat(row, previous, physical, source, target):
    for p in (source,target):
        tid, name = p.game_event_types[32]
        ((field, blob, tag),) = p.typeinfos[tid][1][0]
        if (name != row["_event"] or name != "NNet.Game.STriggerChatMessageEvent"
                or (field,tag) != ("m_chatMessage",-1) or p.typeinfos[blob] != ("_blob",[(0,10)])):
            raise ValueError("Unexpected chat payload declaration")
    dt = row["_gameloop"]-previous
    event = GameEvent(dt,row["_userid"]["m_userId"],32,(row["m_chatMessage"],))
    wire = encode_game_events([event])
    read, = iter_game_events(wire)
    if (read.event != event or wire != physical or
            any(named_encode([{**row,"_gameloop":dt}],p) != physical for p in (source,target))):
        raise ValueError("Private trigger-chat input changed")
