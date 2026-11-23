import unittest

from legacy_command_sequences import paired_legacy_sequences


def at(kind, loop=10, user=0, **fields):
    return dict(_eventid=kind, _gameloop=loop, _userid={"m_userId": user}, **fields)


class SequencePairTests(unittest.TestCase):
    def test_explicit_unset_and_interleaved_users(self):
        events = [
            at(104),
            at(105, user=1),
            at(28),
            at(103, user=1, m_state=0, m_sequence=None),
            at(103, m_state=2, m_sequence=42),
        ]
        self.assertEqual(paired_legacy_sequences(events), {0: 42, 1: None})

    def test_different_loop_user_or_intervening_command(self):
        for intervening in (at(25), at(27), at(105), at(103, m_state=3, m_sequence=7)):
            with self.subTest(intervening=intervening["_eventid"]):
                found = paired_legacy_sequences(
                    [at(104), intervening, at(103, m_state=2, m_sequence=2)]
                )
                self.assertNotIn(0, found)
        for row in (at(103, loop=11), at(103, user=1)):
            self.assertFalse(
                paired_legacy_sequences([at(104), dict(row, m_state=2, m_sequence=1)])
            )

    def test_missing_companion_has_no_prediction(self):
        self.assertEqual(paired_legacy_sequences([at(105, m_sequence=100)]), {})
