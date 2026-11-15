"""Exercise the publication command used by the R5 workflow on JSON fixtures."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parent
R5 = '98285-dragon-r5'
ARTIFACT = {
    'name': 'TEN_GREYMANE_client98285_DRAGON_R5_EXPERIMENTAL.StormReplay',
    'sha256': 'f5eac2c4de55db9cc834c97825ac89d5fc0bb4807a2b216ba5ca7fbc63e45f11',
    'size': 1255308, 'parts': 23, 'base64_roundtrip_validated': True,
}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


class DragonPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'work/dragon-r5'
        self.destination = self.root / 'client-checkpoints' / R5
        self.report = {
            'artifact': copy.deepcopy(ARTIFACT), 'build': 98285,
            'status': 'experimental-awaiting-client-test',
            'reference_sha256': 'a' * 64,
            'changed_members': ['replay.initData'], 'changes': 5,
            'header_bytes_preserved': True, 'all_event_bytes_preserved': True,
            'client_playback_validated': False, 'simulation_compatibility_validated': False,
        }
        self.verification = {
            'run_id': 99, 'tested_commit': '1' * 40, 'test_count': 177,
            'repeated_generation_identical': True, 'matches_local_sha256': True,
            'candidate_sha256': ARTIFACT['sha256'],
            'source_pins': {'repair_dragon_dependencies.py': 'b' * 64},
            'private_donor_supplied_to_ci': False,
            'client_playback_validated': False, 'simulation_compatibility_validated': False,
        }
        self.progress = {
            'latest_client_candidate': 98285,
            'latest_client_candidate_id': '98285-resumable-r8',
            'next': 'Investigate the recorded R8 failure.',
            'playback_investigation': {
                'next_trial': '98285-resumable-r8',
                'observations': [{'error': 'ReplayDesync', 'clock': '0:04'}],
                'unknown_future_field': {'preserve': [1, 'yes']},
            },
            'unknown_top_level': {'original': True},
            'client_candidates': {
                '98285-resumable-r8': {'status': 'native-result-recorded', 'unknown': 8},
                R5: {
                    'build': 98285, 'name': ARTIFACT['name'],
                    'sha256': ARTIFACT['sha256'], 'size': ARTIFACT['size'],
                    'base64_parts': ARTIFACT['parts'],
                    'status': 'native-test-result-recorded',
                    'client_playback_validated': True,
                    'simulation_compatibility_validated': False,
                    'user_observation': {'error': 'ReplayDesync', 'clock': '0:04'},
                    'unknown_evidence': [{'retain': True}],
                    'ci_run': 12, 'ci_validation_passed': True,
                    'tests_passed': 166, 'tests_skipped': 0,
                },
            },
        }
        write_json(self.source / 'report.json', self.report)
        write_json(self.source / 'ci-verification.json', self.verification)
        write_json(self.source / 'reference-observation.json', {'synthetic': 'observation'})
        write_json(self.source / 'candidate-profile.json', {'synthetic': 'profile'})
        (self.source / 'changes.jsonl').write_text('{"synthetic": "delta"}\n', encoding='ascii')
        write_json(self.root / 'progress.json', self.progress)
        published_report = dict(self.report, status='native-result-recorded',
                                native_observation={'message': 'ReplayDesync'})
        write_json(self.destination / 'report.json', published_report)
        write_json(self.destination / 'ci-verification.json', dict(
            self.verification, run_id=12, client_playback_validated=True,
            extra_evidence={'preserve': 'native observation'}))
        (self.destination / 'retained.jsonl').write_text('{"keep": true}\n', encoding='utf-8')
        # Reuse the checked-in ASCII publication, never a raw replay fixture.
        for path in (REPO / 'client-checkpoints' / R5).iterdir():
            if '.base64.part' in path.name or path.suffix == '.sha256':
                raw = path.read_bytes()
                (self.source / path.name).write_bytes(raw)
                (self.destination / path.name).write_bytes(raw)

    def run_publication(self, success=True):
        # Execute the very command wired into the workflow, rather than a
        # duplicate of its former inline progress-writing implementation.
        workflow = (REPO / '.github/workflows/dragon-dependencies.yml').read_text(encoding='utf-8')
        commands = [line.strip() for line in workflow.splitlines()
                    if line.strip().startswith('python scripts/publish_dragon_checkpoint.py ')]
        self.assertEqual(len(commands), 1)
        command = shlex.split(commands[0])
        command[0] = sys.executable
        command[1] = str(REPO / command[1])
        command[1:1] = ['-I', '-S', '-B']
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True, timeout=15)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('ValueError:', result.stderr)
        return result

    def tree(self):
        return {path.relative_to(self.root).as_posix():
                None if path.is_dir() else path.read_bytes()
                for path in self.root.rglob('*')}

    def read_progress(self):
        return json.loads((self.root / 'progress.json').read_text(encoding='utf-8'))

    def without_existing_r5(self):
        del self.progress['client_candidates'][R5]
        write_json(self.root / 'progress.json', self.progress)
        for path in self.destination.iterdir():
            path.unlink()
        self.destination.rmdir()
        (self.source / 'ignored.bin').write_bytes(b'not a checkpoint text artifact')
        write_json(self.source / 'unrelated-extra.json', {'not': 'checkpoint metadata'})

    def assert_refuses_without_writes(self):
        before = self.tree()
        self.run_publication(success=False)
        self.assertEqual(self.tree(), before)

    def test_republication_changes_only_ci_fields_and_preserves_native_evidence(self):
        preserved = {p.name: p.read_bytes() for p in self.destination.iterdir()
                     if p.name != 'ci-verification.json'}
        self.run_publication()
        expected = copy.deepcopy(self.progress)
        expected['client_candidates'][R5].update(
            ci_run=99, ci_validation_passed=True, tests_passed=177, tests_skipped=0)
        self.assertEqual(self.read_progress(), expected)
        for name, raw in preserved.items():
            self.assertEqual((self.destination / name).read_bytes(), raw)
        ci = json.loads((self.destination / 'ci-verification.json').read_text(encoding='utf-8'))
        self.assertEqual(ci['run_id'], 99)
        self.assertTrue(ci['client_playback_validated'])
        self.assertEqual(ci['extra_evidence'], {'preserve': 'native observation'})

    def test_identical_republication_is_idempotent(self):
        self.run_publication()
        before = self.tree()
        self.run_publication()
        self.assertEqual(self.tree(), before)

    def test_first_registration_copies_text_without_selecting_r5(self):
        self.without_existing_r5()
        self.run_publication()
        actual = self.read_progress()
        self.assertEqual(actual['latest_client_candidate_id'], '98285-resumable-r8')
        self.assertEqual(actual['next'], self.progress['next'])
        self.assertEqual(actual['playback_investigation'], self.progress['playback_investigation'])
        self.assertEqual(actual['client_candidates'][R5]['sha256'], ARTIFACT['sha256'])
        self.assertFalse(actual['client_candidates'][R5]['client_playback_validated'])
        self.assertEqual((self.destination / 'report.json').read_bytes(),
                         (self.source / 'report.json').read_bytes())
        self.assertEqual(len(list(self.destination.glob('*.base64.part*'))), 23)
        self.assertFalse((self.destination / 'ignored.bin').exists())
        self.assertFalse((self.destination / 'unrelated-extra.json').exists())

    def test_first_registration_does_not_create_active_selection_fields(self):
        self.without_existing_r5()
        write_json(self.root / 'progress.json', {'goal': 'full recovery'})
        self.run_publication()
        actual = self.read_progress()
        self.assertEqual(set(actual), {'goal', 'client_candidates'})

    def test_changed_existing_candidate_identity_refuses_before_any_write(self):
        original = copy.deepcopy(self.progress)
        for field, value in (('sha256', '0' * 64), ('name', 'different.StormReplay'),
                             ('size', 123), ('base64_parts', 2), ('build', 98348),
                             ('size', True)):
            with self.subTest(field=field, value=value):
                modified = copy.deepcopy(original)
                modified['client_candidates'][R5][field] = value
                write_json(self.root / 'progress.json', modified)
                self.assert_refuses_without_writes()

    def test_changed_generated_artifact_refuses_before_any_write(self):
        for field, value in (('sha256', '0' * 64), ('name', 'different.StormReplay'),
                             ('size', 123), ('parts', 2)):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.report)
                changed['artifact'][field] = value
                write_json(self.source / 'report.json', changed)
                self.assert_refuses_without_writes()

    def test_changed_published_report_identity_refuses_before_any_write(self):
        changed = copy.deepcopy(self.report)
        changed['artifact']['sha256'] = '0' * 64
        write_json(self.destination / 'report.json', changed)
        self.assert_refuses_without_writes()

    def test_changed_generated_ci_identity_refuses_before_any_write(self):
        changed = dict(self.verification, candidate_sha256='0' * 64)
        write_json(self.source / 'ci-verification.json', changed)
        self.assert_refuses_without_writes()

    def test_changed_published_ci_identity_refuses_before_any_write(self):
        changed = dict(self.verification, candidate_sha256='0' * 64)
        write_json(self.destination / 'ci-verification.json', changed)
        self.assert_refuses_without_writes()

    def test_failed_or_incomplete_ci_refuses_before_any_write(self):
        for field, value in (('test_count', 165), ('run_id', True),
                             ('matches_local_sha256', False),
                             ('repeated_generation_identical', False)):
            with self.subTest(field=field):
                write_json(self.source / 'ci-verification.json', dict(self.verification, **{field: value}))
                self.assert_refuses_without_writes()

    def test_incomplete_first_publication_refuses_without_creating_destination(self):
        self.without_existing_r5()
        next(self.source.glob('*.base64.part*')).unlink()
        self.assert_refuses_without_writes()
        self.assertFalse(self.destination.exists())

    def test_corrupt_generated_base64_refuses_before_any_write(self):
        part = next(self.source.glob('*.base64.part*'))
        raw = bytearray(part.read_bytes())
        raw[0] = ord('A') if raw[0] != ord('A') else ord('B')
        part.write_bytes(raw)
        self.assert_refuses_without_writes()

    def test_corrupt_retained_base64_refuses_before_any_write(self):
        part = next(self.destination.glob('*.base64.part*'))
        raw = bytearray(part.read_bytes())
        raw[0] = ord('A') if raw[0] != ord('A') else ord('B')
        part.write_bytes(raw)
        self.assert_refuses_without_writes()

    def test_corrupt_partial_first_destination_cannot_be_mixed_with_source(self):
        self.without_existing_r5()
        self.destination.mkdir()
        source_part = next(self.source.glob('*.base64.part*'))
        (self.destination / source_part.name).write_bytes(b'AAAA')
        self.assert_refuses_without_writes()

    def test_real_checked_in_r5_record_and_metadata_survive_ci_refresh(self):
        published = REPO / 'client-checkpoints' / R5
        for name in ('report.json', 'ci-verification.json'):
            (self.destination / name).write_bytes((published / name).read_bytes())
        real = json.loads((REPO / 'progress.json').read_text(encoding='utf-8'))
        candidate = copy.deepcopy(real['client_candidates'][R5])
        candidate['additional_native_evidence'] = {'error': 'ReplayDesync', 'clock': '0:04'}
        self.progress['client_candidates'][R5] = candidate
        write_json(self.root / 'progress.json', self.progress)
        before = {path.name: path.read_bytes() for path in self.destination.iterdir()
                  if path.name != 'ci-verification.json'}
        self.run_publication()
        candidate.update(ci_run=99, ci_validation_passed=True, tests_passed=177, tests_skipped=0)
        self.assertEqual(self.read_progress()['client_candidates'][R5], candidate)
        self.assertEqual({path.name: path.read_bytes() for path in self.destination.iterdir()
                          if path.name != 'ci-verification.json'}, before)

    def test_null_existing_candidate_is_not_treated_as_first_publication(self):
        self.progress['client_candidates'][R5] = None
        write_json(self.root / 'progress.json', self.progress)
        self.assert_refuses_without_writes()


if __name__ == '__main__':
    unittest.main()
