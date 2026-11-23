"""Compare Dragon Shire map predictions with opening birth records and stationary command snapshots."""

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing
import json
from pathlib import Path
from xml.etree import ElementTree

import first_sync_game
from command_authored_xy import BUILDINGS, fixed, get_target
from command_snapshot_owners import OwnerHistory
from dragon_startup_births import indexed, predict, xy
from first_sync_game import game
from hero_revive_wire import GATE_MAP, STOCK
from map_startup_identity import parse_objects
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from opening_birth_wire import FIELDS, model
from placement_xy import fixed_coordinate
from predict_camp_captures import SOURCE
from project_rank_targets import MAP, lifetime_ends
from repair_unit_tags import components, pack
from unit_spatial_descriptor import position_fields


def positions(objects, regions, script, mechanics):
    authored = parse_objects(objects)
    _, details = predict(objects, regions, script, mechanics.read_bytes())
    points = indexed(ElementTree.fromstring(objects), "ObjectPoint", "Id")
    rows = [(p.object_id, p.unit_type, p.x, p.y) for p in authored]
    for camp in details["camps"]:
        point = xy(points[camp["captain_point_id"]])
        rows.append((None, "TownMercCampCaptureBeacon", *point))
        if camp["sconce_object_id"] is not None:
            rows.append((None, "JungleCampIconUnitTeamColor", *point))
    for name in ("DragonShireShrineSun", "DragonShireShrineMoon"):
        shrine, = [r for r in authored if r.unit_type == name]
        rows.append((None, "DragonballCaptureBeacon", shrine.x, shrine.y))
    return rows


def measure(replay, digest, build, package, mechanics):
    proto, game_data = game(replay, digest, build)
    with closing(MPQArchive(replay)) as archive:
        recorded_map = proto.decode_replay_details(archive.read_file("replay.details"))["m_cacheHandles"][-1][8:].hex()
        if recorded_map != MAP[build]:
            if build == 98348:
                return {"map_excluded": True}, []
            raise ValueError("Unexpected TEN map")
        tracker = list(proto.decode_replay_tracker_events(archive.read_file("replay.tracker.events")))
    with closing(MPQArchive(package)) as archive:
        placements = positions(*(read_member(archive,k) for k in ("Objects","Regions","MapScript.galaxy")), mechanics)
    placed, _, map_sha = model(replay, build, proto, package, mechanics)
    if map_sha != (GATE_MAP if build == 41810 else STOCK):
        raise ValueError("Unexpected historical or stock map package")
    births = [r for r in tracker if r["_gameloop"] == 0 and r["_eventid"] == 1]
    if [tuple(p[k] for k in FIELDS) for p in placed] != [tuple(b[k] for k in FIELDS) for b in births]:
        raise ValueError("Opening tag, owner, position or type diverged from the map model")
    entries = {}
    exact_xml_pairs = rounded_pairs = 0
    for (obj, kind, authored_x, authored_y), born in zip(placements, placed, strict=True):
        x, y = fixed(authored_x), fixed(authored_y)
        if x is not None and y is not None:
            exact_xml_pairs += 1
        elif obj is not None:
            x, y = fixed_coordinate(authored_x), fixed_coordinate(authored_y)
            rounded_pairs += 1
        key = born["m_unitTagIndex"], born["m_unitTagRecycle"]
        owner = born["m_controlPlayerId"]
        if min(authored_x, authored_y) < 0 or (born["m_unitTypeName"].decode(), born["m_x"], born["m_y"]) != (
                kind, int(authored_x), int(authored_y)):
            raise ValueError("Object and modeled tracker birth disagree")
        # The parsed ObjectUnit path is verified. Keep fractional ObjectPoint values masked
        # unless they have exact representations or their own native reader is verified.
        if ((x is not None and x // 4096 != born["m_x"])
                or (y is not None and y // 4096 != born["m_y"])):
            raise ValueError("Parsed fixed position and independently observed birth cell differ")
        fields = position_fields(pack(*key, 22), owner, x if x is not None else born["m_x"]*4096,
                                 y if y is not None else born["m_y"]*4096)
        mask = 0xffffff
        if x is None:
            mask &= ~(3 << 18)
        if y is None:
            mask &= ~(3 << 21)
        entries[key] = dict(object_id=obj, unit=kind, index=key[0], generation=key[1],
                            owner=owner, x=x, y=y, low24=fields[0] & mask, low24_mask=mask,
                            cell_x=fields[1], cell_y=fields[2])
    ends, owners = lifetime_ends(tracker, entries), OwnerHistory(tracker)
    shift = 18 if build == 41810 else 22
    counts, observations = Counter(), defaultdict(Counter)
    for event in proto.decode_replay_game_events(game_data):
        target = get_target(event)
        if not target:
            continue
        tag = target["m_tag"]
        key = components(tag, shift)
        row = entries.get(key)
        tick = event["_gameloop"]
        if (not row or row["unit"] not in BUILDINGS or row["low24_mask"] != 0xffffff
                or not 0 < tick < ends.get(key, float("inf"))):
            continue
        pair, reason = owners.lookup(tag, tick, shift)
        if reason != "alive" or not pair or pair[0] != row["owner"]:
            continue
        point = target["m_snapshotPoint"]
        matched_xy = (point["x"], point["y"]) == (row["x"], row["y"])
        counts["stationary_xy_match" if matched_xy else "stationary_xy_mismatch"] += 1
        observed_owner = target.get("m_snapshotControlPlayerId")
        if observed_owner is None:
            continue
        # Compute the bits directly from bytes carried by the command, independently of position_fields.
        x, y = point["x"], point["y"]
        low = (tag >> shift) | ((observed_owner & 15) << 14) | (((x & 7168) >> 10) << 18) | (((y & 7168) >> 10) << 21)
        agrees = matched_xy and (low, x//8192, y//8192) == (row["low24"], row["cell_x"], row["cell_y"])
        observations[key]["match" if agrees else "mismatch"] += 1
    for key, c in observations.items():
        counts.update({f"owner_xy_{k}": v for k,v in c.items()})
        entries[key]["snapshot_matches"] = c["match"]
        entries[key]["snapshot_mismatches"] = c["mismatch"]
    confirmed = sum(c["match"] > 0 and c["mismatch"] == 0 for c in observations.values())
    return dict(build=build, map_sha256=map_sha, authored=sum(obj is not None for obj, *_ in placements),
                exact_fixed_xy=exact_xml_pairs, native_rounded_xy=rounded_pairs,
                resolved_fixed_xy=sum(r["low24_mask"] == 0xffffff for r in entries.values()), map_and_birth_agree=len(placed),
                corroborated_stationary_objects=confirmed, **counts), list(entries.values())


def measure_control(args):
    return measure(*args)[0]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("source", "gate_map", "mechanics", "control_manifest", "stock_map"):
        parser.add_argument(field,type=Path)
    parser.add_argument("--private-ledger",type=Path)
    parser.add_argument("--jobs",type=int,default=3)
    args = parser.parse_args()
    source, ledger = measure(args.source, SOURCE, 41810, args.gate_map, args.mechanics)
    paths = json.loads(args.control_manifest.read_bytes())
    refs = Path(first_sync_game.__file__).parent / "observations/first-sync-game.json"
    if set(paths) != {r["replay_sha256"] for r in json.loads(refs.read_bytes())["references"]} or len(paths) != 24:
        raise ValueError("Wrong build-98348 control set")
    with ProcessPoolExecutor(args.jobs) as pool:
        results = list(pool.map(measure_control, ((Path(path), key, 98348, args.stock_map, args.mechanics)
                                                  for key, path in sorted(paths.items()))))
    stock = [r for r in results if not r.get("map_excluded")]
    if len(stock) != 15:
        raise ValueError("Expected fifteen Dragon Shire controls")
    if args.private_ledger:
        with args.private_ledger.open("x",encoding="utf8") as stream:
            json.dump(ledger,stream,separators=(",",":"))
    total = Counter()
    for observation in stock:
        total.update({k:v for k,v in observation.items() if k not in ("build","map_sha256")})
    print(json.dumps(dict(ten=source, native_recordings=len(stock), native_totals=total,
                          descriptor_bits_from_tag_owner_and_xy=56, game_crc_verified=False),indent=2))
