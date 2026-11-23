import unittest
from symbolic_command_starts import references, relation


class SymbolicStarts(unittest.TestCase):
    def test_point_comparison_uses_every_coordinate(self):
        point = dict(x=3, y=4, z=-5)
        issue = {"m_data": {"TargetPoint": point}}
        update = {"_eventid": 104, "m_target": dict(point)}
        self.assertEqual(relation(issue, update), "identical_point")
        self.assertEqual(relation(issue, {**update, "m_target": {**point, "z": -4}}), "changed_point")

    def test_unit_update_can_follow_point_issue(self):
        update = {"_eventid": 105, "m_target": {"m_tag": 6, "m_timer": 12}}
        self.assertEqual(relation({"m_data": {"TargetPoint": {}}}, update), "different_target_kind")
        self.assertEqual(
            relation({"m_data": {"TargetUnit": {"m_tag": 6, "m_timer": 2}}}, update), "same_unit_tag"
        )
        self.assertEqual(relation({"m_data": {"TargetUnit": {"m_tag": 7}}}, update), "changed_unit_tag")

    def test_reject_empty_reference_manifest(self):
        with self.assertRaises(ValueError):
            references({})


if __name__ == "__main__":
    unittest.main()
