"""Invented physical-bit fixtures; only the admission table is patched in tests."""
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import legacy_mapinfo_framing as codec

class Fixture:
    def __init__(self,start=3,records=1,overrides=None):
        self.records=codec.native._schema().records
        self.records[1828]['bounds'].update(bits=7,max=127)
        self.overrides=overrides or {};self.physical=[1]*start;self.spans={};self.bounds=[];self.counts=[]
        for _ in range(records):
            begin=len(self.physical);self.write(5852);end=len(self.physical)
            self.bounds.append((begin,end));self.counts.append(self.spans['/m_requiredPermissions'][0])
        self.physical += [1,0,1,1,0,0,1]*9
        self.raw=self.pack(self.physical)
    @staticmethod
    def pack(bits):
        out=bytearray((len(bits)+7)//8)
        for at,v in enumerate(bits):out[at//8]|=v<<(at%8)
        return bytes(out)
    def bits(self,value,width):
        if not 0<=value<(1<<width):raise ValueError('Synthetic scalar outside width')
        left=width
        while left:
            count=min(left,8-len(self.physical)%8);left-=count;chunk=(value>>left)&((1<<count)-1)
            self.physical.extend((chunk>>bit)&1 for bit in range(count))
    def blob(self,raw):
        self.physical += [0]*(-len(self.physical)%8)
        for b in raw:self.bits(b,8)
    def write(self,i,path=''):
        r=self.records[i];kind=r['kind'];bound=r.get('bounds');start=len(self.physical)
        if kind=='USER':self.write(r['element_type'],path)
        elif kind=='STRUCT':
            for name,child in zip(r['field_names'],r['field_types']):self.write(child,path+'/'+name)
        elif kind=='OPTIONAL':
            present=self.overrides.get(path,0);self.bits(present,1)
            if present:self.write(r['element_type'],path+'/value')
        elif kind=='ARRAY':
            count=self.overrides.get(path,bound['min']);self.bits(count-bound['min'],bound['bits'])
            for j in range(count):self.write(r['element_type'],path+'/'+str(j))
        elif kind in ('ASCII_STRING','STRING','BLOB'):
            value=self.overrides.get(path,b'a'*bound['min']);self.bits(len(value)-bound['min'],bound['bits']+(2 if kind=='STRING'else 0));self.blob(value)
        elif kind in ('INT','ENUM'):
            default=r['tags'][0]if kind=='ENUM'else max(0,bound['min']);self.bits(self.overrides.get(path,default)-bound['min'],bound['bits'])
        elif kind in ('BOOL','FOURCC','REAL32','REAL64'):self.bits(self.overrides.get(path,0),{'BOOL':1,'FOURCC':32,'REAL32':32,'REAL64':64}[kind])
        else:raise AssertionError('Unexpected synthetic fixture kind')
        if kind!='USER':self.spans[path]=(start,len(self.physical))
    def expected(self):
        bits=list(self.physical)
        bits += [0]*(-len(bits)%8)
        for at in reversed(self.counts):bits[at:at+7]=[0]*31
        return self.pack(bits)
    def changed(self,raw,at,width,value):
        bits=[(raw[p//8]>>(p%8))&1 for p in range(len(raw)*8)]
        writer=object.__new__(Fixture);writer.physical=bits[:at];writer.bits(value,width)
        return self.pack(writer.physical+bits[at+width:])

@contextmanager
def admitted(fixture,raw=None,bounds=None):
    raw=fixture.raw if raw is None else raw;bounds=fixture.bounds if bounds is None else bounds
    with patch.object(codec,'_ADMITTED',(('synthetic',codec.sha(raw),tuple(bounds)),)):yield raw

class FramingTests(unittest.TestCase):
    def convert(self,fixture):return codec.convert_mapinfo_framing(fixture.raw,codec.PROFILE)
    def test_only_declared_schema_bounds_differ(self):
        current,legacy=codec._schemas(None)
        self.assertEqual(len(current.records),191)
        for i in current.records:
            a=dict(current.records[i]);b=dict(legacy.records[i])
            if i==1828:
                self.assertEqual((a['bounds']['bits'],b['bounds']['bits']),(31,7));a['bounds']=dict(a['bounds']);a['bounds'].update(bits=7,max=127)
            self.assertEqual(a,b)
    def test_eight_partial_starts_match_independent_physical_splice(self):
        for start in range(8):
            with self.subTest(start=start):
                f=Fixture(start=start)
                with admitted(f):
                    v=self.convert(f);self.assertEqual(v.converted,f.expected());self.assertEqual(codec.inverse_mapinfo_framing(v,codec.PROFILE),f.raw)
                    self.assertEqual(v.summary()['added_bytes'],3)
    def test_multiple_records_shift_and_preserve_all_32_values(self):
        f=Fixture(records=2,overrides={'/m_handle/m_id':123,'/m_addMultiMod':1,'/m_extraDependencies':2})
        with admitted(f):
            v=self.convert(f);self.assertEqual(v.converted,f.expected());s=v.summary()
            self.assertEqual((s['MapInfo_records'],s['named_root_field_comparisons'],s['added_bytes']),(2,64,6))
            self.assertTrue(s['inverse_whole_member_bytes_exact'])
    def test_wrong_explicit_profile_refused(self):
        f=Fixture()
        with admitted(f):
            with self.assertRaises(codec.LayerError):codec.convert_mapinfo_framing(f.raw,'historical-fixed')
    def test_unadmitted_source_refused(self):
        with self.assertRaises(codec.LayerError):self.convert(Fixture())
    def test_mutated_source_refused_by_whole_digest(self):
        f=Fixture()
        with admitted(f):
            bad=bytes([f.raw[0]^1])+f.raw[1:]
            with self.assertRaises(codec.LayerError):codec.convert_mapinfo_framing(bad,codec.PROFILE)
    def test_all_nonempty_legacy_counts_refused(self):
        for count in (1,2,127):
            with self.subTest(count=count):
                f=Fixture(overrides={'/m_requiredPermissions':count})
                with admitted(f):
                    with self.assertRaisesRegex(codec.LayerError,'Nonempty legacy'):self.convert(f)
    def test_wrong_record_end_is_not_tolerated_padding(self):
        f=Fixture();start,end=f.bounds[0]
        for delta in (-1,1):
            with admitted(f,bounds=[(start,end+delta)]):
                with self.assertRaises(codec.LayerError):self.convert(f)
    def test_record_overlap_refused(self):
        f=Fixture(records=2)
        with admitted(f,bounds=[f.bounds[0],(f.bounds[0][0],f.bounds[1][1])]):
            with self.assertRaises(codec.LayerError):self.convert(f)
    def test_outside_member_boundary_refused(self):
        f=Fixture()
        with admitted(f,bounds=[(f.bounds[0][0],len(f.raw)*8+1)]):
            with self.assertRaises(codec.LayerError):self.convert(f)
    def test_bad_schema_pin_refused(self):
        f=Fixture()
        with admitted(f),tempfile.TemporaryDirectory()as d:
            p=Path(d)/'schema.json';p.write_bytes(b'{}')
            with self.assertRaises(codec.LayerError):codec.convert_mapinfo_framing(f.raw,codec.PROFILE,schema_path=p)
    def test_inverse_wrong_profile_refused(self):
        f=Fixture()
        with admitted(f):
            v=self.convert(f)
            with self.assertRaises(codec.LayerError):codec.inverse_mapinfo_framing(v,'current-observed')
    def test_inverse_changed_digest_refused(self):
        f=Fixture()
        with admitted(f):
            v=self.convert(f);bad=replace(v,converted_sha256='0'*64)
            with self.assertRaises(codec.LayerError):codec.inverse_mapinfo_framing(bad,codec.PROFILE)
    def test_inverse_changed_prefix_and_suffix_refused_even_with_new_hash(self):
        f=Fixture(start=5)
        with admitted(f):
            v=self.convert(f)
            for at in (0,len(v.converted)-1):
                raw=bytearray(v.converted);raw[at]^=1;raw=bytes(raw)
                bad=replace(v,converted=raw,converted_sha256=codec.sha(raw))
                with self.assertRaises(codec.LayerError):codec.inverse_mapinfo_framing(bad,codec.PROFILE)
    def test_inverse_nonempty_count_refused_before_any_element_decode(self):
        f=Fixture()
        with admitted(f):
            v=self.convert(f);at=v.edits[0].target_count_start;raw=f.changed(v.converted,at,31,1)
            bad=replace(v,converted=raw,converted_sha256=codec.sha(raw))
            with self.assertRaisesRegex(codec.LayerError,'Nonempty target'):codec.inverse_mapinfo_framing(bad,codec.PROFILE)
    def test_inverse_changed_other_field_refused(self):
        f=Fixture()
        with admitted(f):
            v=self.convert(f);raw=f.changed(v.converted,v.edits[0].target_start,32,1)
            with self.assertRaises(codec.LayerError):codec.inverse_mapinfo_framing(replace(v,converted=raw,converted_sha256=codec.sha(raw)),codec.PROFILE)
    def test_inverse_forged_edits_refused(self):
        f=Fixture()
        with admitted(f):
            v=self.convert(f);edit=replace(v.edits[0],source_count_start=v.edits[0].source_count_start+1)
            with self.assertRaises(codec.LayerError):codec.inverse_mapinfo_framing(replace(v,edits=(edit,)),codec.PROFILE)
    def test_private_synthetic_author_is_not_in_repr_or_summary(self):
        f=Fixture(overrides={'/m_authorRealName':1,'/m_authorRealName/value/m_givenName':b'SecretSyntheticAuthor','/m_authorRealName/value/m_surname':b'SyntheticFamily'})
        with admitted(f):
            v=self.convert(f)
            for text in (repr(v),repr(v.edits),str(v.summary())):
                self.assertNotIn('SecretSyntheticAuthor',text);self.assertNotIn('SyntheticFamily',text)
    def test_invalid_types_empty_and_size_bound_refused(self):
        for raw in (b'',bytearray(b'abc'),None,b'a'*(codec.MAX_MEMBER_BYTES+1)):
            with self.subTest(kind=type(raw).__name__):
                with self.assertRaises(codec.LayerError):codec.convert_mapinfo_framing(raw,codec.PROFILE)
    def assert_target_refused_before_hash(self,target):
        f=Fixture()
        with admitted(f):
            v=self.convert(f);bad=replace(v,converted=target,converted_sha256='0'*64)
            original=codec.sha;seen=[]
            def guarded(raw):
                if raw is target:raise AssertionError('Forbidden target reached hashing')
                seen.append(raw is f.raw);return original(raw)
            with patch.object(codec,'sha',side_effect=guarded):
                with self.assertRaisesRegex(codec.LayerError,'before hashing'):codec.inverse_mapinfo_framing(bad,codec.PROFILE)
            self.assertEqual(seen,[True])
    def test_inverse_wrong_target_type_refused_before_hash(self):
        self.assert_target_refused_before_hash(bytearray(b'invented'))
    def test_inverse_wrong_target_length_refused_before_hash(self):
        self.assert_target_refused_before_hash(b'x')
    def test_inverse_oversized_target_refused_before_hash(self):
        self.assert_target_refused_before_hash(b'x'*(codec.MAX_MEMBER_BYTES+1))
    def test_admission_patch_does_not_persist(self):
        old=codec._ADMITTED;f=Fixture()
        with admitted(f):self.assertNotEqual(codec._ADMITTED,old)
        self.assertEqual(codec._ADMITTED,old)
if __name__=='__main__':unittest.main()
