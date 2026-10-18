import struct
import unittest
from unittest.mock import patch
from parse_bsn_metadata import MetadataError, Protocol, Reader

def capsule(records=None):
    # Four hand-specified types: alias->u32, u32, two-field struct, bool.
    records=records or [b'\x10'+struct.pack('>I',1),b'\x09\x05\xa0'+b'\0'*4+b'\xff'*4,b'\x8e\x01\x01\x00\x01'+struct.pack('>II',0,3),b'\x05']
    count=4;type_start=20+4*count
    offsets=[];body=b''
    for record in records:offsets.append(type_start+len(body));body+=record
    body+=b'\0'*(-len(body)%4)
    dump_start=type_start+len(body)+4*count
    rows=[['FixtureAlias'],['FixtureU32'],['FixtureStruct','first','second'],['FixtureBool']]
    names=b'';pointers=[];name_start=dump_start+4*(1+sum(map(len,rows)))
    for row in rows:
        for name in row:pointers.append(name_start+len(names));names+=name.encode()+b'\0'
    dump_values=[];at=dump_start+4
    for row in rows:dump_values.append(at);at+=4*len(row)
    dump=b'\0'*4+struct.pack('>'+str(len(pointers))+'I',*pointers)+names
    return struct.pack('>5I',7,0,count,len(body),len(dump))+struct.pack('>4I',*offsets)+body+struct.pack('>4I',*dump_values)+dump

class MetadataTests(unittest.TestCase):
    def test_full_named_record_graph_and_unsigned_bounds(self):
        p=Protocol(capsule());self.assertEqual(p.projection('FixtureStruct',2)['members'][0]['type']['element']['bounds']['max'],4294967295)
        self.assertEqual(p.records[2]['field_names'],['first','second']);self.assertEqual(p.name_reference_count,6)
    def test_declared_extent_truncation_and_trailing_data_rejected(self):
        for raw in (capsule()[:-1],capsule()+b'\0'):
            with self.assertRaises(MetadataError):Protocol(raw)
    def test_type_id_out_of_range_rejected(self):
        raw=bytearray(capsule());struct.pack_into('>I',raw,37,99)
        with self.assertRaises(MetadataError):Protocol(bytes(raw))
    def test_non_ordered_offsets_rejected(self):
        raw=bytearray(capsule());raw[24:28]=raw[20:24]
        with self.assertRaises(MetadataError):Protocol(bytes(raw))
    def test_name_middle_and_out_of_bounds_rejected(self):
        good=Protocol(capsule())
        for dest in (good.name_start+1,len(good.raw)):
            raw=bytearray(good.raw);struct.pack_into('>I',raw,good.dump_start+4,dest)
            with self.assertRaises(MetadataError):Protocol(bytes(raw))
    def test_nonzero_final_padding_rejected(self):
        p=Protocol(capsule());raw=bytearray(p.raw);raw[p.dump_offsets-1]=1
        with self.assertRaises(MetadataError):Protocol(bytes(raw))
    def test_unknown_kind_and_invalid_integer_width_rejected(self):
        for at,value in ((36,63),(42,8)):
            raw=bytearray(capsule());raw[at]=value
            with self.assertRaises(MetadataError):Protocol(bytes(raw))
    def test_signed_integer_and_truncated_width(self):
        self.assertEqual(Reader(b'\xff',0,1).integer(0),-1)
        with self.assertRaises(MetadataError):Reader(b'\0',0,1).integer(7)
    def test_dump_record_misalignment_rejected(self):
        p=Protocol(capsule());raw=bytearray(p.raw);struct.pack_into('>I',raw,p.dump_offsets,p.dump_start+5)
        with self.assertRaises(MetadataError):Protocol(bytes(raw))
    def test_oversize_and_zero_typecount_rejected(self):
        for raw in (b'\0'*(2*1024*1024+1),struct.pack('>5I',7,0,0,0,0)):
            with self.assertRaises(MetadataError):Protocol(raw)
    def test_aggregate_fields_budget_rejects_before_dense_materialization(self):
        with patch('parse_bsn_metadata.MAX_FIELDS',5):
            with self.assertRaisesRegex(MetadataError,'Aggregate'):Protocol(capsule())
    def test_zero_dump_offsets_rejected_as_metadata_error(self):
        p=Protocol(capsule());raw=bytearray(p.raw);raw[p.dump_offsets:p.dump_start]=b'\0'*16
        with self.assertRaises(MetadataError):Protocol(bytes(raw))
    def test_unreferenced_final_unterminated_name_rejected(self):
        raw=bytearray(capsule());struct.pack_into('>I',raw,16,struct.unpack_from('>I',raw,16)[0]+1);raw+=b'X'
        with self.assertRaisesRegex(MetadataError,'Unterminated'):Protocol(bytes(raw))

if __name__=='__main__':unittest.main()
