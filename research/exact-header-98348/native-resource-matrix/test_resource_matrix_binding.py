import dataclasses
from pathlib import Path
import tempfile
import unittest
from resource_matrix_binding import ResourceBlock,ByteReader,ByteWriter,check_static,decode_block,encode_block

class MatrixTests(unittest.TestCase):
    def fixture(self):
        return ResourceBlock((0,18446744073709551615),
            (tuple(range(16)),(0,1,65535,32768,256,255,2,3,4,5,6,7,8,9,10,11)),(b'Hero',b'TEST'))
    def test_hand_specified_big_endian_count_and_cells(self):
        block=self.fixture();raw=encode_block(block)
        self.assertEqual(raw[:2],b'\0\2')
        self.assertEqual(raw[18:22],b'\0\0\0\2')
        self.assertEqual(raw[22:28],b'\0\0\0\1\0\2')
        self.assertEqual(raw[54:62],b'\0\0\0\1\xff\xff\x80\0')
        decoded,bounds=decode_block(raw,0,len(raw));self.assertEqual(decoded,block)
        self.assertEqual(bounds['matrix_start'],18);self.assertEqual(bounds['matrix_end'],86)
    def test_embedded_extent_exact_and_prefix_suffix_preserved(self):
        block=self.fixture();body=encode_block(block);source=b'prefix'+body+b'suffix'
        actual,bounds=decode_block(source,6,6+len(body))
        self.assertEqual(actual,block);self.assertEqual(encode_block(actual),body)
        self.assertEqual(source[:6],b'prefix');self.assertEqual(source[-6:],b'suffix')
    def test_empty_native_arrays(self):
        block=ResourceBlock((),(),());raw=b'\0'*7
        self.assertEqual(encode_block(block),raw);self.assertEqual(decode_block(raw,0,7)[0],block)
    def test_matrix_count_bomb_rejected_before_cell_allocation(self):
        raw=b'\0\0\xff\xff\xff\xff\0'
        with self.assertRaisesRegex(ValueError,'matrix count'):decode_block(raw,0,len(raw))
    def test_truncated_identifier_matrix_and_disabled_payloads(self):
        raw=encode_block(self.fixture())
        for stop in (1,3,20,23,50,len(raw)-1):
            with self.subTest(stop=stop):
                with self.assertRaises(ValueError):decode_block(raw,0,stop)
    def test_wrong_declared_end_refuses_trailing_data(self):
        raw=encode_block(self.fixture())+b'X'
        with self.assertRaisesRegex(ValueError,'end differs'):decode_block(raw,0,len(raw))
    def test_row_width_and_container_types(self):
        for rows in ((tuple(range(15)),),(tuple(range(17)),),[tuple(range(16))],([0]*16,)):
            with self.subTest(shape=str(type(rows))):
                with self.assertRaises(ValueError):encode_block(ResourceBlock((),rows,()))
    def test_unsigned_u16_and_identifier_bounds_no_truncation(self):
        for bad in (-1,65536,True,1.5):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):encode_block(ResourceBlock((),((bad,)+tuple([0]*15),),()))
        for bad in (-1,1<<64,True):
            with self.assertRaises(ValueError):encode_block(ResourceBlock((bad,),(),()))
    def test_disabled_native_bound_and_fourcc_width(self):
        for disabled in ((b'XYZ',),(b'ABCDE',),tuple([b'AAAA']*129)):
            with self.assertRaises(ValueError):encode_block(ResourceBlock((),(),disabled))
        raw=b'\0'*6+bytes((129,))+b'AAAA'*129
        with self.assertRaisesRegex(ValueError,'disabled hero count'):decode_block(raw,0,len(raw))
    def test_reader_type_extent_and_width_bounds(self):
        for args in ((bytearray(),0,0),(b'XX',True,2),(b'XX',0,3),(b'XX',2,1)):
            with self.assertRaises(ValueError):ByteReader(*args)
        with self.assertRaises(ValueError):ByteReader(b'XX',0,2).number(12)
        with self.assertRaises(ValueError):ByteWriter().number(256,8)
    def test_private_values_hidden_from_repr(self):
        block=self.fixture()
        self.assertIs(ResourceBlock.__repr__,object.__repr__)
        self.assertTrue(all(not f.repr for f in dataclasses.fields(ResourceBlock)))
        self.assertNotIn('18446744073709551615',repr(block));self.assertNotIn('Hero',repr(block))
    def test_exact_static_graph_and_tampered_pin_refusal(self):
        report=check_static();self.assertEqual(report['parent']['id'],5842)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'projection.json';path.write_bytes(b'{}\n')
            with self.assertRaisesRegex(ValueError,'pin differs'):check_static(path)

if __name__=='__main__':unittest.main()
