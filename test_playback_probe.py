import copy
import hashlib
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import playback_probe as probe


def manifest(raw=b'MPQ\x1btest'):
    return {'format': 'hots-playback-manifest-v1', 'declared_build': 98285,
            'candidate_sha256': hashlib.sha256(raw).hexdigest(),
            'dependencies': [{'digest': hashlib.sha256(b'cache').hexdigest(), 'extension': 's2ma'}]}


class ProbeTests(unittest.TestCase):
    def test_manifest_rejects_traversal_and_wrong_types(self):
        for digest in ('../' * 22, 'g' * 64, True, None):
            data = manifest()
            data['dependencies'][0]['digest'] = digest
            with self.subTest(digest=digest), self.assertRaises(ValueError):
                probe.validate_manifest(data)

    def test_manifest_rejects_duplicates_and_invalid_builds(self):
        data = manifest()
        data['dependencies'] *= 2
        with self.assertRaises(ValueError):
            probe.validate_manifest(data)
        for value in (True, -1, 0, 2**32, '98285'):
            data = manifest()
            data['declared_build'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                probe.validate_manifest(data)

    def test_manifest_rejects_unbounded_dependencies(self):
        for value in ([], [{}] * 65, None, {}):
            data = manifest()
            data['dependencies'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                probe.validate_manifest(data)

    def test_replay_hash_and_signature_must_match(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.StormReplay'
            path.write_bytes(b'MPQ\x1btest')
            self.assertEqual(probe.verify_replay(path, manifest()), manifest()['candidate_sha256'])
            path.write_bytes(b'MPQ\x1bedited')
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                probe.verify_replay(path, manifest())
            path.write_bytes(b'not a replay')
            with self.assertRaisesRegex(ValueError, 'signature'):
                probe.verify_replay(path, manifest())

    def test_wrong_extension_is_never_opened(self):
        with self.assertRaises(ValueError):
            probe.verify_replay(Path('program.exe'), manifest())

    def test_hashing_rejects_oversized_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'file'
            path.write_bytes(b'12345')
            with self.assertRaises(ValueError):
                probe.digest_file(path, limit=4)

    def test_cache_reports_missing_and_present_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = manifest()
            self.assertEqual(probe.check_cache(data, [root])[0]['observations'][0]['status'], 'absent')
            digest = data['dependencies'][0]['digest']
            path = root / digest[:2] / digest[2:4] / f'{digest}.s2ma'
            path.parent.mkdir(parents=True)
            path.write_bytes(b'cache')
            item = probe.check_cache(data, [root])[0]['observations'][0]
            self.assertTrue(item['raw_sha256_matches_identifier'])
            self.assertEqual(path.read_bytes(), b'cache')
            path.write_bytes(b'other')
            self.assertFalse(probe.check_cache(data, [root])[0]['observations'][0]['raw_sha256_matches_identifier'])

    def test_unavailable_cache_root_is_not_an_absent_file(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(probe.check_cache(manifest(), [Path(directory) / 'missing'])[0]['observations'][0]['status'], 'cache-root-unavailable')

    def test_snapshot_reads_only_bounded_text_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'log.txt').write_bytes(b'a' * 12)
            (root / 'private.bin').write_bytes(b'not a log')
            with patch.object(probe, 'MAX_LOG_BYTES', 8):
                values = list(probe.log_snapshot([root])['entries'].values())
            self.assertEqual(len(values), 1)
            self.assertEqual(values[0]['tail'], b'a' * 8)
            self.assertTrue(values[0]['tail_truncated'])

    def test_snapshot_explicitly_reports_listing_truncation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index in range(3):
                (root / f'{index}.log').write_text('x')
            with patch.object(probe, 'MAX_LOG_FILES', 2):
                snapshot = probe.log_snapshot([root])
            self.assertEqual(snapshot['scopes'][0]['older_logs_omitted'], 1)
            self.assertFalse(snapshot['scopes'][0]['truncated_listing'])
            self.assertEqual(len(snapshot['entries']), 2)
            with patch.object(probe, 'MAX_LOG_SCAN', 2):
                snapshot = probe.log_snapshot([root])
            self.assertTrue(snapshot['scopes'][0]['truncated_listing'])

    def test_newest_logs_take_priority_over_old_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index in range(3):
                path = root / f'{index}.log'
                path.write_text(str(index))
                os.utime(path, (1000 + index, 1000 + index))
            with patch.object(probe, 'MAX_LOG_FILES', 1):
                result = probe.log_snapshot([root])
            self.assertEqual(next(iter(result['entries'].values()))['tail'], b'2')

    def test_launch_not_requested_never_opens_anything(self):
        with patch.object(probe.os, 'startfile', create=True) as start:
            self.assertEqual(probe.launch_replay(Path('test.StormReplay'), False), 'not-requested')
            start.assert_not_called()

    def test_launch_uses_association_not_shell_command(self):
        with patch.object(probe.sys, 'platform', 'win32'), patch.object(probe.os, 'startfile', create=True) as start:
            self.assertEqual(probe.launch_replay(Path('name with spaces.StormReplay'), True), 'association-open-requested')
            start.assert_called_once_with(str(Path('name with spaces.StormReplay').resolve()))

    def test_launch_rejects_non_windows(self):
        with patch.object(probe.sys, 'platform', 'linux'), self.assertRaises(OSError):
            probe.launch_replay(Path('test.StormReplay'), True)

    def test_changed_logs_are_private_and_never_prove_playback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / 'private-name.log'
            log.write_text('initial\n')
            before = probe.log_snapshot([root])
            log.write_text('initial\nversion mismatch\n')
            after = probe.log_snapshot([root])
            output = root / 'result.zip'
            report = probe.write_bundle(output, manifest(), before, after, [], 'association-open-requested', 'finished', True)
            self.assertFalse(report['client_playback_validated'])
            self.assertFalse(report['simulation_compatibility_validated'])
            self.assertEqual(report['user_reported_result'], 'finished')
            self.assertEqual(report['changed_logs'][0]['text_hints']['version'], 1)
            with zipfile.ZipFile(output) as bundle:
                self.assertEqual(set(bundle.namelist()), {'probe.json', 'logs/changed-001.txt'})
                self.assertNotIn('private-name', bundle.read('probe.json').decode())
            with self.assertRaises(FileExistsError):
                probe.write_bundle(output, manifest(), before, after, [], 'not-requested', 'unknown', True)

    def test_unchanged_logs_are_not_copied(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'unchanged.log').write_text('unchanged')
            snapshot = probe.log_snapshot([root])
            report = probe.write_bundle(root / 'result.zip', manifest(), snapshot, snapshot, [], 'not-requested', 'unknown', True)
            self.assertEqual(report['changed_logs'], [])

    def test_utf16_logs_are_detected_as_text(self):
        self.assertEqual(probe.find_hints('Fatal exception'.encode('utf-16'))['failure'], 1)

    def test_invalid_user_observation_cannot_set_validation(self):
        with self.assertRaises(ValueError):
            probe.write_bundle(Path('unused.zip'), manifest(), {}, {}, [], 'not-requested', 'validated', True)

    def test_nonexistent_log_root_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            result = probe.log_snapshot([Path(directory) / 'missing'])
            self.assertEqual(result['scopes'][0]['status'], 'root-unavailable')
            self.assertEqual(result['entries'], {})


if __name__ == '__main__':
    unittest.main()
