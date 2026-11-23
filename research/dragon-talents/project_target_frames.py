"""Encode isolated 98348 selection frames for the preserved TEN_GREYMANE source.

Use Python 3.11 with this repository and the pinned Blizzard heroprotocol
checkout on PYTHONPATH. The CLI prints public dispositions only. Call
project_target_frames(source, tree_report) for (report, frame_bytes_by_ordinal).
To add the nine independently pinned controls from other maps, supply
supplemental_controls or use --supplemental-controls on the command line.
"""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from hashlib import file_digest, sha256
import json
from pathlib import Path
import sys

from heroprotocol import decoders
from heroprotocol.versions import protocol41810, protocol96477

import native_game_events as native
from migrate_replay import SOURCE_SHA256, encode_events
from mpq_reader import MPQArchive
from source_talent_path_41810 import _tracker_history
from talent_choice_audit import SELECTION


TREE_SHA256 = 'ad2a2e092ff7bbe9fc3ded58e68c9791936d4c9d78edb1c7344cba264478dbae'
DRAGON_FRAMES_SHA256 = '24611512e7aaa20bc9dd231bdc5034e5e2446ff4cfb2dec1e1de63888ee96b70'
SUPPLEMENTAL_SHA256 = '9f3e9663cb969f1f5e073a9f5e880cd9fbd67c7006b8bad63c6c603cc0dcfc34'
SUPPLEMENTAL_BYTES = 33399
TARGET_ROOT = 'c3b3c8bc82e3a5a62e550fdde9a40c28'
UPSTREAM = {
    protocol41810: '879d228d9d8acd21d63563538dd15841aaf49259ee0bb468b8a46b6a4ef866fd',
    protocol96477: 'e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84',
    decoders: '17bfb926af0f7f79e18f6299dbae50fc2821c53b229235d4f9c857c7ef3e96b1',
}


def _encode_frame(delta, slot, event_id, target_index):
    event = native.GameEvent(delta, slot, event_id, (target_index,))
    raw = native.encode_game_events([event])
    # An isolated frame starts at zero, so the named encoder's clock is the
    # delta from the preceding event in the source match.
    named = {'_gameloop': delta, '_userid': {'m_userId': slot}, '_eventid': event_id,
             '_event': SELECTION, 'm_index': target_index}
    if encode_events([named], protocol96477, 'game') != raw:
        raise ValueError('Target selection encoders disagree')
    (decoded,) = native.iter_game_events(raw)
    (upstream,) = protocol96477.decode_replay_game_events(raw)
    if (decoded.event != event or decoded.start_bit != 0 or decoded.aligned_end_bit != len(raw) * 8
            or upstream.pop('_bits') != len(raw) * 8 or upstream != named):
        raise ValueError('Target selection decoders disagree or left trailing bits')
    return raw


def _candidate(frames, row, delta, slot, event_id):
    index = row['direct_position']
    raw = _encode_frame(delta, slot, event_id, index)
    frames[row['ordinal']] = raw
    row.update(status='isolated_wire_candidate', target_index=index, event_id=event_id,
               frame_bytes=len(raw), encoders_byte_equal=True, decoders_agree=True)


def _add_controls(report, frames, envelopes, event_id, path):
    # Bind the extension to the actual public output of the unmodified twelve-control
    # calculation, including its source, selection positions, statuses and schema.
    baseline = (json.dumps(report, indent=2, sort_keys=True) + '\n').encode('utf-8')
    if sha256(baseline).hexdigest() != DRAGON_FRAMES_SHA256:
        raise ValueError('Baseline frame projection differs from the published Dragon Shire result')
    with Path(path).open('rb') as handle:
        data = handle.read(SUPPLEMENTAL_BYTES + 1)
    if len(data) != SUPPLEMENTAL_BYTES or sha256(data).hexdigest() != SUPPLEMENTAL_SHA256:
        raise ValueError('Expected the pinned nine-control talent witness report')
    evidence = json.loads(data)
    if (evidence['format'] != 'supplemental-98348-target-talent-witnesses-v1' or
            evidence['target_build'] != report['target_build'] or evidence['root'] != TARGET_ROOT or
            evidence['dragon_baseline_sha256'] != DRAGON_FRAMES_SHA256 or
            evidence['control_overlaps_with_12_baseline'] != 0 or len(evidence['controls']) != 9):
        raise ValueError('Supplemental controls have a different baseline, sample or data build')

    contexts, cases = {}, defaultdict(list)
    for control in evidence['controls']:
        replay = control['replay_sha256']
        if replay in contexts:
            raise ValueError('Duplicate supplemental replay')
        contexts[replay] = {key: control[key] for key in ('map', 'map_checksum', 'mod_checksum')}
        for case in control['scoped']:
            if case['target_xml_positions'] != [case['index']]:
                raise ValueError('Scoped supplemental observation disagrees with its direct XML row')
            cases[case['hero'], case['purchase']].append((replay, case['index']))

    gained = []
    for row in report['selections']:
        matches = cases[row['hero'], row['purchase']]
        if not matches:
            continue
        counts = Counter(replay for replay, _ in matches)
        indices = sorted(set(row['observed_indices_for_name']) | {index for _, index in matches})
        if indices != [row['direct_position']]:
            raise ValueError('Independent sources disagree on the target index')
        row['dragon_observed_indices_for_name'] = row['observed_indices_for_name']
        row['observed_indices_for_name'] = indices
        row['supplemental_control_case_counts'] = dict(sorted(counts.items()))
        if row['status'] == 'no_independent_current_wire_observation':
            _candidate(frames, row, *envelopes[row['ordinal']], event_id)
            gained.append(dict(ordinal=row['ordinal'], source_loop=row['loop'], hero=row['hero'],
                               purchase=row['purchase'], current_index=indices[0], control_cases=len(matches),
                               control_replays=sorted(counts)))
    if gained != evidence['newly_witnessed_source_selections']:
        raise ValueError('Derived gains disagree with the independent supplemental study')
    report.update(format='ten-greymane-isolated-target-talent-frames-cross-map-v1',
                  dragon_baseline_frames_sha256=DRAGON_FRAMES_SHA256,
                  supplemental_controls_sha256=SUPPLEMENTAL_SHA256, target_data_root=TARGET_ROOT,
                  supplemental_replay_contexts=contexts, new_candidate_frames=len(gained),
                  candidate_frames=len(frames),
                  status_counts=dict(sorted(Counter(row['status'] for row in report['selections']).items())),
                  witness_scope='The original baseline contains twelve Dragon Shire controls. Supplemental '
                                'counts refer to individual replays with the map and mod checksums listed here. '
                                'A numeric witness establishes an isolated frame only in this comparison.')


def project_target_frames(source, tree_report, supplemental_controls=None):
    """Return aggregate-safe dispositions and separate private frame bytes by zero-based source event ordinal."""
    for module, expected in UPSTREAM.items():
        if sha256(Path(module.__file__).read_bytes()).hexdigest() != expected:
            raise ValueError('Unexpected upstream decoder or protocol')
    data = Path(tree_report).read_bytes()
    if sha256(data).hexdigest() != TREE_SHA256:
        raise ValueError('Expected the pinned public 98348 talent-tree comparison')
    ledger = json.loads(data)
    remaining = {row['ordinal']: row for row in ledger['selections']}
    with Path(source).open('rb') as stream:
        if file_digest(stream, 'sha256').hexdigest() != SOURCE_SHA256:
            raise ValueError('Expected the preserved 41810 replay')
    with closing(MPQArchive(source)) as archive:
        game = archive.read_file('replay.game.events')
        tracker = archive.read_file('replay.tracker.events')
        archive.file.seek(0)
        if file_digest(archive.file, 'sha256').hexdigest() != SOURCE_SHA256:
            raise ValueError('Source replay changed during extraction')
    setup, heroes, _, purchases = _tracker_history(protocol41810.decode_replay_tracker_events(tracker))
    (event_id,) = [key for key, (_, name) in protocol96477.game_event_types.items() if name == SELECTION]
    clock = bits = 0
    frames, rows, envelopes = {}, [], {}
    for ordinal, event in enumerate(protocol41810.decode_replay_game_events(game)):
        previous, clock = clock, event['_gameloop']
        bits += event['_bits']
        if event['_event'] != SELECTION:
            continue
        old, slot = event['m_index'], event['_userid']['m_userId']
        setup_tick, player = setup[slot]
        spawn, hero = heroes[player]
        purchase = purchases.pop((player, clock + 1))
        row = remaining.pop(ordinal)
        if (max(setup_tick, spawn) > clock or
                (hero, purchase, old, clock) != (row['hero'], row['purchase'], row['source_index'], row['loop'])):
            raise ValueError('Selection disagrees with recorded history')
        literal = row['target_literal']
        observed = row['observed_indices_for_name']
        result = {'ordinal': ordinal, 'loop': clock, 'hero': hero, 'purchase': purchase, 'source_index': old,
                  'direct_position': None if literal is None else literal['position'],
                  'observed_indices_for_name': observed}
        if supplemental_controls is not None:
            envelopes[ordinal] = (clock - previous, slot)
        if literal is None:
            result['status'] = 'absent_from_direct_tree'
        elif not observed:
            result['status'] = 'no_independent_current_wire_observation'
        elif observed != [literal['position']]:
            result['status'] = 'inconsistent_target_evidence'
        else:
            _candidate(frames, result, clock - previous, slot, event_id)
        rows.append(result)
    if remaining or purchases or bits != len(game) * 8 or len(rows) != len(ledger['selections']):
        raise ValueError('Incomplete source stream or unmatched selection')
    report = {'format': 'ten-greymane-isolated-target-talent-frames-v1', 'source_sha256': SOURCE_SHA256,
              'tree_report_sha256': TREE_SHA256, 'controls_sha256': ledger['controls_sha256'],
              'source_build': ledger['source_build'], 'target_build': ledger['target_build'],
              'target_physical_profile': native.PROFILE, 'target_numeric_schema_sha256': native.SCHEMA_SHA256,
              'source_game_events': ordinal + 1, 'source_selections': len(rows), 'candidate_frames': len(frames),
              'status_counts': dict(sorted(Counter(row['status'] for row in rows).items())),
              'context': 'Isolated frames retain the recorded numeric user slot and the delta from the immediately preceding source game event.',
              'target_player_identity_verified': False, 'semantic_equivalence_verified': False,
              'replay_application_eligible': False, 'selections': rows}
    if supplemental_controls is not None:
        _add_controls(report, frames, envelopes, event_id, supplemental_controls)
    return report, frames


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--tree-report', type=Path, required=True)
    parser.add_argument('--supplemental-controls', type=Path, help='Pinned nine-replay cross-map witness report')
    args = parser.parse_args()
    report, _ = project_target_frames(args.source, args.tree_report, args.supplemental_controls)
    sys.stdout.buffer.write((json.dumps(report, indent=2, sort_keys=True) + '\n').encode('utf-8'))
