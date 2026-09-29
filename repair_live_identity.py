from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from bind_client_metadata import apply_metadata, publish_binary
from encoders import encode_header
from migrate_replay import SOURCE_SHA256, SemanticDecoder, decode_events, dump, encode_events, write_json
from mpq_reader import MPQArchive
from protocol_loader import load_protocol
from reference_replay import inspect_reference, metadata
from repair_startup import native_replace
from verify_checkpoint import stormlib_check

R2_SHA256 = '4c6adf30e2c5fc9440c46b2c614c09fc6d3d5d6ef4b4f57f68aaf9a92bbe4915'
DONOR_SHA256 = '05ec458110db57dd5cf6c044cb6b7270d880282ec803abce725f048f91fc3e75'
OUTPUT_NAME = 'TEN_GREYMANE_client98285_NATIVE_R3_EXPERIMENTAL.StormReplay'


def observe_graphics(raw: bytes) -> dict:
    if not raw or len(raw) > 1048576:
        raise ValueError('Invalid graphics log size')
    text = re.sub(r'^GFX\s+\d{2}:\d{2}:\d{2}\.\d{3}\s+', '', raw.decode('utf-8-sig'), flags=re.M)

    def field(name: str) -> str:
        values = re.findall(r'^' + re.escape(name) + r'[ \t]+([^\r\n]+)', text, re.M)
        if len(values) != 1:
            raise ValueError(f'Expected exactly one {name}')
        return values[0].strip()

    version = field('<Version>')
    if not re.fullmatch(r'\d+\.\d+\.\d+\.\d+', version):
        raise ValueError('Invalid live version')
    executable = re.search(r'[\\/]Base(\d+)[\\/]HeroesOfTheStorm_x64\.exe$', field('Executable'))
    data = re.fullmatch(r'B(\d+)', field('<DataBuild>'))
    if not executable or not data:
        raise ValueError('Missing executable/data build')
    if int(executable[1]) != int(version.split('.')[-1]) or int(data[1]) != int(executable[1]):
        raise ValueError('Conflicting live build evidence')
    if not field('Grandparent Executable').lower().endswith('\\battle.net.exe'):
        raise ValueError('Expected a Battle.net launch, not a replay-switch process')
    parameters = field('<Parameters>').split()
    if '-launch' not in parameters or '-sso=1' not in parameters:
        raise ValueError('Expected ordinary live-launch arguments')
    observed = datetime.fromisoformat(field('LocalTime'))
    return {'format': 'hots-live-client-observation-v1', 'source_sha256': hashlib.sha256(raw).hexdigest(),
            'observed_local': observed.isoformat(timespec='milliseconds'),
            'version': version, 'executable_build': int(executable[1]), 'data_build': int(data[1]),
            'launch_kind': 'Battle.net', 'code_revision': int(field('<CodeRevision>'))}


def latest_observation(observations: list[dict]) -> dict:
    if not observations:
        raise ValueError('No live observations')
    ordered = sorted(observations, key=lambda item: datetime.fromisoformat(item['observed_local']))
    latest = ordered[-1]
    if any(item != latest and item['observed_local'] == latest['observed_local'] for item in ordered):
        raise ValueError('Conflicting observations at the same time')
    return latest


def restore_json(value):
    if isinstance(value, dict):
        if set(value) == {'$bytes_base64'}:
            return base64.b64decode(value['$bytes_base64'], validate=True)
        return {key: restore_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [restore_json(item) for item in value]
    return value


def validate_target(profile: dict, observation: dict) -> None:
    if profile.get('file_sha256') != DONOR_SHA256 or profile.get('observed_payload_roundtrip') is not True:
        raise ValueError('Expected the previously validated original Braxis reference profile')
    target = metadata(profile['target'])
    expected = {'m_flags': 1, 'm_major': 2, 'm_minor': 57, 'm_revision': 0, 'm_build': 98285, 'm_baseBuild': 98285}
    if target['m_version'] != expected or target['m_dataBuildNum'] != 98285:
        raise ValueError('Unexpected reference build tuple')
    if target['m_ngdpRootKey']['m_data'].hex() != 'b5114c16bd78f1844ab9fe97cbd9c305':
        raise ValueError('Unexpected donor root')
    if target['m_replayCompatibilityHash']['m_data'] != bytes(16):
        raise ValueError('Expected the actually observed zero replay hash')
    if profile.get('user_options') != {'m_buildNum': 98285, 'm_baseBuildNum': 98285, 'm_versionFlags': 0}:
        raise ValueError('Unexpected reference player-version options')
    if observation.get('format') != 'hots-live-client-observation-v1' or observation.get('launch_kind') != 'Battle.net':
        raise ValueError('Missing live launch observation')
    if not re.fullmatch(r'[0-9a-f]{64}', observation.get('source_sha256', '')):
        raise ValueError('Missing source log digest')
    datetime.fromisoformat(observation['observed_local'])
    if (observation.get('version'), observation.get('executable_build'), observation.get('data_build')) != ('2.57.0.98285', 98285, 98285):
        raise ValueError('Reference no longer matches the observed running client')


def repair(source: Path, r2: Path, profile_path: Path, observation_path: Path, output: Path) -> dict:
    source, r2, profile_path, observation_path, output = map(Path, (source, r2, profile_path, observation_path, output))
    if output.exists():
        raise FileExistsError(output)
    for path, expected in ((source, SOURCE_SHA256), (r2, R2_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Unexpected immutable input digest')
    profile = restore_json(json.loads(profile_path.read_text(encoding='utf-8')))
    observation = json.loads(observation_path.read_text(encoding='utf-8'))
    validate_target(profile, observation)
    p = load_protocol(96477)
    before_profile = inspect_reference(r2, 96477, 98297)
    archive, original = MPQArchive(r2), MPQArchive(source)
    try:
        header = p.decode_replay_header(archive.header['user_data_header']['content'])
        events = list(decode_events(archive.read_file('replay.game.events'), p, 'game'))
        intended, after, changes = apply_metadata(header, events, profile)
        names = archive.read_file('(listfile)').decode('ascii').splitlines()
        expected = {name: archive.read_file(name) for name in names}
        previous_game = expected['replay.game.events']
        expected['replay.game.events'] = encode_events(after, p, 'game')
        if len(previous_game) != len(expected['replay.game.events']):
            raise ValueError('Client-version-only update changed game-stream size')
        changed_bytes = sum(a != b for a, b in zip(previous_game, expected['replay.game.events']))
        if changed_bytes != 20 or hashlib.sha256(expected['replay.game.events']).hexdigest() != '9b584cfeef157d5bc3a012767db95630ecb236c8bfb27075d9b67ec6332d7205':
            raise ValueError('Expected the exact preserved 98285 command stream')
        initial = SemanticDecoder(expected['replay.initData'], p.typeinfos).instance(p.replay_initdata_typeid)
        if initial['m_syncLobbyState']['m_gameDescription']['m_gameOptions']['m_ammId'] != 50001:
            raise ValueError('R2 lobby hypothesis was not preserved')
        replacements = {name: raw for name, raw in expected.items() if original.read_file(name) != raw}
        if set(replacements) != {'replay.initData', 'replay.game.events'}:
            raise ValueError('Unexpected source-member replacement')
    finally:
        archive.close()
        original.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='live-r3-', dir=output.parent) as temporary:
        stage = Path(temporary) / 'checkpoint'
        stage.mkdir()
        path = stage / OUTPUT_NAME
        container = native_replace(source, path, encode_header(intended, p), replacements)
        candidate = inspect_reference(path, 96477, 98285)
        import mpyq
        checked, independent = MPQArchive(path), mpyq.MPQArchive(str(path), listfile=False)
        try:
            if set(checked.read_file('(listfile)').decode('ascii').splitlines()) != set(names):
                raise ValueError('Archive member set changed')
            for name, raw in expected.items():
                if checked.read_file(name) != raw or independent.read_file(name) != raw:
                    raise ValueError(f'Payload mismatch: {name}')
            if independent.header['user_data_header']['content'] != encode_header(intended, p):
                raise ValueError('Header mismatch')
            members = {**expected, '(listfile)': checked.read_file('(listfile)'), '(attributes)': checked.read_file('(attributes)')}
            native_check = stormlib_check(path, members, True)
        finally:
            checked.close()
            independent.file.close()
        if {key: item['count'] for key, item in candidate['streams'].items()} != {'game': 104257, 'message': 155, 'tracker': 6614}:
            raise ValueError('Event counts changed')
        if any(candidate['streams'][kind]['sha256'] != before_profile['streams'][kind]['sha256'] for kind in ('message', 'tracker')):
            raise ValueError('Untouched event stream changed')
        report = {'format': 'hots-live-identity-r3', 'status': 'experimental-awaiting-client-test',
                  'artifact': {'name': OUTPUT_NAME, **publish_binary(path)}, 'live_observation': observation,
                  'source_sha256': SOURCE_SHA256, 'r2_sha256': R2_SHA256, 'reference_sha256': DONOR_SHA256,
                  'declared_version': '2.57.0.98285', 'metadata_changes': len(changes),
                  'game_stream_changed_bytes_from_r2': changed_bytes, 'container': container,
                  'checks': {'official_observed_payload_roundtrip': True, 'native_stormlib': native_check,
                             'mpyq_payloads_equal': True, 'r2_lobby_preserved': True,
                             'message_tracker_and_map_payloads_preserved': True},
                  'client_playback_validated': False, 'ui_old_label_removed': None, 'crash_fixed': None,
                  'limitations': ['Matches the supplied dated live-launch observation, not every future client.',
                                  'The original reference profile is reused; CI does not receive private donor bytes.',
                                  'R2 lobby and native format are retained, but their relationship to the old crash is unproven.',
                                  'Official schema 96477 validates these payloads, not all possible 98285 structures.',
                                  'Legacy map dependencies, opaque streams and simulation rules remain unresolved.']}
        write_json(stage / 'report.json', report)
        write_json(stage / 'candidate-profile.json', candidate)
        write_json(stage / 'header.before.json', header)
        write_json(stage / 'header.after.json', intended)
        (stage / 'metadata.changes.jsonl').write_text(''.join(dump(change) + '\n' for change in changes), encoding='ascii')
        if output.exists():
            raise FileExistsError(output)
        shutil.move(str(stage), str(output))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='command', required=True)
    observation = commands.add_parser('observe')
    observation.add_argument('log', type=Path)
    observation.add_argument('output', type=Path)
    build = commands.add_parser('build')
    for key in ('source', 'r2', 'profile', 'observation', 'output'):
        build.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'observe':
        result = observe_graphics(args.log.read_bytes())
        with args.output.open('x', encoding='utf-8') as handle:
            handle.write(json.dumps(result, indent=2) + '\n')
    else:
        print(json.dumps(repair(args.source, args.r2, args.profile, args.observation, args.output), indent=2))


if __name__ == '__main__':
    main()
