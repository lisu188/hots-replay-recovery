from __future__ import annotations

import argparse
import copy
import ctypes
import ctypes.util
import hashlib
import json
import re
import shutil
import struct
import tempfile
from pathlib import Path

from bind_client_metadata import publish_binary
from encoders import encode_header
from migrate_replay import SOURCE_SHA256, SemanticDecoder, SemanticEncoder, decode_events, encode_events, note, dump, write_json
from mpq_reader import MPQArchive
from protocol_loader import load_protocol
from reference_replay import inspect_reference

INPUT_SHA256 = '2ecb09f353a30363ad59d04b04d439bb7f0ee623d832000d8d13f7a05dbb0486'
CONFIG_KEY = 'd170b1ad65ebcde3f4252e3088b0c102'
TARGET_BUILD = 98297
OUTPUT_NAME = 'TEN_GREYMANE_client98297_STARTUP_R2_EXPERIMENTAL.StormReplay'
MATCH_OPTIONS = {'m_advancedSharedControl': False, 'm_amm': True, 'm_battleNet': True,
                 'm_clientDebugFlags': 289, 'm_competitive': True, 'm_cooperative': False,
                 'm_fog': 0, 'm_heroDuplicatesAllowed': True, 'm_lockTeams': True,
                 'm_noVictoryOrDefeat': False, 'm_observers': 0, 'm_practice': False,
                 'm_randomRaces': False, 'm_teamsTogether': False, 'm_userDifficulty': 0}


def parse_build_config(raw: bytes) -> dict:
    if len(raw) > 262144 or hashlib.md5(raw).hexdigest() != CONFIG_KEY:
        raise ValueError('Build configuration does not match the installed content-addressed key')
    fields = {}
    for line in raw.decode('ascii').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, separator, value = line.partition(' = ')
        if not separator or key in fields:
            raise ValueError('Invalid or duplicate build configuration field')
        fields[key] = value
    if fields.get('build-name') != 'B98297' or fields.get('build-product') != 'Hero':
        raise ValueError('Unexpected product or build')
    if fields.get('build-release-name') != 'Heroes.57':
        raise ValueError('Unexpected release branch')
    for key in ('root', 'build-replay-hash'):
        if not re.fullmatch(r'[0-9a-f]{32}', fields.get(key, '')):
            raise ValueError(f'Invalid {key}')
    return fields


def v4_profile(path: Path) -> dict:
    raw = Path(path).read_bytes()
    if len(raw) < 16 or raw[:4] != b'MPQ\x1b':
        raise ValueError('Missing replay user-data header')
    base = struct.unpack_from('<I', raw, 8)[0]
    if base < 16 or base + 208 > len(raw) or raw[base:base + 4] != b'MPQ\x1a':
        raise ValueError('Invalid MPQ header bounds')
    if struct.unpack_from('<I', raw, base + 4)[0] != 208 or struct.unpack_from('<H', raw, base + 12)[0] != 3:
        raise ValueError('Expected MPQ v4')
    size, bet, het = struct.unpack_from('<QQQ', raw, base + 44)
    raw_chunk = struct.unpack_from('<I', raw, base + 108)[0]
    if not bet or not het or not raw_chunk or base + size > len(raw):
        raise ValueError('Extended tables or raw-chunk protection are absent')
    if hashlib.md5(raw[base:base + 192]).digest() != raw[base + 192:base + 208]:
        raise ValueError('MPQ header checksum mismatch')
    for position, size_offset, signature in ((het, 92, b'HET\x1a'), (bet, 100, b'BET\x1a')):
        count = struct.unpack_from('<Q', raw, base + size_offset)[0]
        if count < 12 or position < 208 or position + count > size:
            raise ValueError('Invalid extended table bounds')
        if raw[base + position:base + position + 4] != signature:
            raise ValueError('Invalid extended table signature')
    return {'mpq_version': 4, 'het_present': True, 'bet_present': True,
            'raw_chunk_size': raw_chunk, 'header_md5': True, 'archive_bytes': size}


def native_replace(source: Path, output: Path, header: bytes, replacements: dict[str, bytes]) -> dict:
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve() or output.exists():
        raise FileExistsError('Native rewrite requires a new output path')
    original = source.read_bytes()
    before = v4_profile(source)
    if len(header) != struct.unpack_from('<I', original, 12)[0]:
        raise ValueError('This native rewrite preserves the existing user-data allocation')
    if any(not key.startswith('replay.') or len(value) > 64 * 1024 * 1024 for key, value in replacements.items()):
        raise ValueError('Invalid member replacement')
    library = ctypes.util.find_library('storm')
    if not library:
        raise RuntimeError('Native StormLib is required; no classic-table fallback is permitted')
    lib = ctypes.CDLL(library)
    handle, dword = ctypes.c_void_p, ctypes.c_uint32
    signatures = {
        'SFileOpenArchive': ([ctypes.c_char_p, dword, dword, ctypes.POINTER(handle)], ctypes.c_bool),
        'SFileCreateFile': ([handle, ctypes.c_char_p, ctypes.c_uint64, dword, dword, dword, ctypes.POINTER(handle)], ctypes.c_bool),
        'SFileWriteFile': ([handle, ctypes.c_void_p, dword, dword], ctypes.c_bool),
        'SFileFinishFile': ([handle], ctypes.c_bool),
        'SFileFlushArchive': ([handle], ctypes.c_bool),
        'SFileCloseArchive': ([handle], ctypes.c_bool),
    }
    for name, (arguments, result) in signatures.items():
        function = getattr(lib, name)
        function.argtypes, function.restype = arguments, result
    archive = handle()
    try:
        with output.open('xb') as destination:
            destination.write(original[:16] + header + original[16 + len(header):])
        if not lib.SFileOpenArchive(str(output.resolve()).encode(), 0, 0, ctypes.byref(archive)):
            raise RuntimeError('StormLib could not open the original-format copy for writing')
        try:
            for name in sorted(replacements):
                raw = replacements[name]
                member = handle()
                if not lib.SFileCreateFile(archive, name.encode('ascii'), 0, len(raw), 0, 0x81000200, ctypes.byref(member)):
                    raise RuntimeError(f'StormLib could not replace {name}')
                written = False
                try:
                    buffer = ctypes.create_string_buffer(raw)
                    written = bool(lib.SFileWriteFile(member, buffer, len(raw), 2))
                finally:
                    finished = bool(lib.SFileFinishFile(member))
                if not written or not finished:
                    raise RuntimeError(f'StormLib could not finish {name}')
            if not lib.SFileFlushArchive(archive):
                raise RuntimeError('StormLib failed to flush updated extended tables')
        finally:
            closed = bool(lib.SFileCloseArchive(archive))
            archive = handle()
        if not closed:
            raise RuntimeError('StormLib failed to close the updated archive')
        after = v4_profile(output)
        if before['raw_chunk_size'] != after['raw_chunk_size']:
            raise ValueError('Native rewrite changed raw-chunk size')
        return {'writer': 'native-StormLib-preserve-extended-format', 'before': before, 'after': after}
    except BaseException:
        if archive.value:
            lib.SFileCloseArchive(archive)
        output.unlink(missing_ok=True)
        raise


def repair(source: Path, previous: Path, config: Path, output: Path) -> dict:
    source, previous, config, output = map(Path, (source, previous, config, output))
    if output.exists():
        raise FileExistsError(output)
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError('Unexpected immutable source replay')
    if hashlib.sha256(previous.read_bytes()).hexdigest() != INPUT_SHA256:
        raise ValueError('Unexpected prior client candidate')
    configuration = parse_build_config(config.read_bytes())
    prior_profile = inspect_reference(previous, 96477, 98285)
    p = load_protocol(96477)
    a = MPQArchive(previous)
    original = MPQArchive(source)
    try:
        header = p.decode_replay_header(a.header['user_data_header']['content'])
        intended = copy.deepcopy(header)
        changes = []
        for name in ('m_build', 'm_baseBuild'):
            note(changes, f'/header/m_version/{name}', 'installed-build', intended['m_version'][name], TARGET_BUILD)
            intended['m_version'][name] = TARGET_BUILD
        note(changes, '/header/m_dataBuildNum', 'installed-data-build', intended['m_dataBuildNum'], TARGET_BUILD)
        intended['m_dataBuildNum'] = TARGET_BUILD
        for field, key in (('m_ngdpRootKey', 'root'), ('m_replayCompatibilityHash', 'build-replay-hash')):
            new = {'m_data': bytes.fromhex(configuration[key])}
            note(changes, f'/header/{field}', 'verified-build-config-value', intended[field], new)
            intended[field] = new
        initial = SemanticDecoder(a.read_file('replay.initData'), p.typeinfos).instance(p.replay_initdata_typeid)
        options = initial['m_syncLobbyState']['m_gameDescription']['m_gameOptions']
        if options.get('m_ammId') is not None or {k: v for k, v in options.items() if k != 'm_ammId'} != MATCH_OPTIONS:
            raise ValueError('Lobby no longer matches the narrowly scoped initialization repair')
        note(changes, '/initData/m_syncLobbyState/m_gameDescription/m_gameOptions/m_ammId',
             'explicit-matching-reference-mode-hypothesis', None, 50001)
        options['m_ammId'] = 50001
        encoder = SemanticEncoder(p.typeinfos)
        encoder.instance(p.replay_initdata_typeid, initial)
        events = list(decode_events(a.read_file('replay.game.events'), p, 'game'))
        option_count = 0
        for index, event in enumerate(events):
            if event['_event'] != 'NNet.Game.SUserOptionsEvent':
                continue
            option_count += 1
            for key in ('m_buildNum', 'm_baseBuildNum'):
                note(changes, f'/game/{index}/{key}', 'installed-build', event[key], TARGET_BUILD)
                event[key] = TARGET_BUILD
        if option_count != 10:
            raise ValueError('Expected ten preserved player version records')
        names = a.read_file('(listfile)').decode('ascii').splitlines()
        expected = {name: a.read_file(name) for name in names}
        expected['replay.initData'] = encoder.getvalue()
        expected['replay.game.events'] = encode_events(events, p, 'game')
        replacements = {name: raw for name, raw in expected.items() if raw != original.read_file(name)}
        if set(replacements) != {'replay.initData', 'replay.game.events'}:
            raise ValueError('Unexpected changed source members')
    finally:
        a.close()
        original.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='startup-stage-', dir=output.parent) as temporary:
        stage = Path(temporary) / 'checkpoint'
        stage.mkdir()
        path = stage / OUTPUT_NAME
        container = native_replace(source, path, encode_header(intended, p), replacements)
        profile = inspect_reference(path, 96477, TARGET_BUILD)
        check = MPQArchive(path)
        import mpyq
        from verify_checkpoint import stormlib_check
        independent = mpyq.MPQArchive(str(path), listfile=False)
        try:
            names_after = check.read_file('(listfile)').decode('ascii').splitlines()
            if set(names_after) != set(names):
                raise ValueError('Native rewrite changed the archive member set')
            for name, raw in expected.items():
                if check.read_file(name) != raw or independent.read_file(name) != raw:
                    raise ValueError(f'Payload mismatch: {name}')
            if independent.header['user_data_header']['content'] != encode_header(intended, p):
                raise ValueError('Native rewrite changed the intended replay header')
            native_check = stormlib_check(path, {**expected, '(listfile)': check.read_file('(listfile)'),
                                                '(attributes)': check.read_file('(attributes)')}, True)
        finally:
            check.close()
            independent.close()
        if {k: v['count'] for k, v in profile['streams'].items()} != {'game': 104257, 'message': 155, 'tracker': 6614}:
            raise ValueError('Event count changed')
        for kind in ('message', 'tracker'):
            if prior_profile['streams'][kind]['sha256'] != profile['streams'][kind]['sha256']:
                raise ValueError(f'{kind} stream changed')
        artifact = {'name': path.name, **publish_binary(path)}
        report = {'format': 'hots-startup-repair-v2', 'status': 'experimental-awaiting-client-test',
                  'declared_build': TARGET_BUILD, 'declared_version': '2.57.0.98297',
                  'source_sha256': SOURCE_SHA256, 'prior_candidate_sha256': INPUT_SHA256,
                  'config_md5': CONFIG_KEY, 'config_sha256': hashlib.sha256(config.read_bytes()).hexdigest(),
                  'root_from_verified_config': configuration['root'],
                  'compatibility_hash_from_verified_config': configuration['build-replay-hash'],
                  'metadata_changes': len(changes), 'artifact': artifact, 'container': container,
                  'checks': {'official_observed_payload_roundtrip': True, 'mpyq_payloads_equal': True,
                             'native_stormlib': native_check, 'all_gameplay_commands_preserved': True,
                             'map_and_dependency_identifiers_preserved': True,
                             'message_and_tracker_bytes_preserved': True},
                  'events': {k: v['count'] for k, v in profile['streams'].items()},
                  'client_playback_validated': False, 'crash_root_cause_proven': False,
                  'exact_98297_schema_verified': False,
                  'limitations': ['The 98297 version and data build were observed in the live client log.',
                                  'Root and replay hash are from the MD5-verified installed build configuration, not a 98297 replay.',
                                  'Matchmaking ID 50001 is observed in the same-option Braxis reference; its role in this crash is unproven.',
                                  'Schema 96477 covers these serialized payloads, not every possible 98297 field variant.',
                                  'Legacy map dependencies, opaque synchronization payloads and numeric gameplay catalogs remain unchanged.',
                                  'No HotS executable has played this repaired candidate in the validation environment.']}
        write_json(stage / 'report.json', report)
        write_json(stage / 'header.before.json', header)
        write_json(stage / 'header.after.json', intended)
        write_json(stage / 'metadata.changes.json', changes)
        (stage / 'metadata.changes.jsonl').write_text(''.join(dump(change) + '\n' for change in changes), encoding='ascii')
        write_json(stage / 'candidate-profile.json', profile)
        if output.exists():
            raise FileExistsError(output)
        shutil.move(str(stage), str(output))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--previous', type=Path, required=True)
    parser.add_argument('--build-config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(repair(args.source, args.previous, args.build_config, args.output), indent=2))


if __name__ == '__main__':
    main()
