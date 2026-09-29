import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from bind_client_metadata import independent_member
from mpq_reader import MPQ_FILE_EXISTS


class IndependentEmptyMemberTests(unittest.TestCase):
    def archive(self, raw=None, logical=0, stored=0, flags=MPQ_FILE_EXISTS):
        archive = Mock()
        archive.get_hash_table_entry.return_value = SimpleNamespace(block_table_index=0)
        archive.block_table = [SimpleNamespace(size=logical, archived_size=stored, flags=flags)]
        archive.read_file.return_value = raw
        return archive

    def test_normalizes_proven_empty_member(self):
        self.assertEqual(independent_member(self.archive(), 'empty'), b'')

    def test_accepts_already_decoded_empty_member(self):
        self.assertEqual(independent_member(self.archive(raw=b''), 'empty'), b'')

    def test_accepts_compressed_empty_bytes(self):
        self.assertEqual(independent_member(self.archive(raw=b'', stored=4), 'empty'), b'')

    def test_rejects_missing_member(self):
        archive = self.archive()
        archive.get_hash_table_entry.return_value = None
        with self.assertRaises(ValueError):
            independent_member(archive, 'missing')
        archive.read_file.assert_not_called()

    def test_rejects_unallocated_member(self):
        with self.assertRaises(ValueError):
            independent_member(self.archive(flags=0), 'deleted')

    def test_rejects_nonempty_member_returning_none(self):
        with self.assertRaises(ValueError):
            independent_member(self.archive(logical=4), 'truncated')

    def test_does_not_hide_failed_decompression(self):
        with self.assertRaises(ValueError):
            independent_member(self.archive(stored=4), 'corrupt')

    def test_rejects_truncated_payload(self):
        with self.assertRaises(ValueError):
            independent_member(self.archive(raw=b'ab', logical=3, stored=3), 'short')

    def test_accepts_nonempty_payload(self):
        self.assertEqual(independent_member(self.archive(raw=b'abc', logical=3, stored=3), 'valid'), b'abc')


if __name__ == '__main__':
    unittest.main()
