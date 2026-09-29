import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import repair_unit_tags as tags


def pair(index=173, recycle=1):
    return {'m_unitTagIndex': index, 'm_unitTagRecycle': recycle}


def event(value=None):
    return {'_event': 'NNet.Game.SUnitClickEvent', '_gameloop': 52,
            'm_unitTag': tags.pack(173, 1, 18) if value is None else value}


class UnitTagTests(unittest.TestCase):
    def test_measured_source_tag(self):
        self.assertEqual(tags.components(45350913, 18), (173, 1))
        self.assertEqual(tags.pack(173, 1, 22), 725614593)

    def test_measurement_matches_modern_dragon_tag(self):
        self.assertEqual(tags.pack(170, 1, 22), 713031681)

    def test_components_roundtrip_at_boundaries(self):
        for shift in range(1, 32):
            for index, recycle in ((0, 0), ((1 << (32-shift))-1, (1 << shift)-1)):
                self.assertEqual(tags.components(tags.pack(index, recycle, shift), shift), (index, recycle))

    def test_invalid_integers_rejected(self):
        for value in (True, -1, 2**32, '1', None, 1.0):
            with self.subTest(value=value), self.assertRaises(ValueError):
                tags.components(value, 18)

    def test_invalid_shifts_rejected(self):
        for value in (True, 0, -1, 32, '22', None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                tags.pack(1, 1, value)

    def test_target_index_overflow_is_not_truncated(self):
        with self.assertRaises(ValueError):
            tags.pack(1024, 1, 22)

    def test_target_recycle_overflow_is_not_truncated(self):
        with self.assertRaises(ValueError):
            tags.pack(1, 2**22, 22)

    def test_infers_layout_from_tracker_not_declared_build(self):
        self.assertEqual(tags.infer_layout([event()], [pair()])['observed_shift'], 18)

    def test_unmatched_tag_rejected(self):
        with self.assertRaises(ValueError):
            tags.infer_layout([event()], [pair(999, 123)])

    def test_ambiguous_layout_rejected(self):
        with self.assertRaises(ValueError):
            tags.infer_layout([event(1)], [pair(0, 1)])

    def test_reports_ambiguity_without_claiming_unique_layout(self):
        value = tags.infer_layout([event(1)], [pair(0, 1)], require_unique=False)
        self.assertIsNone(value['observed_shift'])
        self.assertEqual(value['compatible_shifts'], list(range(1, 32)))

    def test_missing_tracker_rejected(self):
        with self.assertRaises(ValueError):
            tags.infer_layout([event()], [])

    def test_only_sentinels_rejected(self):
        with self.assertRaises(ValueError):
            tags.infer_layout([event(0), event(0xffffffff)], [pair()])

    def test_transform_preserves_both_components(self):
        output, changes = tags.transform([event()], [pair()], 18, 22)
        self.assertEqual(tags.components(output[0]['m_unitTag'], 22), (173, 1))
        self.assertEqual(changes[0]['gameloop'], 52)
        self.assertEqual(changes[0]['unit_index_preserved'], 173)

    def test_transform_is_reversible(self):
        source = [event()]
        output, _ = tags.transform(source, [pair()], 18, 22)
        restored, _ = tags.transform(output, [pair()], 22, 18)
        self.assertEqual(restored, source)

    def test_transform_does_not_modify_source(self):
        source = [event()]
        before = copy.deepcopy(source)
        tags.transform(source, [pair()], 18, 22)
        self.assertEqual(source, before)

    def test_sentinels_preserved(self):
        output, changes = tags.transform([event(), event(0), event(0xffffffff)], [pair()], 18, 22)
        self.assertEqual([e['m_unitTag'] for e in output[1:]], [0, 0xffffffff])
        self.assertEqual(len(changes), 1)

    def test_wrong_input_layout_rejected(self):
        with self.assertRaises(ValueError):
            tags.transform([event()], [pair()], 22, 18)

    def test_overflow_transform_rejected(self):
        with self.assertRaises(ValueError):
            tags.transform([event(tags.pack(1024, 1, 18))], [pair(1024)], 18, 22)

    def test_selection_tags_handled_without_catalog_changes(self):
        source = {'_event': 'NNet.Game.SSelectionDeltaEvent', '_gameloop': 52,
                  'm_delta': {'m_addUnitTags': [45350913], 'm_addSubgroups': [{'m_unitLink': 807}]}}
        output, _ = tags.transform([source], [pair()], 18, 22)
        self.assertEqual(output[0]['m_delta']['m_addUnitTags'], [725614593])
        self.assertEqual(output[0]['m_delta']['m_addSubgroups'], source['m_delta']['m_addSubgroups'])

    def test_commands_preserve_flags_ability_and_coordinates(self):
        source = {'_event': 'NNet.Game.SCmdEvent', '_gameloop': 61, 'm_cmdFlags': 1048840,
                  'm_abil': {'m_abilLink': 10}, 'm_otherUnit': 45350913,
                  'm_data': {'TargetUnit': {'m_tag': 45350913, 'm_snapshotUnitLink': 807, 'x': 100}}}
        output, changes = tags.transform([source], [pair()], 18, 22)
        expected = copy.deepcopy(source)
        expected['m_otherUnit'] = expected['m_data']['TargetUnit']['m_tag'] = 725614593
        self.assertEqual(output, [expected])
        self.assertEqual(len(changes), 2)

    def test_point_commands_do_not_acquire_tags(self):
        source = {'_event': 'NNet.Game.SCmdEvent', '_gameloop': 61, 'm_otherUnit': None,
                  'm_data': {'TargetPoint': {'x': 100, 'y': 200, 'z': 300}}}
        self.assertEqual(list(tags.references([source])), [])

    def test_unit_target_updates_rebound(self):
        source = {'_event': 'NNet.Game.SCmdUpdateTargetUnitEvent', '_gameloop': 62,
                  'm_target': {'m_tag': 45350913, 'm_snapshotUnitLink': 807}}
        output, _ = tags.transform([source], [pair()], 18, 22)
        self.assertEqual(output[0]['m_target']['m_tag'], 725614593)
        self.assertEqual(output[0]['m_target']['m_snapshotUnitLink'], 807)

    def test_group_and_unrelated_fields_not_treated_as_tags(self):
        self.assertEqual(list(tags.references([{'_event': 'NNet.Game.SCmdEvent', 'm_unitGroup': 10,
                                               'm_data': {'TargetPoint': {'x': 45350913}}}])), [])


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.observation = json.loads((Path(__file__).parent / 'observations/unit-tags-98285-2026-09-29.json').read_text())

    def test_real_references_jointly_identify_22_bits(self):
        tags.validate_observation(self.observation)

    def test_wrong_reference_rejected(self):
        self.observation['references'][0]['reference_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            tags.validate_observation(self.observation)

    def test_missing_reference_rejected(self):
        self.observation['references'].pop()
        with self.assertRaises(ValueError):
            tags.validate_observation(self.observation)

    def test_wrong_build_rejected(self):
        self.observation['references'][0]['declared_build'] = 98297
        with self.assertRaises(ValueError):
            tags.validate_observation(self.observation)

    def test_missing_roundtrip_rejected(self):
        self.observation['references'][0]['observed_payload_roundtrip'] = False
        with self.assertRaises(ValueError):
            tags.validate_observation(self.observation)

    def test_ambiguous_joint_evidence_rejected(self):
        for row in self.observation['references']:
            row['layout']['matching_references_by_shift']['23'] = row['layout']['non_sentinel_references']
        with self.assertRaises(ValueError):
            tags.validate_observation(self.observation)

    def test_empty_scores_rejected(self):
        self.observation['references'][0]['layout']['matching_references_by_shift'] = {}
        with self.assertRaises(ValueError):
            tags.validate_observation(self.observation)

    def test_invalid_score_counts_rejected(self):
        self.observation['references'][0]['layout']['matching_references_by_shift']['18'] = True
        with self.assertRaises(ValueError):
            tags.validate_observation(self.observation)

    def test_wrong_source_never_creates_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'wrong.StormReplay'
            source.write_bytes(b'bad')
            with self.assertRaises(ValueError):
                tags.repair(source, root / 'out', self.observation)
            self.assertFalse((root / 'out').exists())

    def test_existing_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileExistsError):
                tags.repair(Path('unused'), Path(directory), self.observation)

    def test_unknown_private_donor_rejected_before_inspection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'unknown.StormReplay'
            path.write_bytes(b'unknown')
            with patch.object(tags, 'inspect_reference') as inspect, self.assertRaises(ValueError):
                tags.observe([path])
            inspect.assert_not_called()


if __name__ == '__main__':
    unittest.main()
