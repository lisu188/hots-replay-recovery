import copy
import importlib.util
import json
import struct
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from migrate_replay import BitVector, SOURCE_SHA256, json_value
from protocol_loader import load_protocol
from reference_replay import checked_archive, inspect_reference, metadata, native, peek, scan

SOURCE = Path('work/TEN_GREYMANE_source_41810.StormReplay')


class LoaderTests(unittest.TestCase):
    def setUp(self):
        load_protocol.cache_clear()

    def tearDown(self):
        load_protocol.cache_clear()

    def test_rejects_invalid_builds(self):
        for build in (0, -1, True, 1.5, '96477', 2**32):
            with self.subTest(build=build), self.assertRaises(ValueError):
                load_protocol(build)

    def test_exact_schema_without_executing_versions_initializer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'versions').mkdir()
            (root / 'versions/__init__.py').write_text("raise RuntimeError('imp-era initializer executed')\n")
            source = '\n'.join(name + ' = []' for name in
                               ('typeinfos', 'game_event_types', 'message_event_types', 'tracker_event_types',
                                'replay_header_typeid', 'replay_initdata_typeid', 'game_details_typeid'))
            (root / 'versions/protocol96477.py').write_text(source)
            package = types.ModuleType('heroprotocol')
            package.__path__ = [str(root)]
            with patch.dict(sys.modules, {'heroprotocol': package}):
                result = load_protocol(96477)
                self.assertEqual(result.recovery_schema_build, 96477)
                self.assertEqual(len(result.recovery_schema_sha256), 64)
                with self.assertRaises(ModuleNotFoundError):
                    load_protocol(98025)

    def test_ambiguous_schema_locations_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'versions').mkdir()
            (root / 'versions/protocol96477.py').write_text('')
            package = types.ModuleType('heroprotocol')
            package.__path__ = [str(root), str(root)]
            with patch.dict(sys.modules, {'heroprotocol': package}), self.assertRaises(ModuleNotFoundError):
                load_protocol(96477)


class MetadataTests(unittest.TestCase):
    def header(self):
        return {'m_version': dict(m_flags=1, m_major=2, m_minor=55, m_revision=17,
                                  m_build=98025, m_baseBuild=98025),
                'm_dataBuildNum': 98025, 'm_ngdpRootKey': {'m_data': bytes(range(16))},
                'm_replayCompatibilityHash': {'m_data': bytes(range(16, 32))},
                'private_players': ['not for publication']}

    def test_metadata_is_allowlisted(self):
        result = metadata(self.header())
        self.assertNotIn('private_players', result)
        self.assertEqual(result['m_version']['m_build'], 98025)

    def test_bad_identifiers_are_rejected(self):
        for key in ('m_ngdpRootKey', 'm_replayCompatibilityHash'):
            for value in (b'', b'a' * 15, b'a' * 17, 'a' * 16):
                header = self.header()
                header[key]['m_data'] = value
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    metadata(header)

    def test_observed_zero_compatibility_hash_is_preserved(self):
        header = self.header()
        header['m_replayCompatibilityHash']['m_data'] = bytes(16)
        self.assertEqual(metadata(header)['m_replayCompatibilityHash']['m_data'], bytes(16))

    def test_zero_root_key_is_still_rejected(self):
        header = self.header()
        header['m_ngdpRootKey']['m_data'] = bytes(16)
        with self.assertRaises(ValueError):
            metadata(header)

    def test_noninteger_version_is_rejected(self):
        header = self.header()
        header['m_version']['m_build'] = True
        with self.assertRaises(ValueError):
            metadata(header)

    def test_native_bitvectors_equal_official_tuples(self):
        self.assertEqual(native({'v': BitVector(15, 896)}), native({'v': (15, 896)}))

    def test_nonexistent_scan_root_is_not_an_empty_result(self):
        with self.assertRaises(NotADirectoryError):
            scan(Path('/not-a-real-hots-folder'), 98025)

    def test_corrupt_files_are_counted_without_hiding_truncation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for i in range(2):
                (root / f'{i}.StormReplay').write_bytes(b'bad')
            result = scan(root, 98025, limit=1)
            self.assertEqual(result['scanned'], 1)
            self.assertEqual(result['errors'], 1)
            self.assertTrue(result['truncated'])

    def test_oversized_tables_are_rejected_before_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.StormReplay'
            raw = struct.pack('<4sIII', b'MPQ\x1b', 0, 16, 0)
            raw += struct.pack('<4sIIHHIIII', b'MPQ\x1a', 32, 32, 0, 1, 32, 32, 2**32 - 1, 1)
            path.write_bytes(raw)
            with self.assertRaises(ValueError):
                checked_archive(path)


@unittest.skipUnless(SOURCE.is_file(), 'Source replay has not been restored')
class ReferenceIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local = importlib.util.find_spec('heroprotocol') is None
        cls.result = inspect_reference(SOURCE, 41810, 41810, local=cls.local)

    def test_all_source_streams_are_binary_exact(self):
        self.assertEqual(self.result['file_sha256'], SOURCE_SHA256)
        self.assertEqual({k: v['count'] for k, v in self.result['streams'].items()},
                         {'game': 104257, 'message': 155, 'tracker': 6614})
        self.assertTrue(all(v['binary_roundtrip'] for v in self.result['streams'].values()))

    def test_profile_does_not_claim_authenticity_or_playback(self):
        self.assertFalse(self.result['proven_authentic_by_signature'])
        self.assertFalse(self.result['client_playback_validated'])
        self.assertFalse(self.result['all_target_event_types_proven'])
        self.assertNotIn('m_playerList', json.dumps(json_value(self.result)))
        self.assertNotIn('m_chatMessage', json.dumps(json_value(self.result)))

    def test_build_mismatch_is_not_a_fallback(self):
        with self.assertRaisesRegex(ValueError, 'expected 98025'):
            inspect_reference(SOURCE, 41810, 98025, local=self.local)

    def test_header_only_discovery_remains_explicit(self):
        result = peek(SOURCE)
        self.assertTrue(result['header_only'])
        self.assertFalse(result['client_playback_validated'])


if __name__ == '__main__':
    unittest.main()
