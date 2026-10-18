"""Focused wire-format and output-safety regressions with fixed synthetic goldens.

These tiny, explicitly synthetic members cover both supported choices, optional
metadata, nonzero unknown fields, alignment changes and an opaque binary suffix.
They are not game recordings or evidence of playback.
"""
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import battlelobby_attribute_layer as layer

LEGACY = bytes.fromhex(
 '010943616368655c6f6e650173326d6145552020000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f'
 '01000001f3010005df015206172774ff000041014d22d3eadbeebfee1f2354aec2e8633110e11405551539000003e7000001f4004a0eadad4eee0cad268d108d159e00090003c02b00000f270000073401483ab6b7009ee0ca6e0000a35e6f78010080008100000000000000000000000000000901000001f3010005df010500010900003e0700001f040001'
 '0173326d7645552020000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f612b72aa130173326d6c45552020000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f4f504151554500ff835441494c')
MODERN = bytes.fromhex(
 '010943616368655c6f6e650173326d6145552020000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f'
 '01000001f3010005df0142830b9374ff800001112652c3f56df7aff70f91b4576174633210702902aa5531010001f3010000fa004243ab6b4e7b832b2e23142345670811001100d4030000f90300007d004221d5b52e40f706560e0000abf37bc0010020810000000000000000000000000000000902000007670000173f010280000900003e0700001f040001'
 '0173326d7645552020000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f612b72aa130173326d6c45552020000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f4f504151554500ff835441494c')


class LayerTests(unittest.TestCase):
    def setUp(self):
        self.model = layer.decode_layer(LEGACY, 'legacy-10')

    def changed(self, path, value):
        return replace(self.model, tokens=tuple(replace(t, value=value) if t.path == path else t for t in self.model.tokens))

    def test_fixed_goldens_decode_known_values_and_choices(self):
        for raw, profile in ((LEGACY, 'legacy-10'), (MODERN, 'observed-11')):
            model = layer.decode_layer(raw, profile)
            self.assertEqual([a.identifier for a in model.attributes], [3007, 500])
            self.assertEqual(model.attributes[0].values, (int.from_bytes(b'Part', 'big'), int.from_bytes(b'Watc', 'big')))
            self.assertEqual(model.attributes[0].default_choice, layer.Choice(1, ((1, 1), (0, 0))))
            self.assertEqual(model.selections[0].choice, layer.Choice(1, ((0, 1), (1, 1))))
            self.assertEqual(model.selections[1].choice, layer.Choice(0, ((1, 0),)))
            self.assertEqual(layer.encode_layer(model, profile), raw)

    def test_forward_matches_fixed_modern_golden(self):
        raw, report = layer.transcode_member(LEGACY, 'legacy-10', 'observed-11')
        self.assertEqual(raw, MODERN)
        self.assertTrue(report['inverse_roundtrip_exact'])
        self.assertTrue(report['numeric_values_and_flags_preserved'])
        self.assertTrue(all(c['after_bits'] == c['before_bits'] + 1 for c in report['changes']))

    def test_reverse_recovers_frozen_legacy_golden(self):
        raw, _ = layer.transcode_member(MODERN, 'observed-11', 'legacy-10')
        self.assertEqual(raw, LEGACY)

    def test_unknowns_nan_bits_and_optional_metadata_are_preserved(self):
        values = {t.path: t.value for t in self.model.tokens}
        self.assertEqual(values['/attributes/0/values/0/first/f32_bits'], 0x7fc00001)
        self.assertEqual(values['/attributes/0/values/0/extra/unknown32'], 0xdeadbeef)
        self.assertEqual(values['/selected_attributes/unknown127'], (1 << 126) | 9)
        transformed = layer.decode_layer(MODERN, 'observed-11')
        self.assertEqual(self.model.tokens, transformed.tokens)

    def test_opaque_suffix_is_not_parsed_or_replaced(self):
        suffix = b'\0\xffOPAQUE\xff\0'
        boundary = dict(self.model.boundaries)['locale_handles_end'] // 8
        modified = LEGACY[:boundary] + suffix
        raw, report = layer.transcode_member(modified, 'legacy-10', 'observed-11')
        self.assertEqual(layer.decode_layer(raw, 'observed-11').opaque_suffix, suffix)
        self.assertEqual(report['source']['opaque_suffix_sha256'], layer.digest(suffix))

    def test_wrong_profile_is_rejected(self):
        with self.assertRaises(layer.LayerError):
            layer.decode_layer(LEGACY, 'observed-11')

    def test_unsupported_profile_is_rejected(self):
        for profile in ('98348', 'auto', None):
            with self.assertRaises(layer.LayerError):
                layer.decode_layer(LEGACY, profile)

    def test_truncation_in_prefix_attributes_and_locales_is_rejected(self):
        for length in (20, 100, 270):
            with self.subTest(length=length), self.assertRaises(layer.LayerError):
                layer.decode_layer(LEGACY[:length], 'legacy-10')

    def test_nonzero_alignment_padding_is_rejected(self):
        raw = bytearray(LEGACY)
        raw[11] |= 1 << 6  # two padding bits after the dependency handle count
        with self.assertRaisesRegex(layer.LayerError, 'padding'):
            layer.decode_layer(bytes(raw), 'legacy-10')

    def test_unsupported_choice_is_rejected(self):
        raw = layer.encode_layer(self.changed('/attributes/0/default_choice/tag', 2), 'legacy-10')
        with self.assertRaisesRegex(layer.LayerError, 'choice tag'):
            layer.decode_layer(raw, 'legacy-10')

    def test_selection_index_out_of_bounds_is_rejected_even_when_unset(self):
        raw = layer.encode_layer(self.changed('/selected_attributes/1/choice/0/index', 2), 'legacy-10')
        with self.assertRaisesRegex(layer.LayerError, 'outside its value table'):
            layer.decode_layer(raw, 'legacy-10')

    def test_duplicate_selection_is_rejected(self):
        raw = layer.encode_layer(self.changed('/selected_attributes/1/id', 3007), 'legacy-10')
        with self.assertRaisesRegex(layer.LayerError, 'duplicate selected'):
            layer.decode_layer(raw, 'legacy-10')

    def test_selection_count_mismatch_is_rejected(self):
        raw = layer.encode_layer(self.changed('/selected_attributes/count', 1), 'legacy-10')
        with self.assertRaisesRegex(layer.LayerError, 'counts disagree'):
            layer.decode_layer(raw, 'legacy-10')

    def test_narrowing_never_silently_truncates(self):
        model = layer.decode_layer(MODERN, 'observed-11')
        model = replace(model, tokens=tuple(replace(t, value=1024) if t.kind == 'index' else t for t in model.tokens))
        with self.assertRaisesRegex(layer.LayerError, 'without truncation'):
            layer.encode_layer(model, 'legacy-10')

    def test_budgets_bound_valid_but_large_inputs(self):
        for setting, limit in (('MAX_MEMBER_BYTES', 100), ('MAX_TOTAL_VALUES', 3), ('MAX_TOKENS', 20)):
            with self.subTest(setting=setting), patch.object(layer, setting, limit), self.assertRaises(layer.LayerError):
                layer.decode_layer(LEGACY, 'legacy-10')

    def test_attribute_crosscheck_matches_independent_expected_scopes(self):
        expected = {'scopes': {1: {3007: [{'namespace': 999, 'value': b'Part'}]},
                               2: {3007: [{'namespace': 999, 'value': b'Watc'}]},
                               16: {500: [{'namespace': 999, 'value': b'Open'}]}}}
        self.assertEqual(layer.crosscheck_attributes(self.model, expected)['values_matched'], 3)
        expected['scopes'][2][3007][0]['value'] = b'Part'
        with self.assertRaisesRegex(layer.LayerError, 'disagrees'):
            layer.crosscheck_attributes(self.model, expected)

    def test_empty_crosscheck_does_not_pass(self):
        with self.assertRaisesRegex(layer.LayerError, 'empty'):
            layer.crosscheck_attributes(self.model, {'scopes': {}})

    def test_new_output_guard_preserves_existing_files_and_refuses_replays(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'existing.bin'
            p.write_bytes(b'preserve')
            with self.assertRaises(FileExistsError):
                layer._write_new(p, MODERN)
            self.assertEqual(p.read_bytes(), b'preserve')
            with self.assertRaises(layer.LayerError):
                layer._write_new(Path(folder) / 'never.StormReplay', MODERN)

    def test_cli_preflights_report_before_creating_member(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            member, report, output = root / 'source.bin', root / 'existing.json', root / 'new.bin'
            member.write_bytes(LEGACY)
            report.write_text('preserve')
            command = [sys.executable, '-B', str(Path(layer.__file__)), 'transcode-member', str(member),
                       '--source-profile', 'legacy-10', '--target-profile', 'observed-11',
                       '--output', str(output), '--report', str(report)]
            result = subprocess.run(command, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())
            self.assertEqual(report.read_text(), 'preserve')

    def test_cli_missing_report_parent_fails_before_member_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            member = root / 'source.bin'
            report, output = root / 'missing' / 'report.json', root / 'new.bin'
            member.write_bytes(LEGACY)
            command = [sys.executable, '-B', str(Path(layer.__file__)), 'transcode-member', str(member),
                       '--source-profile', 'legacy-10', '--target-profile', 'observed-11',
                       '--output', str(output), '--report', str(report)]
            result = subprocess.run(command, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'Output parent must be an existing directory', result.stderr)
            self.assertFalse(output.exists())
            self.assertFalse(report.exists())
            self.assertEqual(member.read_bytes(), LEGACY)

    def test_cli_missing_member_parent_fails_before_report_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            member = root / 'source.bin'
            report, output = root / 'report.json', root / 'missing' / 'new.bin'
            member.write_bytes(LEGACY)
            command = [sys.executable, '-B', str(Path(layer.__file__)), 'transcode-member', str(member),
                       '--source-profile', 'legacy-10', '--target-profile', 'observed-11',
                       '--output', str(output), '--report', str(report)]
            result = subprocess.run(command, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'Output parent must be an existing directory', result.stderr)
            self.assertFalse(output.exists())
            self.assertFalse(report.exists())
            self.assertEqual(member.read_bytes(), LEGACY)

    def test_cli_parent_file_is_rejected_before_either_output(self):
        for bad_parent_for in ('member', 'report'):
            with self.subTest(output=bad_parent_for), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                member, parent_file = root / 'source.bin', root / 'not-a-directory'
                member.write_bytes(LEGACY)
                parent_file.write_bytes(b'preserve-parent-file')
                output = parent_file / 'new.bin' if bad_parent_for == 'member' else root / 'new.bin'
                report = parent_file / 'report.json' if bad_parent_for == 'report' else root / 'report.json'
                command = [sys.executable, '-B', str(Path(layer.__file__)), 'transcode-member', str(member),
                           '--source-profile', 'legacy-10', '--target-profile', 'observed-11',
                           '--output', str(output), '--report', str(report)]
                result = subprocess.run(command, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'Output parent must be an existing directory', result.stderr)
                self.assertFalse(output.exists())
                self.assertFalse(report.exists())
                self.assertEqual(member.read_bytes(), LEGACY)
                self.assertEqual(parent_file.read_bytes(), b'preserve-parent-file')

    def test_cli_outputs_member_and_audit_without_playback_claim(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            member, report, output = root / 'source.bin', root / 'report.json', root / 'new.bin'
            member.write_bytes(LEGACY)
            command = [sys.executable, '-B', str(Path(layer.__file__)), 'transcode-member', str(member),
                       '--source-profile', 'legacy-10', '--target-profile', 'observed-11',
                       '--output', str(output), '--report', str(report)]
            result = subprocess.run(command, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_bytes(), MODERN)
            evidence = json.loads(report.read_text())
            self.assertFalse(evidence['client_playback_validated'])
            self.assertFalse(evidence['replay_created'])


if __name__ == '__main__':
    unittest.main()
