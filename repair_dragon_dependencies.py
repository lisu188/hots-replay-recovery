from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path

from bind_client_metadata import publish_binary
from dependency_audit import cache_handle
from encoders import BitPackedWriter
from heroprotocol.decoders import BitPackedBuffer
from migrate_replay import SemanticDecoder, SemanticEncoder, dump, note, write_json
from mpq_reader import MPQArchive
from protocol_loader import load_protocol
from reference_replay import SortedVersionedEncoder, inspect_reference
from repair_control_masks import integrity
from repair_startup import native_replace
from verify_checkpoint import stormlib_check

SOURCE_SHA256 = 'edd690c6956b48c1592edf946bc8e01e012220c961b04cf3d86ec983c808367c'
REFERENCE_SHA256 = '5a7b05f4a75bc229dbbd74e6cc09e3b411129fc731874cfaa9217432fb85e7dc'
SCHEMA_SHA256 = 'e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84'
OUTPUT_NAME = 'TEN_GREYMANE_client98285_DRAGON_R5_EXPERIMENTAL.StormReplay'
BUILD = 98285
MAP_FIELDS = ('m_mapFileSyncChecksum', 'm_modFileSyncChecksum', 'm_cacheHandles')
MODE_DIFFERENCES = {'m_amm', 'm_competitive', 'm_ammId'}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def schema():
    p = load_protocol(96477)
    if sha(Path(p.__file__).read_bytes()) != SCHEMA_SHA256:
        raise ValueError('Official schema differs from the inspected Blizzard source')
    return p


def cache_suffix(handle: bytes) -> bytes:
    item = cache_handle(handle)
    if item['extension'] != 's2ma' or item['region'] != 'EU':
        raise ValueError('This experiment supports only the observed EU map handles')
    return item['relative_path'].replace('/', '\\').encode('ascii')


def encode_prefix(paths: list[bytes], handles: list[bytes]) -> bytes:
    if not 0 < len(handles) < 64 or len(paths) != len(handles):
        raise ValueError('Dependency path and handle counts differ or are out of range')
    writer = BitPackedWriter()
    writer.write_bits(len(paths), 6)
    for path, handle in zip(paths, handles, strict=True):
        suffix = cache_suffix(handle)
        if not isinstance(path, bytes) or not 0 < len(path) < 1024 or not path.endswith(b'Cache\\' + suffix):
            raise ValueError('Cache path does not match its handle')
        if b'\0' in path or b'..' in path:
            raise ValueError('Unsafe dependency path')
        writer.write_bits(len(path), 10)
        writer.write_aligned_bytes(path)
    writer.write_bits(len(handles), 6)
    for handle in handles:
        writer.write_aligned_bytes(handle)
    return writer.getvalue()


def parse_prefix(raw: bytes) -> tuple[list[bytes], list[bytes], int]:
    if not isinstance(raw, bytes) or not 1 <= len(raw) <= 64 * 1024 * 1024:
        raise ValueError('Invalid battlelobby size')
    reader = BitPackedBuffer(raw)
    count = reader.read_bits(6)
    if not 0 < count < 64:
        raise ValueError('Empty dependency prefix is unsupported')
    paths = [reader.read_aligned_bytes(reader.read_bits(10)) for _ in range(count)]
    handle_count = reader.read_bits(6)
    if handle_count != count:
        raise ValueError('Battlelobby dependency count mismatch')
    handles = [reader.read_aligned_bytes(40) for _ in range(handle_count)]
    if reader.used_bits() % 8:
        raise ValueError('Dependency prefix does not end at a byte boundary')
    end = reader.used_bits() // 8
    if encode_prefix(paths, handles) != raw[:end]:
        raise ValueError('Unsupported or noncanonical dependency prefix')
    return paths, handles, end


def replace_prefix(raw: bytes, expected: list[bytes], handles: list[bytes]) -> tuple[bytes, dict]:
    paths, old, end = parse_prefix(raw)
    if old != expected:
        raise ValueError('Battlelobby and lobby dependency handles disagree')
    roots = {path[:-len(cache_suffix(handle))] for path, handle in zip(paths, old, strict=True)}
    if len(roots) != 1:
        raise ValueError('Mixed dependency cache roots are unsupported')
    root = roots.pop()
    prefix = encode_prefix([root + cache_suffix(handle) for handle in handles], handles)
    result = prefix + raw[end:]
    actual_paths, actual_handles, new_end = parse_prefix(result)
    if actual_handles != handles or result[new_end:] != raw[end:]:
        raise ValueError('Dependency rewrite did not preserve the opaque tail')
    return result, {'old_prefix_bytes': end, 'new_prefix_bytes': new_end,
                    'tail_bytes': len(raw) - end, 'tail_sha256': sha(raw[end:]),
                    'tail_bytes_preserved': True,
                    'path_count_before': len(paths), 'path_count_after': len(actual_paths)}


def read_models(path: Path):
    p = schema()
    archive = MPQArchive(path)
    try:
        header = p.decode_replay_header(archive.header['user_data_header']['content'])
        initial = SemanticDecoder(archive.read_file('replay.initData'), p.typeinfos).instance(p.replay_initdata_typeid)
        details = p.decode_replay_details(archive.read_file('replay.details'))
        battlelobby = archive.read_file('replay.server.battlelobby')
        return header, initial, details, battlelobby
    finally:
        archive.close()


def observe(path: Path) -> dict:
    path = Path(path)
    if sha(path.read_bytes()) != REFERENCE_SHA256:
        raise ValueError('Unexpected original Dragon Shire reference')
    profile = inspect_reference(path, 96477, BUILD)
    native = integrity(path)
    header, initial, details, battlelobby = read_models(path)
    game = initial['m_syncLobbyState']['m_gameDescription']
    paths, handles, end = parse_prefix(battlelobby)
    if handles != game['m_cacheHandles'] or handles != details['m_cacheHandles']:
        raise ValueError('Reference dependency lists disagree')
    result = {'format': 'hots-dragon-dependency-observation-v1',
              'reference_sha256': REFERENCE_SHA256, 'reference_bytes': path.stat().st_size,
              'build': header['m_version']['m_build'], 'base_build': header['m_version']['m_baseBuild'],
              'data_build': header['m_dataBuildNum'], 'schema_sha256': SCHEMA_SHA256,
              'root': header['m_ngdpRootKey']['m_data'].hex(),
              'compatibility_hash': header['m_replayCompatibilityHash']['m_data'].hex(),
              'map_title': details['m_title'].decode('utf-8'),
              'map_size': [game['m_mapSizeX'], game['m_mapSizeY']],
              'map_file_name_hex': game['m_mapFileName'].hex(),
              'map_author_hex': game['m_mapAuthorName'].hex(),
              'is_blizzard_map': game['m_isBlizzardMap'], 'has_extension_mod': game['m_hasExtensionMod'],
              'map_checksum': game['m_mapFileSyncChecksum'], 'mod_checksum': game['m_modFileSyncChecksum'],
              'handles_hex': [handle.hex() for handle in handles],
              'game_options': game['m_gameOptions'], 'full_reference_roundtrip': True,
              'reference_prefix_roundtrip': True, 'reference_prefix_bytes': end,
              'reference_prefix_sha256': sha(battlelobby[:end]),
              'event_counts': {kind: value['count'] for kind, value in profile['streams'].items()},
              'native_checksums_passed': native['all_available_checksums_passed'],
              'client_playback_observed_by_tool': False}
    validate_observation(result)
    return result


def validate_observation(value: dict) -> list[bytes]:
    if not isinstance(value, dict) or value.get('format') != 'hots-dragon-dependency-observation-v1':
        raise ValueError('Invalid Dragon Shire observation')
    if value.get('reference_sha256') != REFERENCE_SHA256 or value.get('schema_sha256') != SCHEMA_SHA256:
        raise ValueError('Unrecognized reference or schema provenance')
    for key in ('build', 'base_build', 'data_build'):
        if type(value.get(key)) is not int or value[key] != BUILD:
            raise ValueError('Reference does not match the observed client build')
    for key in ('full_reference_roundtrip', 'reference_prefix_roundtrip', 'native_checksums_passed', 'is_blizzard_map'):
        if value.get(key) is not True:
            raise ValueError(f'Reference check is not established: {key}')
    if value.get('has_extension_mod') is not False or value.get('map_title') != 'Dragon Shire':
        raise ValueError('Different map or extension mod')
    if value.get('map_size') != [248, 208]:
        raise ValueError('Unexpected map dimensions')
    if value.get('root') != 'b5114c16bd78f1844ab9fe97cbd9c305' or value.get('compatibility_hash') != '0' * 32:
        raise ValueError('Unexpected client identity')
    for key, expected in (('map_checksum', 886294905), ('mod_checksum', 2276260760)):
        if type(value.get(key)) is not int or value[key] != expected:
            raise ValueError('Checksum differs from the measured same-map reference')
    items = value.get('handles_hex')
    if not isinstance(items, list) or len(items) != 6:
        raise ValueError('Expected six distinct observed dependency handles')
    if any(not isinstance(item, str) or not re.fullmatch('[0-9a-f]{80}', item) for item in items):
        raise ValueError('Malformed dependency handle')
    if len(set(items)) != 6:
        raise ValueError('Duplicate dependency handle')
    handles = [bytes.fromhex(item) for item in items]
    for handle in handles:
        cache_suffix(handle)
    if handles[-2][8:].hex() != 'baae53ca97aa2a0cf370cadbef747a321fd9677c607d5c353878e645bcc14bf9' or handles[-1][8:].hex() != 'f557190f8aaab160789272ce086b8b69d6a8037b152de150332603dae3dc098f':
        raise ValueError('Map dependency differs from the measured reference')
    return handles


def transform(header: dict, initial: dict, details: dict, battlelobby: bytes, observation: dict):
    handles = validate_observation(observation)
    game = initial['m_syncLobbyState']['m_gameDescription']
    if header['m_version']['m_build'] != BUILD or header['m_version']['m_baseBuild'] != BUILD or header['m_dataBuildNum'] != BUILD:
        raise ValueError('Source client version differs')
    if header['m_ngdpRootKey']['m_data'].hex() != observation['root'] or header['m_replayCompatibilityHash']['m_data'].hex() != observation['compatibility_hash']:
        raise ValueError('Source identity differs; this experiment does not retarget clients')
    if details['m_title'] != b'Dragon Shire' or [game['m_mapSizeX'], game['m_mapSizeY']] != observation['map_size']:
        raise ValueError('Source map identity differs')
    for key, value in (('m_mapFileName', bytes.fromhex(observation['map_file_name_hex'])),
                       ('m_mapAuthorName', bytes.fromhex(observation['map_author_hex'])),
                       ('m_isBlizzardMap', True), ('m_hasExtensionMod', False)):
        if game[key] != value:
            raise ValueError(f'Map identity differs: {key}')
    old = game['m_cacheHandles']
    if len(old) != 5 or old[:4] != handles[:4] or details['m_cacheHandles'] != old:
        raise ValueError('Unexpected common dependencies or mismatched duplicate lists')
    if game['m_mapFileSyncChecksum'] != 759447839 or game['m_modFileSyncChecksum'] != 3522231966:
        raise ValueError('Unexpected source checksums')
    differences = {key: {'candidate': game['m_gameOptions'].get(key), 'reference': observation['game_options'].get(key)}
                   for key in set(game['m_gameOptions']) | set(observation['game_options'])
                   if game['m_gameOptions'].get(key) != observation['game_options'].get(key)}
    if set(differences) - MODE_DIFFERENCES:
        raise ValueError('Reference has additional unreviewed game-mode differences')
    target_initial, target_details = copy.deepcopy(initial), copy.deepcopy(details)
    target_game = target_initial['m_syncLobbyState']['m_gameDescription']
    changes = []
    for field, value in zip(MAP_FIELDS, (observation['map_checksum'], observation['mod_checksum'], handles), strict=True):
        note(changes, '/initData/m_syncLobbyState/m_gameDescription/' + field, 'same-map-reference', target_game[field], value)
        target_game[field] = copy.deepcopy(value)
    note(changes, '/details/m_cacheHandles', 'same-map-reference', target_details['m_cacheHandles'], handles)
    target_details['m_cacheHandles'] = copy.deepcopy(handles)
    target_battlelobby, prefix = replace_prefix(battlelobby, old, handles)
    note(changes, '/server.battlelobby/dependency-prefix', 'replace-verified-prefix-preserve-tail',
         [cache_handle(h) for h in old], [cache_handle(h) for h in handles])
    return target_initial, target_details, target_battlelobby, changes, prefix, differences


def repair(source: Path, output: Path, observation: dict) -> dict:
    source, output = Path(source), Path(output)
    if output.exists() or source.resolve() == output.resolve():
        raise FileExistsError(output)
    validate_observation(observation)
    if sha(source.read_bytes()) != SOURCE_SHA256:
        raise ValueError('Expected immutable CONTROLS_R4 input')
    before = inspect_reference(source, 96477, BUILD)
    integrity(source)
    p = schema()
    header, initial, details, battlelobby = read_models(source)
    intended, intended_details, target_battlelobby, changes, prefix, mode = transform(header, initial, details, battlelobby, observation)
    encoder = SemanticEncoder(p.typeinfos)
    encoder.instance(p.replay_initdata_typeid, intended)
    details_encoder = SortedVersionedEncoder(p.typeinfos)
    details_encoder.instance(p.game_details_typeid, intended_details)
    replacements = {'replay.initData': encoder.getvalue(), 'replay.details': details_encoder.getvalue(),
                    'replay.server.battlelobby': target_battlelobby}
    archive = MPQArchive(source)
    try:
        header_bytes = archive.header['user_data_header']['content']
        names = archive.read_file('(listfile)').decode('ascii').splitlines()
        original = {name: archive.read_file(name) for name in names}
        if any(value is None for value in original.values()):
            raise ValueError('Source has a missing replay member')
    finally:
        archive.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='dragon-r5-', dir=output.parent) as directory:
        stage = Path(directory) / 'checkpoint'
        stage.mkdir()
        path = stage / OUTPUT_NAME
        container = native_replace(source, path, header_bytes, replacements)
        after = inspect_reference(path, 96477, BUILD)
        checksum_results = integrity(path)
        from mpyq import MPQArchive as IndependentArchive
        check = MPQArchive(path)
        independent = IndependentArchive(str(path), listfile=False)
        try:
            if check.header['user_data_header']['content'] != header_bytes or independent.header['user_data_header']['content'] != header_bytes:
                raise ValueError('Unintended replay header change')
            if set(check.read_file('(listfile)').decode('ascii').splitlines()) != set(names):
                raise ValueError('Archive member set changed')
            expected = {**original, **replacements}
            for name, payload in expected.items():
                if check.read_file(name) != payload or (independent.read_file(name) or b'') != payload:
                    raise ValueError(f'Archive payload mismatch: {name}')
            native = stormlib_check(path, {**expected, '(listfile)': check.read_file('(listfile)'),
                                          '(attributes)': check.read_file('(attributes)')}, True)
        finally:
            check.close()
            independent.file.close()
        observed = read_models(path)
        if observed != (header, intended, intended_details, target_battlelobby):
            raise ValueError('Decoded candidate differs from the intended transform')
        if before['streams'] != after['streams']:
            raise ValueError('An event stream changed')
        if sha(source.read_bytes()) != SOURCE_SHA256:
            raise ValueError('Immutable source changed')
        artifact = {'name': path.name, **publish_binary(path)}
        report = {'format': 'hots-dragon-dependency-repair-v1', 'status': 'experimental-awaiting-client-test',
                  'build': BUILD, 'source_sha256': SOURCE_SHA256, 'reference_sha256': REFERENCE_SHA256,
                  'reference_observation_sha256': sha(dump(observation).encode('ascii')),
                  'artifact': artifact, 'container': container, 'native_checksums': checksum_results,
                  'native_payload_check': native, 'independent_mpyq_equal': True,
                  'header_bytes_preserved': True, 'all_event_bytes_preserved': True,
                  'events': {kind: value['count'] for kind, value in after['streams'].items()},
                  'changed_members': list(replacements), 'changes': len(changes), 'battlelobby_prefix': prefix,
                  'map_checksum_before': initial['m_syncLobbyState']['m_gameDescription']['m_mapFileSyncChecksum'],
                  'map_checksum_after': observation['map_checksum'],
                  'mod_checksum_before': initial['m_syncLobbyState']['m_gameDescription']['m_modFileSyncChecksum'],
                  'mod_checksum_after': observation['mod_checksum'],
                  'reference_mode_differences_not_copied': mode,
                  'client_playback_validated': False, 'simulation_compatibility_validated': False,
                  'limitations': ['The donor is a custom game; the recorded matchmaking settings are retained, not copied.',
                                  'Map/mod checksums and three dependency lists are matched to the observed same-map reference.',
                                  'Cache references do not embed or independently validate the referenced mod files.',
                                  'The rest of the 2016 battlelobby and opaque synchronization data remain unchanged.',
                                  'Numeric ability/unit catalogs and 2016 game rules are not ported by changing dependency metadata.',
                                  'No HotS executable was run; observed-payload validation uses schema 96477.']}
        write_json(stage / 'report.json', report)
        write_json(stage / 'reference-observation.json', observation)
        write_json(stage / 'candidate-profile.json', after)
        (stage / 'changes.jsonl').write_text(''.join(dump(change) + '\n' for change in changes), encoding='ascii')
        if output.exists():
            raise FileExistsError(output)
        shutil.move(str(stage), str(output))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--reference', type=Path)
    group.add_argument('--observation', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    observation = observe(args.reference) if args.reference else json.loads(args.observation.read_text(encoding='ascii'))
    print(json.dumps(repair(args.source, args.output, observation), indent=2))


if __name__ == '__main__':
    main()
