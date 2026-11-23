from decimal import Decimal
import unittest

from map_startup_identity import Placement
from plan_authored_targets import join_layouts, owner_policy


def placement(oid, x, unit="A"):
    return Placement(oid, unit, Decimal(x), Decimal("8.5"))


class AuthoredTargets(unittest.TestCase):
    def test_ranks_include_unmatched_and_fractional_rows(self):
        old = [placement(1, "7"), placement(2, "7.25"), placement(3, "8")]
        new = [placement(2, "7.2500"), placement(3, "8")]
        self.assertEqual(join_layouts(old, new), {1: 0, 2: 1})

    def test_changed_id_type_or_decimal_rejected(self):
        old = [placement(1, "7.25")]
        for other in (placement(3, "7.25"), placement(1, "7.2501"), placement(1, "7.25", "B")):
            self.assertEqual(join_layouts(old, [other]), {})

    def test_duplicate_position_in_either_layout_rejected(self):
        unique = [placement(3, "7.25")]
        doubled = [placement(2, "7.25")] + unique
        self.assertEqual(join_layouts(unique, doubled), {})
        self.assertEqual(join_layouts(doubled, unique), {})

    def test_owner_boundary_disagreement_and_absent_owner(self):
        self.assertEqual(owner_policy(14, 15, (0, 0), 0), "project_authored_player")
        self.assertTrue(owner_policy(15, 15, (0, 0), 0).startswith("withhold_after"))
        self.assertTrue(owner_policy(16, 15, (0, 0), 0).startswith("withhold_after"))
        self.assertTrue(owner_policy(5, None, (1, 2), 1).startswith("withhold_source"))
        self.assertTrue(owner_policy(5, None, (None, None), 0).startswith("withhold_source"))


if __name__ == "__main__":
    unittest.main()
