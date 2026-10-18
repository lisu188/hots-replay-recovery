"""Synthetic registry tests; genuine package comparisons are separate reports."""
from contextlib import redirect_stderr
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import compare_package_collection_registries as audit


class SyntheticRegistryTests(unittest.TestCase):
    def test_first_occurrence_dedup_keeps_order(self):
        self.assertEqual(audit.unique_first(['B','A','B','C','A']),['B','A','C'])

    def test_same_set_different_order_is_not_exact(self):
        result=audit.comparison(['B','A','B'],['A','B'])
        self.assertTrue(result['same_set'])
        self.assertFalse(result['deduplicated_first_exact_target_order'])

    def test_duplicate_order_exact_match_is_separate_from_raw_count(self):
        result=audit.comparison(['A','B','A'],['A','B'])
        self.assertEqual((result['raw_items'],result['distinct_items'],result['duplicate_item_count']),(3,2,1))
        self.assertTrue(result['deduplicated_first_exact_target_order'])

    def test_partial_preserved_order_never_becomes_complete(self):
        result=audit.comparison([10,30,10],[10,20,30])
        self.assertTrue(result['deduplicated_relative_overlap_order_equal'])
        self.assertFalse(result['same_set'])
        self.assertFalse(result['deduplicated_first_exact_target_order'])
        self.assertEqual((result['package_only_count'],result['target_only_count']),(0,1))

    def test_field23_names_and_field24_numbers_stay_distinct(self):
        self.assertEqual(audit.registry({23:[b'123'],24:[123]},23),['123'])
        self.assertEqual(audit.registry({23:[b'123'],24:[123]},24),[123])
        self.assertFalse(audit.comparison(['123'],[123])['same_set'])

    def test_absent_is_distinct_from_present_empty_registry(self):
        self.assertIsNone(audit.registry({},23))
        self.assertEqual(audit.registry({23:[]},23),[])

    def test_mixed_and_invalid_named_items_refused(self):
        for values in ([b'Valid',1],[b''],[b'\xff'],['AlreadyDecoded']):
            with self.subTest(values=values),self.assertRaises(audit.CollectionError):
                audit.registry({23:values},23)

    def test_bracketed_historical_name_is_compared_exactly_without_raw_export(self):
        values=audit.registry({23:[b'Valid',b'[Unknown Test Name]']},23)
        result=audit.comparison(values,['Valid'])
        self.assertEqual(result['package_only_count'],1)
        self.assertFalse(result['same_set'])
        self.assertNotIn('[Unknown Test Name]',str(result))

    def test_negative_boolean_and_unsigned_overflow_refused(self):
        for values in ([-1],[True],[2**64],[b'123'],[1.0]):
            with self.subTest(values=values),self.assertRaises(audit.CollectionError):
                audit.registry({24:values},24)

    def test_array_and_item_byte_bounds_refused(self):
        with patch.object(audit,'MAX_ITEMS',2),self.assertRaises(audit.CollectionError):
            audit.registry({24:[1,2,3]},24)
        with self.assertRaises(audit.CollectionError):
            audit.registry({23:[b'A'*257]},23)

    def test_scalar_registry_and_unknown_field_refused(self):
        for root,field in (({23:b'A'},23),({24:1},24),({25:[]},25)):
            with self.subTest(field=field),self.assertRaises(audit.CollectionError):
                audit.registry(root,field)

    def test_missing_parent_or_existing_output_fails_before_header_reads(self):
        with tempfile.TemporaryDirectory(prefix='SYNTHETIC-registry-') as folder:
            base=Path(folder)
            existing=base/'existing.json';existing.write_bytes(b'preserve')
            for output in (existing,base/'missing'/'out.json'):
                argv=['audit']
                for key in ('collection-observation','handle-manifest','original-header-root','cache-scan','cache-root'):
                    argv.extend(['--'+key,'SYNTHETIC-UNREAD'])
                argv.extend(['--output',str(output)])
                with patch('sys.argv',argv),patch.object(audit,'analyze') as analyze,redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                    audit.main()
                analyze.assert_not_called()
            self.assertEqual(existing.read_bytes(),b'preserve')


if __name__=='__main__':
    unittest.main()
