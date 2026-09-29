from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import runtime_catalog_journal as journal


def recording(units=None, abilities=None, session='11_22'):
    units = units if units is not None else [('HeroAnubarak', 1), ('', 0), ('HeroGreymane', 1)]
    abilities = abilities if abilities is not None else [('Move', 1), ('Attack', 1)]
    rows = [f'BEGIN|{journal.BUILD}|{journal.MAP_SHA256}', f'COUNT|Unit|46|{len(units)}', f'COUNT|Abil|0|{len(abilities)}']
    for label, items in [('Unit', units), ('Abil', abilities)]:
        rows += [f'ENTRY|{label}|{i}|{valid}|{len(name)}|{name}' for i, (name, valid) in enumerate(items, 1)]
        rows += [f'DONE|{label}|{len(items)}']
    rows += [f'END|{len(units)}|{len(abilities)}']
    return ('\n'.join(f'{journal.TOKEN}|{session}|{r}' for r in rows) + '\n').encode()


class JournalTests(unittest.TestCase):
    def parse(self, raw=None):
        return journal.parse_journal(raw or recording(), {'HeroAnubarak': 1, 'HeroGreymane': 3})

    def rejects(self, raw):
        with self.assertRaises(ValueError):
            self.parse(raw)

    def test_complete_log_preserves_native_indices_and_empty_slot(self):
        result = self.parse()
        self.assertEqual([r['index'] for r in result['catalogs']['Unit']], [1, 2, 3])
        self.assertEqual(result['catalogs']['Unit'][1], {'index': 2, 'id': '', 'valid': False})
        self.assertTrue(result['all_unit_anchors_match'])
        self.assertEqual(result['records'], 11)

    def test_no_runtime_or_playback_claim_even_with_matching_anchors(self):
        result = self.parse()
        for key in ('actual_build_verified', 'evidence_is_authenticated', 'ready_for_unit_catalog_review', 'client_playback_validated', 'automatically_applied_to_replay', 'ability_indices_independently_validated'):
            self.assertIs(result[key], False)

    def test_missing_anchors_are_reported_not_invented(self):
        result = journal.parse_journal(recording(), {'NotInRuntime': 99})
        self.assertFalse(result['all_unit_anchors_match'])
        self.assertEqual(result['anchor_mismatches'][0]['observed_index'], None)

    def test_invalid_entry_not_used_as_anchor(self):
        result = journal.parse_journal(recording([('HeroAnubarak', 0)]), {'HeroAnubarak': 1})
        self.assertFalse(result['all_unit_anchors_match'])

    def test_prefix_and_unrelated_lines(self):
        raw = ('unrelated engine line\n' + ''.join('12:00:01.001 ' + line + '\n' for line in recording().decode().splitlines())).encode()
        self.assertTrue(self.parse(raw)['complete_sequence'])

    def test_bom_and_crlf(self):
        self.assertTrue(self.parse(b'\xef\xbb\xbf' + recording().replace(b'\n', b'\r\n'))['complete_sequence'])

    def test_every_missing_record_is_rejected(self):
        lines = recording().splitlines(True)
        for i in range(len(lines)):
            with self.subTest(i=i):
                self.rejects(b''.join(lines[:i] + lines[i + 1:]))

    def test_every_duplicate_record_is_rejected(self):
        lines = recording().splitlines(True)
        for i in range(len(lines)):
            with self.subTest(i=i):
                self.rejects(b''.join(lines[:i] + [lines[i]] + lines[i:]))

    def test_swapped_entry_order(self):
        lines = recording().splitlines(True)
        lines[3], lines[4] = lines[4], lines[3]
        self.rejects(b''.join(lines))

    def test_mixed_sessions(self):
        self.rejects(recording().replace(b'11_22|ENTRY', b'11_23|ENTRY', 1))

    def test_appended_second_session(self):
        self.rejects(recording() + recording(session='23_24'))

    def test_wrong_build(self):
        self.rejects(recording().replace(b'BEGIN|98285', b'BEGIN|98297'))

    def test_wrong_map(self):
        self.rejects(recording().replace(journal.MAP_SHA256.encode(), b'0' * 64))

    def test_count_mismatch(self):
        self.rejects(recording().replace(b'COUNT|Unit|46|3', b'COUNT|Unit|46|4'))

    def test_zero_and_excessive_counts(self):
        for count in (0, journal.MAX_ENTRIES + 1):
            self.rejects(recording().replace(b'COUNT|Unit|46|3', f'COUNT|Unit|46|{count}'.encode()))

    def test_duplicate_native_catalog(self):
        self.rejects(recording().replace(b'COUNT|Abil|0|2', b'COUNT|Abil|46|2'))

    def test_duplicate_names(self):
        self.rejects(recording([('X', 1), ('X', 1)]))

    def test_name_length_mismatch(self):
        self.rejects(recording().replace(b'|12|HeroAnubarak', b'|13|HeroAnubarak'))

    def test_delimiters_and_nonascii_rejected(self):
        for name in ('x|y', 'a\tb', 'a\nb', 'zażółć', 'x' * 241):
            with self.subTest(name=name):
                self.rejects(recording([(name, 1)]))

    def test_noncanonical_numbers(self):
        for value in ('01', '-1', '1.0', 'True', '100000000000000'):
            self.rejects(recording().replace(b'ENTRY|Unit|1|1', f'ENTRY|Unit|{value}|1'.encode()))

    def test_validity_flag(self):
        self.rejects(recording().replace(b'ENTRY|Unit|1|1', b'ENTRY|Unit|1|2'))

    def test_failure_record(self):
        self.rejects(recording().replace(b'DONE|Unit|3', b'FAIL|catalog_count_out_of_range'))

    def test_ambiguous_marker(self):
        self.rejects(journal.TOKEN.encode() + recording())

    def test_truncated_final_line(self):
        self.rejects(recording()[:-1])

    def test_raw_input_bounds_and_encoding(self):
        for raw in (b'', b'x' * (journal.MAX_BYTES + 1), b'\xff\n', ('x' * 2049 + '\n').encode()):
            with self.assertRaises((ValueError, UnicodeError)):
                journal.parse_journal(raw, {'X': 1})

    def test_invalid_anchor_inputs(self):
        for anchors in ({}, {'X': True}, {'X': 0}, {'X': journal.MAX_ENTRIES + 1}, {'': 1}):
            with self.assertRaises(ValueError):
                journal.parse_journal(recording(), anchors)

    def test_nonce_bounds(self):
        for session in ('0_1', '01_2', '1073741824_1', '1_-1', 'x_y'):
            self.rejects(recording(session=session))

    def test_full_pinned_anchor_fixture_keeps_unverified_scope(self):
        anchors = json.loads((Path(__file__).parent / 'observations/runtime-catalog-reference-anchors.json').read_text())['unit_anchors']
        units = [('', 0)] * max(anchors.values())
        for name, index in anchors.items():
            units[index - 1] = (name, 1)
        result = journal.parse_journal(recording(units), anchors)
        self.assertEqual(result['reference_anchor_count'], 48)
        self.assertTrue(result['all_unit_anchors_match'])
        self.assertFalse(result['ready_for_unit_catalog_review'])

    def test_repeated_reports_are_identical(self):
        self.assertEqual(self.parse(), self.parse())

    def test_all_supported_identifier_characters(self):
        self.assertTrue(journal.parse_journal(recording([('a_@.#:+-9', 1)]), {'a_@.#:+-9': 1})['all_unit_anchors_match'])


class GeneratorTests(unittest.TestCase):
    ORIGINAL = b'void InitMap () { InitLibs(); InitGlobals(); InitTriggers(); }\n'

    def test_original_initialization_retained(self):
        result = journal.instrument(self.ORIGINAL).decode()
        self.assertIn('void HRCJ_OriginalInitMap () { InitLibs(); InitGlobals(); InitTriggers(); }', result)
        self.assertEqual(result.count('void InitMap'), 1)
        self.assertIn('HRCJ_OriginalInitMap();', result)

    def test_nonmatching_hooks_rejected(self):
        for raw in (b'', self.ORIGINAL + b'void InitMap() {}', b'void InitMap() { Other(); }', journal.instrument(self.ORIGINAL)):
            with self.assertRaises(ValueError):
                journal.instrument(raw)

    def test_no_bank_api_is_called(self):
        self.assertNotIn('Bank', journal.galaxy_source())
        self.assertIn('TriggerDebugSetTypeFile', journal.galaxy_source())

    def test_bounded_batch_and_terminal_trigger_disable(self):
        source = journal.galaxy_source()
        self.assertIn('budget < 64', source)
        self.assertEqual(source.count('TriggerEnable(HRCJ_Trigger, false)'), 2)
        self.assertIn('TriggerAddEventTimePeriodic', source)
        self.assertNotIn('@TOKEN@', source)

    def test_entry_index_not_renumbered(self):
        self.assertIn('CatalogEntryGet(catalog, HRCJ_Index)', journal.galaxy_source())
        self.assertIn('IntToString(HRCJ_Index)', journal.galaxy_source())

    def test_wrong_source_rejected_before_loading_native_library(self):
        with tempfile.TemporaryDirectory() as temporary:
            p = Path(temporary) / 'map'
            p.write_bytes(b'wrong')
            with patch.object(journal, 'Storm') as native:
                with self.assertRaises(ValueError):
                    journal.build(p, Path(temporary) / 'out')
                native.assert_not_called()


if __name__ == '__main__':
    unittest.main()
