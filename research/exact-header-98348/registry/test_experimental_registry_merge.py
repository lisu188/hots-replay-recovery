"""Synthetic invariants for explicitly experimental RAM-only registry hypotheses."""
import unittest
import experimental_registry_merge as model


class SyntheticExperimentalMergeTests(unittest.TestCase):
    def test_two_duplicate_gap_candidates_preserve_base_and_current_order(self):
        base,current,prior=[1,1,2],[1,9,2],[1,9,2]
        metadata=model.position_candidates(base,current,prior)
        self.assertEqual(metadata['position_tuples'],[(1,),(2,)])
        candidates=list(model.iter_candidate_vectors(base,current,prior))
        self.assertEqual(candidates,[((1,),(1,9,1,2)),((2,),(1,1,9,2))])
        self.assertFalse(metadata['current_registry_multiplicity_proven'])
        self.assertFalse(metadata['XML_multiplicity_control_used_or_passed'])

    def test_missing_prior_or_repeated_prior_new_ID_refuses(self):
        for prior in ([1,2],[1,9,9,2]):
            with self.subTest(prior=prior),self.assertRaisesRegex(ValueError,'exactly once'):
                model.position_candidates([1,2],[1,9,2],prior)

    def test_changed_existing_order_or_extra_old_ID_refuses(self):
        for current in ([2,9,1],[1,9]):
            with self.subTest(current=current),self.assertRaises(ValueError):
                model.position_candidates([1,2],current,[1,9,2])

    def test_cap_refuses_before_first_RAM_vector(self):
        iterator=model.iter_candidate_vectors([1,1,2],[1,9,2],[1,9,2],cap=1)
        with self.assertRaisesRegex(ValueError,'cap'):next(iterator)

    def test_consecutive_new_values_remain_in_observed_order(self):
        candidates=list(model.iter_candidate_vectors([1,1,2],[1,8,9,2],[1,8,9,2]))
        self.assertEqual(len(candidates),3)
        self.assertTrue(all(list(dict.fromkeys(values))==[1,8,9,2] for _,values in candidates))

    def test_before_first_after_last_and_integer_types_guarded(self):
        self.assertEqual(len(list(model.iter_candidate_vectors([1,1],[8,1,9],[8,1,9]))),2)
        for current in ([1,True,2],[1,-1,2],[1,2**64,2],[1,9,9,2]):
            with self.subTest(current=current),self.assertRaises(ValueError):
                model.position_candidates([1,2],current,[1,9,2])

    def test_invalid_caps_and_more_than_nine_new_IDs_refuse(self):
        for cap in (0,1025,True):
            with self.subTest(cap=cap),self.assertRaises(ValueError):
                model.position_candidates([1,2],[1,9,2],[1,9,2],cap=cap)
        current=list(range(1,13))
        with self.assertRaises(ValueError):model.position_candidates([1,12],current,current)


if __name__=='__main__':unittest.main()
