import copy
import json
import unittest
from pathlib import Path

from dependency_audit import cache_handle
from encoders import BitPackedEncoder
from mod_data_audit import FORMAT, PREFIX_TYPES, compare, dependency_prefix, observe, validate_profile


def fixture(count=2):
    handles = [b's2ma\0\0EU' + bytes([index + 1]) * 32 for index in range(count)]
    paths = [b'C:\\Private\\Cache\\' + cache_handle(raw)['relative_path'].replace('/', '\\').encode() for raw in handles]
    return {'paths': paths, 'handles': handles}


def encoded(value):
    writer = BitPackedEncoder(PREFIX_TYPES)
    writer.instance(4, value)
    return writer.getvalue()


def profile():
    prefix = dependency_prefix(encoded(fixture()) + b'opaque-tail')
    return {'format': FORMAT, 'file_sha256': 'a' * 64, 'schema_sha256': 'c' * 64,
            'version': dict(m_flags=1, m_major=2, m_minor=57, m_revision=0, m_build=98285, m_baseBuild=98285),
            'data_build': 98285, 'root_key': 'b' * 32, 'replay_compatibility_hash': '0' * 32,
            'map_title': 'Dragon Shire', 'map_size': [248, 208],
            'map_file_sync_checksum': 123, 'mod_file_sync_checksum': 456,
            'full_observed_payload_roundtrip': True, 'dependencies': prefix,
            'known_experiment_name': False}


class PrefixTests(unittest.TestCase):
    def test_roundtrip_and_opaque_boundary(self):
        raw = encoded(fixture())
        result = dependency_prefix(raw + b'opaque-tail')
        self.assertEqual(result['prefix_bytes'], len(raw))
        self.assertEqual(result['opaque_tail_bytes'], 11)
        self.assertTrue(result['prefix_roundtrip'])
        self.assertFalse(result['full_battlelobby_schema_verified'])

    def test_export_omits_absolute_paths(self):
        self.assertNotIn('Private', json.dumps(dependency_prefix(encoded(fixture()))))
        self.assertNotIn('C:', json.dumps(dependency_prefix(encoded(fixture()))))

    def test_every_truncated_prefix_is_rejected(self):
        raw = encoded(fixture())
        for size in range(len(raw)):
            with self.subTest(size=size), self.assertRaises(Exception):
                dependency_prefix(raw[:size])

    def test_mismatched_counts_are_rejected(self):
        value = fixture()
        value['paths'].pop()
        with self.assertRaises(ValueError):
            dependency_prefix(encoded(value))

    def test_reordered_handles_are_rejected(self):
        value = fixture()
        value['handles'].reverse()
        with self.assertRaises(ValueError):
            dependency_prefix(encoded(value))

    def test_invalid_cache_directory_is_rejected(self):
        value = fixture()
        value['paths'][0] = value['paths'][0].replace(b'Cache\\01\\01', b'Cache\\02\\01')
        with self.assertRaises(ValueError):
            dependency_prefix(encoded(value))

    def test_duplicate_dependencies_are_rejected(self):
        value = fixture()
        value['paths'][1] = value['paths'][0]
        value['handles'][1] = value['handles'][0]
        with self.assertRaises(ValueError):
            dependency_prefix(encoded(value))

    def test_empty_dependencies_are_rejected(self):
        with self.assertRaises(ValueError):
            dependency_prefix(encoded(fixture(0)))

    def test_noncanonical_padding_is_rejected(self):
        value = fixture()
        raw = bytearray(encoded(value))
        offset = 2 + len(value['paths'][0])
        raw[offset + 1] |= 0x80
        with self.assertRaises(ValueError):
            dependency_prefix(bytes(raw))


class ReferenceGuardTests(unittest.TestCase):
    def compare_to(self, reference):
        candidate = profile()
        reference['file_sha256'] = 'd' * 64
        return compare(candidate, reference)

    def test_matching_identity_is_not_a_validated_transplant(self):
        result = self.compare_to(profile())
        self.assertTrue(result['eligible_for_same_map_investigation'])
        self.assertFalse(result['checksum_transplant_validated'])
        self.assertFalse(result['simulation_compatibility_validated'])
        self.assertFalse(result['client_playback_validated'])

    def test_braxis_is_rejected_even_at_identical_build(self):
        reference = profile()
        reference['map_title'] = 'Braxis Holdout'
        result = self.compare_to(reference)
        self.assertFalse(result['eligible_for_same_map_investigation'])
        self.assertIn('same_map_title', result['blocking_reasons'])

    def test_old_dragon_shire_is_rejected(self):
        reference = profile()
        reference['version']['m_build'] = 93054
        reference['version']['m_baseBuild'] = 93054
        reference['data_build'] = 93054
        result = self.compare_to(reference)
        self.assertFalse(result['eligible_for_same_map_investigation'])
        self.assertIn('same_version', result['blocking_reasons'])

    def test_equal_numeric_build_with_wrong_root_is_rejected(self):
        reference = profile()
        reference['root_key'] = 'e' * 32
        self.assertIn('same_root_key', self.compare_to(reference)['blocking_reasons'])

    def test_experiment_is_not_a_donor(self):
        reference = profile()
        reference['known_experiment_name'] = True
        self.assertIn('not_known_experiment', self.compare_to(reference)['blocking_reasons'])

    def test_same_file_is_not_independent(self):
        self.assertIn('independent_file', compare(profile(), profile())['blocking_reasons'])

    def test_shared_prefix_is_not_mistaken_for_full_dependency_match(self):
        reference = profile()
        reference['dependencies'] = dependency_prefix(encoded(fixture(3)))
        result = self.compare_to(reference)
        self.assertEqual(result['shared_prefix_count'], 2)
        self.assertFalse(result['ordered_dependencies_equal'])
        self.assertEqual(len(result['reference_only_dependencies']), 1)

    def test_profile_validation_rejects_partial_and_out_of_range_values(self):
        for key, value in [('full_observed_payload_roundtrip', False), ('mod_file_sync_checksum', True),
                           ('map_file_sync_checksum', -1), ('mod_file_sync_checksum', 2**32),
                           ('root_key', 'not-a-hash'), ('map_size', [248]), ('map_title', ''),
                           ('data_build', 0), ('file_sha256', '../private')]:
            reference = profile()
            reference[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate_profile(reference)

    def test_comparison_does_not_mutate_profiles(self):
        candidate, reference = profile(), profile()
        saved = copy.deepcopy([candidate, reference])
        compare(candidate, reference)
        self.assertEqual([candidate, reference], saved)


class RealSourceIntegrationTests(unittest.TestCase):
    def test_old_source_checksums_and_all_three_dependency_lists(self):
        path = Path('work/TEN_GREYMANE_source_41810.StormReplay')
        self.assertTrue(path.is_file(), 'Restore the immutable public source fixture before running this test')
        result = observe(path, 41810, 41810, local=True)
        self.assertEqual(result['mod_file_sync_checksum'], 3522231966)
        self.assertEqual(result['map_file_sync_checksum'], 759447839)
        self.assertEqual(len(result['dependencies']['handles']), 5)
        self.assertEqual(result['dependencies']['prefix_bytes'], 861)
        self.assertEqual(result['streams']['game']['count'], 104257)
        self.assertNotIn('players', result)
        self.assertFalse(result['client_playback_validated'])


if __name__ == '__main__':
    unittest.main()
