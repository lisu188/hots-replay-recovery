import unittest

from check_capture_transitions import ownership_forecast


class CaptureForecastTests(unittest.TestCase):
    def test_fixed_old_and_current_delays(self):
        for build, reset in ((41810, 117), (98348, 149)):
            with self.subTest(build=build):
                r = ownership_forecast(
                    {1: [(100, 11), (reset, 0)]}, [(1, 101, 11, None)], build, 200
                )
                self.assertEqual(r["neutral_resets"]["matches"], 1)
                self.assertEqual(r["capture_stats"]["matches"], 1)
                self.assertEqual(r["neutral_resets"]["unexpected_observations"], 0)

    def test_early_reset_is_both_missing_at_prediction_and_unexpected(self):
        r = ownership_forecast(
            {1: [(100, 11), (116, 0)]}, [(1, 101, 11, None)], 41810, 200
        )
        self.assertEqual(r["neutral_resets"]["matches"], 0)
        self.assertEqual(r["neutral_resets"]["missing_observations"], 1)
        self.assertEqual(r["neutral_resets"]["unexpected_observations"], 1)

    def test_orphan_and_duplicate_events_count_with_multiplicity(self):
        r = ownership_forecast(
            {1: [(100, 11), (117, 0), (117, 0)], 2: [(140, 0), (150, 15)]},
            [(1, 101, 11, None), (2, 102, 12, None)],
            41810,
            200,
        )
        self.assertEqual(r["other_ownership_events"], 1)
        self.assertEqual(r["capture_stats"]["unexpected_observations"], 1)
        self.assertEqual(r["neutral_resets"]["unexpected_observations"], 2)

    def test_missing_team_award_and_reset_are_not_silently_ignored(self):
        r = ownership_forecast({1: [(50, 12)]}, [], 41810, 100)
        self.assertEqual(r["team_ownership_events"], 1)
        self.assertEqual(r["capture_stats"]["missing_observations"], 1)
        self.assertEqual(r["neutral_resets"]["missing_observations"], 1)

    def test_finish_before_due_is_censored(self):
        r = ownership_forecast({1: [(100, 12)]}, [(1, 101, 12, None)], 98348, 120)
        self.assertEqual(r["resets_beyond_replay_end"], 1)
        self.assertEqual(r["neutral_resets"]["missing_observations"], 0)


if __name__ == "__main__":
    unittest.main()
