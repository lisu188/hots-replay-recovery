import unittest

from death_capture_baseline import forecast


class DeathCaptureBaselineTests(unittest.TestCase):
    def setUp(self):
        self.a = ("MercDefenderSiegeGiant", 1, 2)
        self.b = ("MercDefenderSiegeGiant", 3, 2)
        self.slots = {self.a: 1, self.b: 1}
        self.kinds = {1: "SiegeGiants"}
        self.start = [(100, "gates"), (2200, "death", 1, self.a, 2)]

    def test_last_death_and_killer_team_drive_capture_and_return(self):
        captures, clock, uncertain, pending = forecast(
            self.kinds, self.slots, self.start + [(2300, "death", 1, self.b, 1)], 5159
        )
        self.assertEqual(captures, [(2325, 1, 1)])
        self.assertEqual(clock.waves, [(2022, 1, True), (5159, 1, False)])
        self.assertEqual((uncertain, pending, dict(clock.faults)), (0, 0, {}))

    def test_horizon_and_ambiguous_killer(self):
        signals = self.start + [(2300, "death", 1, self.b, None)]
        self.assertEqual(forecast(self.kinds, self.slots, signals, 9999)[2], 1)
        tied = [
            (100, "gates"),
            (2200, "death", 1, self.a, 2),
            (2200, "death", 1, self.b, 1),
        ]
        self.assertEqual(forecast(self.kinds, self.slots, tied, 9999)[0], [])
        c, _, _, pending = forecast(
            self.kinds, self.slots, self.start + [(2300, "death", 1, self.b, 1)], 2324
        )
        self.assertEqual((c, pending), ([], 1))

    def test_no_award_input_and_no_duplicate_slot_clear(self):
        with self.assertRaises(ValueError):
            forecast(
                self.kinds, self.slots, [(100, "gates"), (3300, "capture", 1)], 9999
            )
        c, clock, _, _ = forecast(
            self.kinds, self.slots, self.start + [(2300, "death", 1, self.a, 1)], 9999
        )
        self.assertEqual(c, [])
        self.assertEqual(clock.faults["death_outside_living_defender_slot"], 1)
