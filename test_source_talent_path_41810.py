import copy
import unittest

from source_talent_path_41810 import SELECTION, SETUP, STAT, restore_talent_indices


CATALOG = [{'id': 'Test', 'talents': {
    '10': [{'id': 'Upgrade', 'prerequisite': 'Base'}],
    '1': [{'id': 'Other'}, {'id': 'Base'}],
    '4': [{'id': 'Third'}],
}}]


def selection(tick, user=8):
    return {'_event': SELECTION, '_gameloop': tick, '_userid': {'m_userId': user}}


def stat(kind, tick, player, *, level=None, purchase=None):
    ints = [(b'PlayerID', player)]
    strings = []
    if level is not None:
        ints.append((b'Level', level))
    if purchase is not None:
        strings.append((b'PurchaseName', purchase))
    if kind == b'PlayerSpawned':
        strings.append((b'Hero', b'HeroTest'))
    return dict(_event=STAT, _gameloop=tick, m_eventName=kind,
                m_intData=[{'m_key': k, 'm_value': v} for k, v in ints],
                m_stringData=[{'m_key': k, 'm_value': v} for k, v in strings])


def setup(user=8, player=3):
    return [{'_event': SETUP, '_gameloop': 0, 'm_userId': user, 'm_playerId': player},
            stat(b'PlayerSpawned', 1, player), stat(b'LevelUp', 2, player, level=11)]


class HistoricalTalentRecoveryTests(unittest.TestCase):
    def test_erased_indices_restored_by_name_with_numeric_level_sort_and_late_purchase(self):
        camera = {'_event': 'Camera', '_gameloop': 7, 'm_distance': 17}
        game = [selection(5), camera, selection(9)]
        tracker = setup() + [stat(b'TalentChosen', 6, 3, purchase=b'Base'),
                             stat(b'TalentChosen', 10, 3, purchase=b'Upgrade')]
        saved = copy.deepcopy((game, tracker, CATALOG))
        restored, path = restore_talent_indices(game, tracker, CATALOG)
        self.assertEqual(restored, [{**game[0], 'm_index': 1}, camera, {**game[2], 'm_index': 3}])
        self.assertEqual([r['game_event_ordinal'] for r in path], [0, 2])
        self.assertEqual((path[1]['catalog_level'], path[1]['recorded_prior_level']), (10, 11))
        self.assertEqual((game, tracker, CATALOG), saved)

    def test_input_index_must_be_erased_even_if_correct(self):
        with self.assertRaisesRegex(ValueError, 'Erase'):
            restore_talent_indices([{**selection(5), 'm_index': 1}], setup(), CATALOG)

    def test_level_up_on_the_selection_tick_is_not_prior(self):
        history = setup()[:-1] + [stat(b'LevelUp', 5, 3, level=1),
                                  stat(b'TalentChosen', 6, 3, purchase=b'Base')]
        with self.assertRaisesRegex(ValueError, 'strictly before'):
            restore_talent_indices([selection(5)], history, CATALOG)

    def test_equal_hero_does_not_transfer_a_prerequisite_between_players(self):
        history = setup() + setup(9, 6) + [stat(b'TalentChosen', 6, 3, purchase=b'Base'),
                                           stat(b'TalentChosen', 10, 6, purchase=b'Upgrade')]
        with self.assertRaisesRegex(ValueError, 'prerequisite'):
            restore_talent_indices([selection(5), selection(9, 9)], history, CATALOG)

    def test_tracker_only_or_duplicate_purchase_is_rejected(self):
        purchase = stat(b'TalentChosen', 6, 3, purchase=b'Base')
        with self.assertRaisesRegex(ValueError, 'Unpaired'):
            restore_talent_indices([], setup() + [purchase], CATALOG)
        with self.assertRaisesRegex(ValueError, 'Ambiguous recorded purchase'):
            restore_talent_indices([selection(5)], setup() + [purchase, purchase], CATALOG)

    def test_unknown_name_cannot_fall_back_to_first_talent(self):
        with self.assertRaisesRegex(ValueError, 'historical catalog'):
            restore_talent_indices([selection(5)], setup() + [stat(b'TalentChosen', 6, 3, purchase=b'Unknown')], CATALOG)


if __name__ == '__main__':
    unittest.main()
