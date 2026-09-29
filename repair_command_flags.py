from __future__ import annotations

import argparse
import copy
import hashlib
import json
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from bind_client_metadata import independent_member, publish_binary
from catalog_diagnostics import R6_SHA256, REFERENCES
from migrate_replay import decode_events, dump, encode_events, write_json
from mpq_reader import MPQArchive
from protocol_loader import load_protocol
from reference_replay import inspect_reference
from repair_control_masks import integrity
from repair_startup import native_replace
from repair_unit_tags import read_streams, u32

OUTPUT_NAME = 'TEN_GREYMANE_client98285_FLAGS_R7_PARTIAL.StormReplay'
EXPECTED_SOURCE = {256: 1288, 266: 7, 65792: 3, 524544: 16, 1048832: 606,
                   1048840: 1915, 1114376: 66, 2097408: 657}
EXPECTED_MAPPING = {0x100: 0x100, 0x10a: 0x10a, 0x10100: 0x8100,
                    0x100100: 0x80100, 0x100108: 0x80108,
                    0x110108: 0x88108, 0x200100: 0x100100}


def shape(event: dict) -> str:
    data = event.get('m_data')
    if not isinstance(data, dict) or len(data) != 1:
        raise ValueError('A command must contain one target choice')
    target = next(iter(data))
    if target not in ('None', 'TargetPoint', 'TargetUnit', 'Data'):
        raise ValueError('Unsupported command target choice')
    return ('implicit' if event.get('m_abil') is None else 'explicit') + ':' + target


def histogram(events: list[dict]) -> list[dict]:
    result = defaultdict(Counter)
    for event in events:
        if event['_event'] == 'NNet.Game.SCmdEvent':
            result[u32(event['m_cmdFlags'])][shape(event)] += 1
    return [{'flags': flag, 'shapes': dict(sorted(counts.items()))} for flag, counts in sorted(result.items())]


def observe(source: Path, references: list[Path]) -> dict:
    paths = [Path(source), *map(Path, references)]
    digests = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
    if digests[0] != R6_SHA256 or len(digests) != 3 or set(digests[1:]) != set(REFERENCES):
        raise ValueError('The immutable R6 and both reviewed reference files are required')
    rows = []
    for path, digest in zip(paths, digests):
        profile = inspect_reference(path, 96477, 98285)
        game, _ = read_streams(path)
        rows.append({'sha256': digest, 'declared_build': 98285,
                     'observed_payload_roundtrip': profile['observed_payload_roundtrip'],
                     'histogram': histogram(game)})
    return {'format': 'hots-command-flag-observation-v1', 'source': rows[0],
            'references': sorted(rows[1:], key=lambda row: row['sha256']),
            'flag_semantics_proven': False, 'client_playback_validated': False}


def unpack_histogram(rows: list[dict]) -> dict[int, dict[str, int]]:
    if not isinstance(rows, list) or not rows:
        raise ValueError('Missing command observations')
    result = {}
    for row in rows:
        flag = u32(row['flags'])
        if flag >= 1 << 26 or flag in result:
            raise ValueError('Duplicate or out-of-range command flags')
        counts = row['shapes']
        if not isinstance(counts, dict) or not counts:
            raise ValueError('Missing command shapes')
        for name, count in counts.items():
            if name not in {mode + ':' + target for mode in ('implicit', 'explicit')
                            for target in ('None', 'TargetPoint', 'TargetUnit', 'Data')}:
                raise ValueError('Unknown command shape')
            if type(count) is not int or count <= 0:
                raise ValueError('Invalid command count')
        result[flag] = counts
    return result


def delete_zero_bit(value: int, position: int) -> int:
    u32(value)
    if type(position) is not int or not 0 <= position < 26 or value >= 1 << 26:
        raise ValueError('Invalid bit-deletion hypothesis')
    if value & (1 << position):
        raise ValueError('A set bit cannot be discarded')
    return (value & ((1 << position) - 1)) | ((value >> (position + 1)) << position)


def hypothesis(evidence: dict) -> dict:
    if not isinstance(evidence, dict) or evidence.get('format') != 'hots-command-flag-observation-v1':
        raise ValueError('Unknown observation format')
    source = evidence['source']
    rows = evidence['references']
    if source['sha256'] != R6_SHA256 or len(rows) != 2 or {r['sha256'] for r in rows} != set(REFERENCES):
        raise ValueError('Unreviewed command evidence')
    for row in [source, *rows]:
        if type(row.get('declared_build')) is not int or row['declared_build'] != 98285 or row.get('observed_payload_roundtrip') is not True:
            raise ValueError('Unvalidated reference payload')
    old = unpack_histogram(source['histogram'])
    if {f: sum(c.values()) for f, c in old.items()} != EXPECTED_SOURCE:
        raise ValueError('Unexpected R6 command distribution')
    target = defaultdict(set)
    for row in rows:
        for flag, counts in unpack_histogram(row['histogram']).items():
            target[flag].update(counts)
    evaluations = []
    for cut in range(26):
        if any(flag & (1 << cut) for flag in old):
            continue
        supported = {}
        for flag, counts in old.items():
            mapped = delete_zero_bit(flag, cut)
            if set(counts) <= target.get(mapped, set()):
                supported[flag] = mapped
        evaluations.append({'removed_zero_bit': cut, 'mapping': supported,
                            'supported_commands': sum(EXPECTED_SOURCE[f] for f in supported)})
    best_score = max(row['supported_commands'] for row in evaluations)
    best = [row for row in evaluations if row['supported_commands'] == best_score]
    if [row['removed_zero_bit'] for row in best] != list(range(9, 16)):
        raise ValueError('The observed bit-deletion hypotheses changed or are ambiguous')
    if any(row['mapping'] != EXPECTED_MAPPING for row in best) or best_score != 4542:
        raise ValueError('No invariant reviewed mapping across the best-supported hypotheses')
    return {'basis': 'Experimental single-zero-bit-deletion model, compared by command shape; not proven flag meanings.',
            'equivalent_removed_bit_positions': list(range(9, 16)),
            'mapping': [{'before': k, 'after': v} for k, v in sorted(EXPECTED_MAPPING.items())],
            'supported_commands': best_score, 'unsupported_commands_left_unchanged': 16,
            'unsupported_flags': [0x80100], 'semantics_proven': False,
            'evaluations': [{'removed_zero_bit': row['removed_zero_bit'], 'supported_commands': row['supported_commands']} for row in evaluations]}


def transform(events: list[dict], evidence: dict) -> tuple[list[dict], list[dict]]:
    model = hypothesis(evidence)
    if histogram(events) != evidence['source']['histogram']:
        raise ValueError('Command histogram does not match the reviewed source')
    after = copy.deepcopy(events)
    mapping = {row['before']: row['after'] for row in model['mapping']}
    changes = []
    for index, event in enumerate(after):
        if event['_event'] != 'NNet.Game.SCmdEvent':
            continue
        before = event['m_cmdFlags']
        value = mapping.get(before, before)
        if value != before:
            event['m_cmdFlags'] = value
            changes.append({'event_index': index, 'gameloop': event['_gameloop'],
                            'path': f'/game/{index}/m_cmdFlags', 'before': before, 'after': value,
                            'shape': shape(event), 'semantic_equivalence_proven': False})
    if len(changes) != 3247:
        raise AssertionError('Unexpected number of reviewed flag replacements')
    return after, changes


def repair(source: Path, output: Path, evidence: dict) -> dict:
    source, output = Path(source), Path(output)
    if output.exists() or source.resolve() == output.resolve():
        raise FileExistsError('Use a new experiment directory')
    if hashlib.sha256(source.read_bytes()).hexdigest() != R6_SHA256:
        raise ValueError('Only the immutable R6 checkpoint is accepted')
    model = hypothesis(evidence)
    before_profile = inspect_reference(source, 96477, 98285)
    before_integrity = integrity(source)
    game, _ = read_streams(source)
    intended, changes = transform(game, evidence)
    p = load_protocol(96477)
    original = MPQArchive(source)
    try:
        header = original.header['user_data_header']['content']
        names = list(dict.fromkeys(original.read_file('(listfile)').decode('ascii').splitlines() + ['(listfile)', '(attributes)']))
        members = {name: original.read_file(name) for name in names}
    finally:
        original.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.flag-hypothesis-', dir=output.parent) as temporary:
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
                    raise AssertionError('Independent reader mismatch: ' + name)
                if name not in ('replay.game.events', '(attributes)') and raw != members[name]:
                    raise AssertionError('Unrelated replay payload changed: ' + name)
            actual = list(decode_events(check.read_file('replay.game.events'), p, 'game'))
            if actual != intended:
                raise AssertionError('Encoded command changes differ from the intended changes')
            restored = copy.deepcopy(actual)
            for row in changes:
                restored[row['event_index']]['m_cmdFlags'] = row['before']
            if restored != game:
                raise AssertionError('The transformation altered data other than the allowlisted flags')
        finally:
            independent.file.close()
            check.close()
        if hashlib.sha256(source.read_bytes()).hexdigest() != R6_SHA256:
            raise AssertionError('Source was changed')
        report = {'format': 'hots-command-flag-experiment-v1',
                  'status': 'partial-hypothesis-not-verified-in-client', 'input_sha256': R6_SHA256,
                  'artifact': publish_binary(destination), 'hypothesis': model,
                  'changed_flag_values': len(changes),
                  'events': {k: v['count'] for k, v in after_profile['streams'].items()},
                  'event_counts_preserved': all(before_profile['streams'][k]['count'] == v['count'] for k, v in after_profile['streams'].items()),
                  'only_allowlisted_game_fields_changed': True,
                  'header_and_all_non_game_payloads_preserved': True,
                  'unit_tags_and_catalog_links_preserved': True,
                  'sync_checks_removed_or_disabled': False,
                  'input_integrity': before_integrity, 'output_integrity': after_integrity,
                  'container': container, 'official_observed_payload_roundtrip': True,
                  'client_playback_validated': False, 'simulation_compatibility_validated': False,
                  'limitations': ['The flag transformation is a shape-supported hypothesis, not an authoritative flag enumeration.',
                                  'The 16 unsupported source commands remain unchanged.',
                                  'R6 unit instance indices, numeric catalogs and the original synchronization records remain unchanged.',
                                  'Current Dragon Shire initialization differs from the original; matching flags cannot alone establish faithful playback.',
                                  'No HotS executable has played this candidate.']}
        write_json(stage / 'report.json', report)
        write_json(stage / 'flag-observation.json', evidence)
        (stage / 'command-flags.changes.jsonl').write_text(''.join(dump(c) + '\n' for c in changes), encoding='utf-8')
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
