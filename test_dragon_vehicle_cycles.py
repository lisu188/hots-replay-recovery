import unittest
from dataclasses import replace

from dragon_vehicle_cycles import Cycle, rebind_vehicle, vehicle_cycles


class TestVehicleCycles(unittest.TestCase):
    def setUp(self):
        self.cycle = Cycle(2, 2000, 3500, 2500, 3, 1, (32, 19), 4100)
        self.other = replace(self.cycle, tag=(41, 7))

    def test_rebinds_by_cycle_before_and_after_activation(self):
        for tick in (2100, 2600):
            self.assertEqual(rebind_vehicle(self.cycle, [self.other], tick), (41, 7))

    def test_uncertain_or_dead_target_is_rejected(self):
        for targets, tick in [
            ([], 2600), ([self.other, self.other], 2600), ([replace(self.other, team=2)], 2600),
            ([self.other], 3500), ([self.other], 2000), ([replace(self.other, horizon=2200)], 2600),
        ]:
            with self.subTest(targets=targets, tick=tick), self.assertRaises(ValueError):
                rebind_vehicle(self.cycle, targets, tick)

    def test_missing_respawn_is_detected(self):
        pair = dict(m_unitTagIndex=2, m_unitTagRecycle=1)
        events = [
            dict(_gameloop=0, _eventid=1, m_unitTypeName=b"VehicleDragon",
                 m_x=1, m_y=2, m_controlPlayerId=0, m_upkeepPlayerId=0, **pair),
            dict(_gameloop=4, _eventid=3, m_controlPlayerId=1, m_upkeepPlayerId=11, **pair),
            dict(_gameloop=4, _eventid=10, m_eventName=b"DragonKnightActivated",
                 m_intData=[dict(m_key=b"Event", m_value=1)], m_fixedData=[dict(m_key=b"TeamID", m_value=4096)]),
            dict(_gameloop=8, _eventid=2, **pair),
        ]
        self.assertEqual(len(vehicle_cycles(events, (1, 2), {1: 1}, 1900)), 1)
        with self.assertRaisesRegex(ValueError, "Missing vehicle"):
            vehicle_cycles(events, (1, 2), {1: 1}, 1929)
