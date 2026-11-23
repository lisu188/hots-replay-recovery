"""Project camera updates from the physical game member on the two pinned Dragon Shire layouts."""

import argparse
from collections import Counter
from contextlib import closing
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from
from xml.etree import ElementTree

from audit_native_game_fidelity import _anonymous
from camp_owner_wire import STOCK
from encoders import encode_game_events as named_encode
from first_sync_game import game
from hero_revive_wire import GATE_MAP
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from native_game_events import GameEvent, encode_game_events, iter_game_events
from opening_birth_wire import target_protocol
from predict_camp_captures import MAP, SOURCE

KIND = 49
NAME = "NNet.Game.SCameraUpdateEvent"
FIELDS = ("m_target", "m_distance", "m_pitch", "m_yaw", "m_reason", "m_follow")


def signature(protocol):
    tid, name = protocol.game_event_types[KIND]
    if name != NAME:
        raise ValueError("Camera event ID changed")

    def node(t):
        kind, args = protocol.typeinfos[t]
        if kind == "_struct":
            return [(key, tag, node(child)) for key, child, tag in args[0]]
        if kind == "_optional":
            return kind, node(args[0])
        return kind, args

    root = node(tid)
    if tuple(key for key, _, _ in root) != FIELDS:
        raise ValueError("Camera event fields differ")
    return root


def map_geometry(path, build):
    if sha256(path.read_bytes()).hexdigest() != {41810:GATE_MAP, 98348:STOCK}[build]:
        raise ValueError("Unexpected Dragon Shire package")
    with closing(MPQArchive(path)) as a:
        info = read_member(a, "MapInfo")
        terrain = ElementTree.fromstring(read_member(a, "t3Terrain.xml"))
        objects = ElementTree.fromstring(read_member(a, "Objects"))
    width, height = unpack_from("<II", info, 16)
    if (width, height) != (248, 208) or tuple(map(int,terrain.find("heightMap").get("dim").split())) != (249,209):
        raise ValueError("Unexpected MapInfo dimensions or terrain grid")
    anchors = set()
    for point in objects.findall("./ObjectPoint[@Type='StartLoc']"):
        x, y, _ = (Decimal(v) for v in point.get("Position").split(","))
        coords = (x*256, y*256)
        if coords != tuple(map(int,coords)):
            raise ValueError("Starting coordinate cannot be represented exactly")
        anchors.add(tuple(map(int,coords)))
    if len(anchors) != 10:
        raise ValueError("Incomplete authored start points")
    return width,height,anchors


def frame_rows(protocol, raw):
    offset = previous = 0
    for ordinal, event in enumerate(protocol.decode_replay_game_events(raw)):
        n, rest = divmod(event["_bits"],8)
        tick = event["_gameloop"]
        if rest or not n or offset+n > len(raw) or tick < previous:
            raise ValueError("Invalid enclosing game frame")
        if event["_eventid"] == KIND:
            yield ordinal, previous, event, raw[offset:offset+n]
        previous, offset = tick, offset+n
    if offset != len(raw):
        raise ValueError("Incomplete game member")


def audit(path, digest, build, package):
    source, game_bytes = game(path,digest,build)
    target = target_protocol()
    if signature(source) != signature(target):
        raise ValueError("Historical camera schema differs from target")
    width,height,anchors = map_geometry(package,build)
    with closing(MPQArchive(path)) as a:
        lobby = source.decode_replay_initdata(a.read_file("replay.initData"))["m_syncLobbyState"]
        desc = lobby["m_gameDescription"]
        expected_map = {41810: MAP, 98348: STOCK}[build]
        if desc["m_cacheHandles"][-1][8:].hex() != expected_map:
            raise ValueError("Recording names a different map package")
        users = {s["m_userId"] for s in lobby["m_lobbyState"]["m_slots"] if s["m_control"]==2}
        tracker = source.decode_replay_tracker_events(a.read_file("replay.tracker.events"))
        stat = next(e for e in tracker if e.get("m_eventName")==b"GameStart")
    if (desc["m_mapSizeX"],desc["m_mapSizeY"]) != (width,height) or \
            {f["m_key"]:f["m_value"] for f in stat["m_fixedData"]} != {b"MapSizeX":width*4096,b"MapSizeY":height*4096}:
        raise ValueError("Physical lobby or tracker dimensions disagree with the map")
    tid,_ = target.game_event_types[KIND]
    expected, enclosing, sparse, named = bytearray(), [], [], []
    ordinals, shapes = [], Counter()
    used_anchors, pairs = Counter(), set()
    ranges = {}
    coordinate_bounds = None
    prior_camera = 0
    for ordinal, previous, e, physical in frame_rows(source,game_bytes):
        tick, user = e["_gameloop"], e["_userid"]["m_userId"]
        if user not in users or e["_event"] != NAME:
            raise ValueError("Camera event has unexpected actor or kind")
        shape = "+".join([k[2:] for k in FIELDS[:-1] if e[k] is not None] or ["none"])
        shapes[shape + ("/follow" if e["m_follow"] else "/free")] += 1
        for k in FIELDS[1:-1]:
            if e[k] is not None:
                lo,hi = ranges.get(k,(e[k],e[k]))
                ranges[k] = min(lo,e[k]),max(hi,e[k])
        if e["m_distance"] is not None and e["m_pitch"] is not None:
            pairs.add((e["m_distance"],e["m_pitch"]))
        if e["m_target"] is not None:
            x,y = (e["m_target"][k] for k in ("x","y"))
            if not (0<=x<=width*256 and 0<=y<=height*256):
                raise ValueError("Camera coordinate outside the map")
            if (x,y) in anchors:
                used_anchors[x,y] += 1
            xl,xh,yl,yh = coordinate_bounds or (x,x,y,y)
            coordinate_bounds = min(xl,x),max(xh,x),min(yl,y),max(yh,y)
        payload = _anonymous({k:e[k] for k in FIELDS},target.typeinfos,tid)
        enclosing.append(GameEvent(tick-previous,user,KIND,payload))
        sparse.append(GameEvent(tick-prior_camera,user,KIND,payload))
        named.append(e)
        expected.extend(physical)
        ordinals.append((ordinal,tick,previous))
        prior_camera = tick
    if not named or encode_game_events(enclosing) != expected:
        raise ValueError("Target writer differs from physical enclosing camera frames")
    data = encode_game_events(sparse)
    if data != named_encode(named,target):
        raise ValueError("Sparse target writers disagree")
    read = iter_game_events(data)
    for observed, original in zip(read,sparse,strict=True):
        if observed.event != original:
            raise ValueError("Native camera event, user, loop or optional value changed")
    if build==41810 and (digest != SOURCE or len(sparse)!=17593):
        raise ValueError("Unexpected original TEN camera stream")
    receipt = dict(build=build,replay_sha256=digest,frames=len(named),first_loop=named[0]["_gameloop"],
                   last_loop=prior_camera,enclosing_bytes=len(expected),enclosing_sha256=sha256(expected).hexdigest(),
                   sparse_bytes=len(data),sparse_sha256=sha256(data).hexdigest(),map_dimensions=[width,height],
                   coordinate_bounds_xy_raw=coordinate_bounds,exact_startpoint_hits=sum(used_anchors.values()),
                   distinct_startpoints_hit=len(used_anchors),shapes=dict(sorted(shapes.items())),
                   ranges=ranges)
    return data,receipt,ordinals,pairs


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("replay",type=Path)
    cli.add_argument("digest")
    cli.add_argument("build",type=int,choices=(41810,98348))
    cli.add_argument("map",type=Path)
    cli.add_argument("--private-output",type=Path)
    cli.add_argument("--private-ledger",type=Path,help="Write source ordinal, absolute loop and preceding game loop")
    a = cli.parse_args()
    data,summary,ledger,_ = audit(a.replay,a.digest,a.build,a.map)
    if a.private_output:
        with a.private_output.open("xb") as out:
            out.write(data)
    if a.private_ledger:
        with a.private_ledger.open("x",encoding="utf-8") as out:
            print(json.dumps(ledger,separators=(",",":")),file=out)
    print(json.dumps(summary,indent=2))
