from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import tempfile
from pathlib import Path

from encoders import encode_header
from migrate_replay import SOURCE_SHA256, decode_events, dump, encode_events, write_json
from mpq_rebuild import rebuild_replay, verify_container
from protocol_loader import load_protocol
from reference_replay import TARGET_FIELDS, checked_archive, inspect_reference, native


def apply_metadata(header: dict, events: list[dict], profile: dict) -> tuple[dict, list[dict], list[dict]]:
    if profile.get('observed_payload_roundtrip') is not True:
        raise ValueError('Reference payload validation is required')
    if not profile.get('file_sha256') or len(profile['file_sha256']) != 64:
        raise ValueError('Reference digest is required')
    result = copy.deepcopy(header)
    after = copy.deepcopy(events)
    changes = []
    for key in TARGET_FIELDS:
        actual_key = 'm_fixedFileHash' if key == 'm_replayCompatibilityHash' and 'm_fixedFileHash' in result else key
        if actual_key not in result:
            raise ValueError(f'Target header cannot represent {key}')
        value = copy.deepcopy(profile['target'][key])
        if result[actual_key] != value:
            changes.append({'path': f'/header/{actual_key}', 'before': result[actual_key], 'after': value})
            result[actual_key] = value
    count = 0
    for index, event in enumerate(after):
        if event['_event'] != 'NNet.Game.SUserOptionsEvent':
            continue
        count += 1
        for key in ('m_buildNum', 'm_baseBuildNum', 'm_versionFlags'):
            value = profile['user_options'][key]
            if event[key] != value:
                changes.append({'path': f'/game/{index}/{key}', 'before': event[key], 'after': value})
                event[key] = value
    if count != 10:
        raise ValueError(f'Expected the ten TEN_GREYMANE player-option events, found {count}')
    return result, after, changes


def publish_binary(path: Path) -> dict:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    lines = base64.encodebytes(raw).decode('ascii').splitlines(keepends=True)
    parts = []
    for index, start in enumerate(range(0, len(lines), 1000)):
        part = path.with_name(path.name + f'.base64.part{index:03d}')
        part.write_text(''.join(lines[start:start + 1000]), encoding='ascii', newline='\n')
        parts.append(part)
    decoded = base64.b64decode(''.join(''.join(p.read_text().split()) for p in parts), validate=True)
    if decoded != raw:
        raise AssertionError('Candidate Base64 round-trip failed')
    path.with_name(path.name + '.sha256').write_text(f'{digest}  {path.name}\n', encoding='ascii')
    return {'sha256': digest, 'size': len(raw), 'parts': len(parts), 'base64_roundtrip_validated': True}


def bind(checkpoint: Path, reference: Path, output: Path, expected_build: int,
         require_stormlib: bool = False, local: bool = False) -> dict:
    checkpoint, reference, output = Path(checkpoint), Path(reference), Path(output)
    if output.exists():
        raise FileExistsError('A client experiment must use a new output directory')
    source_report = json.loads((checkpoint / 'report.json').read_text(encoding='utf-8'))
    if source_report.get('source_sha256') != SOURCE_SHA256:
        raise ValueError('Checkpoint is not scoped to the preserved TEN_GREYMANE source')
    if source_report.get('independent_validation', {}).get('blizzard_decoded_all_streams') is not True:
        raise ValueError('An independently validated protocol checkpoint is required')
    schema = source_report['target_protocol']
    source = checkpoint / f'TEN_GREYMANE_protocol{schema}.StormReplay'
    if hashlib.sha256(source.read_bytes()).hexdigest() != source_report['output_sha256']:
        raise ValueError('Checkpoint SHA-256 does not match its validation report')
    if source.resolve() == reference.resolve():
        raise ValueError('The generated checkpoint is not an independent reference')
    if expected_build < schema:
        raise ValueError('Reference build predates the chosen protocol checkpoint')
    profile = inspect_reference(reference, schema, expected_build, local)
    p = load_protocol(schema, local)
    archive = checked_archive(source)
    try:
        header = p.decode_replay_header(archive.header['user_data_header']['content'])
        events = list(decode_events(archive.read_file('replay.game.events'), p, 'game'))
        intended_header, intended_events, changes = apply_metadata(header, events, profile)
        if len(events) != source_report['events']['game']:
            raise ValueError('Checkpoint game-event count differs from its report')
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.client-experiment-', dir=output.parent) as temporary:
            stage = Path(temporary) / 'candidate'
            stage.mkdir()
            path = stage / f'TEN_GREYMANE_client{expected_build}_EXPERIMENTAL.StormReplay'
            container = rebuild_replay(source, path, encode_header(intended_header, p),
                                       {'replay.game.events': encode_events(intended_events, p, 'game')})
            checked = checked_archive(path)
            independent = None
            try:
                import mpyq
                from verify_checkpoint import stormlib_check
                independent = mpyq.MPQArchive(str(path), listfile=False)
                names = archive.read_file('(listfile)').decode().splitlines() + ['(listfile)', '(attributes)']
                members = {}
                for name in dict.fromkeys(names):
                    value = checked.read_file(name)
                    if independent.read_file(name) != value:
                        raise AssertionError(f'Independent MPQ reader disagrees: {name}')
                    if name not in ('replay.game.events', '(attributes)') and value != archive.read_file(name):
                        raise AssertionError(f'Untouched member changed: {name}')
                    members[name] = value
                actual_header = p.decode_replay_header(independent.header['user_data_header']['content'])
                if actual_header != intended_header:
                    raise AssertionError('Candidate header does not round-trip')
                actual = list(decode_events(members['replay.game.events'], p, 'game'))
                if actual != intended_events:
                    raise AssertionError('Candidate game events do not round-trip')
                official = list(p.decode_replay_game_events(members['replay.game.events']))
                if native(official) != native(intended_events):
                    raise AssertionError('Official decoder disagrees with candidate game events')
                checks = {'mpq_v4': verify_container(path), 'mpyq_all_members_equal': True,
                          'stormlib': stormlib_check(path, members, require_stormlib),
                          'official_candidate_game_decode': not local, 'untouched_members_equal': True,
                          'protocol_provider': 'local' if local else 'Blizzard/heroprotocol'}
            finally:
                if independent is not None:
                    independent.file.close()
                checked.close()
            artifact = publish_binary(path)
            report = {'format': 'hots-client-binding-experiment-v1', 'status': 'experimental-not-playback-validated',
                      'source_sha256': SOURCE_SHA256, 'input_checkpoint_sha256': source_report['output_sha256'],
                      'declared_client_build': expected_build, 'schema_build': schema,
                      'reference_sha256': profile['file_sha256'], 'events': source_report['events'],
                      'artifact': artifact, 'metadata_changes': len(changes), 'container': container,
                      'checks': checks, 'client_playback_validated': False, 'simulation_compatibility_validated': False,
                      'target_schema_is_official_exact_build': not local and profile['declared_base_matches_schema'],
                      'limitations': ['The reference is fully decoded, but a newer complete schema is not established.',
                                      'Original map caches, ability/unit identifiers and opaque synchronization data remain unchanged.',
                                      'Copied root/data/hash metadata does not repair changed simulation rules.',
                                      'No game executable has loaded or played this candidate.']}
            write_json(stage / 'report.json', report)
            write_json(stage / 'reference-profile.json', profile)
            write_json(stage / 'header.before.json', header)
            write_json(stage / 'header.after.json', intended_header)
            (stage / 'metadata.changes.jsonl').write_text(''.join(dump(c) + '\n' for c in changes), encoding='utf-8')
            if output.exists():
                raise FileExistsError(output)
            stage.rename(output)
            return report
    finally:
        archive.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('checkpoint', type=Path)
    parser.add_argument('reference', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-build', type=int, required=True)
    parser.add_argument('--require-stormlib', action='store_true')
    args = parser.parse_args()
    print(json.dumps(bind(args.checkpoint, args.reference, args.output, args.expected_build,
                          args.require_stormlib), indent=2))
