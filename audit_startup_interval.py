from __future__ import annotations

import argparse
import hashlib
import json
import itertools
from collections import Counter
from pathlib import Path

from catalog_diagnostics import UnitTimeline, link_fields
from encoders import encode_tracker_events
from reference_replay import native
from migrate_replay import decode_events, encode_events
from mpq_reader import MPQArchive
from protocol_loader import load_protocol
from portable_sync_98348 import decode_sync, summarize_sync
from repair_unit_tags import components, u32

SOURCE_SHA256 = 'e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824'
R8_SHA256 = '4f2435e8cd678aeac16c0b1403cfdf67ab8e513b04f0f93e22d504c187bbaf19'
ANCHOR_SHA256 = '53f70fecc2343f355f67774e9d9694e6dc5f0ac4e0083c83680611da5a2bb7a9'


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sync_summary(raw: bytes, elapsed: int) -> dict:
    """Summarize native record boundaries without inferring divergence semantics."""
    u32(elapsed)
    if type(raw) is not bytes or not raw or len(raw) > 1024 * 1024:
        raise ValueError('Expected nonempty bounded native synchronization records')
    records = decode_sync(raw)
    native_summary = summarize_sync(raw)
    rows = [raw[record.start_bit // 8:record.end_bit // 8] for record in records]
    prefixes = dict(sorted(Counter(row[:2].hex() for row in rows).items()))
    first = rows[0]
    return {'sha256': native_summary['sha256'], 'bytes': len(raw),
            'record_count': len(records), 'prefix_counts': prefixes,
            'first_record_hex': first.hex() if len(first) <= 5 else None,
            'first_record_bytes': len(first),
            'count_matches_elapsed_floor_div_64': len(records) == elapsed // 64,
            'count_comparison_basis': 'Record count only; not a cadence or divergence measurement',
            'record_layout': 'Native98348 typed delta and payload; each record byte-aligned',
            'profile': native_summary['profile'],
            'schema_sha256': native_summary['schema_sha256'],
            'event_id_counts': native_summary['event_id_counts'],
            'delta_variant_counts': native_summary['delta_variant_counts'],
            'record_byte_lengths': native_summary['record_byte_lengths'],
            'vector_words': native_summary['vector_words'],
            'nonzero_padding_records': native_summary['nonzero_padding_records'],
            'first_recorded_gameloop': native_summary['first_recorded_gameloop'],
            'last_recorded_gameloop': native_summary['last_recorded_gameloop'],
            'byte_exact_roundtrip': native_summary['byte_exact_roundtrip'],
            'raw_record_prefix_bytes': 2, 'first_record_hex_max_bytes': 5,
            'parsed_anonymous_payload_values_emitted': False,
            'first_check_tick_measured': False, 'first_divergent_tick_identified': False,
            'checksum_algorithm_identified': False, 'playback_compatibility_proven': False}


def interval_report(game: list[dict], tracker: list[dict], anchors: dict[str, int],
                    stop: int = 64, shift: int = 22) -> dict:
    if type(stop) is not int or not 1 <= stop <= 4096:
        raise ValueError('Audit interval must end between loops 1 and 4096')
    components(0, shift)
    if not isinstance(anchors, dict) or any(not isinstance(k, str) or not k or
            type(v) is not int or not 0 <= v < 65536 for k, v in anchors.items()):
        raise ValueError('Invalid observed catalog anchors')
    last = -1
    early = []
    for event in game:
        loop = u32(event['_gameloop'])
        if loop < last:
            raise ValueError('Game events must be chronological')
        last = loop
        if loop < stop:
            early.append(event)
    timeline = UnitTimeline(tracker)
    fields = []
    for field in link_fields(early):
        identities = []
        for tag in field.tags:
            name, reason = timeline.lookup(tag, field.gameloop, shift)
            index, recycle = components(tag, shift)
            identities.append({'recorded_index': index, 'recorded_recycle': recycle,
                               'tracker_type': name, 'identity_evidence': reason})
        names = {item['tracker_type'] for item in identities if item['tracker_type'] is not None}
        known = bool(identities) and all(item['identity_evidence'] == 'known_alive' for item in identities)
        name = next(iter(names)) if known and len(names) == 1 else None
        reference = anchors.get(name) if name else None
        state = ('identity_unresolved' if name is None else 'no_current_reference_anchor' if reference is None
                 else 'same_as_observed_anchor' if reference == field.link else 'differs_from_observed_anchor')
        fields.append({'event_index': field.event_index, 'gameloop': field.gameloop,
                       'path': list(field.path), 'recorded_catalog_link': field.link,
                       'reference_catalog_link': reference, 'comparison': state,
                       'identities': identities, 'live_instance_identity_verified': False})
    commands = []
    for index, event in enumerate(early):
        if event['_event'] != 'NNet.Game.SCmdEvent':
            continue
        ability = event.get('m_abil')
        if ability is not None and not isinstance(ability, dict):
            raise ValueError('Malformed ability field')
        target = event['m_data']
        if not isinstance(target, dict) or len(target) != 1:
            raise ValueError('Command target must contain one choice')
        commands.append({'event_index': index, 'gameloop': event['_gameloop'],
                         'flags': u32(event['m_cmdFlags']), 'target_kind': next(iter(target)),
                         'ability_link': None if ability is None else u32(ability['m_abilLink']),
                         'command_index': None if ability is None else u32(ability['m_abilCmdIndex'])})
    return {'start_gameloop_inclusive': 0, 'stop_gameloop_exclusive': stop,
            'selection_basis': 'Diagnostic window, not a measured first divergent tick',
            'game_events_in_window': len(early), 'catalog_fields': fields, 'commands': commands,
            'counts': {'catalog_fields': len(fields), 'commands': len(commands),
                       'explicit_ability_commands': sum(row['ability_link'] is not None for row in commands),
                       'catalog_comparisons': dict(sorted(Counter(row['comparison'] for row in fields).items()))},
            'cross_map_catalog_equivalence_proven': False, 'replay_modified': False,
            'first_divergent_tick_identified': False, 'client_playback_validated': False}


def read_verified(path: Path, expected: str, schema: int, declared: int) -> dict:
    path = Path(path)
    raw = path.read_bytes()
    if digest(raw) != expected:
        raise ValueError('Replay does not match the immutable checkpoint')
    protocol = load_protocol(schema)
    archive = MPQArchive(path)
    try:
        header = protocol.decode_replay_header(archive.header['user_data_header']['content'])
        if header['m_version']['m_baseBuild'] != declared:
            raise ValueError('Unexpected declared replay build')
        streams = {}
        for kind in ('game', 'message', 'tracker'):
            payload = archive.read_file('replay.' + kind + '.events')
            events = list(decode_events(payload, protocol, kind))
            encoded = encode_tracker_events(events, protocol) if kind == 'tracker' else encode_events(events, protocol, kind)
            if encoded != payload:
                raise ValueError('Observed payload failed full decode/encode comparison')
            missing = object()
            official = getattr(protocol, 'decode_replay_' + kind + '_events')(payload)
            for left, right in itertools.zip_longest(events, official, fillvalue=missing):
                if left is missing or right is missing or native(left) != native(right):
                    raise ValueError('Official and semantic event decoders disagree')
            streams[kind] = events
        sync = archive.read_file('replay.sync.events')
        summary = sync_summary(sync, header['m_elapsedGameLoops'])
    finally:
        archive.close()
    if digest(path.read_bytes()) != expected:
        raise ValueError('Source changed during audit')
    return {'streams': streams, 'sync': sync, 'sync_summary': summary,
            'elapsed': header['m_elapsedGameLoops'], 'schema_sha256': protocol.recovery_schema_sha256}


def audit(source: Path, candidate: Path, anchor_path: Path) -> dict:
    raw = Path(anchor_path).read_bytes()
    if digest(raw) != ANCHOR_SHA256:
        raise ValueError('Independent reference anchors differ from the reviewed observation')
    observation = json.loads(raw)
    if observation['build'] != 98285 or len(observation['unit_anchors']) != 48:
        raise ValueError('Unexpected reference anchor scope')
    original = read_verified(source, SOURCE_SHA256, 41810, 41810)
    current = read_verified(candidate, R8_SHA256, 96477, 98285)
    if original['elapsed'] != current['elapsed']:
        raise ValueError('Elapsed simulation loops changed')
    counts = {kind: len(events) for kind, events in current['streams'].items()}
    if counts != {'game': 104257, 'message': 155, 'tracker': 6614}:
        raise ValueError('Checkpoint event counts changed')
    return {'format': 'hots-startup-interval-audit-v1', 'source_sha256': SOURCE_SHA256,
            'candidate_sha256': R8_SHA256, 'reference_anchor_sha256': ANCHOR_SHA256,
            'schema_sha256': {'41810': original['schema_sha256'], '96477': current['schema_sha256']},
            'events': counts, 'elapsed_gameloops': current['elapsed'],
            'source_sync': original['sync_summary'], 'candidate_sync': current['sync_summary'],
            'sync_payloads_identical': original['sync'] == current['sync'],
            'startup': interval_report(current['streams']['game'], current['streams']['tracker'],
                                       observation['unit_anchors']),
            'source_and_candidate_unchanged': True, 'replay_modified': False,
            'client_playback_validated': False, 'synchronization_equivalence_proven': False,
            'limitations': ['Native sync decoding identifies recorded gameloops, not a first divergent tick or a checksum algorithm.',
                            'Absent explicit ability commands do not exclude ability data from initial simulation.',
                            'Recorded tracker identities are not the new engine live object allocation.',
                            'Cross-map anchors reveal a comparison gap, not an automatically valid replacement.']}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--anchors', type=Path, default=Path(__file__).parent / 'observations/runtime-catalog-reference-anchors.json')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    report = audit(args.source, args.candidate, args.anchors)
    with args.output.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write('\n')


if __name__ == '__main__':
    main()
