from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from repair_command_flags import EXPECTED_MAPPING, delete_zero_bit, histogram, hypothesis, repair, shape, transform

OBSERVATION = Path(__file__).parent / 'observations/command-flags-98285-2026-09-29.json'


def evidence():
    return json.loads(OBSERVATION.read_text())


def events():
    result = []
    for row in evidence()['source']['histogram']:
        for target, count in row['shapes'].items():
            explicit, kind = target.split(':')
            for _ in range(count):
                result.append({'_event': 'NNet.Game.SCmdEvent', '_gameloop': len(result),
                               'm_cmdFlags': row['flags'], 'm_abil': None if explicit == 'implicit' else {'m_abilLink': 999},
                               'm_data': {kind: None}, 'm_unrelated': 12345})
    return result


class BitModelTests(unittest.TestCase):
    def test_set_bit_never_discarded(self):
        for bit in range(26):
            with self.assertRaises(ValueError):
                delete_zero_bit(1 << bit, bit)

    def test_bounds_and_boolean_cut_rejected(self):
        for bit in (-1, 26, True):
            with self.assertRaises(ValueError):
                delete_zero_bit(0, bit)
        for value in (-1, True, 1 << 26):
            with self.assertRaises(ValueError):
                delete_zero_bit(value, 9)

    def test_equivalent_cut_positions_have_same_observed_result(self):
        for before, after in EXPECTED_MAPPING.items():
            for cut in range(9, 16):
                self.assertEqual(delete_zero_bit(before, cut), after)

    def test_flag_transform_is_reversible_on_zero_bit_domain(self):
        for cut in range(26):
            for value in (0, 0x100, 0x100108, 0x200100):
                if value & (1 << cut):
                    continue
                encoded = delete_zero_bit(value, cut)
                restored = (encoded & ((1 << cut) - 1)) | ((encoded >> cut) << (cut + 1))
                self.assertEqual(restored, value)


class HypothesisTests(unittest.TestCase):
    def test_best_supported_model_remains_explicitly_unproven(self):
        value = hypothesis(evidence())
        self.assertEqual(value['equivalent_removed_bit_positions'], list(range(9, 16)))
        self.assertEqual(value['supported_commands'], 4542)
        self.assertEqual(value['unsupported_commands_left_unchanged'], 16)
        self.assertFalse(value['semantics_proven'])

    def test_wrong_provenance_rejected(self):
        data = evidence()
        data['references'][0]['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            hypothesis(data)

    def test_reference_validation_is_required(self):
        for field, value in (('observed_payload_roundtrip', False), ('declared_build', True), ('declared_build', 98297)):
            data = evidence()
            data['references'][0][field] = value
            with self.assertRaises(ValueError):
                hypothesis(data)

    def test_source_counts_bound_to_reviewed_replay(self):
        data = evidence()
        row = data['source']['histogram'][0]['shapes']
        key = next(iter(row))
        row[key] += 1
        with self.assertRaises(ValueError):
            hypothesis(data)

    def test_duplicate_flag_records_rejected(self):
        data = evidence()
        data['references'][0]['histogram'].append(data['references'][0]['histogram'][0])
        with self.assertRaises(ValueError):
            hypothesis(data)

    def test_unrecognized_shapes_rejected(self):
        data = evidence()
        data['references'][0]['histogram'][0]['shapes']['implicit:Unknown'] = 1
        with self.assertRaises(ValueError):
            hypothesis(data)

    def test_nonpositive_and_boolean_counts_rejected(self):
        for value in (0, -1, True):
            data = evidence()
            row = data['references'][0]['histogram'][0]['shapes']
            row[next(iter(row))] = value
            with self.assertRaises(ValueError):
                hypothesis(data)

    def test_removed_support_is_not_silently_ignored(self):
        data = evidence()
        data['references'][0]['histogram'] = [r for r in data['references'][0]['histogram'] if r['flags'] != 0x100100]
        with self.assertRaises(ValueError):
            hypothesis(data)

    def test_malformed_choice_rejected(self):
        for target in ({}, {'None': None, 'TargetPoint': {}}, {'Unknown': {}}):
            with self.assertRaises(ValueError):
                shape({'m_data': target})


class TransformTests(unittest.TestCase):
    def test_exactly_reviewed_flags_change_and_no_other_data(self):
        before = events()
        original = copy.deepcopy(before)
        after, changes = transform(before, evidence())
        self.assertEqual(len(changes), 3247)
        self.assertEqual(before, original)
        for row in changes:
            self.assertFalse(row['semantic_equivalence_proven'])
            after[row['event_index']]['m_cmdFlags'] = row['before']
        self.assertEqual(after, before)

    def test_unsupported_sixteen_commands_remain_untouched(self):
        before = events()
        after, _ = transform(before, evidence())
        indices = [i for i, row in enumerate(before) if row['m_cmdFlags'] == 0x80100]
        self.assertEqual(len(indices), 16)
        self.assertTrue(all(before[i] == after[i] for i in indices))

    def test_repeat_transform_rejected(self):
        after, _ = transform(events(), evidence())
        with self.assertRaises(ValueError):
            transform(after, evidence())

    def test_unknown_source_flag_rejected(self):
        game = events()
        game[0]['m_cmdFlags'] = 7
        with self.assertRaises(ValueError):
            transform(game, evidence())

    def test_different_command_shape_rejected(self):
        game = events()
        game[0]['m_data'] = {'Data': {}}
        with self.assertRaises(ValueError):
            transform(game, evidence())

    def test_non_command_events_are_preserved(self):
        game = events()
        game.insert(0, {'_event': 'NNet.Game.SCameraUpdateEvent', '_gameloop': 0, 'm_cmdFlags': 999})
        after, _ = transform(game, evidence())
        self.assertEqual(after[0], game[0])

    def test_wrong_source_does_not_create_output_or_decode(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'bad.StormReplay'
            source.write_bytes(b'invalid')
            output = Path(directory) / 'output'
            with patch('repair_command_flags.inspect_reference') as read:
                with self.assertRaises(ValueError):
                    repair(source, output, evidence())
                read.assert_not_called()
            self.assertFalse(output.exists())

    def test_existing_destination_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            with self.assertRaises(FileExistsError):
                repair(output / 'missing.StormReplay', output, evidence())


if __name__ == '__main__':
    unittest.main()
