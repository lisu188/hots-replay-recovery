import unittest

from trace_mana_addict import project_tracker
from talent_choice_audit import STAT


def event(tick, name, owner, text_key=None, text_value=None):
    return {
        "_event": STAT,
        "_gameloop": tick,
        "m_eventName": name,
        "m_intData": [{"m_key": b"PlayerID", "m_value": owner}],
        "m_stringData": [{"m_key": text_key, "m_value": text_value}] if text_key else None,
        "m_fixedData": None,
    }


class TestManaAddict(unittest.TestCase):
    def test_owner_and_equal_loop_order(self):
        stream = [
            event(0, b"PlayerSpawned", 4, b"Hero", b"HeroKaelthas"),
            event(0, b"PlayerSpawned", 7, b"Hero", b"HeroKaelthas"),
            event(1, b"RegenGlobePickedUp", 4),
            event(1, b"TalentChosen", 4, b"PurchaseName", b"KaelthasManaAddict"),
            event(1, b"RegenGlobePickedUp", 4),
            event(2, b"TalentChosen", 7, b"PurchaseName", b"KaelthasManaAddict"),
            event(3, b"RegenGlobePickedUp", 4),
            event(3, b"RegenGlobePickedUp", 4),
            event(4, b"RegenGlobePickedUp", 7),
            event(4, b"RegenGlobePickedUp", 7),
        ]
        source = {"globe_threshold": 3, "max_mana_per_globe": 15}
        target = {"globe_threshold": 2, "max_mana_per_globe": 15}
        a, b = project_tracker(stream, 5, source, target)["owners_by_purchase_order"]
        self.assertEqual((a["credited_before_purchase"], a["ordered_credit_loops"]), (1, [1, 3, 3]))
        self.assertEqual(
            (a["source_threshold_loop"], a["target_threshold_loop_on_source_credits"]), (3, 3)
        )
        self.assertIsNone(a["earlier_target_eligibility_window_on_source_credits"])
        self.assertEqual(b["projected_end_bonus_max_mana"], 30)
        self.assertTrue(
            b["earlier_target_eligibility_window_on_source_credits"][
                "still_open_at_end_of_recorded_credits"
            ]
        )
        no_hero = stream.copy()
        no_hero[0] = event(0, b"PlayerSpawned", 4, b"Hero", b"HeroOther")
        with self.assertRaisesRegex(ValueError, "purchaser"):
            project_tracker(no_hero, 5, source, target)


if __name__ == "__main__":
    unittest.main()
