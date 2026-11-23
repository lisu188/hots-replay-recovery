import unittest

from dragon_lane_roles import rebind_role


class LaneRolesTest(unittest.TestCase):
    def test_semantic_rebind_after_target_slot_changes(self):
        role = dict(kind="FootmanMinion", owner=11, wave=14, lane=3, slot=3, born=6950, xy=[60, 93])
        generation = (90, 4)
        neighbor = (40, 2)
        evidence = {generation: dict(role), neighbor: dict(role, slot=2)}
        self.assertEqual(rebind_role(role, 7128, evidence, {}, 7130), generation)
        for tick, table, deaths in (
            (6950, evidence, {}),
            (7131, evidence, {}),
            (7128, {neighbor: dict(role, lane=1)}, {}),
            (7128, {generation: role, neighbor: role}, {}),
            (7128, evidence, {generation: 7128}),
        ):
            with self.subTest(tick=tick, candidates=len(table)), self.assertRaises(ValueError):
                rebind_role(role, tick, table, deaths, 7130)
