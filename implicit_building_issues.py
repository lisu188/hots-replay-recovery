"""Project ordinary TEN building-target issue frames on the pinned GateOrder package."""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
from xml.etree import ElementTree

from command_authored_xy import fixed
from command_snapshot_owners import OWNER_FIELDS, OwnerHistory
from encoders import encode_game_events as named_encode
from first_point_commands import FLAGS
from first_sync_game import game
from hero_camera_lifetimes import core_horizon
from hero_revive_wire import GATE_MAP, STOCK
from implicit_point_issues import check_schema, native
from map_startup_identity import parse_objects
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from native_game_events import encode_game_events, iter_game_events
from opening_birth_wire import FIELDS, model, target_protocol
from predict_camp_captures import SOURCE
from project_rank_targets import MAP, lifetime_ends
from repair_command_flags import delete_zero_bit
from repair_unit_tags import components, pack
from terrain_snapshot_height import SyncTerrain


CATALOG = "6250c950f81586fde8a255c83d7a03eabd75d0751ecde208877b1d4ed685d55e"
EXTRA = "4732077e899f6894c29586795a01e2a27fba622dbf22b5d29c7b30d57e3ce4fc"


def catalog(path):
    data = path.read_bytes().replace(b"\r\n", b"\n")
    if sha256(data).hexdigest() != CATALOG:
        raise ValueError("Unexpected building catalog observations")
    report = json.loads(data)
    links = {
        name: (r["original_links"][0], r["target_lead"])
        for name, r in report["groups"].items()
        if not r["blocks"] and len(r["original_links"]) == 1 and all(r["live_matching_witnesses_in_two"])
    }
    return links, {r["replay_sha256"] for r in report["controls"]}


def geometry(replay, build, protocol, package, mechanics, tracker, links):
    placed, _, digest = model(replay, build, protocol, package, mechanics)
    if digest != (GATE_MAP if build == 41810 else STOCK):
        raise ValueError("Unexpected package")
    with closing(MPQArchive(package)) as arc:
        objects = read_member(arc, "Objects")
        terrain = SyncTerrain(read_member(arc, "t3SyncHeightMap"))
    elevation = {
        int(u.attrib["Id"]): Decimal(u.attrib["Position"].split(",")[2])
        for u in ElementTree.fromstring(objects).findall("ObjectUnit")
    }
    # The native opening model allocates the authored map units in numeric object-ID order.
    observed = {components_key(e): e for e in tracker if e["_eventid"] == 1 and e["_gameloop"] == 0}
    anchors = {}
    for index, unit in enumerate(parse_objects(objects)):
        if unit.unit_type not in links:
            continue
        e = placed[index]
        key = components_key(e)
        if (key != (index, 1) or e["m_unitTypeName"].decode() != unit.unit_type or
                e["m_x"] != int(unit.x) or e["m_y"] != int(unit.y) or
                tuple(e[k] for k in FIELDS) != tuple(observed[key][k] for k in FIELDS)):
            raise ValueError("Map/pool startup disagrees with independent tracker observation")
        x, y = fixed(unit.x), fixed(unit.y)
        if x is None or y is None or elevation[unit.object_id]:
            continue
        z, remainder = terrain.sample(x, y)
        if not remainder:
            anchors[key] = (unit.unit_type, (x, y, z), (e["m_controlPlayerId"], e["m_upkeepPlayerId"]))
    return anchors


def components_key(e):
    return e["m_unitTagIndex"], e["m_unitTagRecycle"]


def town_lifetimes(anchors, tracker, ends, cutoff):
    halls = {v[1][:2]: k for k, v in anchors.items() if v[0] in ("TownTownHallL2", "TownTownHallL3")}
    town_ids, deaths = {}, {}
    for e in tracker:
        event = e.get("m_eventName")
        if event not in (b"TownStructureInit", b"TownStructureDeath") or e["_gameloop"] > cutoff:
            continue
        (town,) = [r["m_value"] for r in e["m_intData"] if r["m_key"] == b"TownID"]
        if event == b"TownStructureInit":
            xy = {r["m_key"]: r["m_value"] for r in e["m_fixedData"]}
            key = halls[xy[b"PositionX"], xy[b"PositionY"]]
            if e["_gameloop"] or town in town_ids or key in town_ids.values():
                raise ValueError("Ambiguous initial TownID/location")
            town_ids[town] = key
        else:
            key = town_ids[town]
            if key in deaths:
                raise ValueError("Repeated town death")
            deaths[key] = e["_gameloop"]
    hall_keys = set(halls.values())
    if set(town_ids.values()) != hall_keys or len(town_ids) != 12:
        raise ValueError("Incomplete town initialization")
    if deaths != {key: tick for key, tick in ends.items() if key in hall_keys and tick <= cutoff}:
        raise ValueError("TownID/death statistics disagree with physical unit lifetimes")
    return hall_keys, deaths


def scan(replay, digest, build, package, mechanics, catalog_path):
    if build not in (41810, 98348) or build == 41810 and digest != SOURCE:
        raise ValueError("Expected original TEN or a stock target recording")
    links, controls = catalog(catalog_path)
    if build == 98348 and digest not in controls | {EXTRA}:
        raise ValueError("Unexpected native control")
    p, raw = game(replay, digest, build)
    target = target_protocol()
    check_schema(p, build)
    tid = check_schema(target, 98348)
    if {delete_zero_bit(FLAGS[41810], bit) for bit in range(9, 16)} != {FLAGS[98348]}:
        raise ValueError("Ordinary issue flag mapping changed")
    with closing(MPQArchive(replay)) as arc:
        deps = p.decode_replay_details(arc.read_file("replay.details"))["m_cacheHandles"]
        if deps[-1][8:].hex() != MAP[build]:
            raise ValueError("Replay map dependency disagrees")
        tracker = list(p.decode_replay_tracker_events(arc.read_file("replay.tracker.events")))
    anchors = geometry(replay, build, p, package, mechanics, tracker, links)
    owners = OwnerHistory(tracker)
    ends = lifetime_ends(tracker, anchors)
    cutoff = core_horizon(tracker, tracker[-1]["_gameloop"])
    hall_keys, hall_deaths = town_lifetimes(anchors, tracker, ends, cutoff)
    shift = 18 if build == 41810 else 22
    projected, frames = {}, []
    other_flags, kinds, observed = Counter(), Counter(), Counter()
    offset = previous = sparse_previous = 0
    enclosing = bytearray()
    for ordinal, e in enumerate(p.decode_replay_game_events(raw)):
        tick = e["_gameloop"]
        size, rem = divmod(e["_bits"], 8)
        prior, start = previous, offset
        previous, offset = tick, offset + size
        if rem or not size or tick < prior or offset > len(raw):
            raise ValueError("Invalid enclosing event extent")
        if e["_eventid"] != 27 or e["m_abil"] is not None or set(e["m_data"]) != {"TargetUnit"}:
            continue
        observed["all_implicit_unit"] += 1
        if tick > cutoff or e["m_otherUnit"] is not None or e["m_unitGroup"] is not None:
            continue
        u = e["m_data"]["TargetUnit"]
        key = components(u["m_tag"], shift)
        if key not in anchors or not 0 < tick < ends.get(key, cutoff + 1):
            continue
        name, point, pair = anchors[key]
        if (u["m_snapshotPoint"]["x"], u["m_snapshotPoint"]["y"]) != point[:2]:
            continue
        known, reason = owners.lookup(u["m_tag"], tick, shift)
        if reason != "alive" or known != pair:
            continue
        observed["qualified_live_geometry_and_owners"] += 1
        other_flags[hex(e["m_cmdFlags"])] += 1
        if e["m_cmdFlags"] != FLAGS[build]:
            continue
        if e.get("m_vector") is not None:
            raise ValueError("Target-only vector is present on an ordinary building issue")
        # Build the snapshot without reading its flags, timer, either owner, link or height.
        # The selected source tag identifies the intended map object. Its target word
        # uses the opening model's allocated pair, cross-checked before scanning commands.
        tag = pack(*key, 22)
        before, after = links[name]
        snapshot = dict(m_targetUnitFlags=111, m_timer=0, m_tag=tag,
                        m_snapshotUnitLink=after, **dict(zip(OWNER_FIELDS, pair)),
                        m_snapshotPoint=dict(zip(("x", "y", "z"), point)))
        historical_or_native = {**snapshot, "m_snapshotUnitLink": before if build == 41810 else after,
                                "m_tag": pack(*key, shift)}
        if u != historical_or_native:
            raise ValueError("Independent map/catalog/owner snapshot differs from command")
        row = {**e, "m_cmdFlags": FLAGS[98348], "m_vector": None, "m_data": {"TargetUnit": snapshot}}
        # This is the original mandatory issue sequence. Selection/manager continuity
        # and stock-catalog equivalence of the custom target package remain conditions.
        if not 1 <= e["m_sequence"] <= 2**32:
            raise ValueError("Mandatory issue sequence out of range")
        physical = raw[start:offset]
        if named_encode([{**e, "_gameloop": tick - prior}], p) != physical:
            raise ValueError("Source enclosing issue did not reproduce")
        frame = native(row, tick - prior, target, tid)
        if build == 98348 and encode_game_events([frame]) != physical:
            raise ValueError("Generated complete issue disagrees with physical control")
        enclosing.extend(physical)
        frames.append(native(row, tick - sparse_previous, target, tid))
        sparse_previous = tick
        projected[ordinal] = row
        kinds[name] += 1
        if key in hall_keys:
            observed["issues_with_second_town_lifetime_witness"] += 1
    if offset != len(raw):
        raise ValueError("Incomplete traversal")
    data = encode_game_events(frames)
    if named_encode(list(projected.values()), target) != data or any(
        r.event != f for r, f in zip(iter_game_events(data), frames, strict=True)
    ):
        raise ValueError("Native/syntax bitstream mismatch")
    result = dict(replay_sha256=digest, build=build, measured=dict(observed),
                  independently_matched_town_deaths=len(hall_deaths),
                  qualifying_enclosing_bytes=len(enclosing), enclosing_sha256=sha256(enclosing).hexdigest(),
                  ordinary_issues=len(projected), by_unit=dict(sorted(kinds.items())),
                  all_flags_at_qualified_geometry=dict(sorted(other_flags.items())),
                  sparse_bytes=len(data), sparse_sha256=sha256(data).hexdigest(),
                  ordinal_sha256=sha256(json.dumps(list(projected), separators=(",", ":")).encode()).hexdigest())
    return projected, data, result


def generate(source, gate_map, mechanics, catalog_path):
    return scan(source, SOURCE, 41810, gate_map, mechanics, catalog_path)


def control(args):
    return scan(*args)[2]


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for a in ("source", "gate_map", "mechanics", "catalog"):
        cli.add_argument(a, type=Path)
    cli.add_argument("--native-controls", type=Path)
    cli.add_argument("--stock-map", type=Path)
    cli.add_argument("--private-output", type=Path)
    args = cli.parse_args()
    rows, data, result = generate(args.source, args.gate_map, args.mechanics, args.catalog)
    report = dict(source=result, custom_catalog_numeric_identity_verified=False,
                  target_selection_and_manager_continuity_verified=False,
                  target_building_survival_uses_source_tracker=True)
    if args.native_controls:
        if not args.stock_map:
            cli.error("Native controls require --stock-map")
        paths = json.loads(args.native_controls.read_bytes())
        _, keys = catalog(args.catalog)
        if len(keys) != 14 or EXTRA in keys or not keys | {EXTRA} <= paths.keys():
            raise ValueError("Incomplete native cohort")
        tasks = [(Path(paths[h]), h, 98348, args.stock_map, args.mechanics, args.catalog)
                 for h in sorted(keys | {EXTRA})]
        with ProcessPoolExecutor(3) as pool:
            refs = list(pool.map(control, tasks))
        report["controls"] = refs
        report["enclosing_native_frames_equal"] = sum(r["ordinary_issues"] for r in refs)
        report["enclosing_native_bytes_equal"] = sum(r["qualifying_enclosing_bytes"] for r in refs)
        report["catalog_held_out"] = next(r for r in refs if r["replay_sha256"] == EXTRA)
    if args.private_output:
        with args.private_output.open("xb") as f:
            f.write(data)
    print(json.dumps(report, indent=2))
