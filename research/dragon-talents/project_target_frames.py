"""Encode isolated 98348 selection frames for the preserved TEN_GREYMANE source.

Use Python 3.11 with this repository and the pinned Blizzard heroprotocol
checkout on PYTHONPATH. The CLI prints public dispositions only. Call
project_target_frames(source, tree_report) for (report, frame_bytes_by_ordinal).
"""

import argparse
from collections import Counter
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


def project_target_frames(source, tree_report):
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
    frames, rows = {}, []
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
        if literal is None:
            result['status'] = 'absent_from_direct_tree'
        elif not observed:
            result['status'] = 'no_independent_current_wire_observation'
        elif observed != [literal['position']]:
            result['status'] = 'inconsistent_target_evidence'
        else:
            target_index = literal['position']
            raw = _encode_frame(clock - previous, slot, event_id, target_index)
            frames[ordinal] = raw
            result.update(status='isolated_wire_candidate', target_index=target_index,
                          event_id=event_id, frame_bytes=len(raw), encoders_byte_equal=True, decoders_agree=True)
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
    return report, frames


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--tree-report', type=Path, required=True)
    args = parser.parse_args()
    report, _ = project_target_frames(args.source, args.tree_report)
    sys.stdout.buffer.write((json.dumps(report, indent=2, sort_keys=True) + '\n').encode('utf-8'))
