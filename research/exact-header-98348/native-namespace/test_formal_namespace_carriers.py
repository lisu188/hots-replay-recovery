"""Synthetic namespace grammar tests; no real PE/header/replay is opened."""
import dataclasses
import unittest
from types import SimpleNamespace
from assess_formal_namespace_exposure import Carrier,namespace_carriers

class NamespaceTests(unittest.TestCase):
    def base(self):
        return [{'id':160,'kind':'USER','element_type':145},
                {'id':159,'kind':'STRUCT','members':[{'tag':0,'name':'m_nameSpace','type_id':160}]}]
    def test_named_tag_field_only_not_other_u32_coincidence(self):
        result=namespace_carriers(self.base(),159,{0:12345,1:98765,999:12345})
        self.assertEqual(len(result),1);self.assertEqual(result[0].value,12345)
        self.assertTrue(result[0].through_definition_handle)
    def test_direct_module_namespace_is_distinct_carrier(self):
        graph=self.base()+[{'id':4448,'kind':'STRUCT','members':[{'tag':3,'name':'m_mapNamespace','type_id':160}]}]
        result=namespace_carriers(graph,4448,{3:54321})
        self.assertFalse(result[0].through_definition_handle);self.assertEqual(result[0].path,('m_mapNamespace',))
    def test_unsigned32_native_domain_without_bool(self):
        for value in (-1,1<<32,True,'123'):
            with self.subTest(type=type(value)):
                with self.assertRaises(ValueError):namespace_carriers([],145,value)
        self.assertEqual(namespace_carriers([],145,(1<<32)-1)[0].value,(1<<32)-1)
    def test_optional_absent_and_present(self):
        graph=[{'id':10,'kind':'OPTIONAL','element_type':145}]
        self.assertEqual(namespace_carriers(graph,10,None),[])
        self.assertEqual(len(namespace_carriers(graph,10,7)),1)
    def test_array_counts_and_nested_handle(self):
        graph=self.base()+[{'id':20,'kind':'ARRAY','element_type':159,'bounds':{'min':0,'max':2}}]
        self.assertEqual(len(namespace_carriers(graph,20,[{0:1},{0:2}])),2)
        with self.assertRaises(ValueError):namespace_carriers(graph,20,[{0:1}]*3)
    def test_choice_traverses_only_matching_relevant_branch(self):
        graph=[{'id':30,'kind':'CHOICE','members':[{'tag':2,'name':'branch','type_id':145}]}]
        self.assertEqual(len(namespace_carriers(graph,30,SimpleNamespace(tag=2,value=9))),1)
        self.assertEqual(namespace_carriers(graph,30,SimpleNamespace(tag=1,value=9)),[])
    def test_missing_field_is_not_defaulted(self):
        self.assertEqual(namespace_carriers(self.base(),159,{1:99}),[])
    def test_alias_cycle_and_missing_type_are_bounded_errors(self):
        with self.assertRaises(ValueError):namespace_carriers([{'id':1,'kind':'USER','element_type':1}],1,0)
        with self.assertRaises(ValueError):namespace_carriers([],1,0)
    def test_wrong_wire_container_types_reject(self):
        for value in ([],None,9):
            with self.assertRaises(ValueError):namespace_carriers(self.base(),159,value)
    def test_private_namespace_values_not_in_repr(self):
        value=Carrier(('m_mapNamespace',),0xAABBCCDD,False)
        self.assertIs(Carrier.__repr__,object.__repr__)
        self.assertTrue(all(not f.repr for f in dataclasses.fields(Carrier)))
        self.assertNotIn(str(0xAABBCCDD),repr(value))

if __name__=='__main__':unittest.main()
