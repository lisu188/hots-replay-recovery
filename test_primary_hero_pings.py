import unittest

from primary_hero_pings import encode_selected, locate_base, select_primary_pings
from repair_unit_tags import pack


def ping(loop, unit=0):
    return {"_gameloop": loop, "_userid": {"m_userId": 2}, "m_point": {"x": 32, "y": -64},
            "m_unit": unit, "m_pingedMinimap": False, "m_option": 2}


class PrimaryPingsTest(unittest.TestCase):
    def test_lifetime_excludes_same_loop_dead_cutoff_and_recycled_units(self):
        old = pack(175, 1, 18)
        new = pack(175, 1, 22)
        qualified = {(175, 1): (3, b"HeroGreymane", [(50, True), (80, False), (128, True)])}
        events = [ping(t, old) for t in (48, 50, 60, 80, 96, 128, 144, 160)]
        events.extend([ping(145, pack(175, 2, 18)), ping(147)])
        tags, counts = select_primary_pings(events, qualified, 155)
        self.assertEqual(tags, {2: new, 6: new})
        self.assertEqual(dict(counts), {"withheld_pre_birth": 1, "withheld_boundary": 3,
                                        "first_life": 1, "withheld_dead": 1, "alive_after_revive": 1})

    def test_join_keeps_source_order_and_absolute_loop_for_sparse_deltas(self):
        a, b = pack(175, 1, 18), pack(175, 1, 22)
        events = [ping(80), ping(150, a), ping(175), ping(410, a)]
        selected = {3: b, 0: 0}
        self.assertEqual(locate_base(events, encode_selected(events, selected)), selected)

    def test_join_rejects_nonunique_ping(self):
        e = ping(140)
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            locate_base([e, e], encode_selected([e], {0: 0}))

    def test_invalid_ordinal_does_not_select_last_ping(self):
        with self.assertRaisesRegex(ValueError, "ordinal"):
            encode_selected([ping(140)], {-1: 0})


if __name__ == "__main__":
    unittest.main()
