import ctypes.util
import hashlib
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mpq_reader import MPQArchive
from repair_startup import CONFIG_KEY, INPUT_SHA256, native_replace, parse_build_config, repair, v4_profile

SOURCE = Path('work/TEN_GREYMANE_source_41810.StormReplay')
CONFIG = Path('references/build-98297.config')


class BuildConfigTests(unittest.TestCase):
    def test_pinned_current_metadata(self):
        raw = CONFIG.read_bytes()
        self.assertEqual(hashlib.md5(raw).hexdigest(), CONFIG_KEY)
        value = parse_build_config(raw)
        self.assertEqual(value['build-name'], 'B98297')
        self.assertEqual(value['root'], '4cf56214095f863b31776277c55a8fbf')
        self.assertEqual(value['build-replay-hash'], '417671b923a5ca0bad0f5bec63c2a68e')

    def test_modified_config_rejected(self):
        with self.assertRaises(ValueError):
            parse_build_config(CONFIG.read_bytes() + b' ')

    def test_oversized_config_rejected(self):
        with self.assertRaises(ValueError):
            parse_build_config(b'x' * 262145)

    def check_invalid(self, raw):
        with patch('repair_startup.CONFIG_KEY', hashlib.md5(raw).hexdigest()), self.assertRaises(ValueError):
            parse_build_config(raw)

    def test_duplicate_field_rejected(self):
        self.check_invalid(CONFIG.read_bytes() + b'root = abc\n')

    def test_wrong_build_rejected(self):
        self.check_invalid(CONFIG.read_bytes().replace(b'B98297', b'B98285'))

    def test_wrong_product_rejected(self):
        self.check_invalid(CONFIG.read_bytes().replace(b'build-product = Hero', b'build-product = Test'))

    def test_invalid_root_rejected(self):
        self.check_invalid(CONFIG.read_bytes().replace(b'4cf56214095f863b31776277c55a8fbf', b'NOT-A-ROOT'))


class StartupGuardTests(unittest.TestCase):
    def test_repair_does_not_overwrite_existing_directory(self):
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(FileExistsError):
            repair(Path('missing'), Path('missing'), CONFIG, Path(directory))

    def test_repair_rejects_wrong_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'bad'
            source.write_bytes(b'wrong')
            with self.assertRaises(ValueError):
                repair(source, source, CONFIG, root / 'out')
            self.assertFalse((root / 'out').exists())

    def test_native_never_overwrites_source(self):
        with self.assertRaises(FileExistsError):
            native_replace(SOURCE, SOURCE, b'', {})

    def test_native_never_overwrites_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'output'
            output.write_bytes(b'preserve')
            with self.assertRaises(FileExistsError):
                native_replace(SOURCE, output, b'', {})
            self.assertEqual(output.read_bytes(), b'preserve')

    def test_source_has_extended_tables_and_raw_chunks(self):
        result = v4_profile(SOURCE)
        self.assertTrue(result['het_present'])
        self.assertTrue(result['bet_present'])
        self.assertEqual(result['raw_chunk_size'], 16384)

    def test_invalid_header_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad'
            path.write_bytes(b'not-a-replay')
            with self.assertRaises(ValueError):
                v4_profile(path)

    def test_corrupt_header_checksum_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad'
            raw = bytearray(SOURCE.read_bytes())
            base = struct.unpack_from('<I', raw, 8)[0]
            raw[base + 192] ^= 1
            path.write_bytes(raw)
            with self.assertRaises(ValueError):
                v4_profile(path)

    def test_changed_userdata_length_rejected(self):
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
            native_replace(SOURCE, Path(directory) / 'out', b'', {})

    def test_missing_native_library_has_no_fallback(self):
        archive = MPQArchive(SOURCE)
        header = archive.header['user_data_header']['content']
        archive.close()
        with tempfile.TemporaryDirectory() as directory, patch('ctypes.util.find_library', return_value=None):
            path = Path(directory) / 'out'
            with self.assertRaises(RuntimeError):
                native_replace(SOURCE, path, header, {})
            self.assertFalse(path.exists())


@unittest.skipUnless(ctypes.util.find_library('storm'), 'Native StormLib is required')
class NativeWriterTests(unittest.TestCase):
    def test_replace_preserves_extended_tables_and_unchanged_members(self):
        archive = MPQArchive(SOURCE)
        try:
            header = archive.header['user_data_header']['content']
            names = archive.read_file('(listfile)').decode().splitlines()
            before = {name: archive.read_file(name) for name in names}
        finally:
            archive.close()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'native.StormReplay'
            replacement = bytes(range(52))
            report = native_replace(SOURCE, output, header, {'replay.load.info': replacement})
            self.assertTrue(report['after']['het_present'])
            self.assertTrue(report['after']['bet_present'])
            self.assertEqual(report['after']['raw_chunk_size'], 16384)
            after = MPQArchive(output)
            try:
                for name, raw in before.items():
                    self.assertEqual(after.read_file(name), replacement if name == 'replay.load.info' else raw)
                self.assertEqual(after.header['user_data_header']['content'], header)
            finally:
                after.close()


if __name__ == '__main__':
    unittest.main()
