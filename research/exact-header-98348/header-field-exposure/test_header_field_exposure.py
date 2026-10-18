"""Synthetic naming/tag/identity guards and frozen-schema comparison only."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace as N
import unittest
import review_header_field_exposure as audit

def node(tag,value):return N(tag=tag,value=value)

class HeaderExposureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records={r['id']:r for r in json.loads(audit.read(audit.HERE/'native-header-mapinfo-selected-graph.json'))['records']}
    def test_all191_records_and_ordered32_fields_exact(self):
        raw=audit.read(audit.WORK/'native-mapinfo-ready/native_mapinfo_schema_98348.json')
        self.assertEqual(audit.sha(raw),audit.MAPINFO_SCHEMA)
        schema=json.loads(raw)
        self.assertEqual(len(schema['records']),191)
        self.assertTrue(all(r==self.records[r['id']] for r in schema['records']))
        self.assertEqual(schema['ordered_root_fields'],self.records[5852]['field_names'])
    def test_GameHeader_names_only_dummy_BOOL(self):
        result=audit.NamedVersioned(self.records).bind(node(5,[(0,node(6,1))]),4414)
        self.assertEqual(result,{'m_dummy':1})
        self.assertEqual(audit.wire_path(self.records,('m_game','m_dummy'))[0],'root/1/0')
    def test_equal_number_with_wrong_wire_tag_is_not_BOOL(self):
        with self.assertRaises(ValueError):audit.NamedVersioned(self.records).bind(node(5,[(0,node(9,1))]),4449)
    def test_noncanonical_BOOL_rejected(self):
        with self.assertRaises(ValueError):audit.NamedVersioned(self.records).bind(node(5,[(0,node(6,2))]),4449)
    def test_missing_duplicate_or_unknown_struct_fields_rejected(self):
        for value in ([],[(0,node(6,0)),(0,node(6,0))],[(1,node(6,0))]):
            with self.subTest(length=len(value)):
                with self.assertRaises(ValueError):audit.NamedVersioned(self.records).bind(node(5,value),4449)
    def test_scalar_native_range_and_enum_tags_enforced(self):
        records={1:{'kind':'ENUM','bounds':{'min':0,'max':3},'tags':[0,2]}}
        self.assertEqual(audit.NamedVersioned(records).bind(node(9,2),1),2)
        for value in (-1,1,4):
            with self.assertRaises(ValueError):audit.NamedVersioned(records).bind(node(9,value),1)
    def test_array_budget_before_child_projection(self):
        records={1:{'kind':'ARRAY','element_type':2,'bounds':{'min':0,'max':2}},2:{'kind':'BOOL'}}
        with self.assertRaises(ValueError):audit.NamedVersioned(records).bind(node(0,[node(6,0)]*3),1)
    def test_depth_and_total_node_budgets(self):
        records={i:{'kind':'USER','element_type':i+1} for i in range(70)}
        records[70]={'kind':'BOOL'}
        with self.assertRaises(ValueError):audit.NamedVersioned(records).bind(node(6,0),0)
        value=audit.NamedVersioned({1:{'kind':'BOOL'}});value.nodes=200000
        with self.assertRaises(ValueError):value.bind(node(6,0),1)
    def test_optionals_keep_absent_distinct_from_present_zero(self):
        records={1:{'kind':'OPTIONAL','element_type':2},2:{'kind':'BOOL'}}
        decoder=audit.NamedVersioned(records)
        self.assertIsNone(decoder.bind(node(4,None),1))
        self.assertEqual(decoder.bind(node(4,node(6,0)),1),0)
    def test_localized_index_difference_needs_explicit_handle_map(self):
        header={'m_colorHint':None,'m_fileIndex':0,'m_id':37}
        metadata=header|{'m_fileIndex':4};before=copy.deepcopy(metadata)
        self.assertEqual(audit.equivalent_localized(header,metadata,{}),(False,1))
        self.assertEqual(audit.equivalent_localized(header,metadata,{4:0}),(True,1))
        self.assertEqual(metadata,before)
        self.assertFalse(audit.equivalent_localized(header,metadata|{'m_id':38},{4:0})[0])
    def test_all12_locales_required_for_unique_column(self):
        global_files={i:[f'{i}:{j}'.encode() for j in range(6)] for i in range(12)}
        local=[{'m_locale':i,'m_stringFileTable':[global_files[i][3]]} for i in range(12)]
        self.assertEqual(audit.locale_map(local,global_files),{3:0})
        wrong=copy.deepcopy(local);wrong[0]['m_stringFileTable']=[b'other']
        with self.assertRaises(ValueError):audit.locale_map(wrong,global_files)
        with self.assertRaises(ValueError):audit.locale_map(local[:-1],global_files)
    def test_variant_identity_and_index_required(self):
        header={};info={}
        for _,path,name in audit.DIRECT:
            target=header
            for part in path[:-1]:target=target.setdefault(part,{})
            target[path[-1]]=0;info[name]=0
        header['m_variants']=[dict.fromkeys(audit.VARIANT_FIELDS,0)]
        info['m_variants']=[dict.fromkeys(audit.VARIANT_FIELDS,0)|{'m_mapHandle':0,'m_variantIndex':0}]
        self.assertTrue(audit.compare(header,info,{})[1][0]['nine_common_named_fields_equal'])
        info['m_variants'][0]['m_mapHandle']=1
        with self.assertRaises(ValueError):audit.compare(header,info,{})
        info['m_variants'][0].update(m_mapHandle=0,m_variantIndex=1)
        with self.assertRaises(ValueError):audit.compare(header,info,{})
    def test_native_field_path_does_not_invent_author_or_namespace_mapping(self):
        self.assertEqual(audit.wire_path(self.records,('m_bnet','m_mapNamespace'))[0],'root/0/3')
        with self.assertRaises(ValueError):audit.wire_path(self.records,('m_game','m_authorToonHandle'))
        self.assertNotIn('m_mapNamespace',self.records[5852]['field_names'])
        self.assertNotIn('m_authorToonHandle',self.records[4448]['field_names'])
    def test_all15_explicit_named_links_have_compatible_native_value_types(self):
        links=audit.field_schema_links(self.records)
        self.assertEqual(len(links),15)
        self.assertTrue(all(x['named_value_types_compatible'] for x in links))
        self.assertFalse(audit.compatible_named_types(self.records,4449,946))

if __name__=='__main__':unittest.main()
