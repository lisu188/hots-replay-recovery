import unittest

from dragon_loop_zero import membership, player_init
from dragon_mastery_ring_history import zero_rings
from tracker_player_prefix import predict


class TestDragonLoopZero(unittest.TestCase):
    def setUp(self):
        self.slots = [dict(m_observe=0, m_hero=b"fixture", m_control=2, m_userId=15-i,
                           m_teamId=i % 2, m_toonHandle=b"") for i in range(10)]

    def test_setup_uses_user_id_and_playing_slot_separately(self):
        rows = predict(self.slots, 9)
        self.assertEqual([r["m_userId"] for r in rows], list(range(15, 5, -1)))
        self.assertEqual([r["m_slotId"] for r in rows], list(range(10)))
        self.slots[0]["m_userId"] = self.slots[1]["m_userId"]
        with self.assertRaises(ValueError):
            predict(self.slots, 9)

    def test_membership_follows_teams_and_includes_computers(self):
        rows = membership(self.slots)
        self.assertEqual([(r["m_playerId"], r["m_upgradeTypeName"]) for r in rows],
                         [(i, b"IsOnOrderTeam") for i in (1,3,5,7,9,11)]
                         + [(i, b"IsOnChaosTeam") for i in (2,4,6,8,10,12)])

    def test_player_init_conditionally_includes_handle(self):
        self.assertEqual(len(player_init(1, self.slots[0])["m_stringData"]), 1)
        self.slots[0]["m_toonHandle"] = b"fixture"
        self.assertEqual(player_init(1, self.slots[0])["m_stringData"][1]["m_value"], b"fixture")

    def test_pre_ring_players(self):
        self.assertEqual([(r["m_playerId"], r["m_count"]) for r in zero_rings()],
                         [(i, 0) for i in range(1,11)])
