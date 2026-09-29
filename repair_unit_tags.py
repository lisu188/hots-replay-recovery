from __future__ import annotations

import argparse
import copy
import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path

from bind_client_metadata import independent_member, publish_binary
from migrate_replay import decode_events, dump, encode_events, write_json
from mpq_reader import MPQArchive
from protocol_loader import load_protocol
from reference_replay import inspect_reference
from repair_control_masks import integrity
from repair_startup import native_replace

INPUT_SHA256 = 'f5eac2c4de55db9cc834c97825ac89d5fc0bb4807a2b216ba5ca7fbc63e45f11'
OUTPUT_NAME = 'TEN_GREYMANE_client98285_TAGS_R6_PARTIAL.StormReplay'
REFERENCE_DIGESTS = {
    '5a7b05f4a75bc229dbbd74e6cc09e3b411129fc731874cfaa9217432fb85e7dc',
    '05ec458110db57dd5cf6c044cb6b7270d880282ec803abce725f048f91fc3e75',
}
TAG_PATHS = {
    'NNet.Game.SCmdEvent': [('m_data', 'TargetUnit', 'm_tag'), ('m_otherUnit',)],
    'NNet.Game.SCmdUpdateTargetUnitEvent': [('m_target', 'm_tag')],
    'NNet.Game.SUnitClickEvent': [('m_unitTag',)],
}
EXPECTED_COUNTS = {
    'm_delta/m_addUnitTags': 92, 'm_unitTag': 2756,
    'm_data/TargetUnit/m_tag': 1614, 'm_target/m_tag': 10851, 'm_otherUnit': 33,
}


def u32(value: int) -> int:
    if type(value) is not int or not 0 <= value < 2**32:
        raise ValueError('Expected a 32-bit unsigned integer, not a boolean')
    return value


def components(tag: int, shift: int) -> tuple[int, int]:
    u32(tag)
    if type(shift) is not int or not 1 <= shift <= 31:
        raise ValueError('Invalid tag layout')
    return tag >> shift, tag & ((1 << shift) - 1)


def pack(index: int, recycle: int, shift: int) -> int:
    components(0, shift)
    u32(index)
    u32(recycle)
    if index >= 1 << (32 - shift) or recycle >= 1 << shift:
        raise ValueError('Tag components do not fit the target layout')
    return (index << shift) | recycle


def references(events: list[dict]):
    for position, event in enumerate(events):
        for path in TAG_PATHS.get(event['_event'], []):
            parent = event
            for key in path[:-1]:
                parent = parent.get(key) if isinstance(parent, dict) else None
            if isinstance(parent, dict) and parent.get(path[-1]) is not None:
                yield position, path, parent, path[-1], u32(parent[path[-1]])
        if event['_event'] == 'NNet.Game.SSelectionDeltaEvent':
            tags = event['m_delta']['m_addUnitTags']
            if not isinstance(tags, list):
                raise ValueError('Invalid selection tag array')
            for index, tag in enumerate(tags):
                yield position, ('m_delta', 'm_addUnitTags', index), tags, index, u32(tag)


def tracker_pairs(events: list[dict]) -> set[tuple[int, int]]:
    result = set()
    for event in events:
        if 'm_unitTagIndex' in event and 'm_unitTagRecycle' in event:
            result.add((u32(event['m_unitTagIndex']), u32(event['m_unitTagRecycle'])))
    if not result:
        raise ValueError('No tracker unit identities are available')
    return result


def infer_layout(events: list[dict], tracker: list[dict], require_unique: bool = True) -> dict:
    pairs = tracker_pairs(tracker)
    rows = list(references(events))
    tags = [row[4] for row in rows if row[4] not in (0, 0xffffffff)]
    if not tags:
        raise ValueError('No non-sentinel unit references')
    matches = {str(shift): sum(components(tag, shift) in pairs for tag in tags)
               for shift in range(1, 32)}
    exact = [int(shift) for shift, count in matches.items() if count == len(tags)]
    if not exact or (require_unique and len(exact) != 1):
        raise ValueError('Observed tags do not identify one complete layout')
    counts = Counter('/'.join(str(k) for k in row[1] if type(k) is not int) for row in rows)
    return {'observed_shift': exact[0] if len(exact) == 1 else None, 'compatible_shifts': exact, 'references': len(rows),
            'non_sentinel_references': len(tags), 'unique_non_sentinel_tags': len(set(tags)),
            'field_counts': dict(sorted(counts.items())), 'matching_references_by_shift': matches,
            'all_observed_non_sentinel_tags_match_tracker': True,
            'scope': 'Observed game-event references joined to recorded tracker identities, not live engine state.'}


def read_streams(path: Path) -> tuple[list[dict], list[dict]]:
    p = load_protocol(96477)
    archive = MPQArchive(path)
    try:
        return (list(decode_events(archive.read_file('replay.game.events'), p, 'game')),
                list(decode_events(archive.read_file('replay.tracker.events'), p, 'tracker')))
    finally:
        archive.close()


def observe(paths: list[Path]) -> dict:
    observations = []
    for path in paths:
        digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        if digest not in REFERENCE_DIGESTS:
            raise ValueError('Reference must be one of the preserved original 98285 recordings')
        profile = inspect_reference(Path(path), 96477, 98285)
        game, tracker = read_streams(Path(path))
        observations.append({'reference_sha256': digest, 'declared_build': 98285,
                             'observed_payload_roundtrip': profile['observed_payload_roundtrip'],
                             'layout': infer_layout(game, tracker, require_unique=False)})
    result = {'format': 'hots-observed-unit-tags-v1', 'references': observations,
              'target_shift': 22, 'complete_build_schema_verified': False,
              'runtime_instance_mapping_proven': False}
    validate_observation(result)
    return result


def validate_observation(value: dict) -> None:
    if not isinstance(value, dict) or value.get('format') != 'hots-observed-unit-tags-v1':
        raise ValueError('Invalid unit-tag observation')
    rows = value.get('references')
    if not isinstance(rows, list) or len(rows) != 2 or any(not isinstance(row, dict) for row in rows):
        raise ValueError('Both independent reference recordings are required')
    if {row.get('reference_sha256') for row in rows} != REFERENCE_DIGESTS:
        raise ValueError('Reference provenance mismatch')
    if type(value.get('target_shift')) is not int or value['target_shift'] != 22:
        raise ValueError('Unexpected target layout')
    compatible = set(range(1, 32))
    for row in rows:
        layout = row.get('layout', {})
        if not isinstance(layout, dict):
            raise ValueError('Invalid layout evidence')
        if type(row.get('declared_build')) is not int or row['declared_build'] != 98285:
            raise ValueError('Wrong reference build')
        if row.get('observed_payload_roundtrip') is not True:
            raise ValueError('Reference payloads have not been checked')
        count = layout.get('non_sentinel_references')
        if type(count) is not int or count <= 0:
            raise ValueError('Missing layout evidence')
        scores = layout.get('matching_references_by_shift', {})
        if not isinstance(scores, dict) or set(scores) != {str(i) for i in range(1, 32)}:
            raise ValueError('Incomplete layout comparison')
        if any(type(v) is not int or not 0 <= v <= count for v in scores.values()):
            raise ValueError('Invalid layout comparison counts')
        compatible &= {int(key) for key, n in scores.items() if n == count}
    if compatible != {22}:
        raise ValueError('Ambiguous or unsupported target layout across both references')


def transform(events: list[dict], tracker: list[dict], old_shift: int, new_shift: int):
    if infer_layout(events, tracker)['observed_shift'] != old_shift:
        raise ValueError('Input tag layout differs from the requested transformation')
    after = copy.deepcopy(events)
    changes = []
    for position, path, parent, key, before in references(after):
        if before in (0, 0xffffffff):
            continue
        index, recycle = components(before, old_shift)
        new = pack(index, recycle, new_shift)
        if new in (0, 0xffffffff):
            raise ValueError('Transformation would introduce a sentinel identity')
        if before != new:
            parent[key] = new
            changes.append({'event_index': position, 'gameloop': after[position]['_gameloop'],
                            'path': '/game/' + str(position) + '/' + '/'.join(map(str, path)),
                            'before': before, 'after': new, 'unit_index_preserved': index,
                            'recycle_preserved': recycle})
    if infer_layout(after, tracker)['observed_shift'] != new_shift:
        raise AssertionError('Result does not have the intended tag layout')
    return after, changes


def repair(source: Path, output: Path, evidence: dict) -> dict:
    source, output = Path(source), Path(output)
    if output.exists() or source.resolve() == output.resolve():
        raise FileExistsError('Use a new checkpoint directory')
    validate_observation(evidence)
    if hashlib.sha256(source.read_bytes()).hexdigest() != INPUT_SHA256:
        raise ValueError('Only the immutable R5 replay is accepted')
    before_profile = inspect_reference(source, 96477, 98285)
    before_integrity = integrity(source)
    game, tracker = read_streams(source)
    before = infer_layout(game, tracker)
    if before['field_counts'] != EXPECTED_COUNTS or before['observed_shift'] != 18:
        raise ValueError('R5 tag observations differ from the reviewed input')
    intended, changes = transform(game, tracker, 18, 22)
    p = load_protocol(96477)
    original = MPQArchive(source)
    try:
        header = original.header['user_data_header']['content']
        names = original.read_file('(listfile)').decode('ascii').splitlines() + ['(listfile)', '(attributes)']
        members = {name: original.read_file(name) for name in names}
    finally:
        original.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='unit-tags-', dir=output.parent) as temporary:
        stage = Path(temporary) / 'checkpoint'
        stage.mkdir()
        destination = stage / OUTPUT_NAME
        encoded = encode_events(intended, p, 'game')
        container = native_replace(source, destination, header, {'replay.game.events': encoded})
        after_profile = inspect_reference(destination, 96477, 98285)
        after_integrity = integrity(destination)
        from mpyq import MPQArchive as IndependentArchive
        check = MPQArchive(destination)
        independent = IndependentArchive(str(destination), listfile=False)
        try:
            if check.header['user_data_header']['content'] != header:
                raise AssertionError('Header changed')
            for name in names:
                raw = check.read_file(name)
                if independent_member(independent, name) != raw:
                    raise AssertionError('Independent reader disagrees: ' + name)
                if name not in ('replay.game.events', '(attributes)') and raw != members[name]:
                    raise AssertionError('Untouched member changed: ' + name)
            actual = list(decode_events(check.read_file('replay.game.events'), p, 'game'))
            if actual != intended:
                raise AssertionError('Game events do not match intended tag replacements')
        finally:
            independent.file.close()
            check.close()
        if hashlib.sha256(source.read_bytes()).hexdigest() != INPUT_SHA256:
            raise AssertionError('Input changed during processing')
        report = {'format': 'hots-unit-tag-migration-v1', 'status': 'partial-format-repair-not-playback-ready',
                  'input_sha256': INPUT_SHA256, 'artifact': publish_binary(destination),
                  'layout_before': before, 'layout_after': infer_layout(actual, tracker),
                  'changed_tag_values': len(changes), 'changed_events': len({c['event_index'] for c in changes}),
                  'events': {k: v['count'] for k, v in after_profile['streams'].items()},
                  'event_counts_preserved': all(before_profile['streams'][k]['count'] == v['count']
                                                for k, v in after_profile['streams'].items()),
                  'header_and_all_non_game_replay_payloads_preserved': True,
                  'sync_checks_removed_or_disabled': False,
                  'input_integrity': before_integrity, 'output_integrity': after_integrity,
                  'container': container, 'official_observed_payload_roundtrip': True,
                  'client_playback_validated': False, 'simulation_compatibility_validated': False,
                  'limitations': ['Packed representation is corrected, but unit instance indices are still those of the old simulation.',
                                  'Numeric unit and ability catalog links have not been rebound.',
                                  'Recorded synchronization values remain unchanged; Replay Desync may persist at the first check.',
                                  'No game executable has run this checkpoint; do not present it as a recovered match.']}
        write_json(stage / 'report.json', report)
        write_json(stage / 'reference-observation.json', evidence)
        (stage / 'unit-tags.changes.jsonl').write_text(''.join(dump(c) + '\n' for c in changes), encoding='utf-8')
        if output.exists():
            raise FileExistsError(output)
        stage.rename(output)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--observation', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(repair(args.source, args.output, json.loads(args.observation.read_text())), indent=2))
