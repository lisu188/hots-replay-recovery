"""Synthetic boundary tests for the strict seven-record framing limit."""
import unittest
import legacy_mapinfo_framing as codec
from test_legacy_mapinfo_framing import Fixture, admitted


class SevenControlAdmissionTests(unittest.TestCase):
    def test_seven_synthetic_records_preserve_bits_and_inverse(self):
        fixture = Fixture(records=7, start=5,
                          overrides={'/m_handle/m_id': 123, '/m_extraDependencies': 2})
        with admitted(fixture):
            value = codec.convert_mapinfo_framing(fixture.raw, codec.PROFILE)
            self.assertEqual(value.converted, fixture.expected())
            self.assertEqual(codec.inverse_mapinfo_framing(value, codec.PROFILE), fixture.raw)
            report = value.summary()
            self.assertEqual((report['MapInfo_records'], report['added_bytes'],
                              report['named_root_field_comparisons']), (7, 21, 224))
            self.assertTrue(report['all_non_count_tokens_and_outside_bits_exact'])

    def test_eight_records_refused_even_with_test_digest_admission(self):
        fixture = Fixture(records=8)
        with admitted(fixture):
            with self.assertRaises(codec.LayerError):
                codec.convert_mapinfo_framing(fixture.raw, codec.PROFILE)


if __name__ == '__main__':
    unittest.main()
