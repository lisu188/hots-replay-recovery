import unittest
from point_ability_births import projected_issue


class PointAbilities(unittest.TestCase):
    def setUp(self):
        self.cast = dict(
            _eventid=27,
            _gameloop=13,
            _userid={"m_userId": 3},
            m_sequence=19,
            m_abil={"m_abilLink": 244, "m_abilCmdIndex": 0, "m_abilCmdData": None},
            m_cmdFlags=0x100,
            m_data={"TargetPoint": {"x": 7, "y": 8, "z": -5}},
            m_otherUnit=None,
            m_unitGroup=None,
        )

    def test_only_link_flags_and_absent_vector_change(self):
        expected = {
            **self.cast,
            "m_abil": {**self.cast["m_abil"], "m_abilLink": 523},
            "m_cmdFlags": 0x2100100,
            "m_vector": None,
        }
        self.assertEqual(projected_issue(self.cast, "Nova", "NovaHoloClone"), expected)
        self.assertEqual(self.cast["m_abil"]["m_abilLink"], 244)

    def test_cloaked_variant_and_unrelated_birth(self):
        for unit in ("NovaHoloCloneCloaked", "HeroNova"):
            self.assertIsNone(projected_issue(self.cast, "Nova", unit))

    def test_new_issues_and_other_input_forms_are_excluded(self):
        for change in (
            {"_eventid": 104},
            {"m_abil": None},
            {"m_data": {"TargetUnit": {}}},
            {"m_otherUnit": 0},
            {"m_cmdFlags": 0x200100},
            {"m_unitGroup": 1},
        ):
            self.assertIsNone(projected_issue({**self.cast, **change}, "Nova", "NovaHoloClone"))


if __name__ == "__main__":
    unittest.main()
