"""Recover tracker identities for map-authored startup units from a replay and its map."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import math
from pathlib import Path
from xml.etree import ElementTree

from encoders import encode_tracker_events
from mpq_reader import MPQArchive
from protocol_loader import load_protocol

SCHEMAS = {41810: 41810, 98348: 96477}
BIRTH = "NNet.Replay.Tracker.SUnitBornEvent"


@dataclass(frozen=True)
class Placement:
    object_id: int
    unit_type: str
    x: Decimal
    y: Decimal


@dataclass(frozen=True)
class StartupAnchor:
    object_id: int
    unit_type: str
    authored_x: str
    authored_y: str
    tracker_x: int
    tracker_y: int
    index: int
    recycle: int
    event_offset: (
        int  # Ordinal in the full decoded tracker stream, including non-birth events.
    )


def parse_objects(xml: bytes) -> list[Placement]:
    """Parse direct ObjectUnit children and sort by numeric author ID."""
    root = ElementTree.fromstring(xml)
    if root.tag != "PlacedObjects":
        raise ValueError("Expected a PlacedObjects map member")
    rows = []
    for node in root.findall("ObjectUnit"):
        try:
            x, y, z = map(Decimal, node.attrib["Position"].split(","))
            row = Placement(int(node.attrib["Id"]), node.attrib["UnitType"], x, y)
        except (KeyError, ValueError, InvalidOperation) as error:
            raise ValueError("Invalid ObjectUnit Id, UnitType or Position") from error
        if (
            not row.unit_type
            or row.object_id < 0
            or not all(v.is_finite() for v in (x, y, z))
        ):
            raise ValueError("Invalid ObjectUnit Id, UnitType or Position")
        rows.append(row)
    if len({r.object_id for r in rows}) != len(rows):
        raise ValueError("Duplicate ObjectUnit Id")
    return sorted(rows, key=lambda row: row.object_id)


def predict_startup(
    rows: list[Placement], events: list[dict]
) -> tuple[list[StartupAnchor], dict]:
    """Predict tags from type and position. Input events may omit both tag fields.

    Require mutual uniqueness in the rectangle of possible integer coordinates before
    checking the projection. An unpaired row still contributes to later author-ID ranks.
    """
    if any(rows[i - 1].object_id >= rows[i].object_id for i in range(1, len(rows))):
        raise ValueError("Expected unique placements sorted by numeric author Id")
    births = [
        (n, e)
        for n, e in enumerate(events)
        if e["_gameloop"] == 0 and e["_event"] == BIRTH
    ]
    locations = defaultdict(list)
    for offset, event in births:
        key = (event["m_unitTypeName"].decode("utf-8"), event["m_x"], event["m_y"])
        if type(key[1]) is not int or type(key[2]) is not int:
            raise ValueError("Expected integer birth coordinates")
        locations[key].append(offset)

    # A birth inside two candidate rectangles is ambiguous even if either has no other birth.
    candidates = []
    for row in rows:
        nearby = []
        for x in {math.floor(row.x), math.ceil(row.x)}:
            for y in {math.floor(row.y), math.ceil(row.y)}:
                nearby.extend(locations.get((row.unit_type, x, y), ()))
        candidates.append(nearby)
    usage = Counter(n for nearby in candidates for n in nearby)
    excluded = Counter()
    anchors = []
    for index, (row, nearby) in enumerate(zip(rows, candidates)):
        if min(row.x, row.y) < 0:
            excluded["unsupported_negative_coordinate"] += 1
            continue
        if not nearby:
            excluded["missing_birth"] += 1
            continue
        if len(nearby) != 1 or usage[nearby[0]] != 1:
            excluded["ambiguous_location"] += 1
            continue
        offset = nearby[0]
        event = events[offset]
        x, y = event["m_x"], event["m_y"]
        if (x, y) != (math.floor(row.x), math.floor(row.y)):
            excluded["coordinate_projection_disagrees"] += 1
            continue
        anchors.append(
            StartupAnchor(
                row.object_id,
                row.unit_type,
                str(row.x),
                str(row.y),
                x,
                y,
                index,
                1,
                offset,
            )
        )
    return anchors, dict(
        authored_units=len(rows),
        startup_births=len(births),
        spatial_predictions=len(anchors),
        excluded=dict(sorted(excluded.items())),
    )


def verify_startup(predictions, original_events, prediction_report, *, strict=True):
    """Compare frozen predictions to the revealed tags. Strict mode rejects contradictions."""
    recorded = {}
    for ordinal, event in enumerate(original_events):
        if event["_event"] == BIRTH and event["_gameloop"] == 0:
            tag = event["m_unitTagIndex"], event["m_unitTagRecycle"]
            if any(type(v) is not int for v in tag):
                raise ValueError("Expected integer tracker tag components")
            recorded[ordinal] = tag
    frequency = Counter(recorded.values())
    excluded = Counter(prediction_report["excluded"])
    accepted = []
    for anchor in predictions:
        actual = recorded[anchor.event_offset]
        if frequency[actual] != 1:
            excluded["repeated_startup_tag"] += 1
        elif actual != (anchor.index, anchor.recycle):
            excluded["index_or_recycle_disagrees"] += 1
        else:
            accepted.append(anchor)
    contradictions = {
        k: excluded[k]
        for k in (
            "coordinate_projection_disagrees",
            "repeated_startup_tag",
            "index_or_recycle_disagrees",
        )
        if excluded[k]
    }
    if strict and contradictions:
        raise ValueError(f"Contradictory startup observations: {contradictions}")
    report = dict(
        prediction_report,
        verified=len(accepted),
        contradictions=contradictions,
        excluded=dict(sorted(excluded.items())),
        fractional_verified=sum(
            Decimal(a.authored_x) != a.tracker_x or Decimal(a.authored_y) != a.tracker_y
            for a in accepted
        ),
    )
    return accepted, report


def match_startup(rows, events, *, strict=True):
    predictions, report = predict_startup(rows, events)
    return verify_startup(predictions, events, report, strict=strict)


def reconstruct_startup(rows, events):
    """Mask both tag components at every startup birth before predicting and verifying.

    Restore only independently verified tags from predictions. Copy out-of-scope tags
    from the supplied tracker after predictions are fixed; count these explicitly.
    """
    masked = list(events)
    birth_offsets = [
        n for n, e in enumerate(events) if e["_event"] == BIRTH and e["_gameloop"] == 0
    ]
    for n in birth_offsets:
        masked[n] = {
            k: v
            for k, v in events[n].items()
            if k not in ("m_unitTagIndex", "m_unitTagRecycle")
        }
    predictions, before = predict_startup(rows, masked)
    anchors, report = verify_startup(predictions, events, before)
    restored = {a.event_offset: (a.index, a.recycle) for a in anchors}
    for n in birth_offsets:
        if n in restored:
            tag = restored[n]
        else:
            tag = events[n]["m_unitTagIndex"], events[n]["m_unitTagRecycle"]
        masked[n]["m_unitTagIndex"], masked[n]["m_unitTagRecycle"] = tag
    report.update(
        masked_birth_tags=len(birth_offsets),
        tags_restored_from_map_predictions=len(restored),
        unmatched_tags_restored_from_original=len(birth_offsets) - len(restored),
    )
    return masked, anchors, report


def inspect_replay(
    map_path: Path, replay_path: Path, build: int
) -> tuple[list[StartupAnchor], dict]:
    """Read verified layout and replay identity from the two supplied physical archives."""
    if build not in SCHEMAS:
        raise ValueError("Unsupported physical replay build")
    protocol = load_protocol(SCHEMAS[build])
    map_hash = sha256(map_path.read_bytes()).digest()
    with closing(MPQArchive(map_path)) as archive:
        xml = archive.read_file("Objects")
    with closing(MPQArchive(replay_path)) as archive:
        header = protocol.decode_replay_header(
            archive.header["user_data_header"]["content"]
        )
        if (
            header["m_version"]["m_build"],
            header["m_version"]["m_baseBuild"],
            header["m_dataBuildNum"],
        ) != (build,) * 3:
            raise ValueError("Replay build differs from selected physical build")
        details = protocol.decode_replay_details(archive.read_file("replay.details"))
        init = protocol.decode_replay_initdata(archive.read_file("replay.initData"))
        deps = details["m_cacheHandles"]
        if (
            not deps
            or deps != init["m_syncLobbyState"]["m_gameDescription"]["m_cacheHandles"]
            or len(deps[-1]) != 40
            or deps[-1][:4] != b"s2ma"
            or deps[-1][8:] != map_hash
        ):
            raise ValueError(
                "Map SHA-256 differs from replay dependency or dependency lists disagree"
            )
        wire = archive.read_file("replay.tracker.events")
    events = list(protocol.decode_replay_tracker_events(wire))
    reconstructed, anchors, report = reconstruct_startup(parse_objects(xml), events)
    if encode_tracker_events(reconstructed, protocol) != wire:
        raise ValueError("Full reconstructed tracker differs from original bytes")
    report.update(
        build=build,
        schema_build=SCHEMAS[build],
        map_sha256=map_hash.hex(),
        replay_sha256=sha256(replay_path.read_bytes()).hexdigest(),
        objects_sha256=sha256(xml).hexdigest(),
        tracker_sha256=sha256(wire).hexdigest(),
        tracker_bytes=len(wire),
        reconstructed_tracker_byte_equal=True,
    )
    return anchors, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map", type=Path)
    parser.add_argument("replay", type=Path)
    parser.add_argument("--build", type=int, choices=sorted(SCHEMAS), required=True)
    parser.add_argument(
        "--anchors", action="store_true", help="include verified per-object identities"
    )
    args = parser.parse_args()
    try:
        anchors, report = inspect_replay(args.map, args.replay, args.build)
    except (OSError, ValueError, ElementTree.ParseError) as error:
        parser.error(str(error))
    if args.anchors:
        report["anchors"] = [asdict(a) for a in anchors]
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
