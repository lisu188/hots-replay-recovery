from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

OPAQUE_MEMBERS = (
    'replay.load.info', 'replay.resumable.events', 'replay.server.battlelobby',
    'replay.smartcam.events', 'replay.sync.events', 'replay.sync.history',
)
COMMAND_FIELDS = (
    '_gameloop', '_userid', 'm_cmdFlags', 'm_abil', 'm_data',
    'm_sequence', 'm_otherUnit', 'm_unitGroup',
)
CACHE_PATH = re.compile(rb'(?i)Cache[\\/]([0-9a-f]{2})[\\/]([0-9a-f]{2})[\\/]([0-9a-f]{64})\.([a-z0-9]{4})')


def cache_handle(raw: bytes) -> dict:
    if not isinstance(raw, bytes) or len(raw) != 40:
        raise ValueError('Cache handles must be exactly 40 bytes')
    extension = raw[:4].decode('ascii')
    region = raw[4:8].strip(b'\0').decode('ascii')
    if not re.fullmatch(r'[a-z0-9]{4}', extension) or not re.fullmatch(r'[A-Z]{2}', region):
        raise ValueError('Unsupported cache handle extension or region')
    digest = raw[8:].hex()
    return {'extension': extension, 'region': region, 'digest': digest,
            'relative_path': f'{digest[:2]}/{digest[2:4]}/{digest}.{extension}'}


def battlelobby_cache_paths(raw: bytes) -> list[str]:
    paths = []
    for match in CACHE_PATH.finditer(raw):
        first, second, digest, extension = [part.decode('ascii').lower() for part in match.groups()]
        if first != digest[:2] or second != digest[2:4]:
            raise ValueError('Inconsistent cache-directory prefix in battlelobby')
        paths.append(f'{first}/{second}/{digest}.{extension}')
    return paths


def describe(path: Path, schema: int, local: bool = False) -> dict:
    from migrate_replay import decode_events, dump
    from protocol_loader import load_protocol
    from reference_replay import MAX_EVENTS, checked_archive

    path = Path(path)
    digest_before = hashlib.sha256(path.read_bytes()).hexdigest()
    p = load_protocol(schema, local)
    a = checked_archive(path)
    try:
        header = p.decode_replay_header(a.header['user_data_header']['content'])
        details = p.decode_replay_details(a.read_file('replay.details'))
        lobby = p.decode_replay_initdata(a.read_file('replay.initData'))['m_syncLobbyState']['m_gameDescription']
        handles = [cache_handle(raw) for raw in details.get('m_cacheHandles') or []]
        lobby_handles = [cache_handle(raw) for raw in lobby.get('m_cacheHandles') or []]
        opaque = {}
        for name in OPAQUE_MEMBERS:
            entry = a.get_hash_table_entry(name)
            raw = a.read_file(name) if entry is not None else None
            opaque[name] = {'present': entry is not None, 'bytes': len(raw or b''),
                            'sha256': hashlib.sha256(raw or b'').hexdigest() if entry is not None else None}
        count, commands, nonempty_vectors = 0, 0, 0
        command_digest = hashlib.sha256()
        types = Counter()
        for event in decode_events(a.read_file('replay.game.events'), p, 'game'):
            count += 1
            if count > MAX_EVENTS:
                raise ValueError('Game event limit exceeded')
            types[event['_event']] += 1
            if event['_event'] == 'NNet.Game.SCmdEvent':
                commands += 1
                projection = {key: event[key] for key in COMMAND_FIELDS}
                command_digest.update((dump(projection) + '\n').encode('ascii'))
                nonempty_vectors += event.get('m_vector') is not None
        tracker_raw = a.read_file('replay.tracker.events')
        paths = battlelobby_cache_paths(a.read_file('replay.server.battlelobby') or b'')
        result = {
            'file_sha256': digest_before, 'schema_build': schema,
            'schema_provider': 'repository-local' if local else 'Blizzard-sourced',
            'declared_build': header['m_version']['m_build'],
            'elapsed_game_loops': header['m_elapsedGameLoops'],
            'map_title': details['m_title'].decode('utf-8'),
            'map_sync_checksum': lobby['m_mapFileSyncChecksum'],
            'mod_sync_checksum': lobby['m_modFileSyncChecksum'],
            'cache_handles': handles,
            'details_and_lobby_handles_equal_in_order': handles == lobby_handles,
            'battlelobby_cache_paths': paths,
            'battlelobby_paths_match_details_in_order': paths == [h['relative_path'] for h in handles],
            'opaque_members': opaque, 'game_events': count, 'game_event_types': dict(sorted(types.items())),
            'command_count': commands, 'command_projection_sha256': command_digest.hexdigest(),
            'command_projection_fields': list(COMMAND_FIELDS), 'nonempty_command_vectors': nonempty_vectors,
            'tracker_bytes': len(tracker_raw or b''),
            'tracker_sha256': hashlib.sha256(tracker_raw or b'').hexdigest(),
        }
    finally:
        a.close()
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest_before:
        raise ValueError('Replay changed during inspection')
    return result


def compare(source: dict, candidate: dict, reference: dict | None = None) -> dict:
    old_paths = {h['relative_path'] for h in source['cache_handles']}
    new_paths = {h['relative_path'] for h in candidate['cache_handles']}
    result = {
        'format': 'hots-dependency-audit-v1', 'source': source, 'candidate': candidate,
        'checks': {
            'same_map_title': source['map_title'] == candidate['map_title'],
            'same_duration': source['elapsed_game_loops'] == candidate['elapsed_game_loops'],
            'same_map_and_mod_checksums': all(source[k] == candidate[k] for k in ('map_sync_checksum', 'mod_sync_checksum')),
            'same_cache_handles_in_order': source['cache_handles'] == candidate['cache_handles'],
            'same_opaque_members': source['opaque_members'] == candidate['opaque_members'],
            'same_command_projection': source['command_count'] == candidate['command_count'] and source['command_projection_sha256'] == candidate['command_projection_sha256'],
            'same_tracker_bytes': source['tracker_bytes'] == candidate['tracker_bytes'] and source['tracker_sha256'] == candidate['tracker_sha256'],
        },
        'candidate_cache_added': sorted(new_paths - old_paths),
        'candidate_cache_removed': sorted(old_paths - new_paths),
        'client_playback_validated': False, 'simulation_compatibility_validated': False,
        'limitations': [
            'Equal command numbers do not prove equal catalog meaning in different game builds.',
            'Opaque members are compared byte-for-byte, not decoded or proven compatible.',
            'Cache identifiers are references, not proof that local or remote files exist.',
            'Cache path extraction is an ASCII observation, not a complete battlelobby parser.',
        ],
    }
    if reference is not None:
        reference_paths = {h['relative_path'] for h in reference['cache_handles']}
        result['reference'] = reference
        result['reference_comparison'] = {
            'same_map': reference['map_title'] == source['map_title'],
            'shared_cache_paths': sorted(old_paths & reference_paths),
            'source_only_cache_paths': sorted(old_paths - reference_paths),
            'reference_only_cache_paths': sorted(reference_paths - old_paths),
            'caveat': 'Different maps can legitimately have different dependencies; differences are not proof of a missing required modern dependency.',
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--schema', type=int, default=96477)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = describe(args.source, 41810, local=True)
    candidate = describe(args.candidate, args.schema)
    reference = describe(args.reference, args.schema) if args.reference else None
    report = compare(source, candidate, reference)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(report['checks'], sort_keys=True))


if __name__ == '__main__':
    main()
