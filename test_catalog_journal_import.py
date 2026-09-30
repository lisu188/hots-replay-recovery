from __future__ import annotations

import json
import stat
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

import import_catalog_journal as importer
from plan_catalog_migration import propose
from test_catalog_journal import recording

ANCHORS_PATH = Path(__file__).parent / 'observations/runtime-catalog-reference-anchors.json'
ANCHORS = json.loads(ANCHORS_PATH.read_text())['unit_anchors']


def full_journal():
    units = [('', 0)] * max(ANCHORS.values())
    for name, index in ANCHORS.items():
        units[index - 1] = (name, 1)
    return recording(units)


def context(journals):
    return {'format': 'hots-catalog-journal-collection-v1', 'token': importer.TOKEN,
            'expected_build': importer.BUILD, 'map_sha256': importer.PROBE_SHA256,
            'launched_by_this_invocation': True, 'launch_utc': '2026-09-29T18:00:00.0000000Z',
            'graphics_log_fresh_for_launch': True, 'graphics_map_argument_matched': True,
            'observed_version_lines': ['GFX Heroes of the Storm (B98285)',
                                       'GFX <Version> 2.57.0.98285', 'GFX <DataBuild> B98285'],
            'journals': [{'name': name, 'bytes': len(raw), 'sha256': importer.sha256(raw),
                          'modified_utc': '2026-09-29T18:01:00+00:00', 'fresh_for_launch': True}
                         for name, raw in journals.items()],
            'warnings': [], 'export_contents_validated': False, 'client_playback_validated': False}


def make_zip(path, journals=None, ctx=None, extra=None):
    journals = {'journal-0.txt': full_journal()} if journals is None else journals
    ctx = context(journals) if ctx is None else ctx
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(importer.CONTEXT_NAME, json.dumps(ctx))
        for name, raw in journals.items():
            archive.writestr(name, raw)
        for name, raw in extra or []:
            archive.writestr(name, raw)
    return Path(path)


class JournalImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.zip = self.root / 'synthetic-journal-output.zip'

    def tearDown(self):
        self.temp.cleanup()

    def capture(self, ctx=None, journals=None):
        make_zip(self.zip, journals, ctx)
        before = self.zip.read_bytes()
        result = importer.validate_capture(self.zip, ANCHORS)
        self.assertEqual(self.zip.read_bytes(), before)
        for key in ('actual_build_verified', 'evidence_is_authenticated', 'ability_indices_independently_validated',
                    'automatically_applied_to_replay', 'client_playback_validated'):
            self.assertIs(result[key], False)
        return result

    def test_complete_synthetic_capture_is_only_eligible_for_review(self):
        result = self.capture()
        self.assertTrue(result['ready_for_unit_catalog_review'])
        self.assertEqual(result['blocking_checks'], [])
        self.assertTrue(result['complete_sequence'])
        self.assertEqual(result['reference_anchor_count'], 48)
        self.assertEqual(len(result['catalogs']['Unit']), max(ANCHORS.values()))

    def test_missing_output_generates_actionable_blocked_report(self):
        result = self.capture(journals={})
        self.assertIn('no_journal_collected', result['blocking_checks'])
        self.assertFalse(result['ready_for_unit_catalog_review'])
        self.assertEqual(result['catalogs'], {'Unit': [], 'Abil': []})

    def test_multiple_journals_never_auto_select_a_session(self):
        result = self.capture(journals={'journal-0.txt': full_journal(), 'journal-1.txt': full_journal()})
        self.assertIn('multiple_journals_require_explicit_session_resolution', result['blocking_checks'])
        self.assertFalse(result['ready_for_unit_catalog_review'])
        self.assertFalse(result['complete_sequence'])

    def test_invalid_truncated_empty_and_mixed_session_journals_block(self):
        good = full_journal()
        for raw in (b'', b'\xff\n', good[:-20], good + good, good.replace(b'11_22|ENTRY', b'12_23|ENTRY', 1)):
            with self.subTest(size=len(raw)):
                result = self.capture(journals={'journal-0.txt': raw})
                self.assertIn('journal_sequence_invalid_or_incomplete', result['blocking_checks'])
                self.assertFalse(result['ready_for_unit_catalog_review'])

    def test_wrong_anchors_do_not_become_ready(self):
        make_zip(self.zip)
        wrong = dict(ANCHORS)
        wrong[next(iter(wrong))] += 1
        result = importer.validate_capture(self.zip, wrong)
        self.assertIn('unit_reference_anchors_mismatch', result['blocking_checks'])
        self.assertFalse(result['ready_for_unit_catalog_review'])

    def test_independent_context_checks_all_block(self):
        journals = {'journal-0.txt': full_journal()}
        for field, value in [('launched_by_this_invocation', False), ('graphics_log_fresh_for_launch', False),
                             ('graphics_map_argument_matched', False), ('map_sha256', '0' * 64),
                             ('warnings', ['input_enumeration_limit_reached'])]:
            with self.subTest(field=field):
                ctx = context(journals)
                ctx[field] = value
                self.assertFalse(self.capture(ctx, journals)['ready_for_unit_catalog_review'])

    def test_collect_only_is_not_a_fresh_launch(self):
        journals = {'journal-0.txt': full_journal()}
        ctx = context(journals)
        ctx.update(launched_by_this_invocation=False, graphics_log_fresh_for_launch=False, map_sha256=None)
        ctx['journals'][0]['fresh_for_launch'] = False
        result = self.capture(ctx, journals)
        self.assertIn('collector_did_not_launch_this_probe', result['blocking_checks'])
        self.assertIn('journal_not_reported_fresh', result['blocking_checks'])

    def test_inventory_mtime_checked_not_just_claimed_boolean(self):
        journals = {'journal-0.txt': full_journal()}
        ctx = context(journals)
        ctx['journals'][0]['modified_utc'] = '2026-09-28T18:01:00Z'
        self.assertIn('journal_mtime_predates_launch', self.capture(ctx, journals)['blocking_checks'])

    def test_mtime_tolerance_boundary(self):
        journals = {'journal-0.txt': full_journal()}
        for date, expected in [('2026-09-29T17:59:55Z', True), ('2026-09-29T17:59:54.999999Z', False)]:
            ctx = context(journals)
            ctx['journals'][0]['modified_utc'] = date
            self.assertEqual(self.capture(ctx, journals)['ready_for_unit_catalog_review'], expected)

    def test_missing_wrong_or_conflicting_version_evidence_blocks(self):
        journals = {'journal-0.txt': full_journal()}
        cases = [[], ['GFX <Version> 2.57.0.98285'], context(journals)['observed_version_lines'] + ['GFX <DataBuild> B98297'],
                 [line.replace('98285', '98297') for line in context(journals)['observed_version_lines']]]
        for lines in cases:
            with self.subTest(lines=lines):
                ctx = context(journals)
                ctx['observed_version_lines'] = lines
                self.assertFalse(self.capture(ctx, journals)['ready_for_unit_catalog_review'])

    def test_forbidden_collector_validation_attestations_rejected(self):
        journals = {'journal-0.txt': full_journal()}
        for name in ['export_contents_validated', 'client_playback_validated']:
            ctx = context(journals)
            ctx[name] = True
            with self.assertRaises(ValueError):
                self.capture(ctx, journals)

    def test_context_schema_and_exact_boolean_types(self):
        journals = {'journal-0.txt': full_journal()}
        for name, value in [('expected_build', True), ('launched_by_this_invocation', 1),
                            ('format', 'hots-runtime-probe-collection-v1'), ('token', 'P1'),
                            ('warnings', 'warning'), ('map_sha256', True),
                            ('observed_version_lines', ['x\ny'])]:
            with self.subTest(field=name):
                ctx = context(journals)
                ctx[name] = value
                with self.assertRaises(ValueError):
                    self.capture(ctx, journals)
        ctx = context(journals)
        ctx['unreviewed_attestation'] = True
        with self.assertRaises(ValueError):
            self.capture(ctx, journals)
        del ctx['unreviewed_attestation'], ctx['warnings']
        with self.assertRaises(ValueError):
            self.capture(ctx, journals)

    def test_inventory_tampering_rejected(self):
        journals = {'journal-0.txt': full_journal()}
        for key, value in [('sha256', '0' * 64), ('bytes', 0), ('bytes', True), ('name', '../outside.txt'),
                           ('fresh_for_launch', 1), ('modified_utc', '2026-09-29')]:
            ctx = context(journals)
            ctx['journals'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.capture(ctx, journals)
        ctx = context(journals)
        ctx['journals'] = []
        with self.assertRaises(ValueError):
            self.capture(ctx, journals)

    def test_utc_timestamps_reject_local_offsets_and_bad_dates(self):
        for value in ('2026-09-29T18:00:00', '2026-09-29T18:00:00+02:00', '2026-02-30T18:00:00Z', 12, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                importer.utc_time(value)

    def test_duplicate_and_nonfinite_json_rejected(self):
        for data in ('{"format":1,"format":2}', '{"x":NaN}', '[]'):
            with zipfile.ZipFile(self.zip, 'w') as z:
                z.writestr(importer.CONTEXT_NAME, data)
            with self.assertRaises(ValueError):
                importer.validate_capture(self.zip, ANCHORS)

    def test_unexpected_names_and_traversal_rejected_without_extraction(self):
        for name in ('../outside.txt', '/absolute.txt', 'folder/journal-0.txt', 'journal-8.txt', 'Journal-0.txt', 'journal-01.txt', 'extra.StormBank'):
            with self.subTest(name=name):
                make_zip(self.zip, extra=[(name, b'x')])
                with self.assertRaises(ValueError):
                    importer.read_archive(self.zip)
        self.assertFalse((self.root / 'outside.txt').exists())

    def test_duplicate_zip_names_rejected(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            make_zip(self.zip, extra=[('journal-0.txt', b'duplicate')])
        with self.assertRaises(ValueError):
            importer.read_archive(self.zip)

    def test_zip_symlink_member_rejected(self):
        with zipfile.ZipFile(self.zip, 'w') as z:
            z.writestr(importer.CONTEXT_NAME, json.dumps(context({})))
            info = zipfile.ZipInfo('journal-0.txt')
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(info, 'outside')
        with self.assertRaises(ValueError):
            importer.read_archive(self.zip)

    def test_unsupported_compression_and_invalid_archive_rejected(self):
        with zipfile.ZipFile(self.zip, 'w', zipfile.ZIP_BZIP2) as z:
            z.writestr(importer.CONTEXT_NAME, '{}')
        with self.assertRaises(ValueError):
            importer.read_archive(self.zip)
        self.zip.write_bytes(b'not a zip')
        with self.assertRaises(ValueError):
            importer.read_archive(self.zip)

    def test_context_size_and_journal_numbering_limits(self):
        with zipfile.ZipFile(self.zip, 'w') as z:
            z.writestr(importer.CONTEXT_NAME, b'x' * (importer.MAX_CONTEXT_BYTES + 1))
        with self.assertRaises(ValueError):
            importer.read_archive(self.zip)
        make_zip(self.zip, journals={'journal-1.txt': b'x'})
        with self.assertRaises(ValueError):
            importer.read_archive(self.zip)

    def test_journal_size_and_member_count_limits(self):
        make_zip(self.zip, journals={'journal-0.txt': b'x' * (importer.MAX_BYTES + 1)})
        with self.assertRaises(ValueError):
            importer.read_archive(self.zip)
        make_zip(self.zip, journals={f'journal-{i}.txt': b'x' for i in range(9)})
        with self.assertRaises(ValueError):
            importer.read_archive(self.zip)

    def test_stored_zip_and_bom_json_supported(self):
        journals = {'journal-0.txt': full_journal()}
        with zipfile.ZipFile(self.zip, 'w', zipfile.ZIP_STORED) as z:
            z.writestr(importer.CONTEXT_NAME, b'\xef\xbb\xbf' + json.dumps(context(journals)).encode())
            z.writestr('journal-0.txt', journals['journal-0.txt'])
        self.assertTrue(importer.validate_capture(self.zip, ANCHORS)['ready_for_unit_catalog_review'])

    def test_plan_uses_only_observed_name_matches_and_keeps_engine_blockers(self):
        capture = self.capture()
        name, index = next(iter(ANCHORS.items()))
        requirements = {'unit_links': [{'source_link': 42, 'source_names': [name], 'identity_status': 'single_observed_name', 'field_count': 3},
                                       {'source_link': 43, 'source_names': ['UnobservedUnit'], 'identity_status': 'single_observed_name', 'field_count': 4}],
                        'unit_link_fields': 7, 'ability_links': [{'source_link': 31}]}
        plan = propose(requirements, capture)
        self.assertEqual(plan['unit_link_plan'][0]['target_link'], index)
        self.assertIsNone(plan['unit_link_plan'][1]['target_link'])
        self.assertFalse(plan['replay_ready_for_playback'])
        self.assertIn('original_synchronization_equivalence_unverified', plan['blocking_checks'])
        self.assertIn('original_ability_link_names_not_established', plan['blocking_checks'])
        capture['ready_for_unit_catalog_review'] = False
        capture['blocking_checks'] = ['journal_mtime_predates_launch']
        self.assertEqual(propose(requirements, capture)['coverage']['reviewable_links'], 0)

    def test_deterministic_output_and_input_preserved(self):
        make_zip(self.zip)
        original = self.zip.read_bytes()
        for name in ('one', 'two'):
            importer.run(self.zip, self.root / name)
        for name in ('summary.json', 'capture.json'):
            self.assertEqual((self.root / 'one' / name).read_bytes(), (self.root / 'two' / name).read_bytes())
        self.assertEqual(original, self.zip.read_bytes())

    def test_existing_output_preserved(self):
        make_zip(self.zip)
        out = self.root / 'out'
        out.mkdir()
        (out / 'sentinel').write_bytes(b'original')
        with self.assertRaises(FileExistsError):
            importer.run(self.zip, out)
        self.assertEqual((out / 'sentinel').read_bytes(), b'original')

    def test_wrong_source_and_modified_anchors_do_not_publish_partial_output(self):
        make_zip(self.zip)
        wrong = self.root / 'wrong'
        wrong.write_bytes(b'wrong input')
        for kwargs in ({'source': wrong}, {'anchors_path': wrong}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                importer.run(self.zip, self.root / 'out', **kwargs)
            self.assertFalse((self.root / 'out').exists())

    def test_cli_exit_codes_distinguish_review_blocked_and_malformed(self):
        script = str(Path(importer.__file__))
        for name, journals, code in [('review', None, 0), ('missing', {}, 2)]:
            make_zip(self.zip, journals=journals)
            out = self.root / name
            completed = subprocess.run([sys.executable, script, str(self.zip), '--output', str(out)], capture_output=True, text=True, timeout=20)
            self.assertEqual(completed.returncode, code, completed.stderr)
            self.assertFalse(json.loads((out / 'summary.json').read_text())['client_playback_validated'])
        self.zip.write_bytes(b'bad zip')
        out = self.root / 'malformed'
        completed = subprocess.run([sys.executable, script, str(self.zip), '--output', str(out)], capture_output=True, text=True, timeout=20)
        self.assertEqual(completed.returncode, 1)
        self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
