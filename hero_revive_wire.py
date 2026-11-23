"""Build target tracker revival frames from the original map, lobby and ordinary hero timers."""

import argparse
from collections import Counter
from contextlib import closing
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from
from xml.etree import ElementTree

from camp_owner_wire import read_tracker, STOCK, STOCK_PACKAGE, TARGET_SCHEMA_SHA
from encoders import encode_tracker_events
from hero_camera_lifetimes import core_horizon, independent_histories, lobby_predictions, recorded_histories, timers
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from predict_camp_captures import SOURCE
from protocol_loader import load_protocol


HIST_MAP = "d41c5841a5719e76246265940d28b244bae91f4e3fef33e621f3a2e2a0ee7bbd"
WAVE_MAP = "f4d3b425cd9df5ed5390c45dc3c770300a64ba95449c82c228eed8b9928c7d6f"
TIMER_EVIDENCE = "d3155fc0d75ad42b35b11ab1cc977e8c6b155b9e2733b364b5eb1693edff356b"
MEMBERS = {
    41810: ("ce391782dbafe292da064b6c33963f43e99d479551d14a67bf1a4ade12953d1b",
            "5b1f268a147bc854a1d0321826f9e055f45aa690cb970f0e703c5e8cf01476a9", 433),
    98348: ("63183ab3a92963966f07af2a04789e55ff9b68a1a68e5aa71181700edba95572",
            "371d4c7a1ade868b4106d50926a47d50bb2b042a4558a66dab938c06f3cd7ecc", 427),
}
HEROES = {b"Hero" + h for h in (b"Abathur", b"Anubarak", b"Barbarian", b"FaerieDragon",
                                  b"Greymane", b"Kaelthas", b"Nova", b"Tyrande")}
REVIVED = "NNet.Replay.Tracker.SUnitRevivedEvent"
FIELDS = ("m_unitTagIndex", "m_unitTagRecycle", "m_x", "m_y")


def starts(path, build):
    digest = sha256(path.read_bytes()).hexdigest()
    if digest not in ({HIST_MAP, WAVE_MAP} if build == 41810 else {STOCK, STOCK_PACKAGE}):
        raise ValueError("Unexpected map package")
    with closing(MPQArchive(path)) as arc:
        info, xml = (read_member(arc, k) for k in ("MapInfo", "Objects"))
    info_sha, obj_sha, offset = MEMBERS[build]
    if sha256(info).hexdigest() != info_sha or sha256(xml).hexdigest() != obj_sha:
        raise ValueError("Unexpected map player records or Objects")
    points = {}
    for p in ElementTree.fromstring(xml).findall("./ObjectPoint[@Type='StartLoc']"):
        x, y, _ = (Decimal(t) for t in p.attrib["Position"].split(","))
        if min(x,y) < 0 or max(x,y) > 255 or int(p.attrib["Id"]) in points:
            raise ValueError("Invalid start point")
        points[int(p.attrib["Id"])] = int(x), int(y)
    count, = unpack_from("<I", info, offset)
    if count != 14:
        raise ValueError("MapInfo player count")
    offset += 4
    locations = {}
    for _ in range(count):
        player, control, _color = unpack_from("<BII", info, offset)
        offset = info.index(b"\0", offset + 9) + 1
        _, point_id, _ai = unpack_from("<III", info, offset)
        offset = info.index(b"\0", offset + 12) + 1
        if control == 1:
            if player in locations or point_id not in points:
                raise ValueError("Ambiguous player start")
            locations[player] = points[point_id]
    if set(locations) != set(range(1, 11)) or set(locations.values()) != set(points.values()) or len(set(points.values())) != 10:
        raise ValueError("Incomplete player starts")
    return locations, digest


def team_slots(path, protocol):
    with closing(MPQArchive(path)) as arc:
        slots = protocol.decode_replay_initdata(arc.read_file("replay.initData"))["m_syncLobbyState"]["m_lobbyState"]["m_slots"]
    result = {}
    for team in (0, 1):
        selected = [i for i,s in enumerate(slots,1) if s.get("m_hero") and s["m_teamId"] == team]
        if len(selected) != 5:
            return {}
        result.update((p, i + 1 + 5 * team) for i,p in enumerate(selected))
    return result


def target_protocol():
    p = load_protocol(96477)
    tid, name = p.tracker_event_types[12]
    if p.recovery_schema_sha256 != TARGET_SCHEMA_SHA or name != REVIVED or tuple(f[0] for f in p.typeinfos[tid][1][0]) != FIELDS:
        raise ValueError("Unexpected revive structure")
    return p


def values(e):
    return e["_gameloop"], *(e[k] for k in FIELDS)


def as_event(v):
    return dict(_eventid=12, _event=REVIVED, _gameloop=v[0], **dict(zip(FIELDS,v[1:])))


def analyze(path, digest, build, map_path, curve):
    if sha256(path.read_bytes()).hexdigest() != digest or (build == 41810 and digest != SOURCE):
        raise ValueError("Unexpected source replay")
    points, map_sha = starts(map_path, build)
    p, raw, end = read_tracker(path, build)
    tracker = list(p.decode_replay_tracker_events(raw))
    slots = team_slots(path,p)
    cutoff = core_horizon(tracker, end)
    model = independent_histories(lobby_predictions(path,build), tracker, curve, cutoff)
    projected = sorted((tick,*pair,*points[slots[slot]]) for pair,(slot,unit,history) in model.items()
                       if unit in HEROES for tick,alive in history[1:] if alive)
    actual = [values(e) for e in tracker if e["_eventid"] == 12]
    selected = Counter(projected)
    physical = Counter(actual)
    counts = dict(total_native_revives=len(actual), predicted_ordinary_revives=len(projected),
                  exact_predicted=sum((physical & selected).values()), native_insertion_bytes=0,
                  qualified_insertion_bytes=0)
    observed = recorded_histories(tracker)
    coords = {pair:points[slots[slot]] for pair,(slot,unit,_) in observed.items()
              if slot in slots and unit in HEROES}
    counts["registered_ordinary_revival_coordinates"] = sum(v[1:3] in coords for v in actual)
    counts["matched_registered_ordinary_revival_coordinates"] = sum(coords.get(v[1:3]) == v[3:5] for v in actual)
    target = target_protocol()
    position, prior = 0, 0
    for e in tracker:
        length, bits = divmod(e["_bits"],8)
        if bits:
            raise ValueError("Partial physical tracker frame")
        if build == 98348 and e["_eventid"] == 12:
            v = values(e)
            frame = encode_tracker_events([as_event((v[0]-prior, *v[1:]))],target)
            if frame != raw[position:position+length]:
                raise ValueError("Physical frame differs")
            counts["native_insertion_bytes"] += length
            if v in selected:
                counts["qualified_insertion_bytes"] += length
        prior, position = e["_gameloop"], position+length
    if position != len(raw):
        raise ValueError("Incomplete tracker")
    sparse = None
    if build == 41810:
        if not projected or projected != actual or len({v[0] for v in projected}) != len(projected):
            raise ValueError("TEN revival projection or ordering mismatch")
        sparse = encode_tracker_events([as_event(v) for v in projected],target)
        decoded = list(target.decode_replay_tracker_events(sparse))
        if [values(e) for e in decoded] != projected or any(e["_eventid"] != 12 for e in decoded) or sum(e["_bits"] for e in decoded) != len(sparse)*8:
            raise ValueError("Incomplete target encoding")
        counts.update(sparse_bytes=len(sparse),sparse_sha256=sha256(sparse).hexdigest())
    return dict(build=build, replay_sha256=digest, map_sha256=map_sha, **counts), sparse


def source_curve(path):
    data = path.read_bytes()
    if sha256(data).hexdigest() != TIMER_EVIDENCE:
        raise ValueError("Unknown original death timers")
    return {int(k): v for k,v in json.loads(data)["seconds_by_level"].items()}


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--map", required=True, type=Path)
    cli.add_argument("--case", required=True, nargs=3, metavar=("REPLAY","SHA256","BUILD"))
    cli.add_argument("--historical-timers", type=Path)
    cli.add_argument("--heroes-lib", type=Path)
    cli.add_argument("--game-lib", type=Path)
    cli.add_argument("--output", type=Path)
    args = cli.parse_args()
    file, digest, build = args.case
    build = int(build)
    if build not in MEMBERS:
        cli.error("Choose 41810 or 98348")
    if build == 41810 and not args.historical_timers:
        cli.error("Historical timer evidence required")
    if build == 98348 and (not args.heroes_lib or not args.game_lib or args.output):
        cli.error("Control mode needs both libraries and produces a report")
    curve = source_curve(args.historical_timers) if build == 41810 else timers(args.heroes_lib,args.game_lib)
    result, raw = analyze(Path(file),digest,build,args.map,curve)
    if args.output:
        with args.output.open("xb") as destination:
            destination.write(raw)
    print(json.dumps(result,indent=2))
