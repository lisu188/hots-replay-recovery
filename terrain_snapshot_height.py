"""Recover Dragon Shire building-target Z from the simulation height grid and map-authored X/Y."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
from decimal import Decimal

from command_authored_xy import analyze, get_target
from map_startup_identity import SCHEMAS
from migrate_replay import decode_events, encode_events
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from protocol_loader import load_protocol

Q = 4096


class SyncTerrain:
    def __init__(self, raw):
        if len(raw) < 64 or raw[:4] != b"SMAP":
            raise ValueError("Expected a complete SMAP header")
        version, self.width, self.height = struct.unpack_from("<III", raw, 4)
        metadata = struct.unpack_from("<12I", raw, 16)
        if version != 102 or metadata != (0, 0, 0, Q, Q, Q, 0, 0, 0, 0, 0, 0):
            raise ValueError("Unsupported Dragon Shire terrain metadata")
        if min(self.width, self.height) < 2 or len(raw) != 64 + 4 * self.width * self.height:
            raise ValueError("Invalid SMAP dimensions or length")
        self.raw = raw

    def sample(self, x, y):
        """Return exact Q12 terrain height; expose rounding or unsupported positions explicitly."""
        if type(x) is not int or type(y) is not int:
            raise ValueError("Expected integer fixed-point coordinates")
        x0, fx = divmod(x, Q)
        y0, fy = divmod(y, Q)
        if not (0 <= x0 < self.width - 1 and 0 <= y0 < self.height - 1):
            raise ValueError("Coordinates outside supported terrain cells")
        heights = []
        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
            offset = 64 + 4 * ((y0 + dy) * self.width + x0 + dx)
            (low,) = struct.unpack_from("<H", self.raw, offset)
            if low >= 0x8000:
                raise ValueError("Unverified sign of terrain height")
            heights.append(16 * low)
        a, b, c, d = heights
        numerator = (Q - fy) * ((Q - fx) * a + fx * b) + fy * ((Q - fx) * c + fx * d)
        z, remainder = divmod(numerator, Q * Q)
        return z, remainder


def check_height(map_path, replay_path, build, overlay=None):
    xy = analyze(map_path, replay_path, build, observations=True)
    if not xy["full_game_byte_equal"] or xy["counts"].get("mismatches", 0):
        raise ValueError("Unverified building command coordinates")
    with closing(MPQArchive(map_path)) as arc:
        terrain = read_member(arc, "t3SyncHeightMap")
        objects = read_member(arc, "Objects")
    if overlay is not None:
        with closing(MPQArchive(overlay)) as arc:
            if terrain != read_member(arc, "t3SyncHeightMap") or objects != read_member(arc, "Objects"):
                raise ValueError("Package terrain or placements differ from replay map")
    heights = {
        int(o.attrib["Id"]): Decimal(o.attrib["Position"].split(",")[2])
        for o in ET.fromstring(objects).findall("ObjectUnit")
    }
    grid = SyncTerrain(terrain)
    protocol = load_protocol(SCHEMAS[build])
    with closing(MPQArchive(replay_path)) as arc:
        game = arc.read_file("replay.game.events")
    events = list(decode_events(game, protocol, "game"))
    counts = Counter()
    z_values = set()
    for row in xy["projected_rows"]:
        if heights[row["object_id"]] != 0:
            raise ValueError("Nonzero placement offset is outside the tested model")
        target = get_target(events[row["ordinal"]])
        x, y = row["xy"]
        z, r = grid.sample(x, y)
        if r:
            raise ValueError("Inexact building terrain sample")
        point = target["m_snapshotPoint"]
        del point["x"], point["y"], point["z"]
        point.update(x=x, y=y, z=z)
        counts["recovered_xyz"] += 1
        counts["fractional_xy"] += bool(x % Q or y % Q)
        z_values.add(z)
    if encode_events(events, protocol, "game") != game:
        raise ValueError("Map-derived XYZ failed whole-member comparison")
    return dict(
        build=build,
        replay_sha256=xy["replay_sha256"],
        map_sha256=xy["map_sha256"],
        overlay_sha256=sha256(overlay.read_bytes()).hexdigest() if overlay else None,
        terrain_sha256=sha256(terrain).hexdigest(),
        width=grid.width,
        height=grid.height,
        terrain_bytes=len(terrain),
        structures=xy["distinct_targeted_structures"],
        distinct_predicted_z=len(z_values),
        **counts,
        game_bytes=len(game),
        game_sha256=sha256(game).hexdigest(),
        full_game_bytes_equal=True
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map", type=Path)
    parser.add_argument("replay", type=Path)
    parser.add_argument("--build", required=True, type=int, choices=sorted(SCHEMAS))
    parser.add_argument(
        "--overlay", type=Path, help="Independently compare terrain and Objects from a map copy"
    )
    args = parser.parse_args()
    print(json.dumps(check_height(args.map, args.replay, args.build, args.overlay), indent=2))
