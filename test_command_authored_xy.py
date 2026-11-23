from types import SimpleNamespace
from unittest import TestCase

from command_authored_xy import BUILDINGS, fixed, get_target, lifetime_ends
from project_layout_xy import MAPS, SOURCE, correspondence


class FixedCoordinateTests(TestCase):
    def test_exact_and_inexact_decimal(self):
        self.assertEqual(fixed("153.5"), 628736)
        self.assertEqual(fixed("1.000244140625"), 4097)
        self.assertEqual(fixed("0"), 0)
        for value in ("108.0297", "-1", "NaN"):
            self.assertIsNone(fixed(value))

    def test_recycle_and_lifetime(self):
        def event(kind, loop, recycle):
            return dict(_event=kind, _gameloop=loop, m_unitTagIndex=9, m_unitTagRecycle=recycle)

        anchor = SimpleNamespace(index=9, recycle=1)
        for kind in ("SUnitTypeChangeEvent", "SUnitDiedEvent", "SUnitRevivedEvent", "SUnitInitEvent"):
            self.assertEqual(
                lifetime_ends([event("SUnitBornEvent", 0, 1), event(kind, 10, 1)], [anchor]), {9: 10}
            )
        self.assertEqual(
            lifetime_ends([event("SUnitBornEvent", 0, 1), event("SUnitBornEvent", 6, 2)], [anchor]), {9: 6}
        )
        self.assertNotIn("VehicleDragon", BUILDINGS)
        self.assertIsNone(get_target(dict(_event="NNet.Game.SCmdEvent", m_data={"TargetPoint": {}})))


class TransferTests(TestCase):
    def src(self):
        p = dict(
            object_id=7,
            type="TownMoonwellL2",
            index=1,
            recycle=1,
            xy=[2048, 4096],
            startup_owners=[11, 11],
            matching_commands=1,
        )
        return dict(
            build=41810,
            map_sha256=MAPS[41810],
            replay_sha256=SOURCE,
            full_game_byte_equal=True,
            counts={},
            structure_positions=[p],
            projected_rows=[dict(ordinal=3, loop=2, type=p["type"], object_id=7, xy=p["xy"])],
        )

    def dst(self):
        s = self.src()
        s.update(build=98348, map_sha256=MAPS[98348], replay_sha256="held-out-control")
        s["structure_positions"][0].update(index=2, xy=[6144, 8192])
        return s

    def test_moved_structure_can_change_index_and_xy(self):
        counts, rows = correspondence(self.src(), [self.dst()])
        self.assertEqual(counts, {"xy_changes": 1})
        self.assertEqual((rows[0]["source_index"], rows[0]["target_index"]), (1, 2))
        self.assertEqual(rows[0]["target_xy"], [6144, 8192])

    def test_missing_object_wrong_type_side_or_witness(self):
        for change, reason in (
            ({"object_id": 8}, "no_same_id_target_structure"),
            ({"type": "KingsCore"}, "same_id_but_type_or_team_differs"),
            ({"startup_owners": [12, 12]}, "same_id_but_type_or_team_differs"),
            ({"matching_commands": 0}, "same_id_type_team_without_target_command_witness"),
        ):
            target = self.dst()
            target["structure_positions"][0].update(change)
            self.assertEqual(correspondence(self.src(), [target]), ({reason: 1}, []))

    def test_conflicting_or_duplicate_controls(self):
        first, second = self.dst(), self.dst()
        with self.assertRaises(ValueError):
            correspondence(self.src(), [first, second])
        second["replay_sha256"] = "different"
        second["structure_positions"][0]["index"] = 3
        with self.assertRaises(ValueError):
            correspondence(self.src(), [first, second])
        first["full_game_byte_equal"] = False
        with self.assertRaises(ValueError):
            correspondence(self.src(), [first])
