import unittest
from io import BytesIO
from unittest.mock import Mock

from mpq_reader import MPQArchive, MPQBlockTableEntry, MPQ_FILE_EXISTS, MPQ_FILE_COMPRESS


class EmptyMemberTests(unittest.TestCase):
    def archive(self, archived=0, logical=0, flags=MPQ_FILE_EXISTS):
        archive = object.__new__(MPQArchive)
        archive.file = BytesIO(b'unchanged')
        archive.header = {'offset': 0}
        archive.block_table = [MPQBlockTableEntry(0, archived, logical, flags)]
        archive.get_hash_table_entry = Mock(return_value=Mock(block_table_index=0))
        return archive

    def test_existing_empty_member_is_bytes(self):
        self.assertEqual(self.archive().read_file('empty'), b'')

    def test_existing_empty_compressed_member_is_bytes(self):
        self.assertEqual(self.archive(flags=MPQ_FILE_EXISTS | MPQ_FILE_COMPRESS).read_file('empty'), b'')

    def test_missing_member_is_still_none(self):
        archive = self.archive()
        archive.get_hash_table_entry.return_value = None
        self.assertIsNone(archive.read_file('missing'))

    def test_unallocated_member_is_still_none(self):
        self.assertIsNone(self.archive(flags=0).read_file('deleted'))

    def test_nonempty_member_without_storage_is_rejected(self):
        with self.assertRaises(ValueError):
            self.archive(logical=4).read_file('truncated')

    def test_empty_read_does_not_seek_or_consume(self):
        archive = self.archive()
        archive.file.seek(3)
        self.assertEqual(archive.read_file('empty', force_decompress=True), b'')
        self.assertEqual(archive.file.tell(), 3)


if __name__ == '__main__':
    unittest.main()
