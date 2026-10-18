"""Synthetic tag/path refusal and accounting guards; no real inputs opened."""
from types import SimpleNamespace as N
import unittest
from assess_original_header_mapinfo import named_node,resolve,struct_delta

def n(tag,value):return N(tag=tag,value=value)
class GuardTests(unittest.TestCase):
    def setUp(self):
        self.r={1:{'id':1,'kind':'STRUCT','field_names':['m_permissions'],'tags':[17],'field_types':[2]},2:{'id':2,'kind':'ARRAY','element_type':3},3:{'id':3,'kind':'INT'}}
    def test_explicit_empty_array_kept(self):
        result,tid,path=named_node(self.r,n(5,[(17,n(0,[]))]),1,('m_permissions',))
        self.assertEqual((result.tag,result.value,tid,path),(0,[],2,'root/17'))
    def test_missing_array_is_not_empty(self):
        with self.assertRaises(KeyError):named_node(self.r,n(5,[]),1,('m_permissions',))
    def test_duplicate_tag_refused(self):
        with self.assertRaises(ValueError):named_node(self.r,n(5,[(17,n(0,[])),(17,n(0,[]))]),1,('m_permissions',))
    def test_wrong_parent_wire_tag_refused(self):
        with self.assertRaises(ValueError):named_node(self.r,n(0,[]),1,('m_permissions',))
    def test_unknown_name_is_not_guessed_from_equal_value(self):
        with self.assertRaises(ValueError):named_node(self.r,n(5,[(17,n(0,[]))]),1,('m_other',))
    def test_current_missing_and_old_extra_tags_retained(self):
        self.r[1]['tags']=[24]
        self.assertEqual(struct_delta(self.r,n(5,[(23,n(0,[]))]),1,'root/0'),{'path':'root/0','missing_current_tags':[24],'extra_historical_tags':[23]})
    def test_wrong_wire_tag_preserved_without_value(self):
        self.assertEqual(struct_delta(self.r,n(0,[n(9,123)]),1,'root'),{'path':'root','expected_wire_tag':5,'actual_wire_tag':0})
    def test_alias_cycle_refused(self):
        with self.assertRaises(ValueError):resolve({1:{'kind':'USER','element_type':1}},1)
if __name__=='__main__':unittest.main()
