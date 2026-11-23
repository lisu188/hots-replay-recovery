import unittest

from command_snapshot_owners import CHANGE, DEATH, PREFIX, REVIVE, OwnerHistory
from repair_unit_tags import pack


def record(kind, loop, recycle=1, pair=None):
    event = dict(_event=kind, _gameloop=loop, m_unitTagIndex=2, m_unitTagRecycle=recycle)
    if pair is not None:
        event["m_controlPlayerId"], event["m_upkeepPlayerId"] = pair
    return event


class OwnerHistoryTests(unittest.TestCase):
    def test_distinct_roles_and_zero_are_recovered(self):
        history = OwnerHistory([record(PREFIX + "SUnitBornEvent", 0, pair=(0, 11))])
        self.assertEqual(history.lookup(pack(2, 1, 18), 1, 18), ((0, 11), "alive"))
        self.assertEqual(
            history.lookup(pack(2, 1, 18), 0, 18), ((0, 11), "constant_lifetime_role_transition_loop")
        )

    def test_owner_transfer_never_rewrites_prior_snapshot_by_guessing(self):
        tag = pack(2, 1, 22)
        history = OwnerHistory(
            [record(PREFIX + "SUnitBornEvent", 0, pair=(11, 11)), record(CHANGE, 5, pair=(12, 12))]
        )
        self.assertEqual(history.lookup(tag, 4, 22), ((11, 11), "alive"))
        self.assertEqual(history.lookup(tag, 5, 22), (None, "transition_loop"))
        self.assertEqual(history.lookup(tag, 7, 22), (None, "ownership_changed"))

    def test_revival_and_index_reuse(self):
        first, second = pack(2, 1, 22), pack(2, 2, 22)
        history = OwnerHistory(
            [
                record(PREFIX + "SUnitInitEvent", 0, pair=(2, 12)),
                record(DEATH, 1),
                record(REVIVE, 3),
                record(PREFIX + "SUnitBornEvent", 6, 2, pair=(3, 11)),
            ]
        )
        self.assertEqual(history.lookup(first, 2, 22), ((2, 12), "constant_lifetime_role_dead"))
        self.assertEqual(history.lookup(first, 5, 22), ((2, 12), "revived"))
        self.assertEqual(history.lookup(first, 7, 22), (None, "unknown_generation"))
        self.assertEqual(history.lookup(second, 7, 22), ((3, 11), "alive"))

    def test_transfer_only_excludes_the_role_that_changed_even_after_return(self):
        history = OwnerHistory(
            [
                record(PREFIX + "SUnitBornEvent", 0, pair=(11, 11)),
                record(CHANGE, 2, pair=(4, 11)),
                record(CHANGE, 5, pair=(11, 11)),
            ]
        )
        tag = pack(2, 1, 22)
        for loop in (3, 6):
            self.assertEqual(history.lookup(tag, loop, 22), ((None, 11), "one_stable_role"))

    def test_missing_generation_and_sentinels(self):
        history = OwnerHistory([record(REVIVE, 1), record(CHANGE, 3, pair=(1, 1))])
        self.assertEqual(history.lookup(pack(2, 1, 22), 4, 22), (None, "unknown_generation"))
        self.assertEqual(history.lookup(0, 4, 22), (None, "sentinel"))
        self.assertEqual(history.lookup(0xFFFFFFFF, 4, 22), (None, "sentinel"))

    def test_out_of_order_tracker_is_rejected(self):
        with self.assertRaises(ValueError):
            OwnerHistory([record(REVIVE, 5), record(DEATH, 4)])

    def test_stale_generation_events_are_rejected(self):
        born = PREFIX + "SUnitBornEvent"
        starts = [record(born, 0, 1, (0, 0)), record(born, 3, 2, (1, 1))]
        for stale in (record(DEATH, 4, 1), record(born, 4, 1, (0, 0))):
            with self.assertRaisesRegex(ValueError, "generation"):
                OwnerHistory([*starts, stale])

    def test_tracker_owner_range(self):
        with self.assertRaisesRegex(ValueError, "four-bit"):
            OwnerHistory([record(PREFIX + "SUnitBornEvent", 0, pair=(16, 1))])
