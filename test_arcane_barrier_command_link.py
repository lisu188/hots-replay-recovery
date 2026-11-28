import unittest

import arcane_barrier_command_link as link


class HelperTests(unittest.TestCase):
    def test_bursts_merge_key_repeats_within_one_second(self):
        self.assertEqual(link.bursts([15947, 15948, 15948, 17244, 17245, 19665, 19666, 23290]), [15947, 17244, 19665, 23290])
        self.assertEqual(link.bursts([100, 116, 131]), [100, 116])
        self.assertEqual(link.bursts([]), [])

    def test_stat_player_requires_one_player(self):
        event = {"m_intData": [{"m_key": b"PlayerID", "m_value": 4}]}
        self.assertEqual(link.stat_player(event), 4)
        for rows in ([], [{"m_key": b"PlayerID", "m_value": 1}, {"m_key": b"PlayerID", "m_value": 2}]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                link.stat_player({"m_intData": rows})


if __name__ == "__main__":
    unittest.main()
