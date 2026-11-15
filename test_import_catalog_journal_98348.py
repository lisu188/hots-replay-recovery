"""Contract fixtures below are synthetic; they are never engine-capture evidence."""
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

import import_catalog_journal as legacy
import import_catalog_journal_98348 as current
import runtime_catalog_journal as journal

PROFILE = current.DEFAULT_ANCHORS
ANCHORS = json.loads(PROFILE.read_bytes())['unit_anchors']


def synthetic_journal(begin=98285):
    by_index = {i: n for n, i in ANCHORS.items()}
    count = max(by_index)
    rows = [f'BEGIN|{begin}|{journal.MAP_SHA256}', f'COUNT|Unit|1|{count}', 'COUNT|Abil|2|1']
    for index in range(1, count + 1):
        name = by_index.get(index, '')
        rows.append(f'ENTRY|Unit|{index}|{int(bool(name))}|{len(name)}|{name}')
    rows += [f'DONE|Unit|{count}', 'ENTRY|Abil|1|1|16|SyntheticAbility', 'DONE|Abil|1', f'END|{count}|1']
    return ('\n'.join(f'{journal.TOKEN}|1_2|{row}' for row in rows) + '\n').encode()


def context(journals):
    return {'format': 'hots-catalog-journal-collection-v1', 'token': journal.TOKEN,
        'expected_build': 98285, 'map_sha256': legacy.PROBE_SHA256,
        'launched_by_this_invocation': True, 'launch_utc': '2026-11-15T00:00:00Z',
        'graphics_log_fresh_for_launch': True, 'graphics_map_argument_matched': True,
        'observed_version_lines': ['GFX Heroes of the Storm (B98348)',
            'GFX <Version> 2.57.0.98348', 'GFX <DataBuild> B98348'],
        'journals': [{'name': n, 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(),
            'modified_utc': '2026-11-15T00:00:01Z', 'fresh_for_launch': True} for n, b in journals.items()],
        'warnings': [], 'export_contents_validated': False, 'client_playback_validated': False}


def make_zip(path, journals=None, supplied_context=None, compression=zipfile.ZIP_DEFLATED):
    journals = {'journal-0.txt': synthetic_journal()} if journals is None else journals
    ctx = context(journals) if supplied_context is None else supplied_context
    with zipfile.ZipFile(path, 'w', compression=compression) as archive:
        archive.writestr('collection-context.json', json.dumps(ctx))
        for name, raw in journals.items():
            archive.writestr(name, raw)
    return path


class CurrentJournalImportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.capture = self.directory / 'SYNTHETIC-journal-output.zip'

    def test_fixed_profile_measurements_and_sanitized_provenance(self):
        profile = current.load_profile()
        self.assertEqual(profile['build'], 98348)
        self.assertEqual((len(profile['unit_anchors']), len(profile['all_unambiguous_current_candidates'])), (48, 103))
        self.assertTrue(all(len(x['supporting_reference_replay_sha256']) >= 3 for x in profile['anchor_provenance']))
        self.assertFalse(profile['measurement_scope']['fresh_raw_replay_or_stream_redecode'])
        self.assertNotIn(b'C:/', PROFILE.read_bytes())
        self.assertNotIn(b'private-members', PROFILE.read_bytes())

    def test_valid_synthetic_zip_is_reported_context_review_only(self):
        result = current.validate_capture(make_zip(self.capture))
        self.assertTrue(result['ready_for_98348_unit_catalog_review'])
        self.assertFalse(result['ready_for_unit_catalog_review'])
        self.assertFalse(result['legacy_98285_migration_planner_eligible'])
        self.assertEqual(result['blocking_checks'], [])
        self.assertEqual((result['emitter_declared_build'], result['runtime_profile_build']), (98285, 98348))
        self.assertNotIn('expected_build', result)
        self.assertEqual(result['reference_anchor_count'], 48)
        self.assertEqual(result['source_map_sha256'], journal.MAP_SHA256)
        self.assertEqual(result['delivered_map_sha256'], legacy.PROBE_SHA256)
        self.assertNotEqual(result['source_map_sha256'], result['delivered_map_sha256'])
        for field in ('actual_build_verified', 'evidence_is_authenticated', 'ability_indices_independently_validated',
                      'automatically_applied_to_replay', 'client_playback_validated', 'simulation_compatibility_validated'):
            self.assertIs(result[field], False)

    def test_legacy_context_still_rejects_current_runtime(self):
        values = {'journal-0.txt': synthetic_journal()}
        old_result = legacy.validate_context(context(values), values)
        self.assertEqual(set(old_result['blocking_checks']), set(current.RUNTIME_REQUIREMENTS))
        self.assertEqual(journal.BUILD, 98285)

    def test_new_BEGIN_or_mixed_session_never_becomes_valid_capture(self):
        for raw in (synthetic_journal(98348), synthetic_journal().replace(b'|1_2|END|', b'|2_3|END|')):
            make_zip(self.capture, {'journal-0.txt': raw})
            result = current.validate_capture(self.capture)
            self.assertFalse(result['ready_for_98348_unit_catalog_review'])
            self.assertIn('journal_sequence_invalid_or_incomplete', result['blocking_checks'])

    def test_incomplete_sequence_and_wrong_source_map_rejected(self):
        raw = synthetic_journal()
        for candidate in (raw.rsplit(b'\n', 2)[0] + b'\n', raw.replace(journal.MAP_SHA256.encode(), b'0' * 64)):
            result = current.validate_capture(make_zip(self.capture, {'journal-0.txt': candidate}))
            self.assertIn('journal_sequence_invalid_or_incomplete', result['blocking_checks'])

    def test_each_runtime_field_is_independently_required(self):
        values = {'journal-0.txt': synthetic_journal()}
        ctx = context(values)
        for index, blocker in enumerate(('executable_build_header_missing_conflicting_or_wrong',
                                         'version_log_missing_conflicting_or_wrong',
                                         'data_build_log_missing_conflicting_or_wrong')):
            with self.subTest(field=index):
                changed = copy.deepcopy(ctx)
                changed['observed_version_lines'].pop(index)
                self.assertEqual(current.validate_runtime_context(changed, values)['blocking_checks'], [blocker])

    def test_wrong_or_mixed_runtime_evidence_rejected(self):
        values = {'journal-0.txt': synthetic_journal()}
        ctx = context(values)
        for lines in ([s.replace('98348', '98285') for s in ctx['observed_version_lines']],
                      ctx['observed_version_lines'] + ['GFX <DataBuild> B98285'],
                      ctx['observed_version_lines'] + ['GFX <Version> 2.57.0.98285'],
                      ['GFX <Version> 2.57.0.98348']):
            changed = dict(ctx, observed_version_lines=lines)
            self.assertTrue(current.validate_runtime_context(changed, values)['blocking_checks'])

    def test_every_nonruntime_blocker_is_preserved_from_legacy(self):
        values = {'journal-0.txt': synthetic_journal()}
        ctx = context(values)
        cases = [('launched_by_this_invocation', False), ('graphics_log_fresh_for_launch', False),
                 ('graphics_map_argument_matched', False), ('map_sha256', '0' * 64),
                 ('warnings', ['no_journal_found'])]
        for key, value in cases:
            with self.subTest(key=key):
                changed = dict(ctx, **{key: value})
                old = legacy.validate_context(changed, values)['blocking_checks']
                self.assertEqual(current.validate_runtime_context(changed, values)['blocking_checks'],
                                 [b for b in old if b not in current.RUNTIME_REQUIREMENTS])
        changed = copy.deepcopy(ctx)
        changed['journals'][0].update(fresh_for_launch=False, modified_utc='2026-11-14T23:59:54Z')
        self.assertEqual(set(current.validate_runtime_context(changed, values)['blocking_checks']),
                         {'journal_not_reported_fresh', 'journal_mtime_predates_launch'})

    def test_collect_only_cannot_gain_eligibility(self):
        values = {'journal-0.txt': synthetic_journal()}
        ctx = dict(context(values), launched_by_this_invocation=False)
        result = current.validate_capture(make_zip(self.capture, values, ctx))
        self.assertFalse(result['ready_for_98348_unit_catalog_review'])
        self.assertIn('collector_did_not_launch_this_probe', result['blocking_checks'])

    def test_changed_token_emitter_build_extra_key_and_nonboolean_flags_rejected(self):
        values = {'journal-0.txt': synthetic_journal()}
        for patch_values in ({'token': 'HRC98348'}, {'expected_build': 98348}, {'extra': True},
                             {'launched_by_this_invocation': 1}, {'client_playback_validated': True},
                             {'export_contents_validated': True}):
            with self.subTest(changed=tuple(patch_values)), self.assertRaises(ValueError):
                current.validate_runtime_context(dict(context(values), **patch_values), values)

    def test_stale_timestamp_blocks_despite_true_freshness_flag(self):
        values = {'journal-0.txt': synthetic_journal()}
        ctx = context(values)
        ctx['journals'][0]['modified_utc'] = '2026-11-14T23:59:54Z'
        result = current.validate_capture(make_zip(self.capture, values, ctx))
        self.assertIn('journal_mtime_predates_launch', result['blocking_checks'])

    def test_inventory_digest_size_or_duplicate_rows_rejected(self):
        values = {'journal-0.txt': synthetic_journal()}
        for field, replacement in (('sha256', '0' * 64), ('bytes', 1)):
            ctx = context(values)
            ctx['journals'][0][field] = replacement
            with self.subTest(field=field), self.assertRaises(ValueError):
                current.validate_capture(make_zip(self.capture, values, ctx))
        ctx = context(values)
        ctx['journals'] *= 2
        with self.assertRaises(ValueError):
            current.validate_capture(make_zip(self.capture, values, ctx))

    def test_no_journal_and_multiple_journals_stay_blocked(self):
        for values, blocker in (({}, 'no_journal_collected'),
                ({'journal-0.txt': synthetic_journal(), 'journal-1.txt': synthetic_journal()},
                 'multiple_journals_require_explicit_session_resolution')):
            result = current.validate_capture(make_zip(self.capture, values))
            self.assertIn(blocker, result['blocking_checks'])
            self.assertFalse(result['ready_for_98348_unit_catalog_review'])

    def test_anchor_mismatch_blocks_complete_sequence(self):
        name = sorted(ANCHORS)[0]
        raw = synthetic_journal().replace(f'|{len(name)}|{name}\n'.encode(), b'|11|WrongAnchor\n')
        result = current.validate_capture(make_zip(self.capture, {'journal-0.txt': raw}))
        self.assertTrue(result['complete_sequence'])
        self.assertIn('unit_reference_anchors_mismatch', result['blocking_checks'])

    def test_mutated_profile_fails_before_JSON_ZIP_or_output_side_effects(self):
        bad = self.directory / 'mutated-profile.json'
        bad.write_bytes(b'{not valid JSON')
        output = self.directory / 'new-parent' / 'output'
        with (patch.object(current.capture_json, 'strict_json', side_effect=AssertionError('JSON parsed')) as parse,
              patch.object(current.legacy, 'read_archive', side_effect=AssertionError('ZIP read')) as archive):
            with self.assertRaisesRegex(ValueError, 'pinned observation'):
                current.run(self.directory / 'missing.zip', output, bad)
            parse.assert_not_called()
            archive.assert_not_called()
        self.assertFalse(output.parent.exists())

    def test_profile_directory_and_oversized_profile_rejected(self):
        with self.assertRaises(ValueError):
            current.load_profile(self.directory)
        bad = self.directory / 'too-large.json'
        bad.write_bytes(b' ' * (current.MAX_PROFILE_BYTES + 1))
        with self.assertRaises(ValueError):
            current.load_profile(bad)

    def test_changed_shared_contract_source_rejected(self):
        changed = self.directory / 'changed.py'
        changed.write_text('# changed contract\n')
        with patch.object(current.legacy, '__file__', str(changed)), self.assertRaisesRegex(ValueError, 'legacy contract source'):
            current.load_profile()

    def test_duplicate_unsafe_nonregular_and_unsupported_ZIP_members_rejected(self):
        ctx = json.dumps(context({'journal-0.txt': synthetic_journal()}))
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(self.capture, 'w') as z:
                z.writestr('collection-context.json', ctx)
                z.writestr('journal-0.txt', synthetic_journal())
                z.writestr('journal-0.txt', synthetic_journal())
        with self.assertRaises(ValueError):
            current.validate_capture(self.capture)
        for name in ('../journal-0.txt', 'journal-1.txt'):
            make_zip(self.capture, {name: synthetic_journal()})
            with self.subTest(name=name), self.assertRaises(ValueError):
                current.validate_capture(self.capture)
        with zipfile.ZipFile(self.capture, 'w') as z:
            z.writestr('collection-context.json', ctx)
            member = zipfile.ZipInfo('journal-0.txt')
            member.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(member, synthetic_journal())
        with self.assertRaises(ValueError):
            current.validate_capture(self.capture)
        make_zip(self.capture, compression=zipfile.ZIP_BZIP2)
        with self.assertRaises(ValueError):
            current.validate_capture(self.capture)

    def test_encrypted_flag_and_oversized_context_rejected(self):
        make_zip(self.capture)
        raw = bytearray(self.capture.read_bytes())
        central = raw.index(b'PK\x01\x02')
        for offset in (6, central + 8):
            flags = struct.unpack_from('<H', raw, offset)[0]
            struct.pack_into('<H', raw, offset, flags | 1)
        self.capture.write_bytes(raw)
        with self.assertRaises(ValueError):
            current.validate_capture(self.capture)
        with zipfile.ZipFile(self.capture, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr('collection-context.json', b' ' * (legacy.MAX_CONTEXT_BYTES + 1))
        with self.assertRaises(ValueError):
            current.validate_capture(self.capture)

    def test_duplicate_JSON_keys_rejected(self):
        values = {'journal-0.txt': synthetic_journal()}
        ctx = json.dumps(context(values)).replace('"expected_build": 98285', '"expected_build": 98285, "expected_build": 98285')
        with zipfile.ZipFile(self.capture, 'w') as z:
            z.writestr('collection-context.json', ctx)
            z.writestr('journal-0.txt', values['journal-0.txt'])
        with self.assertRaises(ValueError):
            current.validate_capture(self.capture)

    def test_output_is_two_reports_only_and_existing_output_unchanged(self):
        make_zip(self.capture)
        output = self.directory / 'result'
        summary = current.run(self.capture, output)
        self.assertEqual({p.name for p in output.iterdir()}, {'capture.json', 'summary.json'})
        self.assertFalse(summary['catalog_plan_created'])
        before = {p.name: p.read_bytes() for p in output.iterdir()}
        with self.assertRaises(FileExistsError):
            current.run(self.capture, output)
        self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, before)

    def test_CLI_omits_source_planner_and_returns_review_status_only(self):
        make_zip(self.capture)
        output = self.directory / 'cli-output'
        env = dict(os.environ, PYTHONPATH=str(Path(legacy.__file__).parent))
        command = [sys.executable, str(Path(current.__file__)), str(self.capture), str(output)]
        completed = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        summary = json.loads(completed.stdout)
        self.assertTrue(summary['ready_for_98348_unit_catalog_review'])
        self.assertFalse(summary['ready_for_unit_catalog_review'])
        self.assertFalse(summary['actual_build_verified'])
        refused = subprocess.run(command + ['--source', 'never-read.StormReplay'], env=env, capture_output=True, text=True)
        self.assertEqual(refused.returncode, 2)
        self.assertIn('unrecognized arguments', refused.stderr)

    def test_legacy_planner_refuses_new_result_at_its_first_gate(self):
        from plan_catalog_migration import propose
        result = current.validate_capture(make_zip(self.capture))
        self.assertTrue(result['ready_for_98348_unit_catalog_review'])
        # Empty requirements exercise only eligibility, without inventing old replay data.
        plan = propose({'unit_links': [], 'ability_links': [], 'unit_link_fields': 0}, result)
        self.assertIn('runtime_capture_not_eligible', plan['blocking_checks'])
        self.assertFalse(plan['unit_plan_complete'])
        self.assertFalse(plan['replay_ready_for_playback'])


if __name__ == '__main__':
    unittest.main()
