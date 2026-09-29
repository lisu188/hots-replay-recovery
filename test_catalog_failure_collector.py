from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

SCRIPT = Path(__file__).parent / 'scripts/collect_catalog_diagnostics.ps1'
TOKEN = 'HRC98285_20260929_P1'


class FailureCollectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shell = os.environ.get('HOTS_TEST_POWERSHELL') or shutil.which('pwsh') or shutil.which('powershell')
        if not cls.shell:
            raise RuntimeError('PowerShell is required; run this suite on the Windows CI job')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.docs = self.root / 'Documents with spaces'
        self.docs.mkdir()
        self.output = self.root / 'output with spaces'

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, path, text):
        p = self.docs / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
        return p

    def run_collect(self, success=True):
        before = {str(p.relative_to(self.docs)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.docs.rglob('*') if p.is_file()}
        run = subprocess.run([self.shell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(SCRIPT),
                              '-GameDocuments', str(self.docs), '-OutputDirectory', str(self.output)],
                             capture_output=True, text=True, timeout=40)
        if success:
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        else:
            self.assertNotEqual(run.returncode, 0)
            return
        after = {str(p.relative_to(self.docs)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.docs.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        with zipfile.ZipFile(str(self.output) + '.zip') as z:
            self.assertIsNone(z.testzip())
            self.raw_context = z.read('diagnostic-context.json')
            self.report = json.loads(self.raw_context)
            self.members = {n: z.read(n) for n in z.namelist() if not n.endswith('/')}
        self.assertFalse(self.report['capture_eligible_for_catalog_mapping'])
        self.assertFalse(self.report['game_launched_by_collector'])
        self.assertFalse(self.report['replay_modified'])
        self.assertFalse(self.report['client_playback_validated'])

    def test_no_banks_still_produces_diagnostic_zip(self):
        self.run_collect()
        self.assertEqual(self.report['collection_status'], 'manifest-not-found')
        self.assertEqual(self.report['collected_bank_files'], 0)

    def test_missing_documents_still_reported(self):
        self.docs.rmdir()
        self.run_collect()
        self.assertFalse(self.report['documents_directory_found'])

    def test_nested_manifest_and_chunks_copied_with_digests(self):
        self.write(f'Accounts/a/Banks/{TOKEN}_Manifest.StormBank', '<Bank/>')
        self.write(f'Accounts/a/Banks/{TOKEN}_Unit_0.StormBank', '<Bank>test</Bank>')
        self.run_collect()
        self.assertEqual(self.report['collected_bank_files'], 2)
        self.assertEqual(self.report['collection_status'], 'manifest-present-not-validated')
        for row in self.report['bank_files']:
            self.assertEqual(hashlib.sha256(self.members[row['name']]).hexdigest(), row['sha256'])

    def test_chunk_without_manifest_not_reported_as_export(self):
        self.write(f'Banks/{TOKEN}_Unit_0.StormBank', '<Bank/>')
        self.run_collect()
        self.assertEqual(self.report['collection_status'], 'manifest-not-found')
        self.assertEqual(self.report['collected_bank_files'], 1)

    def test_unrelated_banks_not_copied(self):
        self.write('Banks/AccountPrivate.StormBank', 'private data')
        self.write(f'Banks/{TOKEN}_Unknown.StormBank', 'private data')
        self.run_collect()
        self.assertEqual(self.report['collected_bank_files'], 0)
        self.assertNotIn(b'private data', b''.join(self.members.values()))

    def test_replay_is_never_collected(self):
        self.write('Accounts/a/Replays/TEST.StormReplay', 'private replay')
        self.run_collect()
        self.assertEqual(set(self.members), {'diagnostic-context.json'})

    def test_script_error_preserved_without_export(self):
        self.write('GameLogs/Script.txt', 'Galaxy compile error: MapScript.galaxy:120: Unknown identifier HRC_Test\n')
        self.run_collect()
        self.assertIn(b'MapScript.galaxy:120', self.raw_context)
        self.assertEqual(self.report['collection_status'], 'manifest-not-found')

    def test_probe_launch_detected_without_private_path(self):
        self.write('GameLogs/Graphics.txt', 'GFX <Parameters> "C:\\Users\\SecretName\\TEN_GREYMANE_CATALOG_PROBE_98285.StormMap"\nGFX <Version> 2.57.0.98285\nGFX <DataBuild> B98285')
        self.run_collect()
        self.assertTrue(self.report['log_evidence'][0]['probe_map_argument_observed'])
        self.assertNotIn(b'SecretName', self.raw_context)
        self.assertIn(b'2.57.0.98285', self.raw_context)

    def test_variables_only_replay_basename(self):
        self.write('Variables.txt', 'LastAccountName=secret@example.com\nlastReplayFilePath=C:\\Users\\SecretName\\R8.StormReplay\npassword=private')
        self.run_collect()
        self.assertEqual(self.report['last_replay_basename_recorded'], 'R8.StormReplay')
        self.assertNotIn(b'secret@example', self.raw_context)
        self.assertNotIn(b'SecretName', self.raw_context)

    def test_error_paths_and_emails_redacted(self):
        self.write('GameLogs/Script.txt', 'Galaxy error "C:\\Users\\SecretName\\test.galaxy" user@example.com\n')
        self.run_collect()
        self.assertNotIn(b'SecretName', self.raw_context)
        self.assertNotIn(b'user@example.com', self.raw_context)
        self.assertIn(b'[email]', self.raw_context)

    def test_credential_like_line_is_omitted(self):
        self.write('GameLogs/error.log', 'error authorization Bearer very-secret\n')
        self.run_collect()
        self.assertNotIn(b'very-secret', self.raw_context)

    def test_large_log_is_not_read(self):
        self.write('GameLogs/error.log', 'x' * (4 * 1024 * 1024 + 1))
        self.run_collect()
        self.assertEqual(len(self.report['log_evidence']), 0)
        self.assertIn('log_size_limit_reached', self.report['warnings'])

    def test_large_bank_not_copied(self):
        self.write(f'Banks/{TOKEN}_Manifest.StormBank', 'x' * (4 * 1024 * 1024 + 1))
        self.run_collect()
        self.assertEqual(self.report['collected_bank_files'], 0)
        self.assertIn('bank_size_limit_reached', self.report['warnings'])

    def test_log_count_bound(self):
        for i in range(41):
            self.write(f'GameLogs/{i}.txt', 'Galaxy error')
        self.run_collect()
        self.assertEqual(len(self.report['log_evidence']), 40)
        self.assertIn('log_count_limit_reached', self.report['warnings'])

    def test_error_lines_bound(self):
        self.write('GameLogs/error.log', 'Galaxy error\n' * 301)
        self.run_collect()
        self.assertEqual(len(self.report['log_evidence'][0]['selected_lines']), 300)

    def test_line_length_bound(self):
        self.write('GameLogs/error.log', 'Galaxy error ' + 'x' * 2000)
        self.run_collect()
        self.assertLess(len(self.report['log_evidence'][0]['selected_lines'][0]), 1100)

    def test_different_bank_directories_do_not_overwrite_each_other(self):
        for folder in ('a', 'b'):
            self.write(f'Accounts/{folder}/Banks/{TOKEN}_Manifest.StormBank', '<Bank>' + folder + '</Bank>')
        self.run_collect()
        self.assertEqual(self.report['observed_manifest_files'], 2)
        self.assertEqual(len(self.report['bank_files']), 2)
        self.assertEqual(len({row['name'] for row in self.report['bank_files']}), 2)

    def test_existing_output_is_preserved(self):
        self.output.mkdir()
        marker = self.output / 'keep.txt'; marker.write_text('keep')
        self.run_collect(False)
        self.assertEqual(marker.read_text(), 'keep')

    def test_existing_zip_is_preserved(self):
        p = Path(str(self.output) + '.zip'); p.write_bytes(b'keep')
        self.run_collect(False)
        self.assertEqual(p.read_bytes(), b'keep')

    def test_filename_pattern_is_case_exact(self):
        self.write(f'Banks/{TOKEN.lower()}_Manifest.StormBank', 'wrong token')
        self.run_collect()
        self.assertEqual(self.report['collected_bank_files'], 0)

    def test_no_map_or_executable_required(self):
        self.run_collect()
        self.assertFalse(self.report['game_installation_modified'])
        self.assertFalse(self.report['export_contents_validated'])


if __name__ == '__main__':
    unittest.main()
