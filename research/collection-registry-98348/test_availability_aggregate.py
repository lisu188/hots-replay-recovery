"""Synthetic aggregate-only cases; no actual player state fixtures."""
import unittest
from audit_collection_availability_aggregates import aggregate


class SyntheticAvailabilityAggregateTests(unittest.TestCase):
    def test_all_zero_is_reported_without_values(self):
        result=aggregate([bytes(32),bytes(32)])
        self.assertEqual((result['rows'],result['zero_rows'],result['distinct_32byte_rows']),(2,2,1))
        self.assertTrue(result['all_rows_identical'])
        self.assertTrue(result['all_bytes_zero'])
        self.assertEqual(result['distinct_two_byte_cell_values'],1)

    def test_mixed_rows_stay_nonconstant_and_aggregate_only(self):
        result=aggregate([bytes(32),b'\x07\x00'+bytes(30)])
        self.assertEqual((result['zero_rows'],result['nonzero_rows'],result['distinct_32byte_rows']),(1,1,2))
        self.assertFalse(result['all_rows_identical'])
        self.assertFalse(result['all_bytes_zero'])
        self.assertEqual((result['nonzero_bytes'],result['distinct_two_byte_cell_values']),(1,2))
        self.assertTrue(all(isinstance(value,(int,bool)) for value in result.values()))

    def test_empty_wrong_size_and_mutable_rows_refused(self):
        for rows in ([],[b'A'*31],[b'A'*33],[bytearray(32)]):
            with self.subTest(rows=rows),self.assertRaises(ValueError):aggregate(rows)


if __name__=='__main__':unittest.main()
