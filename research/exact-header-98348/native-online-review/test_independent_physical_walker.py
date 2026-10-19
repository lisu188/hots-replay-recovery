"""Invented negative controls for the reviewer's independent physical walker."""
from dataclasses import replace
from types import SimpleNamespace as NS
import unittest
from review_native_online import PhysicalWalker

def token(width,value):return NS(width=width,value=value)
def field(path,tid,start,end,kind,value):return NS(path=path,type_id=tid,start_bit=start,end_bit=end,kind=kind,value=value)
def native(tokens,fields=(),end=0,pad=0):return NS(tokens=tuple(tokens),fields=tuple(fields),payload_end_bit=end,padding_bits=pad)

class IndependentPhysicalWalkerTests(unittest.TestCase):
    def test_hand_calculated_cross_byte_chunks_and_zero_width(self):
        raw=bytes.fromhex('d669b435')
        values=((3,6),(10,841),(0,0),(7,52),(12,2869))
        other=native([token(w,v) for w,v in values])
        walker=PhysicalWalker({},raw,other)
        self.assertEqual([walker.number(w) for w,_ in values],[v for _,v in values])
        self.assertEqual(bytes(walker.out),raw)
        self.assertEqual((walker.pos,walker.ti),(32,5))
    def test_blob_alignment_is_reconstructed_from_zero_bits(self):
        raw=b'\x01\xff';other=native([token(1,1),token(None,b'\xff')])
        walker=PhysicalWalker({},raw,other)
        self.assertEqual(walker.number(1),1)
        self.assertEqual(walker.blob(1),b'\xff')
        self.assertEqual(bytes(walker.out),raw)
    def test_nonzero_alignment_is_rejected(self):
        walker=PhysicalWalker({},b'\x03\xff',native([token(1,1),token(None,b'\xff')]))
        walker.number(1)
        with self.assertRaisesRegex(ValueError,'alignment'):walker.blob(1)
    def test_truncation_width_and_wrong_expected_scalar_are_rejected(self):
        for width in (-1,128,True,9):
            with self.subTest(width=width),self.assertRaisesRegex(ValueError,'bounds'):
                PhysicalWalker({},b'\x00',native([token(8,0)])).number(width)
        with self.assertRaisesRegex(ValueError,'scalar token differs'):
            PhysicalWalker({},b'\x00',native([token(8,1)])).number(8)
    def test_small_struct_has_exact_postorder_spans_and_whole_bytes(self):
        records={5917:{'kind':'STRUCT','field_names':['x'],'field_types':[1]},1:{'kind':'INT','bounds':{'bits':8,'min':0,'max':255}}}
        fields=[field('/x',1,0,8,'INT',97),field('',5917,0,8,'STRUCT',{'x':97})]
        result=PhysicalWalker(records,b'a',native([token(8,97)],fields,8)).finish()
        self.assertTrue(result['whole_physical_bits_reencoded_exact'])
        self.assertEqual(result['decoded_fields'],2)
    def test_wrong_field_span_or_value_is_rejected(self):
        records={5917:{'kind':'INT','bounds':{'bits':8,'min':0,'max':255}}}
        for end,value in ((7,97),(8,98)):
            with self.subTest(end=end,value=value),self.assertRaisesRegex(ValueError,'field'):
                PhysicalWalker(records,b'a',native([token(8,97)],[field('',5917,0,end,'INT',value)],8)).finish()
    def test_zero_EOF_padding_and_nonzero_refusal(self):
        records={5917:{'kind':'INT','bounds':{'bits':7,'min':0,'max':127}}}
        fields=[field('',5917,0,7,'INT',0)]
        result=PhysicalWalker(records,b'\x00',native([token(7,0),token(1,0)],fields,7,1)).finish()
        self.assertEqual(result['zero_EOF_padding_bits'],1)
        with self.assertRaisesRegex(ValueError,'EOF padding'):
            PhysicalWalker(records,b'\x80',native([token(7,0),token(1,1)],fields,7,1)).finish()

if __name__=='__main__':unittest.main()
