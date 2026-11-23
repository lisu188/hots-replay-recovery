import unittest

from legacy_camp_wave_model import WaveClock


class WaveClockTests(unittest.TestCase):
    def setUp(self):
        self.slots = {("MercDefenderSiegeGiant", 99, 75): 1, ("MercDefenderSiegeGiant", 102, 76): 1}
        self.clock = WaveClock({1: "SiegeGiants"}, self.slots)
        self.clock.event(610, "gates")

    def capture(self):
        for loop, slot in zip((3000, 3100), self.slots):
            self.clock.event(loop, "death", 1, slot)
        self.assertEqual(self.clock.camps[1].state, "awaiting_capture")
        self.clock.event(3200, "capture", 1)

    def test_first_wave_and_ordinary_respawn(self):
        self.clock.advance(2531)
        self.assertEqual(self.clock.waves, [])
        self.clock.advance(2532)
        self.assertEqual(self.clock.camps[1].alive, set(self.slots))
        self.capture()
        self.clock.advance(6033)
        self.assertEqual(len(self.clock.waves), 1)
        self.clock.advance(6034)
        self.assertEqual(self.clock.waves, [(2532, 1, True), (6034, 1, False)])

    def test_dragon_does_not_delay_initial_wave(self):
        self.clock.event(2514, "dragon_on")
        self.clock.advance(2532)
        self.assertEqual(self.clock.waves, [(2532, 1, True)])

    def test_dragon_delays_ready_camp_until_vehicle_dies(self):
        self.capture()
        self.clock.event(6000, "dragon_on")
        self.clock.advance(6075)
        self.assertEqual(self.clock.camps[1].state, "waiting_for_dragon_end")
        self.clock.event(6100, "dragon_off")
        self.clock.advance(6102)
        self.assertEqual(len(self.clock.waves), 1)
        self.clock.advance(6103)
        self.assertEqual(self.clock.waves[-1], (6103, 1, False))
        self.assertEqual(self.clock.holds, 1)

    def test_duplicate_slot_death_keeps_other_slot_alive(self):
        first = next(iter(self.slots))
        self.clock.event(3000, "death", 1, first)
        self.clock.event(3001, "death", 1, first)
        self.assertEqual(len(self.clock.camps[1].alive), 1)
        self.assertEqual(self.clock.faults["death_outside_living_defender_slot"], 1)
        self.clock.event(3002, "capture", 1)
        self.assertEqual(self.clock.faults["capture_without_complete_observed_defeat"], 1)

    def test_unobserved_same_tick_order_is_reported(self):
        self.capture()
        self.clock.event(6032, "dragon_on")
        self.assertEqual(self.clock.faults["unverified_same_loop_dragon_transition_and_ready_timer"], 1)


if __name__ == "__main__":
    unittest.main()
