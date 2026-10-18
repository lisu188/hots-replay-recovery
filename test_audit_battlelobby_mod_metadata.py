import json
from pathlib import Path
import tempfile
import unittest

from audit_battlelobby_mod_metadata import LayerError, audit_metadata, main

# Fixed small metadata-section goldens. They contain one synthetic mod, a name
# blob XY, a CAFEBABE sentinel, a terminal s2mh handle and an opaque END suffix.
LEGACY = bytes.fromhex('000000000000000000000000000000000001000015000000000501000005020000000100000000000000000000000000000000000000000000000000000000000058590000000000000000000000000000000000000000000000000000000000000000000000050200000001000000000000ca7f5d5f000000000000000000000173326d68000000000000000000000000000000000000000000000000000000000000000000000000454e44')
LEGACY_HERO = bytes.fromhex('000000000000000000000000000000000001000015000000000501000005020000000100000000000000000000000000000000000000000000000000000000000058590000000000000000000000000000000000000000000000000000000000000000000000050200000001000000000000ca7f5d5f000000000000000002002001000a0000000000000000000e00000003020000000010000000040000001200000b00000c00000d00000f000201000402000901001400001500004932b93701000000000173326d68000000000000000000000000000000000000000000000000000000000000000000000000454e44')
CURRENT = bytes.fromhex('00000000000000000000000000000000010000010a00000021020000002a0000000100000000000000000000000000000000000000000000000000000000000058590000000000000000000000000000000000000000000000000000000000000000000000050200000001000000000000ca7f5d5f000000000000000000000000000173326d68000000000000000000000000000000000000000000000000000000000000000000000000454e44')
CURRENT_HERO = bytes.fromhex('00000000000000000000000000000000010000010a00000021020000002a0000000100000000000000000000000000000000000000000000000000000000000058590000000000000000000000000000000000000000000000000000000000000000000000050200000001000000000000ca7f5d5f000000000000000002004001000a00000000020000000000000000010200000000000000000100000000000000000001020000000000000000010000000200000b00004932b93701000000000000000173326d68000000000000000000000000000000000000000000000000000000000000000000000000454e44')


def flip(raw, bit):
    data = bytearray(raw)
    data[bit // 8] ^= 1 << (bit % 8)
    return bytes(data)


class MetadataAuditTests(unittest.TestCase):
    def test_fixed_legacy_counts_and_sentinel(self):
        report = audit_metadata(LEGACY, 0, 'historical-fixed')
        self.assertEqual((report['used_mod_count'], report['mod_metadata_count'], report['terminal_s2mh_count']), (1, 1, 1))
        self.assertEqual(report['legacy_extra_three_bits'], 0)
        self.assertTrue(report['entries'][0]['cafebabe_valid'])
        self.assertEqual(report['entries'][0]['final_unknown_filler_bits'], 8)
        self.assertEqual(report['after_section_bytes'], 3)
        self.assertTrue(report['same_profile_full_member_roundtrip_exact'])

    def test_historical_arcade_is_named_array_data(self):
        entry = audit_metadata(LEGACY_HERO, 0, 'historical-fixed')['entries'][0]
        self.assertTrue(entry['has_static_arcade_info'])
        self.assertEqual((entry['how_to_play_sections']['section_header_count'], entry['how_to_play_sections']['localized_item_count']), (3, 9))
        self.assertEqual(entry['how_to_play_section_end_bit']-entry['how_to_play_section_start_bit'], 458)
        self.assertEqual(entry['matchmaker_tag_count'], 1)
        self.assertNotIn('historical_fixed_fields', entry)
        self.assertNotIn('current_choice', entry)

    def test_fixed_current_no_hero(self):
        report = audit_metadata(CURRENT, 0, 'current-observed')
        self.assertIsNone(report['legacy_extra_three_bits'])
        self.assertEqual(report['entries'][0]['final_unknown_filler_bits'], 32)

    def test_current_five_headers_are_an_array(self):
        entry = audit_metadata(CURRENT_HERO, 0, 'current-observed')['entries'][0]
        self.assertEqual((entry['how_to_play_sections']['section_header_count'], entry['how_to_play_sections']['localized_item_count']), (5, 1))
        self.assertEqual(entry['how_to_play_section_end_bit']-entry['how_to_play_section_start_bit'], 434)
        self.assertEqual(entry['game_info_screenshots_count'], 0)
        self.assertEqual(entry['how_to_play_screenshots_count'], 0)

    def test_wrong_profile_refused(self):
        for raw, profile in ((LEGACY, 'current-observed'), (CURRENT, 'historical-fixed')):
            with self.subTest(profile=profile), self.assertRaises(LayerError):
                audit_metadata(raw, 0, profile)

    def test_sentinel_corruption_refused(self):
        bit = audit_metadata(LEGACY, 0, 'historical-fixed')['entries'][0]['cafebabe_bit']
        with self.assertRaisesRegex(LayerError, 'sentinel'):
            audit_metadata(flip(LEGACY, bit), 0, 'historical-fixed')

    def test_inconsistent_mod_identity_refused(self):
        # The first used-mod identifier begins after128+3+6 bits.
        with self.assertRaisesRegex(LayerError, 'identities'):
            audit_metadata(flip(LEGACY, 137), 0, 'historical-fixed')

    def test_cache_magic_corruption_refused(self):
        with self.assertRaisesRegex(LayerError, 'magic'):
            audit_metadata(LEGACY.replace(b's2mh', b'EVIL'), 0, 'historical-fixed')

    def test_invalid_arcade_list_format_refused(self):
        entry = audit_metadata(CURRENT_HERO, 0, 'current-observed')['entries'][0]
        bit = entry['how_to_play_section_start_bit']+4+23+32
        data = bytearray(CURRENT_HERO)
        for position in (bit, bit+1): data[position//8] |= 1 << (position%8)
        with self.assertRaisesRegex(LayerError, 'list type'):
            audit_metadata(bytes(data), 0, 'current-observed')

    def test_uninterpreted_nonempty_auxiliary_arcade_arrays_refused(self):
        bit = audit_metadata(LEGACY_HERO, 0, 'historical-fixed')['entries'][0]['static_arcade_info_flag_bit']+1
        with self.assertRaisesRegex(LayerError, 'auxiliary'):
            audit_metadata(flip(LEGACY_HERO, bit), 0, 'historical-fixed')

    def test_unobserved_tutorial_link_refused(self):
        entry = audit_metadata(LEGACY_HERO, 0, 'historical-fixed')['entries'][0]
        bit = entry['patch_note_section_end_bit']+1  # after the absent map-icon flag
        with self.assertRaisesRegex(LayerError, 'tutorial'):
            audit_metadata(flip(LEGACY_HERO, bit), 0, 'historical-fixed')

    def test_truncated_handle_refused(self):
        with self.assertRaises(LayerError):
            audit_metadata(LEGACY[:-10], 0, 'historical-fixed')

    def test_nonzero_alignment_padding_refused(self):
        report = audit_metadata(LEGACY, 0, 'historical-fixed')
        padding_start = report['mod_metadata_end_bit'] + 6
        self.assertNotEqual(padding_start % 8, 0)
        with self.assertRaisesRegex(LayerError, 'padding'):
            audit_metadata(flip(LEGACY, padding_start), 0, 'historical-fixed')

    def test_invalid_arguments_refused(self):
        for start, profile in ((1, 'historical-fixed'), (-8, 'historical-fixed'), (0, 'guessed')):
            with self.subTest(start=start, profile=profile), self.assertRaises(LayerError):
                audit_metadata(LEGACY, start, profile)

    def test_report_privacy_and_no_compatibility_claim(self):
        report = audit_metadata(LEGACY_HERO, 0, 'historical-fixed')
        self.assertNotIn('XY', json.dumps(report))
        self.assertNotIn('identity', json.dumps(report).replace('raw_blob_or_identity_values_emitted', ''))
        self.assertFalse(report['conversion_performed'])
        self.assertFalse(report['full_member_semantics_validated'])
        self.assertFalse(report['current_profile_compatibility_proven'])
        self.assertFalse(report['client_launched'])
        self.assertTrue(report['dependency_version_fields_preserved'])
        self.assertFalse(report['dependency_version_resolution_semantics_validated'])

    def test_existing_report_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'report.json'
            path.write_text('preserve')
            with self.assertRaises(SystemExit):
                main(['--case', 'fixture', 'legacy-10', 'historical-fixed', 'unused', '--report', str(path)])
            self.assertEqual(path.read_text(), 'preserve')


if __name__ == '__main__':
    unittest.main()
