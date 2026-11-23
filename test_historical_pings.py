import unittest

from convert_historical_pings import native_frame, target_for
from repair_unit_tags import pack


class HistoricalPingTests(unittest.TestCase):
    def test_explicit_absence_and_unresolved_instance_are_distinct(self):
        self.assertEqual(target_for(0, 10, {}, {}), (0, "no_explicit_unit"))
        self.assertEqual(target_for(1, 10, {}, {}), (None, "unresolved_instance"))

    def test_startup_binding_requires_matching_generation_and_lifetime(self):
        tag = pack(27, 1, 18)
        anchors = {(27, 1): 30}
        ends = {(27, 1): 100}
        self.assertEqual(target_for(tag, 99, anchors, ends)[0], pack(30, 1, 22))
        for loop in (0, 100, 101):
            self.assertIsNone(target_for(tag, loop, anchors, ends)[0])
        self.assertIsNone(target_for(pack(27, 2, 18), 99, anchors, ends)[0])

    def test_preserves_point_option_and_minimap(self):
        e = {
            "m_point": {"x": -15, "y": 17},
            "m_option": -1,
            "m_pingedMinimap": True,
            "_userid": {"m_userId": 3},
        }
        frame = native_frame(e, 0, 70)
        self.assertEqual(
            (frame.delta, frame.user_id, frame.event_id, frame.payload),
            (70, 3, 36, ((-15, 17), 0, True, -1)),
        )
