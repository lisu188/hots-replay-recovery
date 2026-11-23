"""Read the map checksum declared by a Dragon Shire package and test its replay binding."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from
from zlib import crc32

from dependency_audit import cache_handle
from first_sync_game import game
from gate_map_resources import resources
from mpq_mixed_sectors import read_member
from mpq_reader import MPQArchive
from predict_camp_captures import SOURCE
from setup_resource_crc import R8, project, setup_crc, template


def header(path, expected_sha):
    blob = path.read_bytes()
    if sha256(blob).hexdigest() != expected_sha:
        raise ValueError("Map package SHA-256 differs from its resource handle")
    with closing(MPQArchive(path)) as archive:
        data = read_member(archive, "DocumentHeader")
    if len(data) < 48 or data[:12] != b"oreH\x08\0\0\0oreH":
        raise ValueError("Unexpected map document header")
    return data, crc32(blob)


def recorded(path, digest, build, cache):
    protocol, _ = game(path, digest, build)
    with closing(MPQArchive(path)) as archive:
        setup = protocol.decode_replay_initdata(archive.read_file("replay.initData"))
        desc = setup["m_syncLobbyState"]["m_gameDescription"]
        details = protocol.decode_replay_details(archive.read_file("replay.details"))
    if details["m_cacheHandles"] != desc["m_cacheHandles"]:
        raise ValueError("Map differs between recorded replay members")
    handle = desc["m_cacheHandles"][-1]
    if len(handle) != 40 or handle[:4] != b"s2ma":
        raise ValueError("Expected a map resource")
    key = handle[8:].hex()
    data, whole_crc = header(cache / cache_handle(handle)["relative_path"], key)
    word, adjacent = unpack_from("<II", data, 28)
    if word != desc["m_mapFileSyncChecksum"]:
        raise ValueError("Stored map checksum and map DocumentHeader differ")
    return key, dict(declared=f"{word:08x}", next_word_also_matches=adjacent == word,
                     archive_crc_matches=whole_crc == word, header_sha256=sha256(data).hexdigest())


def compare(cases, source, r8, overlay, cache):
    import first_sync_game
    pinfile = Path(first_sync_game.__file__).resolve().parent / "observations" / "first-sync-game.json"
    pins = {r["replay_sha256"] for r in json.loads(pinfile.read_bytes())["references"]}
    if len(pins) != 24 or set(cases) != pins:
        raise ValueError("Expected all 24 pinned target recordings")
    counts, groups = Counter(), {}
    for digest, name in sorted(cases.items()):
        key, info = recorded(Path(name), digest, 98348, cache)
        if key in groups and groups[key] != info:
            raise ValueError("Conflicting observations for a byte-identical target map")
        counts[key] += 1
        groups[key] = info
    old_key, old = recorded(source, SOURCE, 41810, cache)
    handles, _, info = resources(source, overlay, cache)
    data, whole_crc = header(overlay, info["map_sha256"])
    if sha256(data).hexdigest() != old["header_sha256"]:
        raise ValueError("Historical and overlay headers differ")
    word = unpack_from("<I", data, 28)[0]
    p, named, root, _ = template(r8, R8, 98285)
    def output(mod_value):
        return project(p, named, root, handles, word, mod_value)
    base = setup_crc(output(0))
    cols = [setup_crc(output(1 << bit)) ^ base for bit in range(32)]
    for value in (0x12345678, 0xa781fe13, 0xffffffff):
        combined = base
        for bit, column in enumerate(cols):
            if value & 1 << bit:
                combined ^= column
        if combined != setup_crc(output(value)):
            raise ValueError("Declared-map setup CRC projection disagrees with serialization")
    return dict(target_build=98348, controls=sum(counts.values()), target_map_packages=len(groups),
                target_groups={k:dict(recordings=counts[k], **v) for k,v in sorted(groups.items())},
                original_map=old_key, original=old, overlay=info["map_sha256"],
                overlay_declared_word=f"{word:08x}", overlay_archive_crc=f"{whole_crc:08x}",
                setup_template=R8, projected_bytes=len(output(0)), mod_zero_algebraic_constant=f"{base:08x}",
                mod_lsb_first_columns=[f"{x:08x}" for x in cols],
                actual_overlay_resource_validation_verified=False, mod_checksum_resolved=False)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "original", "r8", "overlay", "cache"):
        cli.add_argument(name, type=Path)
    a = cli.parse_args()
    print(json.dumps(compare(json.loads(a.manifest.read_bytes()), a.original, a.r8, a.overlay, a.cache), indent=2))
