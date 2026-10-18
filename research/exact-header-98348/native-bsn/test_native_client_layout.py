from types import SimpleNamespace
import unittest
from native_client_layout import NativeDecoder
from battlelobby_attribute_layer import _Writer

def integer(width):return {'kind':'INT','bounds':{'bits':width,'min':0,'max':(1<<width)-1}}
def fixture(prefix,network,permissions=0):
    records=[{'kind':'STRUCT','field_names':['network','voice','profile','permissions'],'field_types':[1,2,3,5]},integer(8),integer(64),
        {'kind':'STRUCT','field_names':['label','id'],'field_types':[4,2]},integer(32),
        {'kind':'ARRAY','bounds':{'bits':31,'min':0,'max':2147483647},'element_type':3}]
    w=_Writer();w.bits(0,prefix);w.bits(network,8);w.bits(0x0123456789abcdef,64);w.bits(0x12345678,32);w.bits(0xabcdef0123456789,64);w.bits(permissions,31)
    for _ in range(permissions):w.bits(0,32);w.bits(0,64)
    w.bits(0,1)
    return SimpleNamespace(records=records),bytes(w.raw)

class NativeClientTests(unittest.TestCase):
    def test_entire_199_bit_segment_at_all_bit_alignments(self):
        for prefix in range(8):
            p,raw=fixture(prefix,73);d=NativeDecoder(p,raw,prefix);d.decode(0)
            self.assertEqual(d.reader.position,prefix+199);self.assertTrue(d.exact_consumed_bits())
            self.assertEqual(d.field('/network').end-d.field('/network').start,8)
    def test_first_network_wire_bit_is_scalar_at_every_alignment(self):
        for prefix in range(8):
            p,raw=fixture(prefix,0);changed=bytearray(raw);changed[prefix//8]|=1<<(prefix%8)
            d=NativeDecoder(p,bytes(changed),prefix);d.decode(0)
            self.assertNotEqual(d.field('/network').value,0);self.assertEqual(d.reader.position,prefix+199);self.assertTrue(d.exact_consumed_bits())
    def test_nonempty_permission_list_consumes_real_child_payload(self):
        p,raw=fixture(3,1,1);d=NativeDecoder(p,raw,3);d.decode(0)
        self.assertEqual(d.field('/permissions','ARRAY').value,1);self.assertEqual(d.reader.position,3+199+96)
        self.assertEqual(d.field('/permissions/0/id').end-d.field('/permissions/0/id').start,64)
    def test_permission_count_budget_rejects_before_allocating(self):
        p,raw=fixture(0,0);w=_Writer();w.bits(0,8+64+32);w.bits(0,64);w.bits(32769,31)
        with self.assertRaises(ValueError):NativeDecoder(p,bytes(w.raw),0).decode(0)
    def test_outside_choice_tag_rejected(self):
        p=SimpleNamespace(records=[{'kind':'CHOICE','bounds':{'bits':2,'min':0,'max':2},'tags':[0,1,2],'field_types':[1,1,1],'field_names':['none','endpoint','stream']},{'kind':'NULL'}])
        with self.assertRaises(ValueError):NativeDecoder(p,b'\x03',0).decode(0)
    def test_truncated_known_width_rejected(self):
        p,raw=fixture(0,0)
        with self.assertRaises(ValueError):NativeDecoder(p,raw[:7],0).decode(0)
    def test_utf8_payload_validated_independently_of_byte_count(self):
        p=SimpleNamespace(records=[{'kind':'STRING','bounds':{'bits':3,'min':0,'max':6}}]);w=_Writer();w.bits(1,5);w.blob(b'\xff')
        with self.assertRaises(UnicodeDecodeError):NativeDecoder(p,bytes(w.raw),0).decode(0)
    def test_reencoding_detects_a_changed_output_bit(self):
        p,raw=fixture(0,1);d=NativeDecoder(p,raw,0);d.decode(0);self.assertTrue(d.exact_consumed_bits());d.writer.raw[0]^=1;self.assertFalse(d.exact_consumed_bits())
    def test_recursive_alias_budget_rejected(self):
        p=SimpleNamespace(records=[{'kind':'USER','element_type':0}])
        with self.assertRaises(ValueError):NativeDecoder(p,b'\0',0).decode(0)
    def test_invalid_start_rejected(self):
        p,raw=fixture(0,1)
        for start in (-1,len(raw)*8+1,True):
            with self.assertRaises(ValueError):NativeDecoder(p,raw,start)

if __name__=='__main__':unittest.main()
