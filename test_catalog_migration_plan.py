import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import plan_catalog_migration as p


def born(index, name, loop=0, recycle=1):
    return {'_event': 'NNet.Replay.Tracker.SUnitBornEvent', '_gameloop': loop,
            'm_unitTagIndex': index, 'm_unitTagRecycle': recycle, 'm_unitTypeName': name.encode()}


def selection(index=173, link=807, loop=52, recycle=1):
    return {'_event': 'NNet.Game.SSelectionDeltaEvent', '_gameloop': loop,
            'm_delta': {'m_addSubgroups': [{'m_unitLink': link, 'm_count': 1}],
                        'm_addUnitTags': [(index << 18) | recycle]}}


def capture(rows=None):
    return {'ready_for_unit_catalog_review': True, 'blocking_checks': [], 'all_unit_anchors_match': True,
            'capture_zip_sha256': 'a' * 64,
            'catalogs': {'Unit': rows or [{'index': 1000, 'id': 'HeroGreymane', 'valid': True}]}}


class RequirementTests(unittest.TestCase):
    def setUp(self):
        self.game = [selection()]
        self.tracker = [born(173, 'HeroGreymane')]

    def req(self):
        return p.source_requirements(self.game, self.tracker)

    def test_original_tag_representation_is_used(self):
        row = self.req()['unit_links'][0]
        self.assertEqual((row['source_link'], row['source_names']), (807, ['HeroGreymane']))
        self.assertEqual(row['fields_through_loop_64'], 1)

    def test_mixed_names_are_not_majority_voted(self):
        self.game += [selection(174)] * 20
        self.tracker += [born(174, 'AnotherUnit')]
        row = self.req()['unit_links'][0]
        self.assertEqual(row['identity_status'], 'ambiguous_source_identity')
        self.assertEqual(row['source_names'], ['AnotherUnit', 'HeroGreymane'])

    def test_same_tick_spawn_does_not_establish_identity(self):
        self.tracker[0]['_gameloop'] = 52
        self.assertEqual(self.req()['unit_links'][0]['identity_status'], 'no_source_identity')

    def test_future_birth_is_not_used(self):
        self.tracker[0]['_gameloop'] = 53
        self.assertEqual(self.req()['unit_links'][0]['source_names'], [])

    def test_dead_identity_is_not_used(self):
        self.tracker.append({'_event': 'NNet.Replay.Tracker.SUnitDiedEvent', '_gameloop': 40,
                             'm_unitTagIndex': 173, 'm_unitTagRecycle': 1})
        self.assertEqual(self.req()['excluded_identity_fields'], {'dead_or_unknown': 1})

    def test_recycle_counter_must_match(self):
        self.tracker[0]['m_unitTagRecycle'] = 2
        self.assertEqual(self.req()['unit_links'][0]['source_names'], [])

    def test_inputs_are_not_mutated(self):
        before = copy.deepcopy((self.game, self.tracker))
        self.req()
        self.assertEqual(before, (self.game, self.tracker))

    def test_invalid_selection_count_rejected(self):
        self.game[0]['m_delta']['m_addSubgroups'][0]['m_count'] = 2
        with self.assertRaises(ValueError): self.req()

    def test_ability_inventory_retains_index_and_unknown_identity(self):
        self.game.append({'_event': 'NNet.Game.SCmdEvent', '_gameloop': 133,
                          'm_abil': {'m_abilLink': 548, 'm_abilCmdIndex': 0}, 'm_data': {}})
        row = self.req()['ability_links'][0]
        self.assertEqual((row['source_link'], row['first_gameloop']), (548, 133))
        self.assertIsNone(row['portable_name'])
        self.assertFalse(row['identity_established'])

    def test_implicit_commands_do_not_get_invented_abilities(self):
        self.game.append({'_event': 'NNet.Game.SCmdEvent', '_gameloop': 61, 'm_abil': None, 'm_data': {}})
        self.assertEqual(self.req()['command_events'], 1)
        self.assertEqual(self.req()['ability_links'], [])

    def test_boolean_ability_rejected(self):
        self.game.append({'_event': 'NNet.Game.SCmdEvent', '_gameloop': 133,
                          'm_abil': {'m_abilLink': True, 'm_abilCmdIndex': 0}, 'm_data': {}})
        with self.assertRaises(ValueError): self.req()

    def test_out_of_range_ability_rejected(self):
        self.game.append({'_event': 'NNet.Game.SCmdEvent', '_gameloop': 133,
                          'm_abil': {'m_abilLink': 65536, 'm_abilCmdIndex': 0}, 'm_data': {}})
        with self.assertRaises(ValueError): self.req()


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.req = p.source_requirements([selection()], [born(173, 'HeroGreymane')])

    def test_no_capture_never_uses_guessed_reference_numbers(self):
        result = p.propose(self.req, None)
        self.assertEqual(result['coverage']['reviewable_links'], 0)
        self.assertIsNone(result['unit_link_plan'][0]['target_link'])

    def test_synthetic_capture_builds_only_a_review_plan(self):
        result = p.propose(self.req, capture())
        self.assertEqual(result['unit_link_plan'][0]['target_link'], 1000)
        self.assertTrue(result['unit_plan_complete'])
        for key in ('replay_ready_for_playback', 'replay_modified', 'client_playback_validated',
                    'synchronization_checks_disabled'):
            self.assertIs(result[key], False)

    def test_context_blockers_prevent_mapping(self):
        value = capture()
        value['blocking_checks'] = ['wrong_build']
        self.assertEqual(p.propose(self.req, value)['coverage']['reviewable_links'], 0)

    def test_anchor_failure_prevents_mapping(self):
        value = capture()
        value['all_unit_anchors_match'] = False
        self.assertEqual(p.propose(self.req, value)['coverage']['reviewable_links'], 0)

    def test_unready_capture_prevents_mapping(self):
        value = capture()
        value['ready_for_unit_catalog_review'] = False
        self.assertEqual(p.propose(self.req, value)['coverage']['reviewable_links'], 0)

    def test_missing_name_is_not_zero_or_a_default(self):
        result = p.propose(self.req, capture([{'index': 20, 'id': 'Other', 'valid': True}]))
        self.assertEqual(result['unit_link_plan'][0]['status'], 'name_missing_or_invalid_in_runtime')
        self.assertIsNone(result['unit_link_plan'][0]['target_link'])

    def test_invalid_definition_is_not_promoted(self):
        result = p.propose(self.req, capture([{'index': 20, 'id': 'HeroGreymane', 'valid': False}]))
        self.assertEqual(result['coverage']['reviewable_links'], 0)

    def test_duplicate_target_name_is_rejected(self):
        value = capture([{'index': 20, 'id': 'HeroGreymane', 'valid': True},
                         {'index': 21, 'id': 'HeroGreymane', 'valid': True}])
        with self.assertRaises(ValueError): p.propose(self.req, value)

    def test_duplicate_target_index_is_rejected(self):
        value = capture([{'index': 20, 'id': 'HeroGreymane', 'valid': True},
                         {'index': 20, 'id': 'Other', 'valid': False}])
        with self.assertRaises(ValueError): p.propose(self.req, value)

    def test_boolean_target_index_rejected(self):
        with self.assertRaises(ValueError):
            p.propose(self.req, capture([{'index': True, 'id': 'HeroGreymane', 'valid': True}]))

    def test_source_conflict_stays_unresolved(self):
        self.req['unit_links'][0].update(identity_status='ambiguous_source_identity', source_names=['HeroGreymane', 'Other'])
        result = p.propose(self.req, capture())
        self.assertEqual(result['unit_link_plan'][0]['status'], 'ambiguous_source_identity')
        self.assertIsNone(result['unit_link_plan'][0]['target_link'])

    def test_abilities_do_not_map_by_equal_numbers(self):
        self.req['ability_links'] = [{'source_link': 10, 'commands': 1}]
        value = capture()
        value['catalogs']['Abil'] = [{'index': 10, 'id': 'SyntheticAbility', 'valid': True}]
        result = p.propose(self.req, value)
        self.assertEqual(result['coverage']['mapped_ability_links'], 0)
        self.assertIn('original_ability_link_names_not_established', result['blocking_checks'])

    def test_planning_does_not_mutate_requirements_or_capture(self):
        value = capture()
        before = copy.deepcopy((self.req, value))
        p.propose(self.req, value)
        self.assertEqual(before, (self.req, value))

    def test_zero_fields_do_not_claim_complete_catalog(self):
        self.req['unit_links'] = []
        self.assertFalse(p.propose(self.req, capture())['unit_plan_complete'])


class GuardTests(unittest.TestCase):
    def test_invalid_source_does_not_invoke_decoder(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'fake.StormReplay'
            path.write_bytes(b'not-the-original')
            with patch.object(p, 'MPQArchive') as parser:
                with self.assertRaises(ValueError): p.read_source(path)
                parser.assert_not_called()

    def test_directory_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError): p.read_source(Path(root))

    def test_existing_output_prevents_any_reads(self):
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / 'already.json'
            output.write_text('original')
            with patch('sys.argv', ['plan', '--source', 'missing', '--output', str(output)]):
                with patch.object(p, 'read_source') as source:
                    with self.assertRaises(FileExistsError): p.main()
                    source.assert_not_called()
            self.assertEqual(output.read_text(), 'original')


if __name__ == '__main__':
    unittest.main()
