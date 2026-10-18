"""Synthetic insertion invariants only; no real header is reconstructed."""
import unittest
import registry_insertion_control as audit


class SyntheticInsertionTests(unittest.TestCase):
    def test_exact_multiset_keeps_duplicate_multiplicity(self):
        result=audit.control([1,1,2],[1,9,2],[1,1,2,9],set())
        self.assertTrue(result['single_occurrence_insertion_prerequisite_passed'])

    def test_one_existing_extra_XML_duplicate_refuses_all_candidates(self):
        with self.assertRaisesRegex(ValueError,'prerequisite'):
            next(audit.iter_insertions([1,1,2],[1,9,2],[1,1,1,2,9],set()))

    def test_new_ID_multiple_XML_occurrences_refuses_singleton_assumption(self):
        result=audit.control([1,2],[1,9,2],[1,2,9,9],set())
        self.assertTrue(result['exact_multiplicity_control_passed'])
        self.assertFalse(result['single_occurrence_insertion_prerequisite_passed'])
        with self.assertRaises(ValueError):next(audit.iter_insertions([1,2],[1,9,2],[1,2,9,9],set()))

    def test_all_duplicate_gap_insertions_preserve_first_order(self):
        candidates=list(audit.iter_insertions([1,1,2],[1,9,2],[1,1,2,9],set()))
        self.assertEqual(candidates,[(1,9,1,2),(1,1,9,2)])

    def test_consecutive_new_IDs_share_gap_in_observed_order(self):
        candidates=list(audit.iter_insertions([1,1,2],[1,8,9,2],[1,1,2,8,9],set()))
        self.assertEqual(len(candidates),3)
        self.assertTrue(all(list(dict.fromkeys(row))==[1,8,9,2] for row in candidates))

    def test_before_first_and_after_last_gaps_are_bounded(self):
        candidates=list(audit.iter_insertions([1,1],[8,1,9],[1,1,8,9],set()))
        self.assertEqual(candidates,[(8,1,9,1),(8,1,1,9)])

    def test_cap_fails_before_yielding_any_vector(self):
        iterator=audit.iter_insertions([1,1,1,2],[1,9,2],[1,1,1,2,9],set(),cap=2)
        with self.assertRaisesRegex(ValueError,'cap'):next(iterator)

    def test_invalid_numeric_values_and_mutated_existing_order_refused(self):
        for package,current,xml in [([True,2],[1,9,2],[1,2,9]),([1,2],[2,9,1],[1,2,9]),([1,2],[1,9,9,2],[1,2,9])]:
            with self.subTest(package=package),self.assertRaises(ValueError):audit.control(package,current,xml,set())

    def test_excluded_current_ID_or_excessive_cap_refused(self):
        with self.assertRaises(ValueError):audit.control([1,2],[1,9,2],[1,2,9],{9})
        with self.assertRaises(ValueError):next(audit.iter_insertions([1,2],[1,9,2],[1,2,9],set(),cap=1025))


if __name__=='__main__':unittest.main()
