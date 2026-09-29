from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from mpq_reader import MPQArchive
from repair_dragon_dependencies import BUILD, MAP_FIELDS, OUTPUT_NAME, SOURCE_SHA256, cache_suffix, encode_prefix, parse_prefix, read_models, repair, replace_prefix, sha, transform, validate_observation

SOURCE = Path('work/R4.StormReplay')
OBSERVATION = Path('observations/dragon-98285-2026-09-29.json')


def observation():
    return json.loads(OBSERVATION.read_text())


class PrefixTests(unittest.TestCase):
    def setUp(self):
        self.handles = validate_observation(observation())
        self.paths = [b'C:\\ProgramData\\Blizzard Entertainment\\Battle.net\\Cache\\' + cache_suffix(h) for h in self.handles]
        self.prefix = encode_prefix(self.paths, self.handles)

    def test_prefix_roundtrip_and_offset(self):
        paths, handles, end = parse_prefix(self.prefix + b'opaque-tail')
        self.assertEqual((paths, handles, end), (self.paths, self.handles, len(self.prefix)))

    def test_rejects_mismatched_counts(self):
        with self.assertRaises(ValueError):
            encode_prefix(self.paths[:-1], self.handles)

    def test_rejects_empty_prefix(self):
        with self.assertRaises(ValueError):
            parse_prefix(b'\0')

    def test_rejects_truncated_handle(self):
        with self.assertRaises(Exception):
            parse_prefix(self.prefix[:-1])

    def test_rejects_noncanonical_padding(self):
        corrupt = bytearray(self.prefix)
        corrupt[len(self.prefix) - 40 * len(self.handles) - 1] |= 0x80
        with self.assertRaises(ValueError):
            parse_prefix(bytes(corrupt))

    def test_rejects_wrong_path_digest(self):
        paths = self.paths.copy()
        paths[0] = paths[1]
        with self.assertRaises(ValueError):
            encode_prefix(paths, self.handles)

    def test_rejects_unsafe_path(self):
        paths = self.paths.copy()
        paths[0] = b'..\\' + paths[0]
        with self.assertRaises(ValueError):
            encode_prefix(paths, self.handles)

    def test_rejects_unsupported_region(self):
        with self.assertRaises(ValueError):
            cache_suffix(self.handles[0][:6] + b'US' + self.handles[0][8:])

    def test_rejects_mixed_roots(self):
        paths = self.paths.copy()
        paths[0] = b'D:' + paths[0][2:]
        with self.assertRaises(ValueError):
            replace_prefix(encode_prefix(paths, self.handles), self.handles, self.handles)

    def test_rejects_unexpected_original_handles(self):
        with self.assertRaises(ValueError):
            replace_prefix(self.prefix, self.handles[::-1], self.handles)

    def test_replacement_preserves_arbitrary_tail(self):
        tail = bytes(range(256)) * 3
        raw, audit = replace_prefix(self.prefix + tail, self.handles, self.handles[:-1])
        self.assertEqual(raw[parse_prefix(raw)[2]:], tail)
        self.assertEqual(audit['tail_sha256'], sha(tail))


class ObservationTests(unittest.TestCase):
    def test_accepts_known_reference(self):
        self.assertEqual(len(validate_observation(observation())), 6)

    def test_rejects_wrong_provenance(self):
        for key in ('reference_sha256', 'schema_sha256'):
            with self.subTest(key=key):
                value = observation()
                value[key] = '0' * 64
                with self.assertRaises(ValueError):
                    validate_observation(value)

    def test_rejects_wrong_or_noninteger_build(self):
        for value in (98297, True, '98285', 98285.0):
            with self.subTest(value=value):
                item = observation()
                item['build'] = value
                with self.assertRaises(ValueError):
                    validate_observation(item)

    def test_rejects_unverified_markers(self):
        for key in ('full_reference_roundtrip', 'reference_prefix_roundtrip', 'native_checksums_passed'):
            with self.subTest(key=key):
                item = observation()
                item[key] = 1
                with self.assertRaises(ValueError):
                    validate_observation(item)

    def test_rejects_different_map_or_extension(self):
        for key, value in (('map_title', 'Braxis Holdout'), ('has_extension_mod', True), ('map_size', [248, 209])):
            with self.subTest(key=key):
                item = observation()
                item[key] = value
                with self.assertRaises(ValueError):
                    validate_observation(item)

    def test_rejects_changed_checksums(self):
        for key in ('map_checksum', 'mod_checksum'):
            with self.subTest(key=key):
                item = observation()
                item[key] ^= 1
                with self.assertRaises(ValueError):
                    validate_observation(item)

    def test_rejects_invalid_handle_lists(self):
        original = observation()['handles_hex']
        for items in (original[:-1], [original[0]] * 6, ['bad'] + original[1:], [[]] + original[1:]):
            with self.subTest(items=items[:1]):
                item = observation()
                item['handles_hex'] = items
                with self.assertRaises(ValueError):
                    validate_observation(item)

    def test_rejects_changed_target_map_digest(self):
        item = observation()
        item['handles_hex'][-1] = item['handles_hex'][-1][:-1] + '0'
        with self.assertRaises(ValueError):
            validate_observation(item)


class ActualR4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SOURCE.is_file():
            raise RuntimeError('Restore the immutable public R4 fixture before running these tests')
        cls.models = read_models(SOURCE)
        cls.obs = observation()

    def test_only_allowlisted_lobby_and_details_fields_change(self):
        header, initial, details, battlelobby = copy.deepcopy(self.models)
        snapshot = copy.deepcopy((header, initial, details, battlelobby))
        after, after_details, server, changes, audit, modes = transform(header, initial, details, battlelobby, self.obs)
        self.assertEqual((header, initial, details, battlelobby), snapshot)
        old_game = initial['m_syncLobbyState']['m_gameDescription']
        new_game = after['m_syncLobbyState']['m_gameDescription']
        self.assertEqual({key for key in old_game if old_game[key] != new_game[key]}, set(MAP_FIELDS))
        self.assertEqual({key for key in details if details[key] != after_details[key]}, {'m_cacheHandles'})
        restored = copy.deepcopy(after)
        for key in MAP_FIELDS:
            restored['m_syncLobbyState']['m_gameDescription'][key] = old_game[key]
        self.assertEqual(restored, initial)
        self.assertEqual(len(changes), 5)
        self.assertEqual(set(modes), {'m_amm', 'm_competitive', 'm_ammId'})
        self.assertTrue(audit['tail_bytes_preserved'])
        self.assertEqual(server[parse_prefix(server)[2]:], battlelobby[parse_prefix(battlelobby)[2]:])

    def test_rejects_additional_game_mode_difference(self):
        item = copy.deepcopy(self.obs)
        item['game_options']['m_fog'] = 1
        with self.assertRaises(ValueError):
            transform(*self.models, item)

    def test_rejects_source_identity_change(self):
        models = copy.deepcopy(self.models)
        models[0]['m_version']['m_build'] = 98297
        with self.assertRaises(ValueError):
            transform(*models, self.obs)

    def test_rejects_source_dependency_disagreement(self):
        models = copy.deepcopy(self.models)
        models[2]['m_cacheHandles'] = models[2]['m_cacheHandles'][::-1]
        with self.assertRaises(ValueError):
            transform(*models, self.obs)

    def test_rejects_source_checksum_change(self):
        models = copy.deepcopy(self.models)
        models[1]['m_syncLobbyState']['m_gameDescription']['m_modFileSyncChecksum'] ^= 1
        with self.assertRaises(ValueError):
            transform(*models, self.obs)

    def test_native_repair_is_reproducible_and_preserves_events(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = repair(SOURCE, root / 'one', self.obs)
            second = repair(SOURCE, root / 'two', self.obs)
            self.assertEqual((root / 'one' / OUTPUT_NAME).read_bytes(), (root / 'two' / OUTPUT_NAME).read_bytes())
            self.assertEqual(first['artifact']['sha256'], second['artifact']['sha256'])
            self.assertEqual(first['events'], {'game': 104257, 'message': 155, 'tracker': 6614})
            self.assertTrue(first['native_payload_check']['all_members_equal'])
            self.assertFalse(first['client_playback_validated'])
            old, new = MPQArchive(SOURCE), MPQArchive(root / 'one' / OUTPUT_NAME)
            try:
                for kind in ('game', 'message', 'tracker', 'sync', 'resumable', 'smartcam'):
                    name = f'replay.{kind}.events'
                    self.assertEqual(old.read_file(name), new.read_file(name))
            finally:
                old.close()
                new.close()
            self.assertEqual(sha(SOURCE.read_bytes()), SOURCE_SHA256)

    def test_refuses_existing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(FileExistsError):
                repair(SOURCE, Path(temporary), self.obs)

    def test_refuses_wrong_source_without_creating_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'bad.StormReplay'
            source.write_bytes(b'not the source')
            with self.assertRaises(ValueError):
                repair(source, root / 'out', self.obs)
            self.assertFalse((root / 'out').exists())


if __name__ == '__main__':
    unittest.main()
