from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from catalog_diagnostics import PREFIX, UnitTimeline, analyze, commands, compare_initial, inventory, link_fields, propose_mapping


def tag(index=1, recycle=1):
    return index << 22 | recycle


def unit(kind='SUnitBornEvent', loop=0, index=1, recycle=1, name=b'HeroA', x=10, y=20):
    return {'_event': PREFIX + kind, '_gameloop': loop, 'm_unitTagIndex': index,
            'm_unitTagRecycle': recycle, 'm_unitTypeName': name,
            'm_controlPlayerId': 1, 'm_upkeepPlayerId': 1, 'm_x': x, 'm_y': y}


def selection(loop=2, link=100, tags=None, groups=None):
    tags = [tag()] if tags is None else tags
    groups = [{'m_count': len(tags), 'm_unitLink': link}] if groups is None else groups
    return {'_event': 'NNet.Game.SSelectionDeltaEvent', '_gameloop': loop,
            'm_delta': {'m_addUnitTags': tags, 'm_addSubgroups': groups}}


def table(*rows):
    return {'entries': [{'unit_type': name, 'links': [{'link': link} for link in links]} for name, links in rows]}


class TimelineTests(unittest.TestCase):
    def test_resolves_only_preceding_alive_type(self):
        line = UnitTimeline([unit(loop=1)])
        self.assertEqual(line.lookup(tag(), 2), ('HeroA', 'known_alive'))
        self.assertEqual(line.lookup(tag(), 0), (None, 'no_prior_identity'))

    def test_birth_same_tick_not_assumed_preceding(self):
        self.assertEqual(UnitTimeline([unit(loop=1)]).lookup(tag(), 1), (None, 'same_tick_transition'))

    def test_dead_snapshot_is_not_catalog_evidence(self):
        line = UnitTimeline([unit(), unit('SUnitDiedEvent', 2)])
        self.assertEqual(line.lookup(tag(), 3), (None, 'dead_or_unknown'))

    def test_morph_uses_temporal_type(self):
        line = UnitTimeline([unit(), unit('SUnitTypeChangeEvent', 3, name=b'HeroB')])
        self.assertEqual(line.lookup(tag(), 2)[0], 'HeroA')
        self.assertEqual(line.lookup(tag(), 3)[1], 'same_tick_transition')
        self.assertEqual(line.lookup(tag(), 4)[0], 'HeroB')

    def test_future_morph_not_used(self):
        line = UnitTimeline([unit(), unit('SUnitTypeChangeEvent', 100, name=b'HeroB')])
        self.assertEqual(line.lookup(tag(), 90)[0], 'HeroA')

    def test_recycle_values_separate_lifetimes(self):
        line = UnitTimeline([unit(), unit('SUnitDiedEvent', 2), unit(loop=3, recycle=2, name=b'HeroB')])
        self.assertEqual(line.lookup(tag(), 5)[0], None)
        self.assertEqual(line.lookup(tag(recycle=2), 5)[0], 'HeroB')

    def test_revived_unit_keeps_known_type(self):
        line = UnitTimeline([unit(), unit('SUnitDiedEvent', 2), unit('SUnitRevivedEvent', 4)])
        self.assertEqual(line.lookup(tag(), 5)[0], 'HeroA')

    def test_revive_without_identity_remains_unknown(self):
        line = UnitTimeline([unit('SUnitRevivedEvent', 4)])
        self.assertEqual(line.lookup(tag(), 5), (None, 'dead_or_unknown'))

    def test_sentinels_do_not_become_units(self):
        line = UnitTimeline([unit()])
        for value in (0, 0xffffffff):
            self.assertEqual(line.lookup(value, 10)[1], 'sentinel')

    def test_chronology_and_integer_types_are_checked(self):
        for events in ([unit(loop=2), unit(loop=1)], [unit(loop=True)], [unit(index=True)]):
            with self.assertRaises(ValueError):
                UnitTimeline(events)

    def test_empty_or_nonbinary_type_is_rejected(self):
        for name in (b'', 'HeroA', b'a' * 257):
            with self.assertRaises(ValueError):
                UnitTimeline([unit(name=name)])


class FieldTests(unittest.TestCase):
    def test_selection_subgroups_are_joined_by_counts(self):
        event = selection(tags=[tag(), tag(2), tag(3)], groups=[{'m_count': 2, 'm_unitLink': 100}, {'m_count': 1, 'm_unitLink': 101}])
        rows = list(link_fields([event]))
        self.assertEqual([row.tags for row in rows], [(tag(), tag(2)), (tag(3),)])
        self.assertEqual(rows[1].path, ('m_delta', 'm_addSubgroups', 1, 'm_unitLink'))

    def test_group_count_mismatch_fails_closed(self):
        for count in (0, 2, True, -1):
            with self.assertRaises(ValueError):
                list(link_fields([selection(groups=[{'m_count': count, 'm_unitLink': 100}])]))

    def test_unassigned_tag_is_rejected(self):
        with self.assertRaises(ValueError):
            list(link_fields([selection(groups=[])]))

    def test_link_width_is_checked(self):
        for value in (-1, True, 65536):
            with self.assertRaises(ValueError):
                list(link_fields([selection(link=value)]))

    def test_only_allowlisted_target_fields_are_read(self):
        target = {'m_snapshotUnitLink': 30, 'm_tag': tag()}
        events = [{'_event': 'NNet.Game.SCmdEvent', '_gameloop': 2, 'm_data': {'TargetUnit': target}},
                  {'_event': 'NNet.Game.SCmdUpdateTargetUnitEvent', '_gameloop': 3, 'm_target': target},
                  {'_event': 'NNet.Game.Other', '_gameloop': 4, 'm_target': target}]
        self.assertEqual(len(list(link_fields(events))), 2)

    def test_conflicting_group_types_are_excluded(self):
        result = inventory([selection(tags=[tag(), tag(2)])], [unit(), unit(index=2, name=b'HeroB')])
        self.assertEqual(result['fields_classified'], 0)
        self.assertEqual(result['early_fields'][0]['classification'], 'mixed_unit_types_in_subgroup')

    def test_unique_instance_counts_and_input_preservation(self):
        game = [selection(), selection(3)]
        tracker = [unit()]
        before = copy.deepcopy((game, tracker))
        result = inventory(game, tracker)
        self.assertEqual(result['entries'][0]['links'][0], {'link': 100, 'fields': 2, 'distinct_unit_instances': 1})
        self.assertEqual((game, tracker), before)

    def test_same_tick_unknown_and_dead_are_not_evidence(self):
        result = inventory([selection(0), selection(2)], [unit(), unit('SUnitDiedEvent', 1)])
        self.assertEqual(result['entries'], [])
        self.assertEqual(sum(result['excluded_fields'].values()), 2)


class MappingTests(unittest.TestCase):
    def test_unique_observed_pair_is_only_a_proposal(self):
        value = propose_mapping(table(('HeroA', [100])), [table(('HeroA', [50]))])
        self.assertEqual(value['observed_pairs'], [{'unit_type': 'HeroA', 'before': 100, 'after': 50}])
        self.assertFalse(value['automatically_applied'])
        self.assertFalse(value['cross_map_catalog_independence_proven'])

    def test_reference_disagreement_is_not_voted_away(self):
        value = propose_mapping(table(('HeroA', [100])), [table(('HeroA', [50])), table(('HeroA', [51]))])
        self.assertEqual(value['observed_pairs'], [])
        self.assertEqual(value['unresolved'][0]['reason'], 'ambiguous_type_to_link')

    def test_collisions_in_either_direction_are_rejected(self):
        for source, references in ((table(('HeroA', [100]), ('HeroB', [100])), [table(('HeroA', [50]))]),
                                   (table(('HeroA', [100])), [table(('HeroA', [50]), ('HeroB', [50]))])):
            value = propose_mapping(source, references)
            self.assertEqual(value['observed_pairs'], [])

    def test_missing_target_is_explicit(self):
        value = propose_mapping(table(('HeroA', [100])), [table(('HeroB', [50]))])
        self.assertEqual(value['unresolved'][0]['reason'], 'not_observed_in_current_references')


class InitialAndCommandTests(unittest.TestCase):
    def test_initial_matching_uses_type_owner_and_position(self):
        result = compare_initial([unit(index=10), unit(index=20, x=30)], [unit(index=9), unit(index=15, x=30)])
        self.assertEqual(result['index_offset_counts'], {'-1': 1, '-5': 1})
        self.assertFalse(result['runtime_mapping_proven'])

    def test_ambiguous_object_matches_not_assigned(self):
        result = compare_initial([unit(index=1), unit(index=2)], [unit(index=3)])
        self.assertEqual(result['exact_unique_matches'], [])
        self.assertEqual(len(result['ambiguous_matches']), 1)

    def test_relocated_objects_remain_unmatched(self):
        result = compare_initial([unit(x=10)], [unit(x=11)])
        self.assertEqual(len(result['source_only']), 1)
        self.assertEqual(len(result['reference_only']), 1)

    def test_later_spawns_not_used_as_initial_state(self):
        with self.assertRaises(ValueError):
            compare_initial([unit(loop=1)], [unit()])

    def test_command_shapes_do_not_prove_flag_semantics(self):
        event = {'_event': 'NNet.Game.SCmdEvent', '_gameloop': 61, 'm_cmdFlags': 0x100108,
                 'm_abil': None, 'm_data': {'TargetPoint': {}}}
        before = copy.deepcopy(event)
        result = commands([event])
        self.assertEqual(result['implicit_target_point_flags'], {'0x100108': 1})
        self.assertFalse(result['ability_or_flag_mapping_applied'])
        self.assertEqual(event, before)

    def test_wrong_replay_digest_prevents_decode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.StormReplay'
            path.write_bytes(b'not a replay')
            with patch('catalog_diagnostics.inspect_reference') as read:
                with self.assertRaises(ValueError):
                    analyze(path, [])
                read.assert_not_called()


if __name__ == '__main__':
    unittest.main()
