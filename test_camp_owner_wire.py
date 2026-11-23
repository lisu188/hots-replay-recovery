import unittest

from camp_owner_wire import (
    capture_stats,
    encode_sparse,
    frame_bytes,
    normalized,
    project,
    target_protocol,
)


class BeaconWireTests(unittest.TestCase):
    def test_recorded_owners_are_irrelevant_to_projection(self):
        stat = {
            "_gameloop": 100,
            "m_eventName": b"JungleCampCapture",
            "m_intData": [{"m_key": b"CampID", "m_value": 2}],
            "m_fixedData": [{"m_key": b"TeamID", "m_value": 8192}],
        }
        poison = {
            "_eventid": 3,
            "_gameloop": 99,
            "m_unitTagIndex": 999,
            "m_controlPlayerId": 1,
        }
        tags = {2: (8, 1)}
        records, missing = project(capture_stats([stat, poison]), tags, 16, 116)
        self.assertEqual(missing, 0)
        self.assertEqual(
            normalized(records), [(99, 3, 8, 1, 12, 12), (116, 3, 8, 1, 0, 0)]
        )
        changed, missing = project(capture_stats([poison, stat]), {2: (10, 1)}, 48, 116)
        self.assertEqual(normalized(changed), [(99, 3, 10, 1, 12, 12)])
        self.assertEqual(missing, 1)

    def test_rejects_unjustified_order_and_invalid_stats(self):
        for stats in ([(100, 1, 1), (100, 2, 1)], [(100, 1, 1), (117, 2, 2)]):
            with self.subTest(stats=stats), self.assertRaisesRegex(
                ValueError, "ordering"
            ):
                project(stats, {1: (5, 1), 2: (8, 1)}, 16, 200)
        for stats in ([(201, 1, 1)], [(0, 1, 2)], [(10, 3, 1)], [(10, 1, True)]):
            with self.subTest(stats=stats), self.assertRaises(ValueError):
                project(stats, {1: (5, 1)}, 16, 200)

    def test_sparse_deltas_and_recorded_scaffold_deltas(self):
        rows, _ = project([(200, 1, 1)], {1: (201, 1)}, 16, 216)
        raw, decoded = encode_sparse(rows)
        protocol = target_protocol()
        first = frame_bytes(rows[0], 0, protocol)
        second = frame_bytes(rows[1], 199, protocol)
        self.assertEqual(raw, first + second)
        self.assertEqual(normalized(rows), normalized(decoded))
        self.assertEqual(sum(r["_bits"] for r in decoded), len(raw) * 8)
        tied = frame_bytes(rows[0], 199, protocol)
        self.assertNotEqual(first, tied)
        self.assertEqual(
            list(protocol.decode_replay_tracker_events(tied))[0]["_gameloop"], 0
        )


if __name__ == "__main__":
    unittest.main()
