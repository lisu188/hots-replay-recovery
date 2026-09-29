from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from catalog_diagnostics import UnitTimeline, link_fields
from import_catalog_capture import ANCHORS_SHA256, strict_json, validate_capture
from migrate_replay import SOURCE_SHA256, decode_events, encode_events
from mpq_reader import MPQArchive
import protocol41810

MAX_SOURCE_BYTES = 4 * 1024 * 1024


def source_requirements(game: list[dict], tracker: list[dict]) -> dict:
    timeline = UnitTimeline(tracker)
    uses = defaultdict(list)
    names = defaultdict(set)
    exclusions = Counter()
    for field in link_fields(game):
        matches = [timeline.lookup(tag, field.gameloop, 18) for tag in field.tags]
        types = {name for name, _ in matches if name is not None}
        reasons = {reason for name, reason in matches if name is None}
        reason = 'known_alive'
        if reasons:
            reason = ','.join(sorted(reasons))
        elif len(types) != 1:
            reason = 'mixed_unit_types'
        if reason == 'known_alive':
            names[field.link].update(types)
        else:
            exclusions[reason] += 1
        uses[field.link].append({'event_index': field.event_index, 'gameloop': field.gameloop,
                                'path': list(field.path), 'classification': reason})
    units = []
    for link, fields in sorted(uses.items()):
        identifiers = sorted(names[link])
        state = 'single_observed_name' if len(identifiers) == 1 else (
            'ambiguous_source_identity' if identifiers else 'no_source_identity')
        units.append({'source_link': link, 'source_names': identifiers, 'identity_status': state,
                      'field_count': len(fields),
                      'identity_backed_fields': sum(f['classification'] == 'known_alive' for f in fields),
                      'first_gameloop': min(f['gameloop'] for f in fields),
                      'fields_through_loop_64': sum(f['gameloop'] <= 64 for f in fields)})
    abilities = defaultdict(list)
    total_commands = 0
    for index, event in enumerate(game):
        if event['_event'] != 'NNet.Game.SCmdEvent':
            continue
        total_commands += 1
        ability = event.get('m_abil')
        if ability is None:
            continue
        link, command = ability['m_abilLink'], ability['m_abilCmdIndex']
        if type(link) is not int or not 0 <= link < 65536 or type(command) is not int or not 0 <= command < 32:
            raise ValueError('Invalid serialized ability link or command index')
        abilities[link].append((event['_gameloop'], command))
    return {'format': 'hots-original-catalog-requirements-v1', 'original_tag_shift': 18,
            'game_events': len(game), 'tracker_events': len(tracker), 'unit_links': units,
            'unit_link_fields': sum(len(v) for v in uses.values()),
            'excluded_identity_fields': dict(sorted(exclusions.items())),
            'command_events': total_commands,
            'explicit_ability_commands': sum(len(v) for v in abilities.values()),
            'ability_links': [{'source_link': link, 'commands': len(rows),
                              'command_indices': sorted({row[1] for row in rows}),
                              'first_gameloop': min(row[0] for row in rows),
                              'portable_name': None, 'identity_established': False}
                             for link, rows in sorted(abilities.items())],
            'source_identity_policy': 'Use known alive tracker types strictly before the event tick; never majority-vote conflicting names.'}


def read_source(path: Path) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= MAX_SOURCE_BYTES:
        raise ValueError('A bounded regular original replay is required')
    with path.open('rb') as source:
        original = source.read(MAX_SOURCE_BYTES + 1)
    if hashlib.sha256(original).hexdigest() != SOURCE_SHA256:
        raise ValueError('Only the immutable original TEN_GREYMANE replay is accepted')
    archive = MPQArchive(path)
    try:
        header = protocol41810.decode_replay_header(archive.header['user_data_header']['content'])
        if header['m_version']['m_baseBuild'] != 41810:
            raise ValueError('Original base build differs')
        game_raw = archive.read_file('replay.game.events')
        tracker_raw = archive.read_file('replay.tracker.events')
        game = list(decode_events(game_raw, protocol41810, 'game'))
        tracker = list(decode_events(tracker_raw, protocol41810, 'tracker'))
        if len(game) != 104257 or len(tracker) != 6614:
            raise ValueError('Original event counts differ')
        if encode_events(game, protocol41810, 'game') != game_raw:
            raise ValueError('Original game stream did not round-trip exactly')
        result = source_requirements(game, tracker)
        result['provenance'] = {'source_sha256': SOURCE_SHA256, 'source_build': 41810,
                                'game_stream_sha256': hashlib.sha256(game_raw).hexdigest(),
                                'tracker_stream_sha256': hashlib.sha256(tracker_raw).hexdigest(),
                                'game_binary_roundtrip': True,
                                'decoder': 'committed-protocol41810',
                                'decoder_sha256': hashlib.sha256(Path(protocol41810.__file__).read_bytes()).hexdigest()}
    finally:
        archive.close()
    if path.read_bytes() != original:
        raise ValueError('Original replay changed during inspection')
    return result


def propose(requirements: dict, capture: dict | None) -> dict:
    rows = requirements['unit_links']
    capture_ok = (capture is not None and capture.get('ready_for_unit_catalog_review') is True
                  and capture.get('blocking_checks') == [] and capture.get('all_unit_anchors_match') is True)
    current = {}
    indices = set()
    if capture_ok:
        catalog = capture['catalogs']['Unit']
        for row in catalog:
            if type(row['index']) is not int or not 1 <= row['index'] < 65536 or type(row['valid']) is not bool:
                raise ValueError('Invalid runtime catalog row')
            if not isinstance(row['id'], str) or row['index'] in indices:
                raise ValueError('Duplicate runtime index or invalid name')
            indices.add(row['index'])
            if row['id'] and row['valid']:
                if row['id'] in current:
                    raise ValueError('Ambiguous runtime unit catalog')
                current[row['id']] = row['index']
    plan = []
    for source in rows:
        state = source['identity_status']
        after = None
        if state == 'single_observed_name':
            if not capture_ok:
                state = 'runtime_capture_required' if capture is None else 'runtime_capture_blocked'
            else:
                after = current.get(source['source_names'][0])
                state = 'reviewable_name_match' if after is not None else 'name_missing_or_invalid_in_runtime'
        plan.append({**source, 'target_link': after, 'status': state,
                     'applied_to_replay': False})
    mapped = [row for row in plan if row['target_link'] is not None]
    blockers = ['unit_instance_allocation_not_reconciled', 'simulation_rules_not_reconciled',
                'original_synchronization_equivalence_unverified']
    if capture is None:
        blockers.insert(0, 'no_runtime_catalog_capture')
    elif not capture_ok:
        blockers[:0] = ['runtime_capture_not_eligible', *capture.get('blocking_checks', [])]
    if len(mapped) != len(plan):
        blockers.append('unit_catalog_plan_is_incomplete')
    if requirements['ability_links']:
        blockers.append('original_ability_link_names_not_established')
    result = {'format': 'hots-catalog-migration-plan-v1', 'status': 'diagnostic-plan-not-a-replay',
              'source_requirements': requirements, 'unit_link_plan': plan,
              'coverage': {'source_links': len(plan), 'reviewable_links': len(mapped),
                           'source_fields': requirements['unit_link_fields'],
                           'fields_with_reviewable_link': sum(row['field_count'] for row in mapped),
                           'source_ability_links': len(requirements['ability_links']),
                           'mapped_ability_links': 0},
              'blocking_checks': blockers, 'unit_plan_complete': len(mapped) == len(plan) and bool(plan),
              'capture_zip_sha256': None if capture is None else capture.get('capture_zip_sha256'),
              'replay_modified': False, 'replay_ready_for_playback': False,
              'client_playback_validated': False, 'synchronization_checks_disabled': False,
              'limitations': ['A matching catalog name does not establish equivalent gameplay behavior.',
                              'Catalog type indices are not unit-instance indices.',
                              'An exported current ability list does not identify the original numeric ability links.',
                              'The supplied screenshot time does not identify the first divergent simulation tick.']}
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--capture', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError('Output already exists')
    requirements = read_source(args.source)
    capture = None
    if args.capture is not None:
        anchors_raw = (Path(__file__).parent / 'observations/runtime-catalog-reference-anchors.json').read_bytes()
        if hashlib.sha256(anchors_raw).hexdigest() != ANCHORS_SHA256:
            raise ValueError('Pinned reference anchors differ')
        capture = validate_capture(args.capture, strict_json(anchors_raw)['unit_anchors'])
    result = propose(requirements, capture)
    with args.output.open('x', encoding='utf-8') as output:
        output.write(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'coverage': result['coverage'], 'blocking_checks': result['blocking_checks'],
                      'replay_modified': False, 'client_playback_validated': False}, indent=2))


if __name__ == '__main__':
    main()
