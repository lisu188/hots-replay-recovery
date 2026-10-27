import copy
import unittest

from talent_choice_audit import SELECTION, SETUP, STAT, audit_talent_choices, compare_observed_names


def selection(tick=10, user=8, index=15):
    return {'_event': SELECTION, '_gameloop': tick, '_userid': {'m_userId': user}, 'm_index': index}


def setup(user=8, player=3, tick=0):
    return {'_event': SETUP, '_gameloop': tick, 'm_userId': user, 'm_playerId': player}


def stat(name=b'TalentChosen', value=b'KaelthasLivingBombIgnite', tick=11, player=3):
    return {'_event': STAT, '_gameloop': tick, 'm_eventName': name,
            'm_intData': [{'m_key': b'PlayerID', 'm_value': player}],
            'm_stringData': [{'m_key': b'Hero' if name == b'PlayerSpawned' else b'PurchaseName', 'm_value': value}]}


def tracker():
    return [setup(), stat(b'PlayerSpawned', b'HeroKaelthas', 0), stat()]


class TalentChoiceAuditTests(unittest.TestCase):
    def test_explicit_mapping_fixed_offset_and_no_input_mutation(self):
        game, track = [selection()], tracker()
        before = copy.deepcopy((game, track))
        result = audit_talent_choices(game, track)
        self.assertEqual(result['unique_one_loop_pairs'], 1)
        self.assertEqual(result['observations'], [{'hero_id': 'HeroKaelthas', 'index': 15,
                                                 'purchase_name': 'KaelthasLivingBombIgnite', 'count': 1}])
        self.assertEqual(result['fixed_offset_single_candidate_counts'], {'-2': 0, '-1': 0, '0': 0, '1': 1, '2': 0})
        self.assertEqual((game, track), before)
        self.assertNotIn('player', repr(result))

    def test_nearest_or_same_tick_is_never_a_fallback(self):
        for tick in (8, 9, 10, 12):
            track = tracker(); track[-1]['_gameloop'] = tick
            result = audit_talent_choices([selection()], track)
            self.assertEqual(result['unique_one_loop_pairs'], 0)
            self.assertEqual(result['unpaired_tracker_purchases'], 1)

    def test_different_player_at_correct_tick_does_not_match(self):
        track = tracker(); track[-1]['m_intData'][0]['m_value'] = 4
        self.assertEqual(audit_talent_choices([selection()], track)['unique_one_loop_pairs'], 0)

    def test_duplicate_purchase_key_is_ambiguous_even_for_equal_names(self):
        track = tracker() + [stat()]
        result = audit_talent_choices([selection()], track)
        self.assertEqual(result['unique_one_loop_pairs'], 0)
        self.assertEqual(result['unpaired_tracker_purchases'], 2)

    def test_duplicate_selection_key_is_ambiguous(self):
        result = audit_talent_choices([selection(), selection(index=20)], tracker())
        self.assertEqual(result['unique_one_loop_pairs'], 0)
        self.assertEqual(result['unpaired_selection_events'], 2)

    def test_user_plus_one_is_not_assumed(self):
        result = audit_talent_choices([selection(user=2)], tracker())
        self.assertEqual(result['selection_events_user_unmapped'], 1)
        self.assertEqual(result['unique_one_loop_pairs'], 0)

    def test_future_setup_or_hero_cannot_backfill_selection(self):
        track = tracker(); track[0]['_gameloop'] = 12
        self.assertEqual(audit_talent_choices([selection()], track)['selection_events_user_unmapped'], 1)
        track = tracker(); track[1]['_gameloop'] = 12
        result = audit_talent_choices([selection()], track)
        self.assertEqual(result['mapped_selections_without_prior_hero'], 1)
        self.assertEqual(result['unique_one_loop_pairs'], 0)

    def test_ambiguous_setup_or_conflicting_hero_rejected(self):
        for extra in (setup(), setup(9, 3), setup(8, 4), stat(b'PlayerSpawned', b'HeroGreymane', 1)):
            with self.assertRaises(ValueError):
                audit_talent_choices([selection()], tracker() + [extra])

    def test_duplicate_stat_keys_rejected(self):
        track = tracker(); track[-1]['m_intData'].append({'m_key': b'PlayerID', 'm_value': 4})
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            audit_talent_choices([selection()], track)

    def test_bounds_types_and_extra_selection_fields_rejected(self):
        for index in (-1, 1 << 32, True, '15'):
            with self.assertRaises(ValueError):
                audit_talent_choices([selection(index=index)], tracker())
        event = selection(); event['m_guessedTier'] = 4
        with self.assertRaises(ValueError):
            audit_talent_choices([event], tracker())

    def test_identifier_validation_and_missing_hero(self):
        track = tracker(); track[-1]['m_stringData'][0]['m_value'] = b'private name with spaces'
        with self.assertRaises(ValueError):
            audit_talent_choices([selection()], track)
        result = audit_talent_choices([selection()], [tracker()[0], tracker()[-1]])
        self.assertEqual(result['unique_one_loop_pairs'], 0)
        self.assertEqual(result['mapped_selections_without_prior_hero'], 1)

    def test_comparison_preserves_conflicts_and_does_not_infer_replacement_index(self):
        source_track = tracker(); source_track[-1]['m_stringData'][0]['m_value'] = b'KaelthasLivingBombSunKingsFury'
        source = audit_talent_choices([selection()], source_track)
        target = audit_talent_choices([selection(), selection(tick=20, index=20)], tracker() + [stat(tick=21)])
        rows = compare_observed_names(source, target)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['index'], 15)
        self.assertFalse(rows[0]['name_sets_equal'])
        self.assertEqual(rows[0]['target_purchase_names'], ['KaelthasLivingBombIgnite'])
        self.assertFalse(source['index_semantics_or_rule_equivalence_proven'])


if __name__ == '__main__':
    unittest.main()
