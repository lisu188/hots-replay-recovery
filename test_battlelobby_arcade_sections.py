"""Frozen static-package fragments, plus malformed-input checks.

The first two fragments were extracted by physical bit masking from the
original member. Their numeric trees independently match authenticated depot
headers b34d0f30... (HeroesData) and9bdcdbb1... (DragonShire). They contain no
player data or text. The current fragment is observed member evidence only.
"""
from dataclasses import replace
import hashlib
import unittest

from battlelobby_arcade_sections import (ArcadeSection, LocalizationKey, SectionHeader,
    LayerError, from_depot_subtree, read_section, summary, verify_binding, write_section)
from battlelobby_attribute_layer import _Reader, _Writer
from depot_s2mh_wire import decode_verified_header

OLD_DATA = bytes.fromhex('200103df000000000200000003e3000000030200000003e50000000402000012000760000f21001f02003e04007c0600f90302f40003e900076a')
OLD_MAP = bytes.fromhex('0c00000a0000000000000000000e00000043000000000010000000040000000900000b0001040003010007010011000012000013000014000105')
CURRENT_MAP = bytes.fromhex('1400000a00000040000000000000000000410000000000000000000100000000000000000041000000000000000000010000000100000b')


def key(index):
    return LocalizationKey(None, 0, index)


def section(titles, offsets, types, items):
    return ArcadeSection(tuple(SectionHeader(key(t), o, f, key(0))
                               for t, o, f in zip(titles, offsets, types)),
                         tuple(key(i) for i in items))


OLD_DATA_TREE = section([991, 995, 997], [0, 3, 4], [2, 2, 2],
                        [992, 993, 994, 996, 998, 999, 1000, 1001, 1002])
OLD_MAP_TREE = section([10, 14, 16], [0, 3, 4], [0, 2, 0],
                       [11, 12, 13, 15, 17, 18, 19, 20, 21])
CURRENT_MAP_TREE = section([10, 0, 0, 0, 0], [0, 1, 1, 1, 1], [2, 2, 0, 2, 0], [11])


class ArcadeSectionTests(unittest.TestCase):
    def test_old_data_all_named_fields_and_physical_bits(self):
        result = verify_binding(OLD_DATA, 5, OLD_DATA_TREE)
        self.assertEqual((result['section_header_count'], result['localized_item_count'], result['section_bits']), (3, 9, 458))
        self.assertTrue(result['full_member_reencoding_exact'])

    def test_old_map_different_alignment_same_real_structure(self):
        result = verify_binding(OLD_MAP, 2, OLD_MAP_TREE)
        self.assertEqual((result['end_bit'], result['section_bits']), (460, 458))

    def test_current_observed_five_headers(self):
        result = verify_binding(CURRENT_MAP, 2, CURRENT_MAP_TREE)
        self.assertEqual((result['section_header_count'], result['localized_item_count'], result['section_bits']), (5, 1, 434))

    def test_zero_header_and_item_counts(self):
        self.assertEqual(verify_binding(bytes(2), 5, ArcadeSection((), ()))['section_bits'], 11)

    def test_title_corruption_is_not_a_compatible_binding(self):
        wrong = replace(OLD_MAP_TREE, headers=(replace(OLD_MAP_TREE.headers[0], title=key(9)),) + OLD_MAP_TREE.headers[1:])
        with self.assertRaisesRegex(LayerError, 'differ'):
            verify_binding(OLD_MAP, 2, wrong)

    def test_truncated_original_fragment_refused(self):
        with self.assertRaises(LayerError):
            verify_binding(OLD_MAP[:-1], 2, OLD_MAP_TREE)

    def test_invalid_offsets_refused(self):
        invalid = replace(OLD_MAP_TREE, headers=(replace(OLD_MAP_TREE.headers[0], start_offset=1),) + OLD_MAP_TREE.headers[1:])
        with self.assertRaisesRegex(LayerError, 'offset'):
            write_section(_Writer().bits, invalid)

    def test_unsupported_list_type_refused(self):
        invalid = replace(OLD_MAP_TREE, headers=(replace(OLD_MAP_TREE.headers[0], list_type=3),) + OLD_MAP_TREE.headers[1:])
        with self.assertRaisesRegex(LayerError, 'list type'):
            write_section(_Writer().bits, invalid)

    def test_capacity_and_scalar_bounds_refused(self):
        invalid = [replace(OLD_MAP_TREE, headers=OLD_MAP_TREE.headers * 6),
                   replace(OLD_MAP_TREE, items=tuple(key(0) for _ in range(128))),
                   replace(OLD_MAP_TREE, items=(LocalizationKey(None, 64, 0),)),
                   replace(OLD_MAP_TREE, items=(LocalizationKey(None, 0, 65536),)),
                   replace(OLD_MAP_TREE, items=(LocalizationKey(None, 0, True),))]
        for value in invalid:
            with self.subTest(value=type(value).__name__), self.assertRaises(LayerError):
                write_section(_Writer().bits, value)

    def test_named_depot_shape_is_exact_and_private_summary_is_hashes(self):
        data = {0: [{0: {0: None, 1: 0, 2: 10}, 1: 0, 2: 2,
                     3: {0: None, 1: 0, 2: 0}}], 1: [{0: None, 1: 0, 2: 11}]}
        expected = section([10], [0], [2], [11])
        self.assertEqual(from_depot_subtree(data), expected)
        self.assertEqual(summary(expected)['section_header_count'], 1)
        with self.assertRaises(LayerError):
            from_depot_subtree({**data, 2: 'unrecognized'})

    def test_colored_key_is_separately_labelled_synthetic_roundtrip(self):
        synthetic = replace(OLD_MAP_TREE, items=(LocalizationKey(0x12345678, 0, 11),) * 9)
        writer = _Writer()
        write_section(writer.bits, synthetic)
        decoded = read_section(_Reader(bytes(writer.raw)).bits)
        self.assertEqual(decoded, synthetic)
        self.assertFalse(summary(decoded)['all_localization_colors_absent'])

    def test_verified_wire_digest_and_trailing_input(self):
        # Minimal wire: outer struct{0: struct{},1: uint8(0)}. Synthetic only.
        raw = bytes.fromhex('0504000500020600')
        self.assertEqual(decode_verified_header(raw, hashlib.sha256(raw).hexdigest()), {0: {}, 1: 0})
        with self.assertRaisesRegex(ValueError, 'digest'):
            decode_verified_header(raw, '0' * 64)
        tail = raw + b'X'
        with self.assertRaisesRegex(ValueError, 'Trailing'):
            decode_verified_header(tail, hashlib.sha256(tail).hexdigest())


if __name__ == '__main__':
    unittest.main()
