import unittest
from zlib import crc32

from native_resource_checksums import mod_checksum, serialized_mod_vector_crc


class ModResourceChecksumTests(unittest.TestCase):
    def test_known_endian_and_count(self):
        self.assertEqual(mod_checksum([]),0xc622f71d)
        self.assertEqual(mod_checksum([0x12345678]),0x80b5f71e)

    def test_inverse_at_all_lengths(self):
        for length in range(256):
            words = [0x01020304+i for i in range(length)]
            wire = bytes([length])+b"".join(w.to_bytes(4,"big") for w in words)
            self.assertEqual(serialized_mod_vector_crc(mod_checksum(words)),crc32(wire))

    def test_reject_invalid_native_values(self):
        for words in ([True],[-1],[2**32],[0]*256,{1,2},{1:0,2:0},b"\x01\x02"):
            with self.assertRaises(ValueError):
                mod_checksum(words)
        for crc in (False,-1,2**32):
            with self.assertRaises(ValueError):
                serialized_mod_vector_crc(crc)


if __name__ == "__main__":
    unittest.main()
