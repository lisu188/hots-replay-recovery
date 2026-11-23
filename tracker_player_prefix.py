"""Generate the complete initial player-setup block for a ten-human Dragon Shire lobby."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from camp_owner_wire import read_tracker, TARGET_SCHEMA_SHA
from encoders import encode_tracker_events
from mpq_reader import MPQArchive
from protocol_loader import load_protocol

SETUP = "NNet.Replay.Tracker.SPlayerSetupEvent"
FIELDS = ("m_playerId", "m_type", "m_userId", "m_slotId")


def predict(slots, event_id):
    players = [(index, slot) for index, slot in enumerate(slots) if slot["m_observe"] == 0 and slot.get("m_hero")]
    if [index for index, _ in players] != list(range(10)):
        raise ValueError("Expected ten occupied playing slots in Dragon Shire lobby order")
    if any(s["m_control"] != 2 or s["m_userId"] is None for _, s in players):
        raise ValueError("Nonhuman or unbound playing slot")
    if len({s["m_userId"] for _, s in players}) != len(players):
        raise ValueError("Duplicate human user ID")
    return [dict(_eventid=event_id, _event=SETUP, _gameloop=0, m_playerId=i + 1, m_type=1,
                 m_userId=slot["m_userId"], m_slotId=i) for i, slot in players]


def generate(replay, digest, build):
    if sha256(replay.read_bytes()).hexdigest() != digest:
        raise ValueError("Unexpected replay digest")
    source, tracker, _ = read_tracker(replay, build)
    target = load_protocol(96477)
    if target.recovery_schema_sha256 != TARGET_SCHEMA_SHA:
        raise ValueError("Unexpected target protocol")
    (event_id,) = [i for i, (tid, name) in target.tracker_event_types.items()
                   if name == SETUP and tuple(f[0] for f in target.typeinfos[tid][1][0]) == FIELDS]
    with closing(MPQArchive(replay)) as archive:
        init = source.decode_replay_initdata(archive.read_file("replay.initData"))
    slots = init["m_syncLobbyState"]["m_lobbyState"]["m_slots"]
    events = predict(slots, event_id)
    payload = encode_tracker_events(events, target)
    if not tracker.startswith(payload):
        raise ValueError("Projected header frames differ from the physical tracker prefix")
    observed = source.decode_replay_tracker_events(tracker)
    consumed = 0
    for row in events:
        event = next(observed)
        if row != {k: v for k, v in event.items() if k != "_bits"}:
            raise ValueError("Wrong physical setup event")
        consumed += event["_bits"]
    following = next(observed)
    if consumed != len(payload) * 8 or following["_event"] == SETUP:
        raise ValueError("Partial or unaligned player setup block")
    return payload, dict(build=build, replay_sha256=digest, frames=len(events), prefix_bytes=len(payload),
                         prefix_sha256=sha256(payload).hexdigest(), next_kind=following["_event"].rsplit(".", 1)[-1],
                         user_id_differs_from_slot=sum(r["m_userId"] != r["m_slotId"] for r in events),
                         working_set_id_differs_from_slot=sum(s["m_workingSetSlotId"] != i for i, s in enumerate(slots[:10])))


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("replay", type=Path)
    cli.add_argument("sha256")
    cli.add_argument("build", type=int, choices=(41810, 98348))
    cli.add_argument("--output", type=Path)
    args = cli.parse_args()
    wire, receipt = generate(args.replay, args.sha256, args.build)
    if args.output:
        with args.output.open("xb") as stream:
            stream.write(wire)
    print(json.dumps(receipt, indent=2))
