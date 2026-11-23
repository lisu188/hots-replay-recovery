import unittest

from unit_retirement import FINAL, STAGED, Timer, mark_timer, retirement_step


class UnitRetirementTest(unittest.TestCase):
    def step(self, timer, **override):
        args = dict(clock=15, due=15, state_flags=4, debit=3, final_delay=0)
        return retirement_step(timer, **(args | override))

    def test_marker_modes(self):
        self.assertEqual(mark_timer(1, True, 8, 9), Timer(1, 1 | FINAL))
        self.assertEqual(mark_timer(FINAL, False, 8, -9), Timer(8, STAGED | FINAL))
        self.assertEqual(mark_timer(FINAL, False, 0, -9), Timer(1, 0))
        self.assertEqual(mark_timer(0, False, -4, 0), Timer(1, FINAL))
        self.assertEqual(mark_timer(0, False, 0, 9), Timer(9, FINAL))

    def test_unsigned_clock_and_post_callback_flags(self):
        timer = Timer(0, FINAL)
        self.assertEqual(self.step(timer, due=-1), ("retain", timer))
        self.assertEqual(self.step(timer, state_flags=1), ("retain", timer))
        for state in (2, 4, 6):
            self.assertEqual(self.step(timer, state_flags=state), ("retire", timer))

    def test_debit_waits_through_crossing(self):
        timer = Timer(2, FINAL)
        result, timer = self.step(timer)
        self.assertEqual((result, timer), ("debit", Timer(-1, FINAL)))
        self.assertEqual(self.step(timer)[0], "retire")

    def test_stage_waits_through_zero_delay(self):
        timer = Timer(0, STAGED | FINAL | 1)
        result, timer = self.step(timer)
        self.assertEqual((result, timer), ("stage", Timer(0, FINAL | 1)))
        self.assertEqual(self.step(timer)[0], "retire")

    def test_stage_negative_delay_disables_release(self):
        result, timer = self.step(Timer(-1, STAGED | FINAL), final_delay=-9)
        self.assertEqual((result, timer), ("stage", Timer(0, 0)))
        self.assertEqual(self.step(timer), ("retain", timer))

    def test_mark_stage_debit_retire(self):
        timer = mark_timer(0, False, 3, 5)
        steps = []
        for _ in range(5):
            action, timer = self.step(timer, final_delay=5)
            steps.append(action)
        self.assertEqual(steps, ["debit", "stage", "debit", "debit", "retire"])


if __name__ == "__main__":
    unittest.main()
