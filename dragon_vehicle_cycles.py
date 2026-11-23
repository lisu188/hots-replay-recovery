"""Resolve Dragon Shire objective generations from activation, ownership and spawn timing."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import os

from convert_historical_pings import PING, pinned, placements
from map_startup_identity import SCHEMAS
from mpq_reader import MPQArchive
from predict_camp_captures import MAP, number
from protocol_loader import load_protocol
from repair_unit_tags import components
from smartcam_tags import DST_SCHEMA, SRC_SCHEMA, TARGET_MAP
from camp_owner_wire import OWNER, encode_sparse, frame_bytes, target_protocol

RESPAWN_LOOPS = (90 + 30) * 16
MAPS = {41810: MAP, 98348: TARGET_MAP}
LIB = "d49dbde21198963f953efa16c8d8bb6b035d2d8bd8f0d41b5989fecbb4e35b1f"
HEADER = "cef6f04b1723e88bfb33b8a04584798276fea30f9920d1bd21055646e2bb52da"


def timer_evidence(library, header):
    pinned(library, LIB)
    pinned(header, HEADER)
    text = library.read_text(encoding="utf-8-sig")
    constants = header.read_text(encoding="utf-8-sig")
    def seconds(name):
        value, = re.findall(r"const fixed libMapM_gv_mMGardensDragon" + name + r" = (\d+)\.0;", constants)
        return int(value)
    respawn = seconds("DragonTowerRespawnTime_C")
    warning = seconds("WarningTime_C")
    links = [
        'libMapM_gv_mMGardensDragonDragonKnightRespawnPoint = UnitGetPosition(',
        'TriggerAddEventUnitDied(libMapM_gt_MMGardensDragonDragonKnightDiesorExpires, UnitRefFromVariable("libMapM_gv_mMGardensDragonUnit"));',
        'TimerStart(libMapM_gv_mMGardensDragonDragonTowerRespawnTimer, libMapM_gv_mMGardensDragonDragonTowerRespawnTime_C, false, c_timeGame);',
        'TriggerAddEventTimer(libMapM_gt_MMGardensDragonWarningTimerStart, libMapM_gv_mMGardensDragonDragonTowerRespawnTimer);',
        'TimerStart(libMapM_gv_mMGardensDragonDragonTowerWarningTimer, libMapM_gv_mMGardensDragonWarningTime_C, false, c_timeGame);',
        'TriggerAddEventTimer(libMapM_gt_MMGardensDragonWarningTimerExpires, libMapM_gv_mMGardensDragonDragonTowerWarningTimer);',
        'TriggerExecute(libMapM_gt_MMGardensDragonTurnOnDragonTowersAgain, true, false);',
        'UnitCreate(1, "VehicleDragon", c_unitCreateIgnorePlacement, 0, libMapM_gv_mMGardensDragonDragonKnightRespawnPoint, 270.0, null);',
        'libMapM_gv_mMGardensDragonDragonCaptures += 1;',
        'StatEventCreate("DragonKnightActivated");',
        'StatEventAddDataInt(StatEventLastCreated(), "Event", libMapM_gv_mMGardensDragonDragonCaptures);',
    ]
    if (respawn + warning) * 16 != RESPAWN_LOOPS or any(line not in text for line in links):
        raise ValueError("Unexpected Dragon Shire trigger inputs")
    return dict(respawn_seconds=respawn, warning_seconds=warning, loops=RESPAWN_LOOPS)


@dataclass(frozen=True)
class Cycle:
    ordinal: int
    born: int
    died: int | None
    activated: int | None
    pilot: int | None
    team: int | None
    tag: tuple[int, int]
    horizon: int

    def active_at(self, loop):
        return self.born < loop <= self.horizon and (self.died is None or loop < self.died)

    def signature(self):
        return (self.ordinal, self.born, self.died, self.activated, self.pilot, self.team)


def unit_tag(event):
    return event["m_unitTagIndex"], event["m_unitTagRecycle"]


def vehicle_cycles(tracker, position, teams, horizon):
    births = []
    deaths = defaultdict(list)
    changes = defaultdict(list)
    activations = []
    for event in tracker:
        tick, kind = event["_gameloop"], event["_eventid"]
        if kind == 1 and event["m_unitTypeName"] == b"VehicleDragon":
            if (event["m_x"], event["m_y"]) != position or (
                event["m_controlPlayerId"], event["m_upkeepPlayerId"]
            ) != (0, 0):
                raise ValueError("Unexpected vehicle spawn")
            births.append((tick, unit_tag(event)))
        elif kind == 2:
            deaths[unit_tag(event)].append(tick)
        elif kind == 3:
            changes[tick].append((unit_tag(event), event["m_controlPlayerId"], event["m_upkeepPlayerId"]))
        elif event.get("m_eventName") == b"DragonKnightActivated":
            ordinal = number(event, "m_intData", "Event")
            team = number(event, "m_fixedData", "TeamID")
            if ordinal != len(activations) + 1 or team not in (4096, 8192):
                raise ValueError("Invalid objective counter or team")
            activations.append((tick, team // 4096))
    if not births or births[0][0] != 0 or len({k for _, k in births}) != len(births):
        raise ValueError("Missing initial dragon or repeated generation")
    if len(births) - len(activations) not in (0, 1):
        raise ValueError("Vehicle and activation counts disagree")
    result = []
    for i, (tick, tag) in enumerate(births):
        expected = 0 if not result else result[-1].died
        if expected is None or tick != (expected + RESPAWN_LOOPS if result else 0):
            raise ValueError("Vehicle respawn timer disagrees")
        end = deaths[tag]
        if len(end) > 1 or (end and not tick < end[0] <= horizon):
            raise ValueError("Ambiguous vehicle lifetime")
        when = owner = team = None
        if i < len(activations):
            when, team = activations[i]
            if not tick <= when <= (end[0] if end else horizon):
                raise ValueError("Activation outside vehicle lifetime")
            candidates = [(k, p) for k, p, _ in changes[when] if teams.get(p) == team]
            if len(candidates) != 1 or candidates[0][0] != tag:
                raise ValueError("Activation does not independently identify the vehicle")
            owner = candidates[0][1]
        elif end:
            raise ValueError("Unpiloted statue died")
        result.append(Cycle(i + 1, tick, end[0] if end else None, when, owner, team, tag, horizon))
    if result[-1].died is not None and result[-1].died + RESPAWN_LOOPS < horizon:
        raise ValueError("Missing vehicle before match end")
    return result


def activation_owners(cycles, tracker, build):
    """Compare the historical and target upkeep conventions for the piloted vehicle."""
    expected = {(c.activated, c.tag): (c.pilot, c.pilot if build == 41810 else 10 + c.team)
                for c in cycles if c.activated is not None}
    found = {}
    for e in tracker:
        if e["_eventid"] == 3:
            key = e["_gameloop"], unit_tag(e)
            if key in expected:
                if key in found:
                    raise ValueError("Ambiguous activation transfer")
                found[key] = e["m_controlPlayerId"], e["m_upkeepPlayerId"]
    matched = sum(k in found and found[k] == v for k, v in expected.items())
    return dict(matched=matched, different=len(expected) - matched)


def native_pilot_frames(cycles, events, original_bytes, build):
    target = target_protocol()
    frames = {}
    for c in cycles:
        if c.activated is None:
            continue
        row = dict(_gameloop=c.activated, _eventid=3, _event=OWNER,
                   m_unitTagIndex=c.tag[0], m_unitTagRecycle=c.tag[1],
                   m_controlPlayerId=c.pilot, m_upkeepPlayerId=10 + c.team)
        frames[c.activated, c.tag] = row
    raw, _ = encode_sparse(list(frames.values()))
    offset = prior = count = verified_bytes = 0
    for e in events:
        size, remainder = divmod(e["_bits"], 8)
        if remainder:
            raise ValueError("Unaligned tracker frame")
        loop = e["_gameloop"]
        if e["_eventid"] == 3 and (loop, unit_tag(e)) in frames:
            row = frames[loop, unit_tag(e)]
            if build == 98348:
                physical = frame_bytes(row, prior, target)
                if physical != original_bytes[offset:offset + size]:
                    raise ValueError("Native control frame does not match projected owner fields")
                verified_bytes += size
            count += 1
        prior, offset = loop, offset + size
    if offset != len(original_bytes) or count != len(frames):
        raise ValueError("Incomplete activation frame coverage")
    return raw, verified_bytes


def rebind_vehicle(source_cycle, destination_cycles, tick):
    """Resolve an observed vehicle into a separately reconstructed objective trace."""
    if not source_cycle.active_at(tick):
        raise ValueError("Source ping outside the vehicle lifetime")
    hits = [c for c in destination_cycles if c.signature() == source_cycle.signature()]
    if len(hits) != 1 or not hits[0].active_at(tick):
        raise ValueError("Unresolved destination objective generation")
    return hits[0].tag


def inspect(path, digest, build, map_path, retained_output=None):
    pinned(path, digest)
    p = load_protocol(SCHEMAS[build])
    if p.recovery_schema_sha256 != (SRC_SCHEMA if build == 41810 else DST_SCHEMA):
        raise ValueError("Wrong protocol")
    statue, = [u for u in placements(map_path, MAPS[build]) if u.unit_type == "VehicleDragon"]
    pos = math.floor(statue.x), math.floor(statue.y)
    with closing(MPQArchive(path)) as arc:
        h = p.decode_replay_header(arc.header["user_data_header"]["content"])
        if (h["m_version"]["m_build"], h["m_version"]["m_baseBuild"], h["m_dataBuildNum"]) != (build,) * 3:
            raise ValueError("Wrong build")
        lobby = p.decode_replay_initdata(arc.read_file("replay.initData"))["m_syncLobbyState"]
        handles = lobby["m_gameDescription"]["m_cacheHandles"]
        details = p.decode_replay_details(arc.read_file("replay.details"))["m_cacheHandles"]
        if not handles or handles != details or handles[-1][:4] != b"s2ma" or handles[-1][8:].hex() != MAPS[build]:
            raise ValueError("Wrong map")
        teams = {n: slot["m_teamId"] + 1 for n, slot in enumerate(lobby["m_lobbyState"]["m_slots"], 1)
                 if slot.get("m_hero") and slot["m_teamId"] in (0, 1)}
        tracker = arc.read_file("replay.tracker.events")
        events = list(p.decode_replay_tracker_events(tracker))
        game = arc.read_file("replay.game.events")
    if sum(e["_bits"] for e in events) != len(tracker) * 8:
        raise ValueError("Incomplete tracker")
    cycles = vehicle_cycles(events, pos, teams, h["m_elapsedGameLoops"])
    owners = activation_owners(cycles, events, build)
    if owners["different"]:
        raise ValueError("Pilot/upkeep rule differs from observed ownership")
    raw, physical_bytes = native_pilot_frames(cycles, events, tracker, build)
    tags = {c.tag: c for c in cycles}
    pings = Counter()
    bits = 0
    for event in p.decode_replay_game_events(game):
        bits += event["_bits"]
        if event["_eventid"] != PING or not event["m_unit"]:
            continue
        key = components(event["m_unit"], 18 if build == 41810 else 22)
        if key in tags:
            cycle, tick = tags[key], event["_gameloop"]
            if not cycle.active_at(tick):
                pings["at_boundary_or_outside"] += 1
                continue
            if rebind_vehicle(cycle, cycles, tick) != key:
                raise ValueError("Objective generation mismatch")
            pings["before_activation" if cycle.activated is None or tick < cycle.activated else "piloted"] += 1
    if bits != len(game) * 8:
        raise ValueError("Incomplete game stream")
    if retained_output is not None:
        if build != 41810:
            raise ValueError("Historical retained-tracker projection required")
        with TemporaryDirectory(dir=retained_output.parent) as temp:
            staged = Path(temp) / "frames"
            staged.write_bytes(raw)
            os.link(staged, retained_output)
    return dict(build=build, sha256=digest, cycles=len(cycles), timed_respawns=len(cycles)-1,
                activation_owner_matches=sum(c.activated is not None for c in cycles), vehicle_pings=dict(pings),
                pilot_and_upkeep=owners, native_physical_activation_bytes=physical_bytes,
                sparse_target_owner_sha256=sha256(raw).hexdigest(), sparse_target_owner_bytes=len(raw))


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--mechanics", type=Path, required=True)
    cli.add_argument("--header", type=Path, required=True)
    cli.add_argument("--retained-owner-output", type=Path)
    cli.add_argument("--case", action="append", required=True, nargs=4, metavar=("REPLAY", "SHA256", "BUILD", "MAP"))
    args = cli.parse_args()
    timer = timer_evidence(args.mechanics, args.header)
    if len({h for _, h, _, _ in args.case}) != len(args.case):
        raise ValueError("Repeated replay")
    if args.retained_owner_output is not None and len(args.case) != 1:
        cli.error("Writing a sparse projection requires exactly one historical case")
    rows = [inspect(Path(p), h, int(b), Path(m), args.retained_owner_output) for p, h, b, m in args.case]
    print(json.dumps(dict(timer=timer, cases=rows), indent=2))
