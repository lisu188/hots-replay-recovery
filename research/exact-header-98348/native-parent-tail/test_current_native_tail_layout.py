"""Static current graph constraints; no replay or PE is loaded."""
from pathlib import Path
import unittest

import current_native_tail_layout as study


class NativeTailLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = Path(study.HERE/'native_startgame_schema_98348.json').read_bytes()
        cls.records = study.schema(cls.raw)

    def test_schema_pin_rejects_even_parseable_mutation(self):
        with self.assertRaisesRegex(ValueError, 'Pinned'):
            study.schema(self.raw.replace(b'OnlineStartGameRequest', b'OnlineOtherGameRequest'))

    def test_optional_ladder_season_rating_is_not_always_fixed38(self):
        self.assertEqual(study.width(self.records, 1815, present={1840: False}), 38)
        self.assertEqual(study.width(self.records, 1815, present={1840: True}), 70)
        with self.assertRaisesRegex(ValueError, 'presence'):
            study.width(self.records, 1815)

    def test_absent_amm_filler_and_unknown87_cross_native_boundaries(self):
        self.assertEqual(study.width(self.records, 5923, present={5923: False}), 1)
        self.assertEqual(study.width(self.records, 5923, present={5923: True}), 121)
        self.assertEqual(study.width(self.records, 1749), 96)
        self.assertEqual(16+87, 6+study.width(self.records, 1749)+1)

    def test_two_license_IDs_cannot_fit_observed_fixed48_item(self):
        self.assertEqual(study.width(self.records, 2510, counts={908: 0}), 48)
        self.assertEqual(study.width(self.records, 2510, counts={908: 2}), 112)
        with self.assertRaisesRegex(ValueError, 'count'):
            study.width(self.records, 2510, counts={908: 32769})

    def test_mastery_opaque128_is_only_sixteen_byte_branch(self):
        self.assertEqual(study.width(self.records, 1857, counts={1871: 16}), 165)
        self.assertEqual(study.width(self.records, 1857, counts={1871: 0}), 37)
        for bad in (-1, 17, True):
            with self.assertRaisesRegex(ValueError, 'bounds'):
                study.width(self.records, 1857, counts={1871: bad})

    def test_static_global_and_client_license_ID_types_are_distinct(self):
        self.assertEqual(study.width(self.records, 2509), 64)
        self.assertEqual(study.width(self.records, 866), 32)
        self.assertIn('Battlenet::BattlePay::LicenseId', [node['name'] for node in study.resolve(self.records, 2509)])
        self.assertIn('Battlenet::License::Id', [node['name'] for node in study.resolve(self.records, 866)])

    def test_context_dependent_blob_and_unspecified_array_are_refused(self):
        with self.assertRaisesRegex(ValueError, 'Context-dependent'):
            study.width(self.records, 136)
        with self.assertRaisesRegex(ValueError, 'count'):
            study.width(self.records, 1826)
        with self.assertRaisesRegex(ValueError, 'presence'):
            study.width(self.records, 5923, present={5923: 1})

    def test_frozen_whole_probe_boundaries_and_all25_root_names(self):
        report = study.analyze()
        self.assertEqual(len(report['root_fields']), 25)
        self.assertEqual(report['root_fields'][0]['start_bit'], 0)
        self.assertEqual(report['root_fields'][-1]['end_bit'], 2263808)
        self.assertFalse(report['old_to_current_conversion_implemented'])
        self.assertEqual(report['PE_replay_header_fragment_or_network_reads_in_this_stage'], 0)
        self.assertEqual(len(report['native_to_observed_groups']), 13)


if __name__ == '__main__':
    unittest.main()
