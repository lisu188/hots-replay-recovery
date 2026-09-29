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

SCRIPT = Path(__file__).parent / 'scripts/run_catalog_journal.ps1'
TOKEN = 'HRC98285_20260929_J2'
MAP_NAME = 'TEN_GREYMANE_CATALOG_JOURNAL_98285.StormMap'


class JournalCollectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shell = os.environ.get('HOTS_TEST_POWERSHELL') or shutil.which('pwsh') or shutil.which('powershell')
        if not cls.shell or os.name != 'nt':
            raise RuntimeError('This suite requires a Windows PowerShell runner')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.docs = self.root / 'Documents with spaces'
        self.docs.mkdir()
        self.output = self.root / 'output with spaces'

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, data):
        p = self.docs / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data if isinstance(data, bytes) else data.encode('utf-8'))
        return p

    def run_collect(self, success=True, script=SCRIPT, mode='Collect'):
        before = {str(p.relative_to(self.docs)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.docs.rglob('*') if p.is_file()}
        run = subprocess.run([self.shell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script),
                              '-Mode', mode, '-GameDirectory', str(self.root / 'No game installed'),
                              '-GameDocuments', str(self.docs), '-OutputDirectory', str(self.output)],
                             capture_output=True, text=True, timeout=40)
        after = {str(p.relative_to(self.docs)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.docs.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        if not success:
            self.assertNotEqual(run.returncode, 0)
            return run
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        with zipfile.ZipFile(str(self.output) + '.zip') as z:
            self.assertIsNone(z.testzip())
            self.members = {n: z.read(n) for n in z.namelist() if not n.endswith('/')}
            self.context = json.loads(self.members['collection-context.json'])
        self.assertEqual(self.context['format'], 'hots-catalog-journal-collection-v1')
        self.assertFalse(self.context['client_playback_validated'])
        self.assertFalse(self.context['export_contents_validated'])
        self.assertFalse(self.context['launched_by_this_invocation'])
        self.assertFalse(self.context['graphics_log_fresh_for_launch'])
        for row in self.context['journals']:
            self.assertFalse(row['fresh_for_launch'])
            self.assertEqual(row['bytes'], len(self.members[row['name']]))
            self.assertEqual(row['sha256'], hashlib.sha256(self.members[row['name']]).hexdigest())
        return run

    def test_no_journal_still_produces_zip(self):
        self.run_collect()
        self.assertIn('no_journal_found', self.context['warnings'])
        self.assertEqual(set(self.members), {'collection-context.json'})

    def test_missing_documents_produces_zip(self):
        self.docs.rmdir()
        self.run_collect()
        self.assertIn('game_documents_missing', self.context['warnings'])

    def test_direct_journal_preserved_byte_for_byte(self):
        data = b'\xef\xbb\xbf' + TOKEN.encode() + b'|11_22|BEGIN\r\n'
        self.write(TOKEN + '.txt', data)
        self.run_collect()
        self.assertEqual(self.members['journal-0.txt'], data)

    def test_nested_userlogs_and_gamelogs_both_collected(self):
        self.write(f'UserLogs/one/{TOKEN}.txt', 'first\n')
        self.write(f'GameLogs/two/{TOKEN}.txt', 'second\n')
        self.run_collect()
        self.assertEqual(len(self.context['journals']), 2)
        self.assertEqual({self.members['journal-0.txt'], self.members['journal-1.txt']}, {b'first\n', b'second\n'})

    def test_unrelated_journals_and_replays_not_collected(self):
        for name in ('UserLogs/Debug_Output.txt', 'UserLogs/HRC98285_20260929_P1.txt',
                     f'UserLogs/{TOKEN}.txt.bak', 'Accounts/a/Replays/private.StormReplay', 'Variables.txt'):
            self.write(name, 'secret unrelated data')
        self.run_collect()
        self.assertNotIn(b'secret unrelated data', b''.join(self.members.values()))

    def test_oversized_journal_reported_not_copied(self):
        self.write(f'UserLogs/{TOKEN}.txt', b'x' * (8 * 1024 * 1024 + 1))
        self.run_collect()
        self.assertEqual(len(self.context['journals']), 0)
        self.assertIn('journal_size_limit', self.context['warnings'])

    def test_too_many_sessions_not_arbitrarily_selected(self):
        for i in range(9):
            self.write(f'UserLogs/{i}/{TOKEN}.txt', 'session\n')
        self.run_collect(success=False)
        self.assertFalse(Path(str(self.output) + '.zip').exists())

    def test_existing_output_directory_preserved(self):
        self.output.mkdir()
        sentinel = self.output / 'preserve.txt'
        sentinel.write_bytes(b'original')
        self.run_collect(success=False)
        self.assertEqual(sentinel.read_bytes(), b'original')

    def test_existing_output_archive_preserved(self):
        out = Path(str(self.output) + '.zip')
        out.write_bytes(b'original')
        self.run_collect(success=False)
        self.assertEqual(out.read_bytes(), b'original')

    def test_matching_graphics_is_evidence_not_fresh_collect_only_launch(self):
        self.write('GameLogs/Graphics.txt',
                   f'GFX <Parameters> C:\\Users\\private\\{MAP_NAME}\n'
                   'GFX LocalTime 2026-09-29 15:46:00.559\nGFX <Version> 2.57.0.98285\n'
                   'GFX <DataBuild> B98285\nGFX LastAccountName=private@example.com\n')
        self.run_collect()
        self.assertTrue(self.context['graphics_map_argument_matched'])
        self.assertEqual(len(self.context['observed_version_lines']), 3)
        self.assertNotIn(b'private@example.com', b''.join(self.members.values()))
        self.assertNotIn(b'C:\\Users', b''.join(self.members.values()))

    def test_other_map_graphics_not_used(self):
        self.write('GameLogs/Graphics.txt', 'GFX <Parameters> Other.StormMap\nGFX <Version> 2.57.0.98285\n')
        self.run_collect()
        self.assertFalse(self.context['graphics_map_argument_matched'])
        self.assertEqual(self.context['observed_version_lines'], [])

    def test_large_graphics_not_loaded(self):
        self.write('GameLogs/Graphics.txt', MAP_NAME + '\n' + 'x' * (1024 * 1024))
        self.run_collect()
        self.assertFalse(self.context['graphics_map_argument_matched'])

    def test_unrendered_run_template_refuses_launch(self):
        run = self.run_collect(success=False, mode='Run')
        self.assertIn('unrendered', run.stderr)
        self.assertFalse(self.output.exists())

    def test_rendered_wrong_map_hash_refuses_launch(self):
        script = self.root / 'run_catalog_journal.ps1'
        script.write_text(SCRIPT.read_text().replace('@MAP_SHA256@', '0' * 64), encoding='utf-8')
        (self.root / MAP_NAME).write_bytes(b'not the diagnostic map')
        run = self.run_collect(success=False, script=script, mode='Run')
        self.assertIn('checksum mismatch', run.stderr)
        self.assertFalse(self.output.exists())

    def test_junction_not_followed(self):
        external = self.root / 'outside'
        external.mkdir()
        (external / (TOKEN + '.txt')).write_text('external unrelated data')
        logs = self.docs / 'UserLogs'
        logs.mkdir()
        junction = logs / 'junction'
        run = subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(external)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        try:
            self.run_collect()
            self.assertEqual(len(self.context['journals']), 0)
            self.assertIn('linked_input_ignored', self.context['warnings'])
        finally:
            os.rmdir(junction)


if __name__ == '__main__':
    unittest.main()
