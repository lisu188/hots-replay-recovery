"""Project source command XY from the 41810-layout HistoricalTalentRules package."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from xml.etree import ElementTree

from command_authored_xy import analyze, fixed, get_target
from map_startup_identity import parse_objects
from migrate_replay import decode_events, encode_events
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from project_layout_xy import MAPS, SOURCE
from protocol_loader import load_protocol

HISTORICAL_PACKAGE = "662a90d5ea72c8454d66a1070b3200e6a2929f3d2069e2c07ecc07cfcc79b800"


def layout(path, digest):
    if sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("Unexpected map archive SHA-256")
    with closing(MPQArchive(path)) as archive:
        return read_member(archive, "Objects")


def placements(xml):
    authored = parse_objects(xml)
    owners = {
        int(n.attrib["Id"]): n.get("Player") for n in ElementTree.fromstring(xml).findall("ObjectUnit")
    }
    return {a.object_id: (a.unit_type, owners[a.object_id], (fixed(a.x), fixed(a.y))) for a in authored}


def match_package_row(row, original, package):
    """Return exact package coordinates only for identical placed objects and verified source commands."""
    object_id = row["object_id"]
    source = original.get(object_id)
    candidate = package.get(object_id)
    if source is None or candidate is None or source != candidate:
        raise ValueError("Missing or changed authored building in historical package")
    unit_type, _, xy = candidate
    if unit_type != row["type"] or None in xy or xy != tuple(row["xy"]):
        raise ValueError("Source command and historical authored position differ")
    return xy


def profile(original_map, package_map, source_replay, stock_map=None, rows=False):
    original_xml = layout(original_map, MAPS[41810])
    package_xml = layout(package_map, HISTORICAL_PACKAGE)
    if package_xml != original_xml:
        raise ValueError("Historical package changed the complete Objects member")
    original, package = placements(original_xml), placements(package_xml)
    stock = placements(layout(stock_map, MAPS[98348])) if stock_map is not None else None
    source = analyze(original_map, source_replay, 41810, observations=True)
    if (
        source["replay_sha256"] != SOURCE
        or not source["full_game_byte_equal"]
        or source["counts"].get("mismatches", 0)
    ):
        raise ValueError("Expected the exact independently reproduced original game stream")
    with closing(MPQArchive(source_replay)) as archive:
        wire = archive.read_file("replay.game.events")
    protocol = load_protocol(41810)
    events = list(decode_events(wire, protocol, "game"))
    stock_counts = Counter()
    moved_ids = set()
    evidence = []
    for row in source["projected_rows"]:
        xy = match_package_row(row, original, package)
        ident = row["object_id"]
        event = events[row["ordinal"]]
        target = get_target(event)
        if target is None or event["_gameloop"] != row["loop"]:
            raise ValueError("Command target or loop differs from source evidence")
        point = target["m_snapshotPoint"]
        if (point["x"], point["y"]) != xy:
            raise ValueError("Original snapshot differs from package-derived coordinates")
        point["x"], point["y"] = xy
        evidence.append([row["ordinal"], row["loop"], ident, xy[0], xy[1]])
        if stock is not None:
            equivalent = stock.get(ident)
            if equivalent is None or equivalent[:2] != original[ident][:2] or None in equivalent[2]:
                stock_counts["no_matching_id_type_owner_exact_xy"] += 1
            elif equivalent[2] == xy:
                stock_counts["same_xy"] += 1
            else:
                stock_counts["different_xy"] += 1
                moved_ids.add(ident)
    rebuilt = encode_events(events, protocol, "game")
    if rebuilt != wire:
        raise ValueError("Package-coordinate reconstruction changed the complete source game member")
    output = dict(
        format="historical-layout-building-command-xy-v1",
        source_sha256=SOURCE,
        original_map_sha256=MAPS[41810],
        package_sha256=HISTORICAL_PACKAGE,
        objects_bytes=len(package_xml),
        objects_sha256=sha256(package_xml).hexdigest(),
        all_objects_identical=True,
        authored_unit_count=len(package),
        source_target_commands=source["counts"]["target_commands"],
        projected_source_commands=len(evidence),
        fractional_commands=source["counts"]["fractional"],
        distinct_addressed_structures=len({row[2] for row in evidence}),
        xy_changes=0,
        row_columns=["game_ordinal", "loop", "object_id", "x", "y"],
        compact_rows_json_sha256=sha256(
            json.dumps(evidence, separators=(",", ":")).encode("ascii")
        ).hexdigest(),
        game_member_bytes=len(wire),
        game_member_sha256=sha256(wire).hexdigest(),
        reconstructed_source_game_byte_equal=True,
        source_mobile_counterexample=next(
            (s for s in source["other_authored_disagreements"] if s["type"] == "VehicleDragon"), None
        ),
        source_other_authored_position_disagreements=source["counts"]["other_authored_type_xy_differences"],
        converted_match_target_lifetimes_verified=False,
        native_playback_verified=False,
    )
    if stock is not None:
        output.update(
            stock_reference_sha256=MAPS[98348],
            stock_layout_comparison=dict(stock_counts),
            moved_stock_structures=len(moved_ids),
        )
    if rows:
        output["rows"] = evidence
    return output


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("original-map", "historical-map", "source-replay"):
        cli.add_argument("--" + name, type=Path, required=True)
    cli.add_argument(
        "--stock-map", type=Path, help="Compare the same editor IDs against stock 98348 Dragon Shire."
    )
    cli.add_argument(
        "--rows", action="store_true", help="Include each retained command ordinal and package-derived X/Y."
    )
    args = cli.parse_args()
    print(
        json.dumps(
            profile(args.original_map, args.historical_map, args.source_replay, args.stock_map, args.rows),
            indent=2,
        )
    )
