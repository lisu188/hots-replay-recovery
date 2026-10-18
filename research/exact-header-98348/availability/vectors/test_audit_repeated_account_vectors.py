"""Synthetic vectors/accounts only; no real replay or private game fixtures."""
import json
from math import factorial
import unittest

from audit_repeated_account_vectors import PrivateControl,assess,column_vectors,iter_active_arrangements,mismatch_count,validate_controls


def control(accounts,vectors):
    size=len(next(iter(vectors.values())))
    columns=tuple(vectors.get(index,bytes(size)) for index in range(16))
    return PrivateControl(accounts,columns)


def synthetic_pair():
    return [control({0:'private-alpha',1:'private-beta',2:'private-gamma'},
        {0:b'\x01\0',1:b'\x02\0',2:b'\x04\0'}),
        control({0:'private-delta',1:'private-alpha',2:'private-epsilon'},
        {0:b'\x08\0',1:b'\x01\0',2:b'\x10\0'})]


class VectorAuditTests(unittest.TestCase):
    def test_direct_repeated_account_and_distinct_account_counts(self):
        result=assess(synthetic_pair());direct=result['direct_working_set_position_alignment']
        self.assertEqual(result['participant_occurrences'],6)
        self.assertEqual(result['distinct_private_accounts'],5)
        self.assertEqual(result['cross_replay_pairs_considered'],9)
        self.assertEqual(direct['same_account_across_replays']['vector_pairs'],1)
        self.assertEqual(direct['same_account_across_replays']['exact_vector_pairs'],1)
        self.assertEqual(direct['different_accounts_across_replays']['vector_pairs'],8)
        self.assertEqual(direct['different_accounts_across_replays']['exact_vector_pairs'],0)

    def test_all_active_arrangements_checked_not_empty_position_permutations(self):
        result=assess(synthetic_pair());presence=result['presence_constraint_aggregate']
        self.assertEqual(presence['distinct_active_arrangements_enumerated'],factorial(3))
        self.assertEqual(presence['never_participant_permutations_not_enumerated'],factorial(13))
        self.assertEqual(presence['all_compatible_position_bijections'],factorial(3)*factorial(13))
        self.assertEqual(sum(row['active_arrangement_count'] for row in result['arrangement_consistency_aggregate']['histogram']),6)

    def test_unique_synthetic_correlation_does_not_export_mapping(self):
        result=assess(synthetic_pair())
        self.assertEqual(result['arrangement_consistency_aggregate']['active_arrangements_attaining_maximum_same_account_exact_pairs'],1)
        for row in result['arrangement_consistency_aggregate']['histogram']:
            self.assertEqual(set(row),{'same_account_exact_vector_pairs','different_account_exact_vector_pairs','active_arrangement_count'})
        self.assertNotIn('selected_mapping',result)

    def test_mismatch_bounds_count_cells_not_bytes_or_bits(self):
        first=control({0:'same'},{0:b'\x01\0\0\0\0\0'})
        second=control({0:'same'},{0:b'\x01\0\x03\x05\x07\x09'})
        repeated=assess([first,second])['direct_working_set_position_alignment']['same_account_across_replays']
        self.assertEqual(repeated['different_vector_pairs'],1)
        self.assertEqual(repeated['differing_pairs_mismatched_registry_rows_min'],2)
        self.assertEqual(repeated['differing_pairs_mismatched_registry_rows_max'],2)
        self.assertEqual(repeated['differing_pairs_total_mismatched_registry_rows'],2)

    def test_no_repeated_accounts_is_explicit_no_consistency_test(self):
        first=control({0:'first'},{0:b'\x01\0'})
        second=control({0:'second'},{0:b'\x02\0'})
        result=assess([first,second])
        self.assertTrue(result['arrangement_consistency_aggregate']['zero_repeated_account_pairs_would_mean_no_consistency_test'])
        self.assertIsNone(result['arrangement_consistency_aggregate']['active_arrangements_with_every_repeated_account_pair_exact'])
        self.assertIsNone(result['direct_working_set_position_alignment']['same_account_across_replays']['differing_pairs_mismatched_registry_rows_min'])

    def test_private_account_renaming_does_not_change_report(self):
        controls=synthetic_pair();mapping={account:('secret-replacement',index) for index,account in enumerate({account for c in controls for account in c.accounts_by_position.values()})}
        renamed=[PrivateControl({slot:mapping[account] for slot,account in c.accounts_by_position.items()},c.columns) for c in controls]
        self.assertEqual(assess(controls),assess(renamed))

    def test_private_position_renaming_does_not_change_report(self):
        controls=synthetic_pair()
        renamed=[PrivateControl({15-slot:account for slot,account in c.accounts_by_position.items()},tuple(reversed(c.columns))) for c in controls]
        self.assertEqual(assess(controls),assess(renamed))

    def test_private_cell_value_bijection_does_not_change_report(self):
        controls=synthetic_pair()
        replaced=[PrivateControl(c.accounts_by_position,tuple(bytes((byte^0x40) if byte else 0 for byte in column) for column in c.columns)) for c in controls]
        self.assertEqual(assess(controls),assess(replaced))

    def test_report_repr_and_serialization_exclude_private_keys_and_vectors(self):
        controls=synthetic_pair();encoded=json.dumps(assess(controls))
        for private_value in ('private-alpha','private-beta','private-gamma','private-delta','private-epsilon','accounts_by_position','columns','\\u0001'):
            self.assertNotIn(private_value,encoded)
            self.assertNotIn(private_value,repr(controls[0]))
        with self.assertRaises(TypeError):json.dumps(controls[0])

    def test_column_construction_keeps_two_byte_cell_boundaries(self):
        first=b''.join(bytes((index+1,0)) for index in range(16))
        second=b''.join(bytes((0,index+1)) for index in range(16))
        columns=column_vectors([first,second])
        self.assertEqual(len(columns),16)
        self.assertEqual(columns[0],b'\x01\0\0\x01')
        self.assertEqual(columns[-1],b'\x10\0\0\x10')

    def test_malformed_rows_and_column_comparison_refused(self):
        for rows in ([],[bytes(31)],[bytes(33)],[bytearray(32)],['private']):
            with self.assertRaises(ValueError):column_vectors(rows)
        with self.assertRaises(ValueError):mismatch_count(b'\0',b'\0')
        with self.assertRaises(ValueError):mismatch_count(bytes(2),bytes(4))

    def test_duplicate_account_within_case_refused(self):
        bad=control({0:'same',1:'same'},{0:b'\x01\0',1:b'\x02\0'})
        with self.assertRaises(ValueError):assess([bad,synthetic_pair()[0]])

    def test_case_bounds_refused(self):
        for controls in ([],synthetic_pair()[:1],[synthetic_pair()[0]]*14):
            with self.assertRaises(ValueError):assess(controls)

    def test_column_size_type_and_active_presence_mismatch_refused(self):
        good=synthetic_pair()[0]
        for columns in ((bytes(2),)*15,(b'\x01',)*16,(bytearray(2),)*16,(bytes(2),)*16,
            tuple(b'\x01\0' if index==0 else bytes(4) for index in range(16))):
            with self.assertRaises(ValueError):validate_controls([PrivateControl({0:'key'},columns),good])

    def test_private_position_bounds_and_bool_refused(self):
        for position in (-1,16,True):
            with self.assertRaises(ValueError):validate_controls([PrivateControl({position:'key'},(b'\x01\0',)*16),synthetic_pair()[0]])

    def test_arrangement_cap_refuses_before_truncation(self):
        groups={(True,True):list(range(8)),(False,False):list(range(8,16))}
        with self.assertRaises(ValueError):next(iter_active_arrangements(groups))
        for cap in (0,4097,True):
            with self.assertRaises(ValueError):next(iter_active_arrangements({(True,True):[0]},cap=cap))


if __name__=='__main__':unittest.main()
