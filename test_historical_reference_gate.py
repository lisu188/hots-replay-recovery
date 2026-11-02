"""Admission and cross-profile failures; real private controls run separately."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import legacy_mapinfo_framing as codec
from scripts import check_historical_references as gate
from test_legacy_mapinfo_framing import Fixture, admitted


class HistoricalReferenceGateTests(unittest.TestCase):
    def test_same_size_wrong_fixture_refused_before_decoder_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'claimed41810.StormReplay'
            for profile in ('41810-local3', '41810-local4', '41810-local5'):
                with self.subTest(profile=profile):
                    path.write_bytes(b'\0' * gate.PROFILES[profile]['bytes'])
                    with patch.object(gate, '_load_pinned_protocol') as loader:
                        with self.assertRaisesRegex(ValueError, 'SHA-256 differs'):
                            gate.verify_reference(path, profile)
                        loader.assert_not_called()

    def source(self):
        fixture = Fixture(start=7, records=5,
                          overrides={'/m_handle/m_id': 123, '/m_extraDependencies': 2})
        with admitted(fixture):
            value = codec.convert_mapinfo_framing(fixture.raw, codec.PROFILE)
            self.assertEqual(value.converted, fixture.expected())
            facts = value.summary()
        expected = {'mod_count': 5, 'lobby_sha256': codec.sha(fixture.raw)}
        framing = {'source_id': 'synthetic',
                   'all_native_field_comparisons': facts['all_native_field_comparisons'],
                   'converted_sha256': codec.sha(fixture.expected())}
        return fixture, expected, framing

    def test_five_record_gate_returns_facts_without_payload(self):
        fixture, expected, framing = self.source()
        with admitted(fixture):
            report = gate.verify_mapinfo(fixture.raw, expected, framing)
        self.assertEqual((report['records'], report['added_bytes'],
                          report['named_root_field_comparisons']), (5, 15, 160))
        self.assertTrue(report['inverse_whole_source_bytes_exact'])
        self.assertFalse(report['payload_written'])
        self.assertFalse(report['whole_replay_conversion_proven'])
        self.assertTrue(all(type(value) in (str, int, bool) for value in report.values()))

    def test_other_profile_source_id_refused(self):
        fixture, expected, framing = self.source()
        framing['source_id'] = 'another-admitted-source'
        with admitted(fixture):
            with self.assertRaisesRegex(ValueError, 'source admission differs'):
                gate.verify_mapinfo(fixture.raw, expected, framing)

    def test_other_profile_converted_digest_refused(self):
        fixture, expected, framing = self.source()
        framing['converted_sha256'] = '0' * 64
        with admitted(fixture):
            with self.assertRaisesRegex(ValueError, 'converted-member pin differs'):
                gate.verify_mapinfo(fixture.raw, expected, framing)

    def test_other_profile_native_field_count_refused(self):
        fixture, expected, framing = self.source()
        framing['all_native_field_comparisons'] += 1
        with admitted(fixture):
            with self.assertRaisesRegex(ValueError, 'comparison counts differ'):
                gate.verify_mapinfo(fixture.raw, expected, framing)

    def test_other_profile_record_count_refused(self):
        fixture, expected, framing = self.source()
        wrong = deepcopy(expected)
        wrong['mod_count'] = 7
        with admitted(fixture):
            with self.assertRaisesRegex(ValueError, 'comparison counts differ'):
                gate.verify_mapinfo(fixture.raw, wrong, framing)


if __name__ == '__main__':
    unittest.main()
