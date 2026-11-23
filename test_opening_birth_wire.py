import unittest

from encoders import encode_tracker_events
from opening_birth_wire import BIRTH, compare, sparse_stream, target_protocol


class OpeningBirthTests(unittest.TestCase):
    def setUp(self):
        self.target = target_protocol()
        self.event = dict(_gameloop=50, _eventid=1, _event=BIRTH, m_unitTagIndex=172,
                          m_unitTagRecycle=1, m_unitTypeName=b"HeroFaerieDragon",
                          m_controlPlayerId=1, m_upkeepPlayerId=1, m_x=31, m_y=105)
        # An intervening non-birth advanced the enclosing physical stream to loop 49.
        self.frame = encode_tracker_events([{**self.event, "_gameloop": 1}], self.target)
        self.obs = (self.event, 49, 0, len(self.frame))

    def test_enclosing_and_sparse_deltas(self):
        report, witness = compare([self.event], [self.obs], self.frame, self.target)
        self.assertEqual(report["ordered_exact_frames"], 1)
        stream = sparse_stream([self.event], witness, self.target)
        self.assertNotEqual(stream, self.frame)
        self.assertEqual(witness[0]["sparse_offset"], 0)
        self.assertEqual(witness[0]["previous_physical_loop"], 49)

    def test_slot_generation_coordinates_and_order(self):
        for field in ("m_unitTagIndex", "m_unitTagRecycle", "m_x", "_gameloop"):
            with self.subTest(field=field):
                wrong = {**self.event, field: self.event[field]+1}
                report, witness = compare([wrong], [self.obs], self.frame, self.target)
                self.assertEqual(report["mismatch_counts"], {field: 1})
                self.assertEqual(witness, [])

    def test_extra_birth_refuses_group(self):
        report, _ = compare([self.event], [self.obs, self.obs], self.frame, self.target)
        self.assertEqual(report["mismatch_counts"], {"count": 1})

    def test_raw_byte_mismatch(self):
        wrong = self.frame[:-1] + bytes([self.frame[-1] ^ 1])
        report, _ = compare([self.event], [self.obs], wrong, self.target)
        self.assertEqual(report["mismatch_counts"], {"physical_bytes": 1})


if __name__ == "__main__":
    unittest.main()
