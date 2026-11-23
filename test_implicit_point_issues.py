import unittest
from immediate_point_updates import match

from implicit_point_issues import eligible, mapped_candidates, project


class PointIssues(unittest.TestCase):
    def test_following_same_loop_prediction_ignores_recorded_sequence(self):
        issue = {**self.row, "m_cmdFlags": 0x100108}
        adjacent = dict(
            _eventid=104, _userid=issue["_userid"], _gameloop=11, m_target={"x": 18, "y": 21, "z": -35}
        )
        for value in (None, 17, 31):
            self.assertEqual(match(issue, {**adjacent, "m_sequence": value}, 41810), 31)
        for change in (
            {"_gameloop": 12},
            {"_userid": {"m_userId": 5}},
            {"m_target": issue["m_data"]["TargetPoint"]},
            {"_eventid": 105},
        ):
            self.assertIsNone(match(issue, {**adjacent, **change}, 41810))
        self.assertIsNone(match(None, adjacent, 41810))
        self.assertIsNone(match(self.row, adjacent, 41810))

    def setUp(self):
        self.row = dict(
            _eventid=27,
            _gameloop=11,
            _userid={"m_userId": 4},
            m_cmdFlags=0x110108,
            m_abil=None,
            m_data={"TargetPoint": {"x": 17, "y": 21, "z": -35}},
            m_sequence=31,
            m_otherUnit=None,
            m_unitGroup=None,
        )

    def test_preserves_nonmonotonic_sequence_and_coordinates(self):
        result = project(self.row)
        self.assertEqual(result, {**self.row, "m_cmdFlags": 0x88108, "m_vector": None})
        self.assertNotIn("m_vector", self.row)

    def test_hidden_dependencies_exclude_issue(self):
        for k, v in (
            ("m_abil", {}),
            ("m_otherUnit", 0),
            ("m_unitGroup", 0),
            ("m_vector", {}),
            ("m_data", {"TargetUnit": {}}),
            ("_eventid", 104),
        ):
            with self.subTest(k=k):
                self.assertFalse(eligible({**self.row, k: v}))
        with self.assertRaises(ValueError):
            project({**self.row, "m_cmdFlags": 0x100})

    def test_compatible_positions_share_one_vector(self):
        old = [0x10A, 0x100108, 0x110108]
        new = {0x10A, 0x810A, 0x80108, 0x88108}
        got = mapped_candidates(old, new)
        self.assertEqual(set(got), set(range(9, 16)))
        self.assertEqual(set(got.values()), {(0x10A, 0x80108, 0x88108)})
        # A second admissible target form destroys uniqueness under the same model.
        self.assertGreater(len(set(mapped_candidates(old, new | {0x90108}).values())), 1)


if __name__ == "__main__":
    unittest.main()
