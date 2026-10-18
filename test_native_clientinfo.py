from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import native_clientinfo as codec
from battlelobby_attribute_layer import LayerError,_Writer

def fixture(overrides=None,prefix=3):
    """Synthetic values serialized from the authenticated selected type graph."""
    records=codec._schema().records;w=_Writer();w.bits(0,prefix);overrides=overrides or {}
    def emit(i,path=''):
        r=records[i];kind=r['kind'];b=r.get('bounds');value=overrides.get(path)
        if kind=='USER':emit(r['element_type'],path)
        elif kind=='STRUCT':
            for name,child in zip(r['field_names'],r['field_types']):emit(child,path+'/'+name)
        elif kind=='CHOICE':
            tag=r['tags'][0] if value is None else value;w.bits(tag-b['min'],b['bits'])
            index=r['tags'].index(tag);emit(r['field_types'][index],path+'/'+r['field_names'][index])
        elif kind=='OPTIONAL':
            present=bool(value);w.bits(int(present),1)
            if present:emit(r['element_type'],path+'/value')
        elif kind=='ARRAY':
            count=b['min'] if value is None else value;w.bits(count-b['min'],b['bits'])
            for j in range(count):emit(r['element_type'],path+'/'+str(j))
        elif kind in ('ASCII_STRING','STRING','BLOB'):
            blob=(b'x'*b['min']) if value is None else value
            w.bits(len(blob)-b['min'],b['bits']+(2 if kind=='STRING' else 0));w.blob(blob)
        elif kind in ('INT','ENUM'):
            v=(r['tags'][0] if kind=='ENUM' else b['min']) if value is None else value;w.bits(v-b['min'],b['bits'])
        elif kind in ('BOOL','FOURCC','REAL32','REAL64'):w.bits(value or 0,{'BOOL':1,'FOURCC':32,'REAL32':32,'REAL64':64}[kind])
        elif kind=='BIT_ARRAY':
            count=b['min'] if value is None else value;w.bits(count-b['min'],b['bits']);w.bits(0,count)
        elif kind!='NULL':raise AssertionError(kind)
    emit(1768);end=w.position;w.bits(1,1)
    return bytes(w.raw),prefix,end

class NativeClientInfoTests(unittest.TestCase):
    def test_default_full_ClientInfo_and_private_repr(self):
        raw,start,end=fixture();value=codec.decode_clientinfo(raw,start,codec.PROFILE)
        self.assertEqual(value.end_bit,end);self.assertEqual(value.summary()['named_segment_widths'],[8,64,96,31]);self.assertTrue(value.summary()['exact_span_reencoding'])
        self.assertNotIn('m_toon',repr(value));self.assertNotIn('value=',repr(value.fields[0]))
    def test_nonzero_network_first_wire_bit_is_still_u8(self):
        for prefix in range(8):
            raw,start,end=fixture(prefix=prefix);base=codec.decode_clientinfo(raw,start,codec.PROFILE);position=base.field('/m_talkerNetworkId').start_bit
            changed=bytearray(raw);changed[position//8]|=1<<(position%8)
            value=codec.decode_clientinfo(bytes(changed),start,codec.PROFILE)
            self.assertEqual(value.end_bit,end);self.assertNotEqual(value.field('/m_talkerNetworkId').value,0)
    def test_all_TalkerId_branches_are_supported(self):
        for choice in (0,1,2):
            raw,start,end=fixture({'/m_talkerInfo/m_id/m_id':choice});value=codec.decode_clientinfo(raw,start,codec.PROFILE)
            self.assertEqual(value.summary()['TalkerId_choice'],choice);self.assertEqual(value.end_bit,end)
    def test_nonempty_permissions_have_96_bit_records(self):
        raw,start,end=fixture({'/m_relevantPermissions':1});value=codec.decode_clientinfo(raw,start,codec.PROFILE)
        self.assertEqual(value.summary()['permission_count'],1);self.assertEqual(value.summary()['named_segment_widths'],[8,64,96,127]);self.assertEqual(value.end_bit,end)
    def test_optional_rating_clan_build_and_nickname_branches(self):
        overrides={'/m_rating':True,'/m_clanTag':True,'/m_clanTag/value':b'abc','/m_clanLogo':True,'/m_highestLeague':True,
            '/m_clientBuildVersion':True,'/m_clientBuildVersion/value':98348,'/m_accountNickname':True,'/m_accountNickname/value':'ż'.encode()}
        raw,start,end=fixture(overrides);value=codec.decode_clientinfo(raw,start,codec.PROFILE)
        self.assertEqual(value.end_bit,end);self.assertEqual(value.field('/m_clientBuildVersion/value').value,98348)
    def test_permission_budget_before_reading_children(self):
        raw,start,_=fixture({'/m_relevantPermissions':1})
        with patch.object(codec,'MAX_ARRAY',0):
            with self.assertRaisesRegex(LayerError,'array'):codec.decode_clientinfo(raw,start,codec.PROFILE)
    def test_truncation_and_wrong_profile_rejected(self):
        raw,start,_=fixture()
        with self.assertRaises(LayerError):codec.decode_clientinfo(raw[:8],start,codec.PROFILE)
        with self.assertRaises(LayerError):codec.decode_clientinfo(raw,start,'current-tail')
    def test_mutated_schema_refused(self):
        raw,start,_=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'wrong.json';p.write_bytes(b'{}')
            with self.assertRaises(LayerError):codec.decode_clientinfo(raw,start,codec.PROFILE,schema_path=p)
    def test_field_and_wire_token_budgets(self):
        raw,start,_=fixture()
        with patch.object(codec,'MAX_TOKENS',2):
            with self.assertRaises(LayerError):codec.decode_clientinfo(raw,start,codec.PROFILE)
    def test_reencoding_refuses_forged_extent_and_cross_profile(self):
        raw,start,_=fixture();value=codec.decode_clientinfo(raw,start,codec.PROFILE)
        with self.assertRaises(LayerError):codec.encode_clientinfo(replace(value,end_bit=value.end_bit+1))
        with self.assertRaises(LayerError):codec.encode_clientinfo(value,'historical-tail')
    def test_member_and_start_bounds(self):
        for raw,start in ((b'',0),(b'x'*(8*1024*1024+1),0),(b'\0',True),(b'\0',8)):
            with self.assertRaises(LayerError):codec.decode_clientinfo(raw,start,codec.PROFILE)
    def test_forged_blob_token_and_noncurrent_tail_rejected(self):
        raw,start,_=fixture();value=codec.decode_clientinfo(raw,start,codec.PROFILE)
        with self.assertRaises(LayerError):codec.encode_clientinfo(replace(value,tokens=(codec.WireToken(None,b'x'*4097),)))
        with self.assertRaises(LayerError):codec.audit_current_client_infos(raw,object())
    def test_same_width_changed_scalar_token_refused(self):
        raw,start,_=fixture();value=codec.decode_clientinfo(raw,start,codec.PROFILE)
        first=value.tokens[0];changed=codec.WireToken(first.width,first.value^1)
        with self.assertRaisesRegex(LayerError,'changed consumed bits'):
            codec.encode_clientinfo(replace(value,tokens=(changed,)+value.tokens[1:]))
    def test_post_recursion_parent_append_respects_field_cap(self):
        raw,start,_=fixture();value=codec.decode_clientinfo(raw,start,codec.PROFILE)
        cap=len(value.fields)-1
        self.assertGreater(cap,len(value.tokens))
        with patch.object(codec,'MAX_TOKENS',cap):
            with self.assertRaisesRegex(LayerError,'field budget'):
                codec.decode_clientinfo(raw,start,codec.PROFILE)

if __name__=='__main__':unittest.main()
