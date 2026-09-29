from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from command_identity_audit import ORDERS, analyse, apply_delta, integer, mask_bits, run
from migrate_replay import BitVector


def born(index=1, loop=0, unit_type=b'HeroAnubarak'):
    return {'_event': 'NNet.Replay.Tracker.SUnitBornEvent', '_gameloop': loop,
            'm_unitTagIndex': index, 'm_unitTagRecycle': 1, 'm_unitTypeName': unit_type}


def selection(indices=(1,), loop=1, mask=None, user=0):
    tags = [(index << 18) | 1 for index in indices]
    return {'_event': 'NNet.Game.SSelectionDeltaEvent', '_gameloop': loop, '_userid': {'m_userId': user},
            'm_controlGroupId': 10, 'm_delta': {'m_subgroupIndex': 0,
            'm_removeMask': mask or {'None': None}, 'm_addUnitTags': tags,
            'm_addSubgroups': [{'m_unitLink': 739, 'm_count': len(tags)}] if tags else []}}


def command(loop=2, ability=31, user=0):
    return {'_event': 'NNet.Game.SCmdEvent', '_gameloop': loop, '_userid': {'m_userId': user},
            'm_abil': None if ability is None else {'m_abilLink': ability, 'm_abilCmdIndex': 0},
            'm_data': {'None': None}, 'm_sequence': 1, 'm_cmdFlags': 256, 'm_otherUnit': None,
            'm_unitGroup': None}


class MaskTests(unittest.TestCase):
    def test_low_bits(self):
        self.assertEqual(mask_bits(BitVector(3, 6), ORDERS[0]), [False, True, True])

    def test_high_bits(self):
        self.assertEqual(mask_bits(BitVector(3, 6), ORDERS[1]), [True, True, False])

    def test_zero_length(self):
        self.assertEqual(mask_bits((0, 0), ORDERS[0]), [])

    def test_overflow(self):
        with self.assertRaises(ValueError): mask_bits((3, 8), ORDERS[0])

    def test_boolean_width(self):
        with self.assertRaises(ValueError): mask_bits((True, 0), ORDERS[0])

    def test_unknown_order(self):
        with self.assertRaises(ValueError): mask_bits((3, 1), 'guessed')

    def test_negative(self):
        with self.assertRaises(ValueError): integer(-1)

    def test_bad_mask_type(self):
        with self.assertRaises(ValueError): mask_bits('010', ORDERS[0])

    def test_sorted_unique_addition(self):
        delta = selection((2, 1))['m_delta']
        self.assertEqual(apply_delta((), delta, ORDERS[0]), ((1 << 18) | 1, (2 << 18) | 1))

    def test_duplicate_addition_rejected(self):
        with self.assertRaises(ValueError): apply_delta((), selection((1, 1))['m_delta'], ORDERS[0])

    def test_subgroup_count(self):
        delta = selection()['m_delta']; delta['m_addSubgroups'][0]['m_count'] = 2
        with self.assertRaises(ValueError): apply_delta((), delta, ORDERS[0])

    def test_empty_subgroup_rejected(self):
        delta = selection(())['m_delta']; delta['m_addSubgroups'] = [{'m_count': 0, 'm_unitLink': 0}]
        with self.assertRaises(ValueError): apply_delta((), delta, ORDERS[0])['m_delta'], ORDERS[0])

    def test_out_of_range_link(self):
        delta = selection()['m_delta']; delta['m_addSubgroups'][0]['m_unitLink'] = 65536
        with self.assertRaises(ValueError): apply_delta((), delta, ORDERS[0])

    def test_none_payload_rejected(self):
        with self.assertRaises(ValueError): apply_delta((), selection((), mask={'None': 1})['m_delta'], ORDERS[0])

    def test_mask_length_rejected(self):
        with self.assertRaises(ValueError): apply_delta((), selection((), mask={'Mask': BitVector(1, 1)})['m_delta'], ORDERS[0])

    def test_zero_indices_empty_clears(self):
        delta = selection((), mask={'ZeroIndices': []})['m_delta']
        self.assertEqual(apply_delta((1, 2), delta, ORDERS[0]), ())

    def test_zero_indices_selects(self):
        delta = selection((), mask={'ZeroIndices': [1]})['m_delta']
        self.assertEqual(apply_delta((1, 2), delta, ORDERS[0]), (2,))

    def test_zero_index_outside_rejected(self):
        with self.assertRaises(ValueError): apply_delta((1,), selection((), mask={'ZeroIndices': [1]})['m_delta'], ORDERS[0])

    def test_one_indices_not_guessed(self):
        with self.assertRaises(ValueError): apply_delta((1,), selection((), mask={'OneIndices': [0]})['m_delta'], ORDERS[0])

    def test_bad_seed_rejected(self):
        with self.assertRaises(ValueError): apply_delta((2, 1), selection(())['m_delta'], ORDERS[0])


class ContextTests(unittest.TestCase):
    def test_single_observed_context_is_not_proof(self):
        summary, rows = analyse([selection(), command()], [born()])
        self.assertEqual(rows[0]['selected_unit_type_candidate'], 'HeroAnubarak')
        self.assertFalse(rows[0]['executed_caster_verified'])
        self.assertIsNone(summary['abilities'][0]['portable_ability_name'])
        self.assertFalse(summary['client_playback_validated'])

    def test_two_mask_interpretations_not_majority_voted(self):
        events = [selection((1, 2)), selection((), loop=2, mask={'Mask': BitVector(2, 2)}), command(3)]
        _, rows = analyse(events, [born(), born(2, unit_type=b'HeroKaelthas')])
        self.assertEqual(rows[0]['classification'], 'mask_interpretations_disagree')
        self.assertIsNone(rows[0]['selected_unit_type_candidate'])

    def test_empty_context(self):
        _, rows = analyse([command()], [born()])
        self.assertEqual(rows[0]['classification'], 'empty_selection')

    def test_multiselect_not_a_caster(self):
        _, rows = analyse([selection((1, 2)), command()], [born(), born(2)])
        self.assertEqual(rows[0]['classification'], 'multiple_selected_units')

    def test_no_future_identity(self):
        _, rows = analyse([selection(), command()], [born(loop=3)])
        self.assertEqual(rows[0]['classification'], 'lifecycle_ambiguous')

    def test_same_tick_identity_excluded(self):
        _, rows = analyse([selection(), command()], [born(loop=2)])
        self.assertEqual(rows[0]['classification'], 'lifecycle_ambiguous')

    def test_dead_unit_excluded(self):
        death = born(loop=2); death['_event'] = 'NNet.Replay.Tracker.SUnitDiedEvent'
        _, rows = analyse([selection(), command(loop=3)], [born(), death])
        self.assertEqual(rows[0]['classification'], 'lifecycle_ambiguous')

    def test_other_unit_excluded(self):
        event = command(); event['m_otherUnit'] = 262145
        _, rows = analyse([selection(), event], [born()])
        self.assertEqual(rows[0]['classification'], 'explicit_source_override_not_interpreted')

    def test_unit_group_excluded(self):
        event = command(); event['m_unitGroup'] = 7
        _, rows = analyse([selection(), event], [born()])
        self.assertIsNone(rows[0]['selected_unit_type_candidate'])

    def test_user_banks_are_separate(self):
        _, rows = analyse([selection(user=1), command(user=0)], [born()])
        self.assertEqual(rows[0]['classification'], 'empty_selection')

    def test_unknown_control_group_event_rejected(self):
        event = {'_gameloop': 1, '_event': 'NNet.Game.SControlGroupUpdateEvent'}
        with self.assertRaises(ValueError): analyse([event], [])

    def test_inactive_selection_rejected(self):
        event = selection(); event['m_controlGroupId'] = 2
        with self.assertRaises(ValueError): analyse([event], [])

    def test_decreasing_events_rejected(self):
        with self.assertRaises(ValueError): analyse([selection(loop=3), command(loop=2)], [born()])

    def test_prefix_counts_implicit_and_explicit_separately(self):
        events = [selection(loop=52), command(loop=61, ability=None), command(loop=133)]
        report, _ = analyse(events, [born()])
        self.assertEqual(report['commands_through_boundary'], 1)
        self.assertEqual(report['explicit_ability_commands_through_boundary'], 0)
        self.assertEqual(report['first_explicit_ability_gameloop'], 133)

    def test_zero_ability_index_not_missing(self):
        report, _ = analyse([command(ability=0)], [born()])
        self.assertEqual(report['ability_links'], 1)

    def test_input_objects_not_modified(self):
        events = [selection(), command()]; original = copy.deepcopy(events)
        analyse(events, [born()]); self.assertEqual(events, original)

    def test_repeated_result_identical(self):
        events = [selection(), command()]
        self.assertEqual(analyse(events, [born()]), analyse(events, [born()]))

    def test_unsupported_tag_shift_rejected(self):
        with self.assertRaises(ValueError): analyse([], [], shift=23)

    def test_target_choice_rejected(self):
        event = command(); event['m_data'] = {'unknown': 1}
        with self.assertRaises(ValueError): analyse([event], [])

    def test_wrong_source_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'wrong.StormReplay'; source.write_bytes(b'not the original')
            output = Path(tmp) / 'audit'
            with self.assertRaises(ValueError): run(source, output)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
