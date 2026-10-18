"""Synthetic bounds/privacy tests; no real dump or process data is read."""
import inspect
import json
import struct
import unittest
from probe_approved_image_fragments import ALLOWED,probe_fragment,read_selected,select_ranges,type_records_valid

def capsule(records=(b'\x05',b'\x05'),dump=b''):
    first=20+4*len(records);body=b''.join(records);offsets=[];at=first
    for record in records:offsets.append(at);at+=len(record)
    return struct.pack('>5I',5,0,len(records),len(body),len(dump))+struct.pack('>'+str(len(records))+'I',*offsets)+body+(b'\0'*(4*len(records)) if dump else b'')+dump

class FragmentTests(unittest.TestCase):
    def test_exact_two_ranges_only_callback_reads(self):
        selected={ALLOWED[0]:100,ALLOWED[1]:2000};calls=[]
        def read(offset,size):calls.append((offset,size));return b'\0'*size
        result=read_selected(read,selected)
        self.assertEqual(calls,[(100,1032),(2000,4)]);self.assertEqual(sum(map(len,result)),1036)
    def test_extra_range_refused_before_any_io(self):
        calls=[];selected={ALLOWED[0]:100,ALLOWED[1]:2000,(0x10,2):4}
        with self.assertRaises(ValueError):read_selected(lambda *args:calls.append(args),selected)
        self.assertEqual(calls,[])
    def test_short_selected_read_refused(self):
        with self.assertRaises(ValueError):read_selected(lambda off,size:b'\0'*(size-1),{ALLOWED[0]:100,ALLOWED[1]:2000})
    def test_descriptor_selection_ignores_unapproved_pointed_ranges(self):
        base=0x10000000;size=0x03000000
        descriptors=[(base+rva,length,100+i*2000) for i,(rva,length) in enumerate(ALLOWED)]
        descriptors += [(0x100,8,5000),(base+0x20,4,6000)]
        selected=select_ranges(descriptors,base,size,8192)
        self.assertEqual(selected,{ALLOWED[0]:100,ALLOWED[1]:2100})
    def test_duplicate_approved_descriptor_rejected(self):
        base=0x10000000;descriptors=[(base+rva,length,100+i*2000) for i,(rva,length) in enumerate(ALLOWED)]
        descriptors.append(descriptors[0])
        with self.assertRaises(ValueError):select_ranges(descriptors,base,0x03000000,8192)
    def test_partial_range_or_file_extent_rejected(self):
        base=0x10000000;descriptors=[(base+rva,length,100+i*2000) for i,(rva,length) in enumerate(ALLOWED)]
        bad=[(descriptors[0][0],1031,descriptors[0][2]),descriptors[1]]
        with self.assertRaises(ValueError):select_ranges(bad,base,0x03000000,8192)
        with self.assertRaises(ValueError):select_ranges(descriptors,base,0x03000000,1000)
    def test_complete_synthetic_nameless_type_grammar(self):
        result=probe_fragment(capsule())
        self.assertEqual(result['complete_type_grammar_candidate_count'],1)
        fact=result['complete_type_grammar_candidates'][0]
        self.assertEqual((fact['version_word'],fact['type_count'],fact['framed_bytes']),(5,2,30))
        self.assertFalse(fact['dump_strings_decoded'])
    def test_fragment_gap_is_never_joined(self):
        raw=capsule();self.assertEqual(probe_fragment(raw)['complete_type_grammar_candidate_count'],1)
        self.assertEqual(probe_fragment(raw[:22])['complete_type_grammar_candidate_count'],0)
        self.assertEqual(probe_fragment(raw[22:])['complete_type_grammar_candidate_count'],0)
    def test_unknown_kind_and_child_type_refusal(self):
        for raw in (capsule((b'\0',b'\5')),capsule((b'\x10'+struct.pack('>I',99),b'\5'))):
            self.assertEqual(probe_fragment(raw)['complete_type_grammar_candidate_count'],0)
    def test_truncated_frame_not_promoted(self):
        result=probe_fragment(capsule()[:-1])
        self.assertEqual(result['complete_type_grammar_candidate_count'],0)
        self.assertEqual(result['header_candidates_requiring_uncaptured_bytes'],1)
    def test_untrusted_counts_and_offset_bounds(self):
        huge=struct.pack('>5I',5,0,20001,20001,0)
        self.assertEqual(probe_fragment(huge)['complete_type_grammar_candidate_count'],0)
        raw=bytearray(capsule());struct.pack_into('>I',raw,20,0)
        self.assertEqual(probe_fragment(bytes(raw))['complete_type_grammar_candidate_count'],0)
    def test_dump_names_are_neither_followed_nor_returned(self):
        secret=b'SYNTHETIC_PRIVATE_NEVER_DECODE\0'
        result=probe_fragment(capsule(dump=secret))
        self.assertEqual(result['complete_type_grammar_candidate_count'],1)
        self.assertNotIn(secret[:-1].decode(),json.dumps(result))
        self.assertNotIn('.decode(',inspect.getsource(probe_fragment))
        self.assertNotIn('.decode(',inspect.getsource(type_records_valid))
    def test_probe_size_and_type_caps(self):
        for raw in (bytearray(),b'X'*1033):
            with self.assertRaises(ValueError):probe_fragment(raw)
        self.assertEqual(probe_fragment(b'\0'*4)['complete_type_grammar_candidate_count'],0)

if __name__=='__main__':unittest.main()
