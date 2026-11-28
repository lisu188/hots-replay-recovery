import unittest

import join_sparse_tracker_range as join


def death(killer):
    return {"_eventid": 2, "_gameloop": 610, "_event": "x", "m_unitTagIndex": 115, "m_unitTagRecycle": 1,
            "m_killerPlayerId": killer, "m_x": 75, "m_y": 78, "m_killerUnitTagIndex": None, "m_killerUnitTagRecycle": None}


class SourceAgreementTests(unittest.TestCase):
    def test_blocker_killer_zero_is_the_only_admitted_difference(self):
        self.assertTrue(join.source_agrees({**death(None), "_bits": 80}, death(0)))
        self.assertFalse(join.source_agrees(death(None), {**death(0), "m_x": 76}))
        for source, target in ((death(None), death(None)), (death(3), death(0)), (death(None), death(5))):
            with self.subTest(source=source["m_killerPlayerId"], target=target["m_killerPlayerId"]), self.assertRaises(ValueError):
                join.source_agrees(source, target)

    def test_other_events_must_match_exactly(self):
        upgrade = {"_eventid": 5, "_gameloop": 610, "m_playerId": 1, "m_upgradeTypeName": b"GatesAreOpen", "m_count": 1}
        self.assertTrue(join.source_agrees({**upgrade, "_bits": 40, "_event": "a"}, {**upgrade, "_event": "b"}))
        self.assertFalse(join.source_agrees(upgrade, {**upgrade, "m_playerId": 2}))


class CatalogTests(unittest.TestCase):
    def test_keyed_records_reject_duplicates(self):
        raw = b'<Catalog><CTalent id="A"><X/></CTalent><CHero id="A"/></Catalog>'
        self.assertEqual(set(join.keyed(raw)), {("CTalent", "A"), ("CHero", "A")})
        with self.assertRaises(ValueError):
            join.keyed(b'<Catalog><CTalent id="A"/><CTalent id="A"/></Catalog>')


if __name__ == "__main__":
    unittest.main()
