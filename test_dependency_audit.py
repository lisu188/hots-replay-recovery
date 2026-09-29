import copy
import unittest

from dependency_audit import battlelobby_cache_paths, cache_handle, compare


class CacheTests(unittest.TestCase):
    def test_decodes_observed_handle(self):
        digest = 'e0a58745837b3b5351015c933560dbffb178d747009d2d57b4153ef425cf7250'
        value = cache_handle(b's2ma\0\0EU' + bytes.fromhex(digest))
        self.assertEqual(value['relative_path'], f'e0/a5/{digest}.s2ma')
        self.assertEqual(value['region'], 'EU')

    def test_rejects_invalid_length_and_type(self):
        for raw in (b'', bytes(39), bytes(41), 'x' * 40):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                cache_handle(raw)

    def test_rejects_unsafe_extensions_and_regions(self):
        for raw in (b'../x\0\0EU', b's2ma../x', b's2ma\0\0\xff\xff'):
            with self.subTest(raw=raw), self.assertRaises((ValueError, UnicodeError)):
                cache_handle(raw + bytes(32))

    def test_extracts_only_cache_paths_without_private_prefix(self):
        digest = 'ab' * 32
        raw = ('C:\\Users\\private\\Cache\\ab\\ab\\' + digest + '.s2ma').encode()
        self.assertEqual(battlelobby_cache_paths(raw), [f'ab/ab/{digest}.s2ma'])
        self.assertNotIn('private', str(battlelobby_cache_paths(raw)))

    def test_rejects_mismatched_cache_subdirectory(self):
        with self.assertRaises(ValueError):
            battlelobby_cache_paths(b'Cache\\00\\ab\\' + b'ab' * 32 + b'.s2ma')

    def test_accepts_forward_slashes_and_uppercase(self):
        self.assertEqual(battlelobby_cache_paths(b'CACHE/AB/AB/' + b'AB' * 32 + b'.S2MA'),
                         ['ab/ab/' + 'ab' * 32 + '.s2ma'])

    def test_unrecognized_binary_data_is_not_interpreted_as_paths(self):
        self.assertEqual(battlelobby_cache_paths(bytes(100)), [])


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.source = {'cache_handles': [cache_handle(b's2ma\0\0EU' + bytes(32))],
                       'map_title': 'Dragon Shire', 'elapsed_game_loops': 19732,
                       'map_sync_checksum': 1, 'mod_sync_checksum': 2,
                       'opaque_members': {}, 'command_count': 2,
                       'command_projection_sha256': '1' * 64,
                       'tracker_bytes': 4, 'tracker_sha256': '2' * 64}

    def test_equal_bytes_never_claim_playback(self):
        report = compare(self.source, copy.deepcopy(self.source))
        self.assertTrue(all(report['checks'].values()))
        self.assertFalse(report['client_playback_validated'])
        self.assertFalse(report['simulation_compatibility_validated'])

    def test_detects_command_mutation(self):
        candidate = copy.deepcopy(self.source)
        candidate['command_projection_sha256'] = '3' * 64
        self.assertFalse(compare(self.source, candidate)['checks']['same_command_projection'])

    def test_detects_lost_commands(self):
        candidate = copy.deepcopy(self.source)
        candidate['command_count'] = 1
        self.assertFalse(compare(self.source, candidate)['checks']['same_command_projection'])

    def test_different_reference_map_is_not_a_compatibility_failure(self):
        reference = copy.deepcopy(self.source)
        reference['map_title'] = 'Braxis Holdout'
        reference['cache_handles'].append(cache_handle(b's2ma\0\0EU' + bytes([1]) * 32))
        report = compare(self.source, self.source, reference)
        self.assertFalse(report['reference_comparison']['same_map'])
        self.assertEqual(len(report['reference_comparison']['shared_cache_paths']), 1)
        self.assertEqual(len(report['reference_comparison']['reference_only_cache_paths']), 1)
        self.assertTrue(all(report['checks'].values()))

    def test_preserves_dependency_order_in_comparison(self):
        candidate = copy.deepcopy(self.source)
        candidate['cache_handles'].append(cache_handle(b's2ma\0\0EU' + bytes([1]) * 32))
        source = copy.deepcopy(candidate)
        candidate['cache_handles'].reverse()
        self.assertFalse(compare(source, candidate)['checks']['same_cache_handles_in_order'])


if __name__ == '__main__':
    unittest.main()
