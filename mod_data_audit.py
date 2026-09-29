from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from dependency_audit import OPAQUE_MEMBERS, battlelobby_cache_paths, cache_handle
from encoders import BitPackedEncoder
from protocol_loader import load_protocol
from reference_replay import checked_archive, inspect_reference

PREFIX_TYPES = [
    ('_blob', [(0, 10)]),
    ('_array', [(0, 6), 0]),
    ('_blob', [(40, 0)]),
    ('_array', [(0, 6), 2]),
    ('_struct', [[('paths', 1, 0), ('handles', 3, 1)]]),
]
FORMAT = 'hots-mod-data-profile-v1'
HEX256 = re.compile(r'[0-9a-f]{64}')
HEX128 = re.compile(r'[0-9a-f]{32}')


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def dependency_prefix(raw: bytes) -> dict:
    from heroprotocol.decoders import BitPackedDecoder

    if not isinstance(raw, bytes) or not 2 <= len(raw) <= 16 * 1024 * 1024:
        raise ValueError('Battlelobby is absent or outside supported bounds')
    decoder = BitPackedDecoder(raw, PREFIX_TYPES)
    value = decoder.instance(4)
    paths, handles = value['paths'], value['handles']
    if not 1 <= len(paths) == len(handles) <= 63:
        raise ValueError('Dependency path and handle counts disagree')
    relative = []
    for path, handle in zip(paths, handles, strict=True):
        found = battlelobby_cache_paths(path)
        expected = cache_handle(handle)['relative_path']
        if found != [expected] or not path.replace(b'\\', b'/').lower().endswith(expected.encode('ascii')):
            raise ValueError('A battlelobby path does not identify its corresponding handle')
        relative.append(expected)
    if len(set(relative)) != len(relative):
        raise ValueError('Duplicate dependency handles are unsupported')
    bits = decoder._buffer.used_bits()
    if bits % 8:
        raise ValueError('Dependency prefix does not end on a byte boundary')
    encoder = BitPackedEncoder(PREFIX_TYPES)
    encoder.instance(4, value)
    length = bits // 8
    if encoder.getvalue() != raw[:length]:
        raise ValueError('Dependency prefix does not round-trip byte-for-byte')
    return {'handles': [v.hex() for v in handles], 'relative_paths': relative,
            'prefix_bytes': length, 'prefix_sha256': digest(raw[:length]),
            'prefix_roundtrip': True, 'opaque_tail_bytes': len(raw) - length,
            'opaque_tail_sha256': digest(raw[length:]), 'full_battlelobby_schema_verified': False}


def observe(path: Path, schema: int, expected_build: int | None = None, local: bool = False) -> dict:
    path = Path(path)
    verified = inspect_reference(path, schema, expected_build, local)
    p = load_protocol(schema, local)
    archive = checked_archive(path)
    try:
        details = p.decode_replay_details(archive.read_file('replay.details'))
        description = p.decode_replay_initdata(archive.read_file('replay.initData'))['m_syncLobbyState']['m_gameDescription']
        handles = description['m_cacheHandles']
        if handles != details['m_cacheHandles']:
            raise ValueError('Details and lobby disagree on ordered dependencies')
        prefix = dependency_prefix(archive.read_file('replay.server.battlelobby'))
        if prefix['handles'] != [v.hex() for v in handles]:
            raise ValueError('Battlelobby and initData disagree on ordered dependencies')
        target = verified['target']
        result = {
            'format': FORMAT, 'file_sha256': verified['file_sha256'],
            'file_bytes': verified['file_bytes'], 'schema_build': schema,
            'schema_sha256': verified['schema_file_sha256'],
            'version': target['m_version'], 'data_build': target['m_dataBuildNum'],
            'root_key': target['m_ngdpRootKey']['m_data'].hex(),
            'replay_compatibility_hash': target['m_replayCompatibilityHash']['m_data'].hex(),
            'map_title': details['m_title'].decode('utf-8'),
            'map_size': [description['m_mapSizeX'], description['m_mapSizeY']],
            'map_file_sync_checksum': description['m_mapFileSyncChecksum'],
            'mod_file_sync_checksum': description['m_modFileSyncChecksum'],
            'dependencies': prefix, 'full_observed_payload_roundtrip': True,
            'streams': {k: {'count': v['count'], 'sha256': v['sha256']} for k, v in verified['streams'].items()},
            'opaque_members': {name: digest(archive.read_file(name) or b'') for name in OPAQUE_MEMBERS},
            'known_experiment_name': bool(re.search(r'EXPERIMENTAL|CONTROL_|protocol\d+', path.name, re.I)),
            'client_playback_validated': False, 'engine_checksum_algorithm_verified': False,
            'limitations': ['The battlelobby prefix is decoded; the remaining battlelobby is opaque.',
                            'Checksums are recorded expectations, not independently calculated engine values.',
                            'References are user-provided observations, not cryptographically authenticated matches.'],
        }
    finally:
        archive.close()
    if digest(path.read_bytes()) != result['file_sha256']:
        raise ValueError('Replay changed during the audit')
    validate_profile(result)
    return result


def validate_profile(profile: dict) -> None:
    if not isinstance(profile, dict) or profile.get('format') != FORMAT:
        raise ValueError('Unsupported mod-data profile')
    for key in ('file_sha256', 'schema_sha256'):
        if not isinstance(profile.get(key), str) or not HEX256.fullmatch(profile[key]):
            raise ValueError(f'Invalid {key}')
    for key in ('root_key', 'replay_compatibility_hash'):
        if not isinstance(profile.get(key), str) or not HEX128.fullmatch(profile[key]):
            raise ValueError(f'Invalid {key}')
    version = profile.get('version')
    if not isinstance(version, dict):
        raise ValueError('Missing version')
    for key in ('m_flags', 'm_major', 'm_minor', 'm_revision', 'm_build', 'm_baseBuild'):
        if type(version.get(key)) is not int or not 0 <= version[key] < 2**32:
            raise ValueError(f'Invalid version field {key}')
    for key in ('data_build', 'map_file_sync_checksum', 'mod_file_sync_checksum'):
        if type(profile.get(key)) is not int or not 0 <= profile[key] < 2**32:
            raise ValueError(f'Invalid {key}')
    if not version['m_build'] or not version['m_baseBuild'] or not profile['data_build']:
        raise ValueError('Zero build is unsupported')
    if not isinstance(profile.get('map_title'), str) or not profile['map_title'].strip():
        raise ValueError('Missing map title')
    size = profile.get('map_size')
    if not isinstance(size, list) or len(size) != 2 or any(type(v) is not int or not 0 <= v <= 255 for v in size):
        raise ValueError('Invalid serialized map dimensions')
    if profile.get('full_observed_payload_roundtrip') is not True:
        raise ValueError('Full observed-payload validation is required')
    dependencies = profile.get('dependencies', {})
    if not isinstance(dependencies, dict):
        raise ValueError('Invalid dependency description')
    handles = dependencies.get('handles')
    if not isinstance(handles, list) or not 1 <= len(handles) <= 63:
        raise ValueError('Invalid dependency count')
    paths = []
    for handle in handles:
        if not isinstance(handle, str) or not re.fullmatch('[0-9a-f]{80}', handle):
            raise ValueError('Invalid cache handle')
        paths.append(cache_handle(bytes.fromhex(handle))['relative_path'])
    if len(set(paths)) != len(paths) or dependencies.get('relative_paths') != paths or dependencies.get('prefix_roundtrip') is not True:
        raise ValueError('Inconsistent dependency provenance')


def compare(candidate: dict, reference: dict) -> dict:
    validate_profile(candidate)
    validate_profile(reference)
    checks = {
        'same_map_title': candidate['map_title'] == reference['map_title'],
        'same_map_dimensions': candidate['map_size'] == reference['map_size'],
        'same_version': candidate['version'] == reference['version'],
        'same_data_build': candidate['data_build'] == reference['data_build'],
        'same_root_key': candidate['root_key'] == reference['root_key'],
        'same_replay_compatibility_hash': candidate['replay_compatibility_hash'] == reference['replay_compatibility_hash'],
        'independent_file': candidate['file_sha256'] != reference['file_sha256'],
        'not_known_experiment': reference.get('known_experiment_name') is False,
    }
    old = candidate['dependencies']['relative_paths']
    new = reference['dependencies']['relative_paths']
    prefix = 0
    for a, b in zip(old, new):
        if a != b:
            break
        prefix += 1
    return {
        'format': 'hots-mod-data-comparison-v1',
        'candidate_sha256': candidate['file_sha256'], 'reference_sha256': reference['file_sha256'],
        'checks': checks, 'blocking_reasons': [key for key, value in checks.items() if not value],
        'eligible_for_same_map_investigation': all(checks.values()),
        'ordered_dependencies_equal': old == new, 'shared_prefix_count': prefix,
        'candidate_only_dependencies': [p for p in old if p not in new],
        'reference_only_dependencies': [p for p in new if p not in old],
        'checksums': {key: {'candidate': candidate[key], 'reference': reference[key], 'equal': candidate[key] == reference[key]}
                      for key in ('map_file_sync_checksum', 'mod_file_sync_checksum')},
        'checksum_transplant_validated': False, 'simulation_compatibility_validated': False,
        'client_playback_validated': False,
        'warning': 'Eligibility is only a prerequisite for investigation. Do not treat copying expected checksums as porting the map or game rules.',
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='command', required=True)
    inspect = commands.add_parser('inspect')
    inspect.add_argument('replay', type=Path)
    inspect.add_argument('--schema-build', type=int, required=True)
    inspect.add_argument('--expected-build', type=int)
    inspect.add_argument('--local-schema', action='store_true')
    inspect.add_argument('--output', type=Path, required=True)
    comparison = commands.add_parser('compare')
    comparison.add_argument('candidate', type=Path)
    comparison.add_argument('reference', type=Path)
    comparison.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    if args.command == 'inspect':
        result = observe(args.replay, args.schema_build, args.expected_build, args.local_schema)
    else:
        result = compare(json.loads(args.candidate.read_text()), json.loads(args.reference.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'output': str(args.output), 'client_playback_validated': False}))


if __name__ == '__main__':
    main()
