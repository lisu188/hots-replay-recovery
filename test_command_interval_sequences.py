import unittest
from command_interval_sequences import SELECTED, candidates


def record(kind, tick, value=None, state=0):
    return {"_eventid": kind, "_gameloop": tick, "m_target": value, "m_state": state}


class CommandIntervalSequences(unittest.TestCase):
    def setUp(self):
        self.issue = {"_gameloop": 4, "m_sequence": 37, "m_data": {"TargetPoint": (1, 2, 3)}}

    def rules(self, events, next_sequence=None):
        rows = [(i, e, None, None) for i, e in enumerate(events)]
        right = None if next_sequence is None else {"m_sequence": next_sequence}
        return [
            (r[0], seq, sorted(set(flags) & set(SELECTED)))
            for r, seq, flags in candidates(self.issue, rows, right)
            if set(flags) & set(SELECTED)
        ]

    def test_anchor_and_manager_share_loop(self):
        events = [record(104, 4, (1, 3, 3)), record(104, 5, (2, 4, 3)), record(103, 5)]
        self.assertEqual(
            self.rules(events, 38),
            [(1, 37, ["chain_firstsame"]), (2, 37, ["manager0_firstsame_latest_same_closed"])],
        )
        self.assertEqual(self.rules(events, 39), [(1, 37, ["chain_firstsame"])])

    def test_manager_and_unit_update_break_continuity(self):
        for stop in (record(103, 5, state=1), record(105, 5)):
            self.assertEqual(
                self.rules([record(104, 4, (2, 2, 3)), stop, record(104, 6, (1, 3, 3))], 38), []
            )

    def test_closed_first_later_requires_point_only_interval(self):
        events = [record(104, 5, (2, 2, 3)), record(104, 6, (2, 3, 3))]
        self.assertEqual(self.rules(events, 38), [(0, 37, ["first_later_no_manager_closed"])])
        self.assertEqual(self.rules(events), [])
        self.assertEqual(self.rules(events + [record(103, 6)], 38), [])

    def test_unchanged_anchor_and_existing_update_field_are_ignored(self):
        self.assertEqual(self.rules([record(104, 4, (1, 2, 3)), record(104, 6, (2, 3, 3))], 38), [])
        events = [record(104, 4, (2, 2, 3)), {**record(104, 6, (2, 3, 3)), "m_sequence": 999}]
        self.assertEqual(self.rules(events, None), [(1, 37, ["chain_firstsame"])])


if __name__ == "__main__":
    unittest.main()
