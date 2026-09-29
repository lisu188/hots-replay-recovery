from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from catalog_diagnostics import UnitTimeline
from encoders import encode_tracker_events
from migrate_replay import SOURCE_SHA256, decode_events, dump, encode_events
from mpq_reader import MPQArchive
from repair_unit_tags import components
import protocol41810

PREFIX = 'NNet.Game.'
MAX_EVENTS = 300000
MAX_SELECTION = 512
ACTIVE_GROUP = 10
ORDERS = ('low_bit_first', 'high_bit_first')


def integer(value, maximum: int = 0xffffffff) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError('Invalid bounded unsigned integer')
    return value


def mask_bits(value, order: str) -> list[bool]:
    if order not in ORDERS:
        raise ValueError('Unknown mask interpretation')
    if hasattr(value, 'length') and hasattr(value, 'value'):
        length, packed = value.length, value.value
    elif isinstance(value, (tuple, list)) and len(value) == 2:
        length, packed = value
    else:
        raise ValueError('Unsupported mask representation')
    integer(length, MAX_SELECTION)
    integer(packed, (1 << length) - 1)
    result = [bool((packed >> index) & 1) for index in range(length)]
    return result if order == ORDERS[0] else result[::-1]


def apply_delta(selected: tuple[int, ...], delta: dict, order: str) -> tuple[int, ...]:
    if order not in ORDERS:
        raise ValueError('Unknown mask interpretation')
    if tuple(sorted(set(selected))) != selected or any(type(t) is not int or not 0 < t < 0xffffffff for t in selected):
        raise ValueError('Seed selection must contain sorted unique non-sentinel tags')
    if not isinstance(delta, dict) or len(selected) > MAX_SELECTION:
        raise ValueError('Invalid selection delta')
    remove = delta['m_removeMask']
    if not isinstance(remove, dict) or len(remove) != 1:
        raise ValueError('Invalid selection removal choice')
    kind, value = next(iter(remove.items()))
    if kind == 'None':
        if value is not None:
            raise ValueError('None mask carries a payload')
        retained = list(selected)
    elif kind == 'Mask':
        bits = mask_bits(value, order)
        if len(bits) > len(selected):
            raise ValueError('Mask exceeds known selection')
        retained = [tag for i, tag in enumerate(selected) if i >= len(bits) or not bits[i]]
    elif kind == 'ZeroIndices':
        if not isinstance(value, list) or len(value) > len(selected):
            raise ValueError('Invalid retained indices')
        indices = [integer(i, len(selected) - 1) for i in value]
        if len(set(indices)) != len(indices):
            raise ValueError('Duplicate retained indices')
        retained = [selected[i] for i in indices]
    else:
        raise ValueError('Removal variant not present in the reviewed original')
    additions = delta['m_addUnitTags']
    groups = delta['m_addSubgroups']
    if not isinstance(additions, list) or not isinstance(groups, list):
        raise ValueError('Invalid selection additions')
    for row in groups:
        if integer(row['m_count'], MAX_SELECTION) == 0:
            raise ValueError('An added subgroup cannot be empty')
        integer(row['m_unitLink'], 65535)
    if sum(integer(row['m_count'], MAX_SELECTION) for row in groups) != len(additions):
        raise ValueError('Subgroup count does not match additions')
    checked = [integer(tag) for tag in additions]
    if any(tag in (0, 0xffffffff) for tag in checked) or len(set(checked)) != len(checked):
        raise ValueError('Invalid or duplicate added unit reference')
    result = tuple(sorted(set(retained).union(checked)))
    if len(result) > MAX_SELECTION:
        raise ValueError('Selection exceeds supported bound')
    return result


def selection_context(selected: tuple[int, ...], timeline: UnitTimeline, loop: int, shift: int) -> dict:
    entries = []
    for tag in selected:
        name, reason = timeline.lookup(tag, loop, shift)
        index, recycle = components(tag, shift)
        entries.append({'unit_index': index, 'recycle': recycle, 'tracker_type': name, 'status': reason})
    if not entries:
        status = 'empty_selection'
    elif any(row['status'] != 'known_alive' for row in entries):
        status = 'lifecycle_ambiguous'
    elif len(entries) != 1:
        status = 'multiple_selected_units'
    else:
        status = 'single_known_selected_unit'
    return {'status': status, 'units': entries}


def analyse(game: Iterable[dict], tracker: list[dict], shift: int = 18, boundary: int = 64) -> tuple[dict, list[dict]]:
    if shift not in (18, 22):
        raise ValueError('Unsupported packed tag representation')
    integer(boundary, 100000)
    timeline = UnitTimeline(tracker)
    selections = {order: defaultdict(tuple) for order in ORDERS}
    trace, early = [], []
    abilities = defaultdict(list)
    classifications = Counter()
    selection_events = 0
    last_loop = -1
    count = 0
    for event_index, event in enumerate(game):
        count += 1
        if count > MAX_EVENTS:
            raise ValueError('Event count exceeds limit')
        loop = integer(event['_gameloop'])
        if loop < last_loop:
            raise ValueError('Game stream is not chronological')
        last_loop = loop
        name = event['_event']
        if 'ControlGroup' in name and name != PREFIX + 'SSelectionDeltaEvent':
            raise ValueError('Unreviewed control-group event; refusing incomplete selection history')
        if name not in (PREFIX + 'SSelectionDeltaEvent', PREFIX + 'SCmdEvent'):
            continue
        user = integer(event['_userid']['m_userId'], 31)
        if name == PREFIX + 'SSelectionDeltaEvent':
            group = integer(event['m_controlGroupId'], ACTIVE_GROUP)
            if group != ACTIVE_GROUP:
                raise ValueError('Original-only audit requires active group 10')
            selection_events += 1
            for order in ORDERS:
                selections[order][user] = apply_delta(selections[order][user], event['m_delta'], order)
            if loop <= boundary:
                early.append({'event_index': event_index, 'gameloop': loop, 'user_id': user,
                              'event': 'selection', 'added_tags': [list(components(t, shift)) for t in event['m_delta']['m_addUnitTags']],
                              'unit_type_links': [integer(g['m_unitLink'], 65535) for g in event['m_delta']['m_addSubgroups']]})
            continue
        contexts = {order: selection_context(selections[order][user], timeline, loop, shift) for order in ORDERS}
        same = contexts[ORDERS[0]] == contexts[ORDERS[1]]
        context = contexts[ORDERS[0]]
        classification = context['status'] if same else 'mask_interpretations_disagree'
        if event.get('m_otherUnit') is not None or event.get('m_unitGroup') is not None:
            classification = 'explicit_source_override_not_interpreted'
        selected_type = context['units'][0]['tracker_type'] if classification == 'single_known_selected_unit' else None
        if not isinstance(event['m_data'], dict) or len(event['m_data']) != 1 or next(iter(event['m_data'])) not in {'None', 'TargetPoint', 'TargetUnit', 'Data'}:
            raise ValueError('Invalid command target choice')
        ability = event['m_abil']
        if ability is not None:
            link = integer(ability['m_abilLink'], 65535)
            cmd_index = integer(ability['m_abilCmdIndex'], 31)
        else:
            link = cmd_index = None
        row = {'event_index': event_index, 'gameloop': loop, 'user_id': user,
               'ability_link': link, 'ability_command_index': cmd_index,
               'sequence': integer(event['m_sequence']), 'command_flags': integer(event['m_cmdFlags']),
               'target_variant': next(iter(event['m_data'])), 'classification': classification,
               'selected_unit_type_candidate': selected_type, 'selection_interpretations': contexts,
               'ability_name': None, 'executed_caster_verified': False}
        trace.append(row)
        classifications[classification] += 1
        if link is not None:
            abilities[link].append(row)
        if loop <= boundary:
            early.append({k: row[k] for k in ('event_index', 'gameloop', 'user_id', 'ability_link', 'classification', 'selected_unit_type_candidate')}
                         | {'event': 'command'})
    ability_rows = []
    for link, rows in sorted(abilities.items()):
        types = Counter(row['selected_unit_type_candidate'] for row in rows if row['selected_unit_type_candidate'] is not None)
        excluded = Counter(row['classification'] for row in rows if row['selected_unit_type_candidate'] is None)
        ability_rows.append({'source_link': link, 'commands': len(rows),
                             'first_gameloop': min(row['gameloop'] for row in rows),
                             'selected_type_candidates': dict(sorted(types.items())),
                             'excluded_commands': dict(sorted(excluded.items())),
                             'command_indices': sorted({row['ability_command_index'] for row in rows}),
                             'portable_ability_name': None, 'identity_established': False})
    explicit = [row for row in trace if row['ability_link'] is not None]
    summary = {'format': 'hots-command-identity-audit-v1', 'status': 'diagnostic-not-a-replay-repair',
               'game_events': count, 'selection_events': selection_events, 'commands': len(trace),
               'explicit_ability_commands': len(explicit), 'ability_links': len(ability_rows),
               'command_classifications': dict(sorted(classifications.items())),
               'selection_rule': 'Sorted unique tag model, independently evaluating both bit-mask orientations; disagreement excludes identity.',
               'tag_shift': shift, 'review_boundary_gameloop': boundary,
               'first_explicit_ability_gameloop': min((row['gameloop'] for row in explicit), default=None),
               'commands_through_boundary': sum(row['gameloop'] <= boundary for row in trace),
               'explicit_ability_commands_through_boundary': sum(row['gameloop'] <= boundary for row in explicit),
               'prefix': early, 'abilities': ability_rows,
               'portable_ability_names_established': 0, 'replay_modified': False,
               'client_playback_validated': False, 'simulation_compatibility_validated': False,
               'limitations': ['A selected unit is context, not proof of the actual executing caster.',
                              'Equal selected context under both mask orientations does not validate every engine selection rule.',
                              'No ability name is assigned from a hero name, command number or timing alone.',
                              'The 64-loop boundary is an analysis window; it is not a measured first divergent engine tick.']}
    return summary, trace


def run(source: Path, output: Path) -> dict:
    source, output = Path(source), Path(output)
    if source.is_symlink() or not source.is_file() or not 0 < source.stat().st_size <= 4 * 1024 * 1024:
        raise ValueError('A bounded regular original replay is required')
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('Only the immutable original TEN_GREYMANE is accepted')
    if output.exists() or output.is_symlink():
        raise FileExistsError('Output must be a new directory')
    archive = MPQArchive(source)
    try:
        member_raw = {kind: archive.read_file('replay.' + kind + '.events') for kind in ('game', 'tracker')}
        events = {kind: list(decode_events(value, protocol41810, kind)) for kind, value in member_raw.items()}
        for kind in ('game', 'tracker'):
            encoded = encode_tracker_events(events[kind], protocol41810) if kind == 'tracker' else encode_events(events[kind], protocol41810, kind)
            if encoded != member_raw[kind]:
                raise ValueError(kind + ' stream did not re-encode exactly')
        report, trace = analyse(events['game'], events['tracker'])
    finally:
        archive.close()
    if len(events['game']) != 104257 or len(events['tracker']) != 6614 or report['commands'] != 4558:
        raise ValueError('Original event counts disagree')
    trace_raw = ''.join(dump(row) + '\n' for row in trace).encode('ascii')
    report['provenance'] = {'source_sha256': SOURCE_SHA256,
                            'decoder_sha256': hashlib.sha256(Path(protocol41810.__file__).read_bytes()).hexdigest(),
                            'decoder_scope': 'Committed source protocol, not newly fetched independent upstream',
                            'observed_source_game_and_tracker_roundtrip': True,
                            'command_trace_sha256': hashlib.sha256(trace_raw).hexdigest()}
    if source.read_bytes() != raw:
        raise ValueError('Source changed while inspected')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.command-audit-', dir=output.parent) as temporary:
        stage = Path(temporary) / 'result'
        stage.mkdir()
        (stage / 'report.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n', encoding='utf-8')
        (stage / 'commands.jsonl').write_bytes(trace_raw)
        if output.exists():
            raise FileExistsError('Output appeared while running')
        stage.rename(output)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    report = run(args.source, args.output)
    print(json.dumps({key: report[key] for key in ('commands', 'ability_links', 'command_classifications', 'first_explicit_ability_gameloop', 'commands_through_boundary')}))


if __name__ == '__main__':
    main()
