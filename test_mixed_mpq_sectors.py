import bz2
import io
import struct
import unittest
import zlib
from types import SimpleNamespace

import mpq_mixed_sectors as p


def fixture(sectors, crc=False):
    parts = []
    for raw, compress in sectors:
        parts.append(b'\x02' + zlib.compress(raw) if compress else raw)
    if crc:
        parts.append(b'\0' * (4 * len(sectors)))
    table_size = 4 * (len(parts) + 1)
    offsets = [table_size]
    for raw in parts:
        offsets.append(offsets[-1] + len(raw))
    return struct.pack(f'<{len(offsets)}I', *offsets) + b''.join(parts)


class MixedSectorTests(unittest.TestCase):
    def test_compressed_first_raw_middle_and_partial_last(self):
        sectors = [(b'A' * 512, True), (b'o' * 512, False), (b'Z' * 71, False)]
        raw = fixture(sectors, True)
        self.assertEqual(p.decode_storage(raw, 1095, p.EXISTS | p.COMPRESS | p.SECTOR_CRC, 0), b'A' * 512 + b'o' * 512 + b'Z' * 71)

    def test_exact_sector_multiple_no_extra_sector(self):
        raw = fixture([(b'A' * 512, True), (b'o' * 512, False)])
        self.assertEqual(p.decode_storage(raw, 1024, p.EXISTS | p.COMPRESS, 0), b'A' * 512 + b'o' * 512)

    def test_full_raw_sector_is_not_a_compression_mask(self):
        self.assertEqual(p.unpack_sector(b'o' * 512, 512), b'o' * 512)

    def test_bzip2_single_unit(self):
        self.assertEqual(p.decode_storage(b'\x10' + bz2.compress(b'A' * 512), 512, p.EXISTS | p.COMPRESS | p.SINGLE_UNIT, 0), b'A' * 512)

    def test_raw_single_unit(self):
        self.assertEqual(p.decode_storage(b'raw', 3, p.EXISTS | p.SINGLE_UNIT, 0), b'raw')

    def test_allocated_empty_member(self):
        self.assertEqual(p.decode_storage(b'', 0, p.EXISTS, 0), b'')

    def test_bad_sector_compression_fails_closed(self):
        with self.assertRaises(ValueError):
            p.unpack_sector(b'\x22abc', 512)

    def test_truncated_zlib_rejected(self):
        with self.assertRaises(ValueError):
            p.unpack_sector((b'\x02' + zlib.compress(b'A' * 512))[:-1], 512)

    def test_trailing_compressed_bytes_rejected(self):
        with self.assertRaises(ValueError):
            p.unpack_sector(b'\x02' + zlib.compress(b'A' * 512) + b'junk', 512)

    def test_decompression_output_bound(self):
        with self.assertRaises(ValueError):
            p.unpack_sector(b'\x02' + zlib.compress(b'A' * 513), 512)

    def test_short_decompressed_sector_rejected(self):
        with self.assertRaises(ValueError):
            p.unpack_sector(b'\x02' + zlib.compress(b'A' * 511), 512)

    def test_invalid_start_offset_rejected(self):
        raw = fixture([(b'A' * 512, True)])
        with self.assertRaises(ValueError):
            p.decode_storage(struct.pack('<I', 9) + raw[4:], 512, p.EXISTS | p.COMPRESS, 0)

    def test_out_of_bounds_offset_rejected(self):
        raw = fixture([(b'A' * 512, True)])
        with self.assertRaises(ValueError):
            p.decode_storage(raw[:4] + struct.pack('<I', len(raw) + 1) + raw[8:], 512, p.EXISTS | p.COMPRESS, 0)

    def test_reversed_offsets_rejected(self):
        with self.assertRaises(ValueError):
            p.decode_storage(struct.pack('<4I', 16, 18, 17, 19) + b'abc', 1025, p.EXISTS | p.COMPRESS, 0)

    def test_encrypted_storage_rejected(self):
        with self.assertRaises(ValueError):
            p.decode_storage(b'abc', 3, p.EXISTS | p.ENCRYPTED, 0)

    def test_missing_or_unallocated_member_rejected(self):
        with self.assertRaises(ValueError):
            p.decode_storage(b'', 0, 0, 0)

    def test_invalid_sector_shift_rejected(self):
        with self.assertRaises(ValueError):
            p.decode_storage(b'xx', 512, p.EXISTS | p.COMPRESS, 16)

    def test_storage_for_empty_member_rejected(self):
        with self.assertRaises(ValueError):
            p.decode_storage(b'x', 0, p.EXISTS, 0)

    def test_reader_preserves_position_and_checks_allocation(self):
        raw = fixture([(b'A' * 512, True), (b'o' * 512, False)])
        file = io.BytesIO(b'prefix' + raw)
        file.seek(3)
        block = SimpleNamespace(offset=6, archived_size=len(raw), size=1024, flags=p.EXISTS | p.COMPRESS)
        a = SimpleNamespace(file=file, header={'offset': 0, 'sector_size_shift': 0}, block_table=[block], get_hash_table_entry=lambda name: SimpleNamespace(block_table_index=0))
        self.assertEqual(p.read_member(a, 'member'), b'A' * 512 + b'o' * 512)
        self.assertEqual(file.tell(), 3)
        block.archived_size += 1
        with self.assertRaises(ValueError):
            p.read_member(a, 'member')
        self.assertEqual(file.tell(), 3)


if __name__ == '__main__':
    unittest.main()
