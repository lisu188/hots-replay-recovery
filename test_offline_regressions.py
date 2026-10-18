import hashlib
import io
from pathlib import Path
import tempfile
import unittest

from scripts import run_offline_regressions as runner


class OfflineRunnerTests(unittest.TestCase):
    def test_empty_discovery_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, 'No root'):
                runner.discover_tests(Path(directory))

    def test_empty_test_module_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'test_empty_offline_probe.py').write_text('VALUE = 1\n')
            with self.assertRaisesRegex(RuntimeError, 'zero tests'):
                runner.discover_tests(root)

    def test_import_failure_cannot_become_a_partial_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'test_broken_offline_probe.py').write_text('raise RuntimeError("fixture failure")\n')
            with self.assertRaisesRegex(RuntimeError, 'import errors'):
                runner.discover_tests(root)

    def test_discovery_includes_every_matching_module(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            names = ['test_first_offline_probe', 'test_second_offline_probe']
            for name in names:
                (root / (name + '.py')).write_text(
                    'import unittest\nclass Probe(unittest.TestCase):\n'
                    '    def test_discovered(self): self.assertTrue(True)\n')
            modules, cases = runner.discover_tests(root)
            report = runner.run_corpus(modules, cases, 'linux', stream=io.StringIO())
            self.assertEqual(report['modules'], names)
            self.assertEqual(report['discovered_tests'], 2)
            self.assertEqual(report['tests_run'], 2)
            self.assertTrue(report['successful'])

    def test_failures_are_reported_as_ids_without_traceback_contents(self):
        class Failure(unittest.TestCase):
            def runTest(self):
                self.fail('fixture content that must not appear in the compact report')
        case = Failure()
        report = runner.run_corpus(['fixture'], [case], 'linux', stream=io.StringIO())
        self.assertFalse(report['successful'])
        self.assertEqual(report['failures'], [case.id()])
        self.assertNotIn('fixture content', str(report))

    def test_unexpected_fixture_or_dependency_skip_fails_the_gate(self):
        class MissingFixture(unittest.TestCase):
            def runTest(self):
                self.skipTest('fixture is missing')
        report = runner.run_corpus(['fixture'], [MissingFixture()], 'linux', stream=io.StringIO())
        self.assertFalse(report['successful'])
        self.assertEqual(len(report['unexpected_skips']), 1)

    def test_declared_platform_exclusion_is_counted_without_running_the_case(self):
        class WindowsOnly(unittest.TestCase):
            def id(self):
                return 'test_catalog_failure_collector.FailureCollectorTests.test_junction_is_not_traversed'

            def runTest(self):
                self.fail('Windows-only case must not execute on Linux')
        report = runner.run_corpus(['fixture'], [WindowsOnly()], 'linux', stream=io.StringIO())
        self.assertTrue(report['successful'])
        self.assertEqual(report['tests_run'], 1)
        self.assertEqual(len(report['skips']), 1)
        self.assertEqual(report['unexpected_skips'], [])

    def test_windows_native_exclusions_do_not_hide_pure_guards(self):
        self.assertTrue(runner.platform_skip_reason(
            'test_control_masks.NativeFixtureTests.test_all_available_checksums_pass', 'win32'))
        self.assertIsNone(runner.platform_skip_reason(
            'test_control_masks.NativeFixtureTests.test_absent_native_library_is_an_error', 'win32'))
        self.assertIsNone(runner.platform_skip_reason(
            'test_control_masks.NativeFixtureTests.test_corrupt_header_checksum_is_rejected', 'win32'))
        self.assertIsNone(runner.platform_skip_reason(
            'test_control_masks.NativeFixtureTests.test_all_available_checksums_pass', 'linux'))

    def test_only_the_precise_windows_symlink_capability_skip_is_accepted(self):
        case = 'test_collection_license_audit.SyntheticLicenseCollectorTests.test_symlink_tree_is_not_followed'
        reason = 'Host does not permit synthetic symlink creation'
        self.assertIsNone(runner.platform_skip_reason(case, 'win32'))
        self.assertTrue(runner.expected_skip(case, reason, 'win32'))
        self.assertFalse(runner.expected_skip(case, reason, 'linux'))
        self.assertFalse(runner.expected_skip(case, 'missing fixture', 'win32'))
        self.assertFalse(runner.expected_skip('some.other.test', reason, 'win32'))

    def test_missing_or_modified_hash_bound_fixture_fails_before_discovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixtures = [('fixture.bin', 'fixture.sha256')]
            with self.assertRaisesRegex(RuntimeError, 'absent'):
                runner.verify_fixtures(root, fixtures)
            (root / 'fixture.bin').write_bytes(b'fixture')
            (root / 'fixture.sha256').write_text('0' * 64 + '\n')
            with self.assertRaisesRegex(RuntimeError, 'SHA-256 differs'):
                runner.verify_fixtures(root, fixtures)
            (root / 'fixture.sha256').write_text(hashlib.sha256(b'fixture').hexdigest() + '\n')
            runner.verify_fixtures(root, fixtures)

    def test_expected_failure_is_not_a_passing_regression_baseline(self):
        class KnownFailure(unittest.TestCase):
            @unittest.expectedFailure
            def runTest(self):
                self.fail('still broken')
        report = runner.run_corpus(['fixture'], [KnownFailure()], 'linux', stream=io.StringIO())
        self.assertFalse(report['successful'])
        self.assertEqual(len(report['expected_failures']), 1)


if __name__ == '__main__':
    unittest.main()
