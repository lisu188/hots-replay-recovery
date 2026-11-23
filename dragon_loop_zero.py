"""Build the contiguous Dragon Shire tracker block from the first map unit through the last camp statistic."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from xml.etree import ElementTree

from camp_owner_wire import read_tracker
from dragon_opening_map_stats import generate as map_statistics
from encoders import encode_tracker_events
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from opening_birth_wire import model, target_protocol
from tracker_player_prefix import predict as player_setup


def upgrade(player, name):
    return dict(_gameloop=0, _eventid=5, _event="NNet.Replay.Tracker.SUpgradeEvent",
                m_playerId=player, m_upgradeTypeName=name, m_count=1)


def membership(slots):
    teams = [[i for i, slot in enumerate(slots[:10], 1) if slot["m_teamId"] == team] for team in (0, 1)]
    if [len(t) for t in teams] != [5, 5]:
        raise ValueError("Expected two five-player teams")
    return [upgrade(player, name) for players, computer, name in
            zip(teams, (11, 12), (b"IsOnOrderTeam", b"IsOnChaosTeam")) for player in [*players, computer]]


def player_init(i, slot):
    strings = [dict(m_key=b"Controller", m_value=b"User")]
    if slot["m_toonHandle"]:
        strings.append(dict(m_key=b"ToonHandle", m_value=slot["m_toonHandle"]))
    return dict(_gameloop=0, _eventid=10, _event="NNet.Replay.Tracker.SStatGameEvent", m_eventName=b"PlayerInit",
                m_stringData=strings, m_intData=[dict(m_key=b"PlayerID", m_value=i),
                dict(m_key=b"Team", m_value=slot["m_teamId"] + 1)], m_fixedData=None)


def assemble(path, digest, build, package, mechanics):
    if sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("Unexpected replay")
    src, raw, _ = read_tracker(path, build)
    dst = target_protocol()
    with closing(MPQArchive(path)) as arc:
        slots = src.decode_replay_initdata(arc.read_file("replay.initData"))["m_syncLobbyState"]["m_lobbyState"]["m_slots"]
    (setup_id,) = [i for i, pair in dst.tracker_event_types.items() if pair[1].endswith(".SPlayerSetupEvent")]
    setup = player_setup(slots, setup_id)
    prefix = encode_tracker_events(setup, dst)
    if not raw.startswith(prefix):
        raise ValueError("Lobby disagrees with the player setup prefix")
    with closing(MPQArchive(package)) as arc:
        authored = len(ElementTree.fromstring(read_member(arc, "Objects")).findall("ObjectUnit"))
    placed, _, _ = model(path, build, src, package, mechanics)
    stats = map_statistics(package, build)
    stats[1:1] = [player_init(i, s) for i, s in enumerate(slots[:10], 1)]
    first = [*placed[:authored], upgrade(15, b"CreepColor"), upgrade(11, b"IsPlayer11"), upgrade(12, b"IsPlayer12")]
    extra = membership(slots)
    rest = [*placed[authored:], *stats]
    target_rows = first + extra + rest
    observed_profile = target_rows if build == 98348 else first + rest

    start = None
    end = None
    tail = []
    offset = drafts = 0
    recorded = []
    for event in src.decode_replay_tracker_events(raw):
        if event["_gameloop"] > 0:
            break
        if start is None:
            if event["_eventid"] == 1:
                start = offset
            elif event["_eventid"] != setup_id:
                if event["_event"].rsplit(".", 1)[-1] not in {"SHeroPickedEvent", "SHeroBannedEvent", "SHeroSwappedEvent"}:
                    raise ValueError("Unexpected record before map startup")
                drafts += 1
        if end is not None:
            tail.append(event.get("m_upgradeTypeName", event["_event"].encode()).decode())
        elif start is not None:
            recorded.append({k:v for k,v in event.items() if k != "_bits"})
        size, rem = divmod(event["_bits"], 8)
        if rem:
            raise ValueError("Unaligned loop-zero record")
        offset += size
        if event.get("m_eventName") == b"JungleCampInit" and event["m_intData"] == [{"m_key": b"CampID", "m_value": 5}]:
            if end is not None:
                raise ValueError("Repeated final camp statistic")
            end = offset
    if len(recorded) != len(observed_profile):
        raise ValueError(f"Expected {len(observed_profile)} frames, found {len(recorded)}")
    for i, (actual, predicted) in enumerate(zip(recorded, observed_profile)):
        if actual != predicted:
            fields = [k for k, v in predicted.items() if actual.get(k) != v]
            raise ValueError(f"Different fields at initialization frame {i}: {fields}")
    if start is None or end is None or encode_tracker_events(observed_profile, dst) != raw[start:end]:
        raise ValueError("The contiguous map initialization block differs from the recording")
    data = encode_tracker_events(target_rows, dst)
    decoded = list(dst.decode_replay_tracker_events(data))
    if ([{k:v for k,v in r.items() if k != "_bits"} for r in decoded] != target_rows
            or sum(r["_bits"] for r in decoded) != 8 * len(data)):
        raise ValueError("Target block does not decode completely")
    receipt = dict(build=build, replay_sha256=digest, map_sha256=sha256(package.read_bytes()).hexdigest(),
                   setup_prefix_bytes=len(prefix), intervening_draft_records=drafts,
                   recorded_block_frames=len(observed_profile), recorded_block_bytes=end-start,
                   target_block_frames=len(target_rows), target_block_bytes=len(data),
                   target_block_sha256=sha256(data).hexdigest(), target_team_upgrades=len(extra),
                   subsequent_loop_zero_kinds={k:tail.count(k) for k in sorted(set(tail))})
    return data, receipt


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("replay", type=Path)
    cli.add_argument("sha256")
    cli.add_argument("build", choices=(41810, 98348), type=int)
    cli.add_argument("map", type=Path)
    cli.add_argument("mechanics", type=Path)
    cli.add_argument("--private-output", type=Path, help="New private file; contains original player identifiers")
    args = cli.parse_args()
    data, result = assemble(args.replay, args.sha256, args.build, args.map, args.mechanics)
    if args.private_output:
        with args.private_output.open("xb") as stream:
            stream.write(data)
    print(json.dumps(result, indent=2))
