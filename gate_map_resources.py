"""Resolve the historical-layout GateOrder map resources from local package contents."""

import argparse
from contextlib import closing
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from xml.etree import ElementTree

from dependency_audit import cache_handle
from encoders import BitPackedEncoder
from first_sync_game import game
from hero_revive_wire import GATE_MAP
from mod_data_audit import dependency_prefix
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from opening_birth_wire import target_protocol
from predict_camp_captures import SOURCE
from reference_replay import SortedVersionedEncoder
from repair_dragon_dependencies import parse_prefix, replace_prefix


STANDARD = ("Core", "Teams10", "Heroes", "HeroesData")
DATA_MOD = "bnet:Heroes of the Storm (Data Mod)/0.0/999,file:Mods/HeroesData.StormMod"


def digest(data):
    return sha256(data).hexdigest()


def dependency_declaration(package):
    with closing(MPQArchive(package)) as archive:
        info = read_member(archive, "DocumentInfo")
        header = read_member(archive, "DocumentHeader")
    declared = [e.text for e in ElementTree.fromstring(info).findall("Dependencies/Value")]
    if (declared != [DATA_MOD] or header[:12] != b"oreH\x08\0\0\0oreH"
            or header[44:48] != b"\x01\0\0\0" or header[48:].split(b"\0", 1)[0] != DATA_MOD.encode("ascii")):
        raise ValueError("Expected the historical Dragon Shire dependency in both documents")
    return digest(info), digest(header)


def resources(source, overlay, cache):
    original, _ = game(source, SOURCE, 41810)
    if digest(overlay.read_bytes()) != GATE_MAP:
        raise ValueError("Unexpected GateOrder map")
    with closing(MPQArchive(source)) as a:
        details_bytes = a.read_file("replay.details")
        details = original.decode_replay_details(details_bytes)
        desc = original.decode_replay_initdata(a.read_file("replay.initData"))["m_syncLobbyState"]["m_gameDescription"]
        lobby = a.read_file("replay.server.battlelobby")
    old = desc["m_cacheHandles"]
    info = dependency_prefix(lobby)
    if (len(old) != 5 or details["m_cacheHandles"] != old or info["handles"] != [h.hex() for h in old]
            or any(h[:8] != b"s2ma\0\0EU" for h in old)):
        raise ValueError("Historical resources disagree across the three replay members")
    new = []
    for label, handle in zip(STANDARD, old[:4], strict=True):
        marker = ("Standard Data: " + label + ".StormMod").encode("ascii")
        if ((cache / cache_handle(handle)["relative_path"]).read_bytes() != marker
                or sha256(marker).digest() != handle[8:]):
            raise ValueError("Standard-data marker does not match its named file and digest")
        new.append(handle[:8] + sha256(marker).digest())
    stock = cache / cache_handle(old[-1])["relative_path"]
    if digest(stock.read_bytes()) != old[-1][8:].hex() or dependency_declaration(stock) != dependency_declaration(overlay):
        raise ValueError("The overlay has different dependency declarations from its historical parent")
    new.append(old[-1][:8] + bytes.fromhex(GATE_MAP))
    target = target_protocol()
    if target.decode_replay_details(details_bytes) != details:
        raise ValueError("Historical and target details views differ")
    projected = deepcopy(details)
    projected["m_cacheHandles"] = new
    encoder = SortedVersionedEncoder(target.typeinfos)
    encoder.instance(target.game_details_typeid, projected)
    encoded = encoder.getvalue()
    if (details_bytes.count(old[-1]) != 1 or encoded != details_bytes.replace(old[-1], new[-1])
            or target.decode_replay_details(encoded) != projected):
        raise ValueError("Projected target details changed outside the selected map handle")
    updated, _ = replace_prefix(lobby, old, new)
    _, handles, end = parse_prefix(updated)
    if handles != new or dependency_prefix(updated)["handles"] != [h.hex() for h in new]:
        raise ValueError("Battlelobby resource prefix disagrees")
    tid = target.replay_initdata_typeid
    for field in ("m_syncLobbyState", "m_gameDescription", "m_cacheHandles"):
        ((_, tid, _),) = [entry for entry in target.typeinfos[tid][1][0] if entry[0] == field]
    writer = BitPackedEncoder(target.typeinfos)
    writer.instance(tid, new)
    artifacts = {"details": encoded, "battlelobby-prefix": updated[:end], "standalone-initdata-handles": writer.getvalue()}
    return new, artifacts, dict(source_build=41810, target_build=98348, map_sha256=GATE_MAP, resources=5,
                                named_standard_dependencies=list(STANDARD), inherited_details_fields=True,
                                public_depot_availability_verified=False, content_sync_checksums_verified=False,
                                artifacts={n: dict(bytes=len(v), sha256=digest(v)) for n, v in artifacts.items()})


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("original", "overlay", "cache"):
        cli.add_argument(name, type=Path)
    cli.add_argument("--private-dir", type=Path, help="Create a new directory for derived member data")
    args = cli.parse_args()
    _, files, report = resources(args.original, args.overlay, args.cache)
    if args.private_dir:
        args.private_dir.mkdir(exist_ok=False)
        for name, value in files.items():
            (args.private_dir / (name + ".private.bin")).write_bytes(value)
    print(json.dumps(report, indent=2))
