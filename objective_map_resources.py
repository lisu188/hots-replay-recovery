"""Bind verified historical-layout resources and evaluate their partial setup CRC offline."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from

from declared_map_checksum import header
from gate_map_resources import GATE_MAP, resources
from repair_dragon_dependencies import cache_suffix, parse_prefix
from setup_resource_crc import R8, project, setup_crc, template


def audit(source, partial, gate, maps, cache, private_dir=None):
    protocol, named, state, _ = template(partial, R8, 98285)
    baseline, original_files, _ = resources(source, gate, cache)
    report = {}
    private = {}
    base_columns = None
    for path in [gate, *maps]:
        key = sha256(path.read_bytes()).hexdigest()
        if key in report:
            raise ValueError("Repeated map")
        handles, files, result = resources(source, path, cache, map_sha256=key)
        if handles[:4] != baseline[:4] or handles[4][:8] != baseline[4][:8]:
            raise ValueError("Unexpected change outside the map digest")
        for filename, original in original_files.items():
            if filename=='battlelobby-prefix':
                old_paths, old_handles, _=parse_prefix(original)
                new_paths, new_handles, end=parse_prefix(files[filename])
                if (old_handles!=baseline or new_handles!=handles or end!=len(files[filename]) or
                        old_paths[:4]!=new_paths[:4] or not old_paths[4].endswith(cache_suffix(baseline[4])) or
                        old_paths[4].removesuffix(cache_suffix(baseline[4]))+cache_suffix(handles[4])!=new_paths[4]):
                    raise ValueError('Battlelobby handle or corresponding cache path differs')
                continue
            if original.count(baseline[4]) != 1 or files[filename] != original.replace(baseline[4],handles[4]):
                raise ValueError("Resource fragments diverge outside the one named map handle")
        document, archive_crc = header(path, key)
        word = unpack_from("<I", document, 28)[0]
        def serialize(mod):
            return project(protocol, named, state, handles, word, mod)
        origin = serialize(0)
        zero = setup_crc(origin)
        columns = [setup_crc(serialize(1<<i)) ^ zero for i in range(32)]
        if base_columns is None:
            base_columns = columns
        if columns != base_columns:
            raise ValueError("The mod word changed bit position or checksum transform")
        for probe in (0x12345678,0x91642b85,0xffffffff):
            expected = zero
            for i, v in enumerate(columns):
                if probe & (1<<i):
                    expected ^= v
            if setup_crc(serialize(probe)) != expected:
                raise ValueError("Algebraic and serialized setup CRC differ")
        report[key] = dict(declared_map_checksum=f"{word:08x}", archive_crc=f"{archive_crc:08x}",
                           setup_bytes=len(origin),mod_zero_constant=f"{zero:08x}",
                           resource_fragments=result["artifacts"])
        private[key] = files
    if report[GATE_MAP]["mod_zero_constant"] != "078b4076":
        raise ValueError("Published GateOrder baseline differs")
    if private_dir:
        private_dir.mkdir(exist_ok=False)
        for key,files in private.items():
            dest=private_dir/key
            dest.mkdir()
            for name,data in files.items():
                (dest/(name+".private.bin")).write_bytes(data)
    return dict(partial_setup_template=R8,maps=report,mod_lsb_first_columns=[f"{v:08x}" for v in base_columns],
                resolved_mod_checksum=False,engine_resource_validation_verified=False,target_syncs_verified=0)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("source","partial","gate","cache"):
        parser.add_argument(name,type=Path)
    parser.add_argument("maps",type=Path,nargs="+")
    parser.add_argument("--private-dir",type=Path)
    print(json.dumps(audit(**vars(parser.parse_args())),indent=2))
