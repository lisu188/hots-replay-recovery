import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from repack_control import archive_manifest, repack

FIXTURE = Path('checkpoints/44256/TEN_GREYMANE_protocol44256.StormReplay')
FIXTURE_HASH = '71cda528067b3ae4fec30634d37eebf6395fffb6b115ef4a1782e5e24094f167'


class RepackGuardTests(unittest.TestCase):
    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileExistsError):
                repack(Path('missing'), Path(directory), '0' * 64, 44256, 44256)

    def test_malformed_source_digest_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                repack(Path('missing'), Path(directory) / 'out', 'bad', 44256, 44256)

    def test_wrong_digest_never_starts_conversion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'input.StormReplay'
            source.write_bytes(b'not-a-replay')
            with patch('repack_control.inspect_reference') as inspect, self.assertRaises(ValueError):
                repack(source, root / 'out', '0' * 64, 44256, 44256)
            inspect.assert_not_called()
            self.assertFalse((root / 'out').exists())

    def test_invalid_replay_leaves_no_published_control(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'input.StormReplay'
            source.write_bytes(b'not-a-replay')
            with self.assertRaises(ValueError):
                repack(source, root / 'out', hashlib.sha256(source.read_bytes()).hexdigest(), 44256, 44256)
            self.assertFalse((root / 'out').exists())


@unittest.skipUnless(FIXTURE.is_file() and importlib.util.find_spec('mpyq'), 'Restore the public fixture and mpyq runtime')
class RepackIntegrationTests(unittest.TestCase):
    def test_container_only_control_preserves_all_payloads(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'control'
            report = repack(FIXTURE, output, FIXTURE_HASH, 44256, 44256, local=True)
            replay = output / report['artifact']['name']
            self.assertTrue(replay.is_file())
            self.assertEqual(archive_manifest(FIXTURE), archive_manifest(replay))
            self.assertTrue(report['header_bytes_unchanged'])
            self.assertTrue(report['all_archived_member_bytes_unchanged'])
            self.assertTrue(report['artifact']['base64_roundtrip_validated'])
            self.assertEqual(report['member_count'], 14)
            self.assertEqual(report['semantic_changes'], [])
            self.assertFalse(report['client_playback_validated'])
            self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), FIXTURE_HASH)
            with self.assertRaises(FileExistsError):
                repack(FIXTURE, output, FIXTURE_HASH, 44256, 44256, local=True)


if __name__ == '__main__':
    unittest.main()
