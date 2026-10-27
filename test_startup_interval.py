from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from audit_startup_interval import audit, interval_report, read_verified, sync_summary
from test_catalog_diagnostics import selection, tag, unit


def command(loop=61, ability=None):
    return {'_event': 'NNet.Game.SCmdEvent', '_gameloop': loop, 'm_cmdFlags': 524552,
            'm_abil': ability, 'm_data': {'TargetPoint': {'x': 1, 'y': 2, 'z': 3}}}


class StartupIntervalTests(unittest.TestCase):
    def test_known_mismatch_is_observation_not_applied_mapping(self):
        r = interval_report([selection(link=739)], [unit(name=b'HeroAnubarak')], {'HeroAnubarak': 468})
        f = r['catalog_fields'][0]
        self.assertEqual((f['recorded_catalog_link'], f['reference_catalog_link']), (739, 468))
        self.assertEqual(f['comparison'], 'differs_from_observed_anchor')
        self.assertFalse(r['cross_map_catalog_equivalence_proven'])
        self.assertFalse(r['replay_modified'])
        self.assertFalse(f['live_instance_identity_verified'])

    def test_matching_anchor_is_not_playback_proof(self):
        r = interval_report([selection(link=468)], [unit(name=b'HeroAnubarak')], {'HeroAnubarak': 468})
        self.assertEqual(r['catalog_fields'][0]['comparison'], 'same_as_observed_anchor')
        self.assertFalse(r['client_playback_validated'])

    def test_unseen_type_not_inferred_by_offset(self):
        r = interval_report([selection(link=807)], [unit(name=b'HeroGreymane')], {'HeroAnubarak': 468})
        self.assertEqual(r['catalog_fields'][0]['comparison'], 'no_current_reference_anchor')
        self.assertIsNone(r['catalog_fields'][0]['reference_catalog_link'])

    def test_tick_64_is_excluded(self):
        r = interval_report([command(63), command(64)], [], {})
        self.assertEqual(len(r['commands']), 1)
        self.assertEqual(r['commands'][0]['gameloop'], 63)
        self.assertFalse(r['first_divergent_tick_identified'])

    def test_explicit_ability_classified_without_name_guess(self):
        r = interval_report([command(5, {'m_abilLink': 31, 'm_abilCmdIndex': 0})], [], {})
        self.assertEqual(r['counts']['explicit_ability_commands'], 1)
        self.assertEqual(r['commands'][0]['ability_link'], 31)

    def test_implicit_commands_do_not_invent_ability_link(self):
        r = interval_report([command()], [], {})
        self.assertEqual(r['counts']['explicit_ability_commands'], 0)
        self.assertIsNone(r['commands'][0]['ability_link'])

    def test_same_tick_birth_not_used(self):
        r = interval_report([selection(loop=2)], [unit(loop=2)], {'HeroA': 1})
        self.assertEqual(r['catalog_fields'][0]['comparison'], 'identity_unresolved')

    def test_future_identity_not_used(self):
        r = interval_report([selection(loop=2)], [unit(loop=3)], {'HeroA': 1})
        self.assertEqual(r['catalog_fields'][0]['identities'][0]['identity_evidence'], 'no_prior_identity')

    def test_old_lifetime_not_reused(self):
        t = [unit(), unit('SUnitDiedEvent', 1), unit(loop=2, recycle=2)]
        r = interval_report([selection(loop=3)], t, {'HeroA': 1})
        self.assertEqual(r['catalog_fields'][0]['comparison'], 'identity_unresolved')

    def test_mixed_type_subgroup_is_not_single_mapping(self):
        t = [unit(), unit(index=2, name=b'HeroB')]
        r = interval_report([selection(tags=[tag(), tag(2)])], t, {'HeroA': 1})
        self.assertEqual(r['catalog_fields'][0]['comparison'], 'identity_unresolved')

    def test_sentinel_does_not_resolve_to_type(self):
        r = interval_report([selection(tags=[0])], [unit(index=0, recycle=0)], {'HeroA': 1})
        self.assertEqual(r['catalog_fields'][0]['identities'][0]['identity_evidence'], 'sentinel')

    def test_event_index_preserved(self):
        r = interval_report([{'_event': 'camera', '_gameloop': 1}, selection(loop=2)], [unit()], {})
        self.assertEqual(r['catalog_fields'][0]['event_index'], 1)

    def test_invalid_interval_rejected(self):
        for stop in (False, 0, -1, 4097, 1.5):
            with self.subTest(stop=stop), self.assertRaises(ValueError):
                interval_report([], [], {}, stop)

    def test_invalid_anchor_rejected(self):
        for anchors in ({'Hero': True}, {'Hero': -1}, {'Hero': 65536}, {'': 1}, []):
            with self.subTest(anchors=anchors), self.assertRaises(ValueError):
                interval_report([], [], anchors)

    def test_out_of_order_event_after_window_rejected(self):
        with self.assertRaises(ValueError):
            interval_report([command(100), command(99)], [], {})

    def test_bool_loop_rejected(self):
        with self.assertRaises(ValueError):
            interval_report([command(True)], [], {})

    def test_malformed_selection_rejected(self):
        with self.assertRaises(ValueError):
            interval_report([selection(tags=[tag()], groups=[])], [], {})

    def test_malformed_command_rejected(self):
        for invalid in ({}, {'TargetPoint': {}, 'None': None}):
            c = command(); c['m_data'] = invalid
            with self.subTest(data=invalid), self.assertRaises(ValueError):
                interval_report([c], [], {})

    def test_invalid_ability_rejected(self):
        with self.assertRaises(ValueError):
            interval_report([command(5, 'attack')], [], {})

    def test_inputs_unchanged_and_repeatable(self):
        game, tracker, anchors = [selection(), command()], [unit()], {'HeroA': 5}
        before = copy.deepcopy((game, tracker, anchors))
        self.assertEqual(interval_report(game, tracker, anchors), interval_report(game, tracker, anchors))
        self.assertEqual((game, tracker, anchors), before)

    def test_sync_framing_uses_native_record_boundaries(self):
        raw = bytes.fromhex('0140131a000140131a00')
        r = sync_summary(raw, 128)
        self.assertEqual(r['first_record_hex'], '0140131a00')
        self.assertEqual(r['first_record_bytes'], 5)
        self.assertEqual(r['record_count'], 2)
        self.assertEqual(r['prefix_counts'], {'0140': 2})
        self.assertEqual(r['record_byte_lengths'], {5: 2})
        self.assertEqual(r['event_id_counts'], {2: 2})
        self.assertEqual((r['first_recorded_gameloop'], r['last_recorded_gameloop']),
                         (64, 128))
        self.assertTrue(r['count_matches_elapsed_floor_div_64'])
        self.assertTrue(r['byte_exact_roundtrip'])
        self.assertFalse(r['first_check_tick_measured'])
        self.assertFalse(r['first_divergent_tick_identified'])
        self.assertFalse(r['checksum_algorithm_identified'])

    def test_different_sync_prefix_is_reported_not_discarded(self):
        # Native delta16384/event2/u16=0x1234 is a six-byte record.
        r = sync_summary(bytes.fromhex('024000131a00'), 64)
        self.assertEqual(r['prefix_counts'], {'0240': 1})
        self.assertEqual(r['record_count'], 1)
        self.assertEqual(r['record_byte_lengths'], {6: 1})
        self.assertEqual(r['first_recorded_gameloop'], 16384)
        self.assertIsNone(r['first_record_hex'])

    def test_different_sync_count_is_reported(self):
        r = sync_summary(bytes.fromhex('00131a00'), 128)
        self.assertFalse(r['count_matches_elapsed_floor_div_64'])
        self.assertEqual(r['first_record_hex'], '00131a00')
        self.assertEqual(r['first_record_bytes'], 4)

    def test_mixed_variable_lengths_are_counted_at_actual_boundaries(self):
        # Hand-laid-out event1(word0x01234567,u16=0xabcd), then event2.
        # Two records occupy14 bytes rather than a multiple of five.
        raw = bytes.fromhex('04000191a2b3abe6010140131a00')
        r = sync_summary(raw, 128)
        self.assertEqual((r['bytes'], r['record_count']), (14, 2))
        self.assertEqual(r['prefix_counts'], {'0140': 1, '0400': 1})
        self.assertEqual(r['record_byte_lengths'], {5: 1, 9: 1})
        self.assertEqual(r['event_id_counts'], {1: 1, 2: 1})
        self.assertEqual(r['delta_variant_counts'], {0: 1, 1: 1})
        self.assertEqual(r['vector_words'], 1)
        self.assertEqual((r['first_recorded_gameloop'], r['last_recorded_gameloop']),
                         (1, 65))
        # Equal record count does not prove a64-loop cadence or a failing tick.
        self.assertTrue(r['count_matches_elapsed_floor_div_64'])
        self.assertFalse(r['first_divergent_tick_identified'])
        self.assertFalse(r['playback_compatibility_proven'])
        self.assertIsNone(r['first_record_hex'])
        self.assertEqual(r['first_record_bytes'], 9)
        self.assertNotIn('04000191a2b3abe601', repr(r))
        self.assertFalse(r['parsed_anonymous_payload_values_emitted'])

    def test_noncanonical_wide_delta_keeps_its_physical_length(self):
        r = sync_summary(bytes.fromhex('03000000154604'), 64)
        self.assertEqual(r['first_recorded_gameloop'], 1)
        self.assertEqual(r['delta_variant_counts'], {3: 1})
        self.assertEqual(r['record_byte_lengths'], {7: 1})
        self.assertIsNone(r['first_record_hex'])
        self.assertTrue(r['byte_exact_roundtrip'])

    def test_nonzero_sync_alignment_bits_are_retained(self):
        r = sync_summary(bytes.fromhex('0140131aaa'), 64)
        self.assertEqual(r['nonzero_padding_records'], 1)
        self.assertEqual(r['first_record_hex'], '0140131aaa')
        self.assertTrue(r['byte_exact_roundtrip'])

    def test_invalid_sync_framing_rejected(self):
        for raw in (b'', b'1', bytes.fromhex('0140131a'),
                    bytes.fromhex('04000191a2b3abe6'), '0140131a00'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                sync_summary(raw, 64)

    def test_invalid_elapsed_sync_context_rejected(self):
        for elapsed in (True, -1, 0x100000000, 1.5):
            with self.subTest(elapsed=elapsed), self.assertRaises(ValueError):
                sync_summary(bytes.fromhex('0140131a00'), elapsed)

    def test_wrong_replay_rejected_before_decoding(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'fake'; p.write_bytes(b'not a replay')
            with self.assertRaises(ValueError):
                read_verified(p, '0' * 64, 41810, 41810)

    def test_wrong_anchor_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'anchors'; p.write_text('{}')
            with self.assertRaises(ValueError):
                audit(Path('absent'), Path('absent'), p)


if __name__ == '__main__':
    unittest.main()
