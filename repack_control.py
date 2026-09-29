from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from pathlib import Path

from bind_client_metadata import publish_binary
from migrate_replay import write_json
from mpq_rebuild import rebuild_replay, verify_container
from reference_replay import checked_archive, inspect_reference


def archive_manifest(path: Path) -> dict:
    import mpyq
    data = Path(path).read_bytes()
    archive = checked_archive(path)
    independent = None
    try:
        independent = mpyq.MPQArchive(str(path))
        names = list(dict.fromkeys([line.decode('ascii') for line in archive.read_file('(listfile)').splitlines()]
                                  + ['(listfile)', '(attributes)']))
        members, indices = {}, set()
        for name in names:
            entry = archive.get_hash_table_entry(name)
            external = independent.get_hash_table_entry(name)
            if entry is None or external is None:
                raise ValueError('A listed archive member is missing')
            indices.add(entry.block_table_index)
            raw = archive.read_file(name)
            other = independent.read_file(name)
            if (raw or b'') != (other or b''):
                raise ValueError('Independent MPQ readers disagree')
            block = archive.block_table[entry.block_table_index]
            start = archive.header['offset'] + block.offset
            compressed = data[start:start + block.archived_size]
            members[name] = {'size': len(raw or b''), 'sha256': hashlib.sha256(raw or b'').hexdigest(),
                             'archived_size': len(compressed), 'archived_sha256': hashlib.sha256(compressed).hexdigest(),
                             'flags': block.flags}
        live = {index for index, block in enumerate(archive.block_table) if block.flags & 0x80000000}
        if indices != live:
            raise ValueError('The control cannot verify every active archive block')
        return {'header': archive.header['user_data_header']['content'], 'members': members}
    finally:
        archive.close()
        if independent is not None:
            independent.file.close()


def repack(source: Path, destination: Path, expected_sha256: str, schema_build: int,
           expected_build: int, local: bool = False) -> dict:
    source, destination = Path(source), Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    if not re.fullmatch(r'[0-9a-fA-F]{64}', expected_sha256):
        raise ValueError('An explicit input SHA-256 is required')
    initial_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if initial_hash != expected_sha256.lower():
        raise ValueError('Control source SHA-256 does not match')
    source_profile = inspect_reference(source, schema_build, expected_build, local)
    before = archive_manifest(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.replay-control-', dir=destination.parent) as directory:
        staging = Path(directory) / 'complete'
        staging.mkdir()
        replay = staging / f'CONTROL_{expected_build}_REPACKED.StormReplay'
        container = rebuild_replay(source, replay, before['header'], {})
        after = archive_manifest(replay)
        if before != after:
            raise ValueError('Container control unexpectedly changed a header or member payload')
        checks = verify_container(replay)
        output_profile = inspect_reference(replay, schema_build, expected_build, local)
        for key in ('target', 'user_options', 'streams'):
            if source_profile[key] != output_profile[key]:
                raise ValueError(f'Container control changed {key}')
        if hashlib.sha256(source.read_bytes()).hexdigest() != initial_hash:
            raise ValueError('Control source changed during validation')
        binary = {'name': replay.name, **publish_binary(replay)}
        report = {'format': 'hots-container-control-v1', 'purpose': 'Isolate MPQ container rewriting from replay payload conversion',
                  'source_sha256': initial_hash, 'artifact': binary, 'source_build': expected_build,
                  'schema_build': schema_build, 'schema_provider': output_profile['protocol_provider'],
                  'header_bytes_unchanged': True, 'all_member_bytes_unchanged': True,
                  'all_archived_member_bytes_unchanged': True, 'member_count': len(after['members']),
                  'all_members': after['members'], 'independent_mpyq_all_members_equal': True,
                  'source_and_control_observed_payload_roundtrip': True,
                  'streams': {kind: {'count': value['count'], 'sha256': value['sha256']}
                              for kind, value in output_profile['streams'].items()},
                  'container_checks': checks,
                  'layout_changes': {'het_bet_tables': container['het_bet_tables'], 'raw_chunk_size': container['raw_chunk_size']},
                  'semantic_changes': [], 'client_playback_validated': False,
                  'simulation_compatibility_validated': False,
                  'privacy': 'Control retains private donor contents. Do not publish its replay, Base64 parts or raw donor to public Git.',
                  'limitations': ['The control intentionally retains the donor build; version switching may still occur.',
                                  'Both source and control must be tested in the game before drawing a causal conclusion.',
                                  'This is a container-only control, not a recovered TEN_GREYMANE match.']}
        write_json(staging / 'report.json', report)
        write_json(staging / 'source-profile.json', source_profile)
        write_json(staging / 'control-profile.json', output_profile)
        if destination.exists():
            raise FileExistsError(destination)
        staging.rename(destination)
        return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--schema-build', type=int, required=True)
    parser.add_argument('--expected-build', type=int, required=True)
    parser.add_argument('--local-schema', action='store_true')
    args = parser.parse_args()
    result = repack(args.source, args.destination, args.expected_sha256, args.schema_build,
                    args.expected_build, args.local_schema)
    print(json.dumps({'name': result['artifact']['name'], 'sha256': result['artifact']['sha256'],
                      'unchanged_members': result['member_count'], 'client_playback_validated': False}))


if __name__ == '__main__':
    main()
