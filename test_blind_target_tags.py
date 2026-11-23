from collections import Counter
import unittest

from check_blind_target_tags import lifetime_ends, pack, positive_flags, predict, training_links


class BlindTargetTests(unittest.TestCase):
    def setUp(self):
        self.point = dict(x=8 * 4096, y=7 * 4096)
        self.xy = self.point["x"], self.point["y"]
        self.units = {self.xy: [("A", (10, 1)), ("B", (11, 1))]}
        self.births = {self.xy: ["A", "B"]}
        self.ends = {(10, 1): 20}

    def guess(self, loop, links):
        return predict(self.point, 42, loop, self.units, self.births, self.ends, links)

    def test_shared_xy_requires_independent_type(self):
        self.assertEqual(self.guess(5, None), (None, "multiple_startup_units_at_xy"))
        self.assertEqual(self.guess(5, {42: "A"}), (pack(10, 1, 22), None))
        self.assertEqual(self.guess(5, {42: "B"}), (pack(11, 1, 22), None))
        self.assertEqual(self.guess(5, {}), (None, "unproven_link"))
        self.births[self.xy].append("A")
        self.assertEqual(self.guess(5, {42: "A"}), (None, "ambiguous_startup_type_at_xy"))

    def test_start_and_end_excluded(self):
        self.assertEqual(self.guess(0, {42: "A"}), (None, "outside_initial_lifetime"))
        self.assertEqual(self.guess(19, {42: "A"}), (pack(10, 1, 22), None))
        for loop in (20, 21):
            self.assertEqual(self.guess(loop, {42: "A"}), (None, "outside_initial_lifetime"))

    def test_index_reuse_ends_initial_life(self):
        tracker = [
            dict(
                _event="Tracker.SUnitBornEvent",
                _gameloop=loop,
                m_unitTagIndex=10,
                m_unitTagRecycle=recycle,
            )
            for loop, recycle in [(0, 1), (16, 2)]
        ]
        self.assertEqual(lifetime_ends(tracker, [(10, 1)]), {(10, 1): 16})

    def test_training_excludes_test_file_and_conflicts(self):
        def observations(*pairs):
            return Counter(pairs)

        sample = [
            ("test", observations((1, "other"), (2, "A"), (4, "test-only")), {}),
            ("a", observations((1, "A"), (2, "A"), (3, "A")), {}),
            ("b", observations((1, "A"), (3, "B")), {}),
        ]
        self.assertEqual(training_links(sample, "test"), {1: "A"})

    def test_flags_exclude_sentinels_and_heldout(self):
        cases = [
            ("test", {}, Counter([(1, False), (2, True)])),
            ("a", {}, Counter([(1, True), (2, True), (3, True)])),
            ("b", {}, Counter([(1, True), (3, True), (3, False)])),
        ]
        self.assertEqual(positive_flags(cases, "test"), [1])


if __name__ == "__main__":
    unittest.main()
