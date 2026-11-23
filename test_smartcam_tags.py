import unittest

from smartcam_tags import decode, pack, phase, RECORD, transpose


def birth(k, t, kind=b"Marine", player=1, x=100):
    return dict(
        _event="NNet.Replay.Tracker.SUnitBornEvent",
        _gameloop=t,
        m_unitTagIndex=k,
        m_unitTagRecycle=1,
        m_unitTypeName=kind,
        m_controlPlayerId=player,
        m_upkeepPlayerId=player,
        m_x=x,
        m_y=80,
    )


def death(k, t):
    return dict(
        _event="NNet.Replay.Tracker.SUnitDiedEvent",
        _gameloop=t,
        m_unitTagIndex=k,
        m_unitTagRecycle=1,
    )


class SmartCamTests(unittest.TestCase):
    def test_true_layout_offsets(self):
        raw = bytes.fromhex("08160300000100bc020100d002")
        self.assertEqual(
            decode(raw, 1000), [(8, 790, pack(175, 1, 18), pack(180, 1, 18))]
        )
        for value, horizon in (
            (raw[:-1], 1000),
            (b"\x07" + raw[1:], 1000),
            (raw, 789),
            (RECORD.pack(8, 791, 1, 2) + raw, 1000),
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                decode(value, horizon)

    def test_different_indices_derived_from_lifetime(self):
        source = [birth(3, 0), birth(4, 0), death(3, 10), death(4, 20)]
        # The two births share every source signature member. Only lifetimes identify them.
        target = [birth(9, 0), birth(7, 0), death(7, 10), death(9, 20)]
        row = (8, 3, pack(3, 1, 18), pack(4, 1, 18))
        generated, mapping = transpose([row], source, target, 18, 22)
        self.assertEqual(mapping, {(3, 1): (7, 1), (4, 1): (9, 1)})
        self.assertEqual(generated, [(8, 3, pack(7, 1, 22), pack(9, 1, 22))])
        self.assertEqual(transpose(generated, target, source, 22, 18)[0], [row])
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            transpose(
                [row],
                source,
                [birth(7, 0), birth(9, 0), death(7, 10), death(9, 10)],
                18,
                22,
            )

    def test_missing_changed_and_generation_boundaries(self):
        source = [birth(9, 0), death(9, 12)]
        for b in ([birth(4, 1)], [birth(4, 0), death(4, 13)]):
            with self.assertRaises(ValueError):
                transpose([(8, 5, pack(9, 1, 18), pack(9, 1, 18))], source, b, 18, 22)
        with self.assertRaisesRegex(ValueError, "missing"):
            transpose([(8, 5, 0, pack(9, 1, 18))], source, source, 18, 22)
        self.assertEqual(
            [phase([(1, True), (12, False)], v) for v in (0, 1, 11, 12, 13)],
            ["pre_birth", "boundary", "live", "boundary", "dead"],
        )


if __name__ == "__main__":
    unittest.main()
