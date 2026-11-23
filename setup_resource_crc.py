"""Evaluate recorded setup serialization and a TEN resource projection with explicit checksum inputs."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from zlib import crc32

from gate_map_resources import resources
from migrate_replay import SemanticDecoder, SemanticEncoder
from mod_data_audit import dependency_prefix
from mpq_reader import MPQArchive
from native_setup import compare_setup_with_official, decode_setup, encode_setup_values
from opening_birth_wire import target_protocol

R8 = "5ed50ccfcd947b92488cba095973dcd9d4de76a976a457417203608d379b3f01"


def setup_crc(raw):
    return crc32(b"\x00" * 4, crc32(raw))


def template(path, digest, build):
    if sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("Unexpected replay identity")
    p = target_protocol()
    with closing(MPQArchive(path)) as a:
        h = p.decode_replay_header(a.header["user_data_header"]["content"])
        if (h["m_version"]["m_build"], h["m_version"]["m_baseBuild"], h["m_dataBuildNum"]) != (build,) * 3:
            raise ValueError("Unexpected recording build")
        raw = a.read_file("replay.initData")
        details = p.decode_replay_details(a.read_file("replay.details"))
        prefix = dependency_prefix(a.read_file("replay.server.battlelobby"))
    s = decode_setup(raw)
    official = p.decode_replay_initdata(raw)
    compare_setup_with_official(s, official, p.typeinfos)
    handles = official["m_syncLobbyState"]["m_gameDescription"]["m_cacheHandles"]
    if handles != details["m_cacheHandles"] or prefix["handles"] != [h.hex() for h in handles]:
        raise ValueError("Inconsistent resource list")
    named = SemanticDecoder(raw, p.typeinfos).instance(p.replay_initdata_typeid)
    encoded = SemanticEncoder(p.typeinfos)
    encoded.instance(p.replay_initdata_typeid, named)
    canonical = encode_setup_values(s.value)
    if encoded.getvalue() != canonical:
        raise ValueError("Native-layout and named setup writers differ")
    return p, named, s.value, dict(bytes=len(raw), canonical_bytes_equal_recorded=canonical == raw,
                                  canonical_setup_crc=hex(setup_crc(canonical)), resources=len(handles))


def project(p, named, root, handles, map_checksum, mod_checksum):
    if any(type(n) is not int or not 0 <= n <= 0xffffffff for n in (map_checksum, mod_checksum)):
        raise ValueError("Both map and mod content checksums must be explicit uint32 values")
    # root type 775 -> game description type 684, declaration slots 14, 17 and 21.
    desc = list(root[1])
    desc[14], desc[17], desc[21] = map_checksum, mod_checksum, tuple(handles)
    raw = encode_setup_values((root[0], tuple(desc), root[2]))
    lobby = named["m_syncLobbyState"]
    game_desc = dict(lobby["m_gameDescription"], m_mapFileSyncChecksum=map_checksum,
                     m_modFileSyncChecksum=mod_checksum, m_cacheHandles=handles)
    compare = SemanticEncoder(p.typeinfos)
    compare.instance(p.replay_initdata_typeid, {"m_syncLobbyState": dict(lobby, m_gameDescription=game_desc)})
    if raw != compare.getvalue():
        raise ValueError("Setup resource projection differs between writers")
    return raw


def influence(p, named, value, handles):
    # The zero pair defines the origin of the affine CRC expression only.
    def encode(a, b):
        return project(p, named, value, handles, a, b)
    origin = encode(0, 0)
    base = setup_crc(origin)
    columns = []
    spans = []
    for field in range(2):
        bits = []
        for bit in range(32):
            word = 1 << bit
            trial = encode(word if field == 0 else 0, word if field == 1 else 0)
            changed = [(i, a ^ b) for i, (a, b) in enumerate(zip(origin, trial, strict=True)) if a != b]
            if len(changed) != 1 or changed[0][1].bit_count() != 1:
                raise ValueError("A checksum bit changed multiple setup positions")
            i, mask = changed[0]
            bits.append(i * 8 + mask.bit_length() - 1)
            columns.append(setup_crc(trial) ^ base)
        spans.append([min(bits), max(bits) + 1])
        if len(set(bits)) != 32 or max(bits) - min(bits) != 31:
            raise ValueError("Checksum does not occupy an exact 32-bit field")
    if spans[0][1] > spans[1][0]:
        raise ValueError("Checksum fields overlap")
    for a, b in [(0xffffffff, 0xffffffff), (0x12345678, 0x23456789), (0xcafed012, 0x2fbca376)]:
        state = base
        for i in range(64):
            if (a | b << 32) & (1 << i):
                state ^= columns[i]
        if state != setup_crc(encode(a, b)):
            raise ValueError("Combined CRC differs from two-writer serialization")
    return dict(template_r8=R8, projected_bytes=len(origin), map_mod_bit_ranges=spans,
                crc_affine_constant=f"{base:08x}", columns_map_lsb_first_then_mod=[f"{v:08x}" for v in columns],
                source_of_other_fields="Frozen partial R8 setup; player and other field migrations remain subject to review",
                field_checksums_resolved=False, actual_committed_ten_setup_crc_verified=False)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for key in ("source", "r8", "map", "cache"):
        cli.add_argument(key, type=Path)
    a = cli.parse_args()
    handles, _, _ = resources(a.source, a.map, a.cache)
    p, named, root, _ = template(a.r8, R8, 98285)
    print(json.dumps(influence(p, named, root, handles), indent=2))
