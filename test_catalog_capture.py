import copy
import hashlib
import json
import stat
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

import import_catalog_capture as c
import runtime_catalog_probe as p
from test_runtime_catalog_probe import fixture, mutate


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.files = fixture()
        self.anchors = {'Unit1': 1, 'Unit2': 2}
        self.context = {
            'format': 'hots-runtime-probe-collection-v1', 'token': p.TOKEN, 'expected_build': p.BUILD,
            'map_sha256': c.PROBE_SHA256, 'launched_by_this_invocation': True,
            'launch_utc': '2026-09-29T13:00:00.0000000Z', 'graphics_log_fresh_for_launch': True,
            'observed_version_lines': ['GFX <Version> 2.57.0.98285', 'GFX <DataBuild> B98285',
                                       'GFX Heroes of the Storm (B98285)'],
            'export_contents_validated': False, 'runtime_catalog_context_validated': False,
            'client_playback_validated': False,
        }
        self.inventory()

    def inventory(self):
        self.context['input_banks'] = [{'name': n, 'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)}
                                       for n, b in sorted(self.files.items())]

    def archive(self, extra=None, raw_context=None, omit_context=False, compression=zipfile.ZIP_DEFLATED):
        path = self.root / 'capture.zip'
        with zipfile.ZipFile(path, 'w', compression) as z:
            for name, raw in self.files.items():
                z.writestr(name, raw)
            if not omit_context:
                z.writestr(c.CONTEXT_NAME, raw_context if raw_context is not None else json.dumps(self.context).encode())
            if extra:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    for name, raw in extra:
                        z.writestr(name, raw)
        return path

    def validate(self, **kwargs):
        return c.validate_capture(self.archive(**kwargs), self.anchors)

    def test_complete_synthetic_capture_only_allows_review(self):
        result = self.validate()
        self.assertTrue(result['ready_for_unit_catalog_review'])
        self.assertFalse(result['client_playback_validated'])
        self.assertFalse(result['actual_build_verified'])
        self.assertFalse(result['evidence_is_authenticated'])
        self.assertFalse(result['ability_indices_independently_validated'])
        self.assertFalse(result['automatically_applied_to_replay'])

    def test_digest_is_for_the_parsed_archive(self):
        path = self.archive()
        result = c.validate_capture(path, self.anchors)
        self.assertEqual(result['capture_zip_sha256'], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_collection_only_is_blocked(self):
        self.context.update(launched_by_this_invocation=False, graphics_log_fresh_for_launch=False, map_sha256=None)
        self.assertFalse(self.validate()['ready_for_unit_catalog_review'])

    def test_stale_log_is_blocked(self):
        self.context['graphics_log_fresh_for_launch'] = False
        self.assertIn('collector_did_not_observe_a_fresh_graphics_log', self.validate()['blocking_checks'])

    def test_wrong_map_is_blocked(self):
        self.context['map_sha256'] = '0' * 64
        self.assertIn('launched_map_digest_is_missing_or_different', self.validate()['blocking_checks'])

    def test_newer_version_is_not_silently_accepted(self):
        self.context['observed_version_lines'] = [line.replace('98285', '98297') for line in self.context['observed_version_lines']]
        self.assertFalse(self.validate()['ready_for_unit_catalog_review'])

    def test_missing_version_lines_block_review(self):
        self.context['observed_version_lines'] = []
        self.assertFalse(self.validate()['ready_for_unit_catalog_review'])

    def test_conflicting_version_lines_block_review(self):
        self.context['observed_version_lines'].append('GFX <Version> 2.57.0.98297')
        self.assertFalse(self.validate()['ready_for_unit_catalog_review'])

    def test_incomplete_version_tuple_blocked(self):
        self.context['observed_version_lines'][0] = 'GFX <Version> 98285'
        self.assertFalse(self.validate()['ready_for_unit_catalog_review'])

    def test_wrong_unit_anchor_blocks_review(self):
        self.anchors['Unit2'] = 3
        self.assertIn('runtime_unit_indices_do_not_match_reference_anchors', self.validate()['blocking_checks'])

    def test_unchanged_export_names_are_not_renumbered(self):
        result = self.validate()
        self.assertEqual(result['catalogs']['Unit'], [{'id': 'Unit1', 'index': 1, 'valid': True}, {'id': 'Unit2', 'index': 2, 'valid': True}])

    def test_missing_context_rejected(self):
        with self.assertRaises(ValueError):
            self.validate(omit_context=True)

    def test_duplicate_context_json_key_rejected(self):
        raw = json.dumps(self.context).replace('"expected_build": 98285', '"expected_build": 98285, "expected_build": 98285').encode()
        with self.assertRaises(ValueError):
            self.validate(raw_context=raw)

    def test_nonfinite_json_rejected(self):
        raw = json.dumps(self.context).replace('"expected_build": 98285', '"expected_build": NaN').encode()
        with self.assertRaises(ValueError):
            self.validate(raw_context=raw)

    def test_integer_instead_of_boolean_rejected(self):
        self.context['launched_by_this_invocation'] = 1
        with self.assertRaises(ValueError):
            self.validate()

    def test_unearned_collector_playback_claim_rejected(self):
        self.context['client_playback_validated'] = True
        with self.assertRaises(ValueError):
            self.validate()

    def test_wrong_context_token_rejected(self):
        self.context['token'] = 'OTHER'
        with self.assertRaises(ValueError):
            self.validate()

    def test_expected_build_boolean_rejected(self):
        self.context['expected_build'] = True
        with self.assertRaises(ValueError):
            self.validate()

    def test_timestamp_without_timezone_rejected(self):
        self.context['launch_utc'] = '2026-09-29T13:00:00'
        with self.assertRaises(ValueError):
            self.validate()

    def test_inventory_hash_mismatch_rejected(self):
        self.context['input_banks'][0]['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            self.validate()

    def test_inventory_byte_count_mismatch_rejected(self):
        self.context['input_banks'][0]['bytes'] += 1
        with self.assertRaises(ValueError):
            self.validate()

    def test_inventory_missing_row_rejected(self):
        self.context['input_banks'].pop()
        with self.assertRaises(ValueError):
            self.validate()

    def test_inventory_duplicate_rejected(self):
        self.context['input_banks'][1] = copy.deepcopy(self.context['input_banks'][0])
        with self.assertRaises(ValueError):
            self.validate()

    def test_traversal_member_rejected_without_extraction(self):
        with self.assertRaises(ValueError):
            self.validate(extra=[('../outside.txt', b'x')])
        self.assertFalse((self.root.parent / 'outside.txt').exists())

    def test_absolute_member_rejected(self):
        with self.assertRaises(ValueError):
            self.validate(extra=[('/absolute.txt', b'x')])

    def test_nested_member_rejected(self):
        with self.assertRaises(ValueError):
            self.validate(extra=[('folder/' + c.CONTEXT_NAME, b'x')])

    def test_unrelated_file_rejected(self):
        with self.assertRaises(ValueError):
            self.validate(extra=[('Variables.txt', b'private')])

    def test_duplicate_zip_member_rejected(self):
        with self.assertRaises(ValueError):
            self.validate(extra=[(c.CONTEXT_NAME, b'{}')])

    def test_zip_symbolic_link_rejected(self):
        name = next(iter(self.files))
        info = zipfile.ZipInfo(name)
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.files = {info: b'target'}
        with self.assertRaises(ValueError):
            self.validate()

    def test_oversized_member_rejected(self):
        path = self.archive()
        with patch.object(c, 'MAX_MEMBER_BYTES', 5):
            with self.assertRaises(ValueError):
                c.validate_capture(path, self.anchors)

    def test_oversized_archive_rejected(self):
        path = self.archive()
        with patch.object(c, 'MAX_ARCHIVE_BYTES', 5):
            with self.assertRaises(ValueError):
                c.validate_capture(path, self.anchors)

    def test_unsupported_compression_rejected(self):
        with self.assertRaises(ValueError):
            self.validate(compression=zipfile.ZIP_BZIP2)

    def test_utf16_bank_rejected(self):
        name = next(iter(self.files))
        self.files[name] = self.files[name].decode().encode('utf-16')
        self.inventory()
        with self.assertRaises(ValueError):
            self.validate()

    def test_power_shell_utf8_bom_context_is_accepted(self):
        self.assertTrue(self.validate(raw_context=b'\xef\xbb\xbf' + json.dumps(self.context).encode())['ready_for_unit_catalog_review'])

    def test_incomplete_bank_rejected(self):
        name = next(iter(self.files))
        self.files[name] = mutate(self.files[name], 'meta', 'complete', 0)
        self.inventory()
        with self.assertRaises(ValueError):
            self.validate()

    def test_mixed_bank_session_rejected(self):
        name = next(iter(self.files))
        self.files[name] = mutate(self.files[name], 'meta', 'session', '456_789')
        self.inventory()
        with self.assertRaises(ValueError):
            self.validate()

    def test_malformed_zip_rejected(self):
        path = self.root / 'bad.zip'
        path.write_bytes(b'not a ZIP')
        with self.assertRaises(ValueError):
            c.validate_capture(path, self.anchors)

    def test_xml_entities_rejected(self):
        name = next(iter(self.files))
        self.files[name] = b'<!DOCTYPE Bank [<!ENTITY bad "bad">]>' + self.files[name]
        self.inventory()
        with self.assertRaises(ValueError):
            self.validate()

    def test_tampered_cli_anchor_file_rejected(self):
        path = self.archive()
        anchors = self.root / 'anchors.json'
        anchors.write_text(json.dumps({'unit_anchors': self.anchors}))
        output = self.root / 'out.json'
        result = subprocess.run([sys.executable, str(Path(c.__file__)), str(path), '--anchors', str(anchors), '--output', str(output)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())

    def test_existing_cli_output_preserved(self):
        output = self.root / 'out.json'
        output.write_text('KEEP')
        result = subprocess.run([sys.executable, str(Path(c.__file__)), str(self.archive()), '--output', str(output)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(output.read_text(), 'KEEP')


if __name__ == '__main__':
    unittest.main()
