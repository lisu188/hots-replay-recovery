"""Synthetic privacy/domain/permutation fixtures; not real replay/player data."""
import json
from math import factorial
import unittest

from audit_availability_representation import PrivateCase, compatible_bijections, position_relation, summarize_rows


def row(nonzero_positions,value=b'\x01\x00'):
    return b''.join(value if index in nonzero_positions else b'\0\0' for index in range(16))


def private(flags,presence=None):
    presence=flags if presence is None else presence
    return PrivateCase(tuple(flags),tuple(flags),tuple(presence),tuple(presence),tuple(presence),frozenset())


class RepresentationTests(unittest.TestCase):
    def test_exact_zero_all_set_positive_control(self):
        result,_=summarize_rows([bytes(32),row({0,3},b'\xff\xff')],{0,3},{0,3},{0,3})
        self.assertTrue(result['two_observed_values_are_exact_zero_and_all_16_bits_set'])
        self.assertFalse(result['every_nonzero_cell_value_has_exactly_one_set_bit'])

    def test_one_bit_domain_without_pattern_export(self):
        result,_=summarize_rows([bytes(32),row({0,3})],{0,3},{0,3},{0,3})
        self.assertFalse(result['two_observed_values_are_exact_zero_and_all_16_bits_set'])
        self.assertTrue(result['zero_cell_value_present'])
        self.assertTrue(result['every_nonzero_cell_value_has_exactly_one_set_bit'])
        self.assertEqual(result['nonzero_cell_value_count'],1)

    def test_multi_bit_pattern_is_not_one_bit(self):
        result,_=summarize_rows([bytes(32),row({0},b'\x03\x00')],{0},{0},{0})
        self.assertFalse(result['every_nonzero_cell_value_has_exactly_one_set_bit'])

    def test_all_zero_does_not_claim_two_value_alphabet(self):
        result,_=summarize_rows([bytes(32)],set(),set(),set())
        self.assertFalse(result['two_observed_values_are_exact_zero_and_all_16_bits_set'])
        self.assertFalse(result['every_nonzero_cell_value_has_exactly_one_set_bit'])
        self.assertEqual(result['positions_with_any_nonzero_cell'],0)

    def test_missing_zero_domain_control(self):
        result,_=summarize_rows([b'\xff'*32],set(range(16)),set(range(16)),set(range(16)))
        self.assertFalse(result['zero_cell_value_present'])
        self.assertFalse(result['two_observed_values_are_exact_zero_and_all_16_bits_set'])

    def test_additional_populated_position_is_not_activity(self):
        result,_=summarize_rows([bytes(32),row({0,3})],{0,3,7},{0,3,7},{0,3})
        working=result['same_position_crosschecks']['working_set_coordinates']['any_nonzero']
        participants=result['same_position_crosschecks']['details_participant_working_set_coordinates']['any_nonzero']
        self.assertEqual(working['unflagged_populated_positions'],1)
        self.assertFalse(working['same_position_flags_equal_population'])
        self.assertTrue(participants['same_position_flags_equal_population'])

    def test_all_sixteen_positions_included(self):
        result,_=summarize_rows([bytes(32),row({15})],{15},{0},{15})
        check=result['same_position_crosschecks']['working_set_coordinates']['any_nonzero']
        self.assertEqual(check['positions_checked'],16)
        self.assertEqual(check['flagged_populated_positions'],1)
        self.assertEqual(check['unflagged_unpopulated_positions'],15)
        self.assertFalse(result['coordinates_have_equal_private_population_flags'])

    def test_private_positions_permuted_give_same_public_counts(self):
        first,_=summarize_rows([bytes(32),row({0,3,12})],{0,3,12},{0,3,12},{0,3,12})
        second,_=summarize_rows([bytes(32),row({2,5,15})],{2,5,15},{2,5,15},{2,5,15})
        self.assertEqual(first,second)

    def test_private_pattern_change_with_same_domain_gives_same_report(self):
        first,one=summarize_rows([bytes(32),row({2},b'\x01\x00')],{2},{2},{2})
        second,two=summarize_rows([bytes(32),row({2},b'\x00\x01')],{2},{2},{2})
        self.assertEqual(first,second)
        self.assertNotEqual(one.alphabet,two.alphabet)

    def test_serialization_and_repr_exclude_private_pattern_and_flags(self):
        result,secret=summarize_rows([bytes(32),row({13},b'\x73\x19')],{13},{13},{13})
        encoded=json.dumps(result)
        for forbidden in ('7319','0x7319','b\'','\\u0019','alphabet','[true','[false'):
            self.assertNotIn(forbidden,encoded.lower())
        self.assertNotIn('True',repr(secret))
        self.assertNotIn('7319',repr(secret))
        with self.assertRaises(TypeError):json.dumps(secret)

    def test_malformed_rows_refused(self):
        for rows in ([],[bytes(31)],[bytes(33)],[bytearray(32)],['private']):
            with self.subTest(type=type(rows).__name__):
                with self.assertRaises(ValueError):summarize_rows(rows,set(),set(),set())

    def test_bad_private_position_values_refused(self):
        for values in ({16},{-1},{True},[0]):
            with self.assertRaises(ValueError):summarize_rows([bytes(32)],values,set(),set())


class PermutationTests(unittest.TestCase):
    def test_unconstrained_all_empty_has_factorial16_permutations(self):
        answer=compatible_bijections([private([False]*16)],'active','working',implication=False)
        self.assertEqual(answer['compatible_bijective_permutations'],factorial(16))
        self.assertEqual(answer['private_compatibility_pairs_checked'],256)

    def test_two_indistinguishable_groups_have_factorial_product(self):
        answer=compatible_bijections([private([True]*10+[False]*6)],'active','working',implication=False)
        self.assertEqual(answer['compatible_bijective_permutations'],factorial(10)*factorial(6))

    def test_four_signature_cases_resolve_synthetic_identity(self):
        cases=[private([bool(position&(1<<bit)) for position in range(16)]) for bit in range(4)]
        answer=compatible_bijections(cases,'active','working',implication=False)
        self.assertEqual(answer['compatible_bijective_permutations'],1)
        self.assertTrue(answer['identity_permutation_compatible'])

    def test_cardinality_mismatch_refutes_exact_not_implication(self):
        case=private([True]+[False]*15,[True,True]+[False]*14)
        self.assertEqual(compatible_bijections([case],'active','working',implication=False)['compatible_bijective_permutations'],0)
        self.assertEqual(compatible_bijections([case],'active','working',implication=True)['compatible_bijective_permutations'],2*factorial(15))

    def test_impossible_nonzero_to_empty_population(self):
        case=private([True]+[False]*15,[False]*16)
        self.assertEqual(compatible_bijections([case],'active','working',implication=True)['compatible_bijective_permutations'],0)

    def test_nonidentity_permutation_compatibility_without_pairs_export(self):
        case=private([True]+[False]*15,[False,True]+[False]*14)
        answer=compatible_bijections([case],'active','working',implication=False)
        self.assertEqual(answer['compatible_bijective_permutations'],factorial(15))
        self.assertFalse(answer['identity_permutation_compatible'])
        self.assertEqual(set(answer),{'compatible_bijective_permutations','possible_bijective_permutations',
            'compatible_cell_position_pairs','private_compatibility_pairs_checked','identity_permutation_compatible'})

    def test_invalid_query_or_private_flags_refused(self):
        good=private([False]*16)
        for cases,activity,coordinates,implication in (([],'active','working',False),([good]*16,'active','working',False),
            ([good],'unknown','working',False),([good],'active','unknown',False),([good],'active','working',1),
            ([private([False]*15)],'active','working',False),([private([0]*16)],'active','working',False)):
            with self.assertRaises(ValueError):compatible_bijections(cases,activity,coordinates,implication=implication)

    def test_position_relation_rejects_partial_or_numeric_flags(self):
        with self.assertRaises(ValueError):position_relation((True,),(True,))
        with self.assertRaises(ValueError):position_relation(tuple([1]*16),tuple([True]*16))


if __name__=='__main__':unittest.main()
