"""Discover the complete root unittest corpus and report explicit platform gaps."""
from __future__ import annotations

import argparse
import ctypes.util
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = (
    ('work/TEN_GREYMANE_source_41810.StormReplay',
     'artifacts/TEN_GREYMANE_source_41810.StormReplay.sha256'),
    ('checkpoints/44256/TEN_GREYMANE_protocol44256.StormReplay',
     'checkpoints/44256/TEN_GREYMANE_protocol44256.StormReplay.sha256'),
    ('client-checkpoints/98285-native-r3/TEN_GREYMANE_client98285_NATIVE_R3_EXPERIMENTAL.StormReplay',
     'client-checkpoints/98285-native-r3/TEN_GREYMANE_client98285_NATIVE_R3_EXPERIMENTAL.StormReplay.sha256'),
    ('work/R4.StormReplay',
     'client-checkpoints/98285-controls-r4/TEN_GREYMANE_client98285_CONTROLS_R4_EXPERIMENTAL.StormReplay.sha256'),
)
WINDOWS_COLLECTOR_CLASSES = (
    'test_catalog_failure_collector.FailureCollectorTests.',
    'test_catalog_journal_collector.JournalCollectorTests.',
)
WINDOWS_NATIVE_EXCLUSIONS = {
    'test_control_masks.NativeFixtureTests.test_all_available_checksums_pass',
    'test_control_masks.NativeFixtureTests.test_corrupt_payload_raw_checksum_is_rejected',
    'test_dragon_dependencies.ActualR4Tests.test_native_repair_is_reproducible_and_preserves_events',
    'test_startup.NativeWriterTests.test_replace_preserves_extended_tables_and_unchanged_members',
}


def platform_skip_reason(test_id: str, platform: str) -> str | None:
    if platform == 'linux' and test_id.startswith(WINDOWS_COLLECTOR_CLASSES):
        return 'Windows-only filesystem collectors exercise Win32 reparse points and PowerShell'
    if platform == 'win32' and test_id in WINDOWS_NATIVE_EXCLUSIONS:
        return 'Native StormLib integration is covered by the Linux libstorm-dev lane'
    return None


class PlatformSkip(unittest.TestCase):
    """Keep each excluded case's original identity and an explicit skip receipt."""

    def __init__(self, original_id: str, reason: str):
        super().__init__('runTest')
        self.original_id = original_id
        self.reason = reason

    def id(self):
        return self.original_id

    def __str__(self):
        return self.original_id

    def runTest(self):
        self.skipTest(self.reason)


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def discover_tests(root: Path):
    modules = sorted(path.stem for path in root.glob('test_*.py'))
    if not modules:
        raise RuntimeError('No root test_*.py modules were found')
    loader = unittest.TestLoader()
    cases = list(flatten(loader.discover(str(root), pattern='test_*.py', top_level_dir=str(root))))
    if loader.errors:
        raise RuntimeError('Unittest discovery has import errors; refusing a partial corpus')
    if not cases:
        raise RuntimeError('Unittest discovery found zero tests')
    populated = {case.__class__.__module__ for case in cases}
    missing = sorted(set(modules) - populated)
    if missing:
        raise RuntimeError('Root test modules contain no discovered tests: ' + ', '.join(missing))
    return modules, cases


def verify_fixtures(root: Path, fixtures=FIXTURES):
    for replay, sidecar in fixtures:
        path = root / replay
        if not path.is_file():
            raise RuntimeError('Required hash-bound fixture is absent: ' + replay)
        tokens = (root / sidecar).read_text(encoding='ascii').split()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if not tokens or digest != tokens[0].lower():
            raise RuntimeError('Required fixture SHA-256 differs: ' + replay)


def require_runtime(root: Path):
    if sys.platform not in ('linux', 'win32'):
        raise RuntimeError('The regression baseline supports Linux and Windows')
    for module in ('heroprotocol', 'six', 'mpyq'):
        if importlib.util.find_spec(module) is None:
            raise RuntimeError('Required pinned parser dependency is absent: ' + module)
    if sys.platform == 'linux' and not ctypes.util.find_library('storm'):
        raise RuntimeError('The Linux lane requires libstorm-dev, not native-test skips')
    if sys.platform == 'win32':
        shell = os.environ.get('HOTS_TEST_POWERSHELL', '')
        if not shell or not shutil.which(shell):
            raise RuntimeError('Select an available HOTS_TEST_POWERSHELL explicitly')
    verify_fixtures(root)


def run_corpus(modules, cases, platform: str, stream=None):
    selected = []
    for case in cases:
        reason = platform_skip_reason(case.id(), platform)
        selected.append(PlatformSkip(case.id(), reason) if reason else case)
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite(selected))
    skips = [{'test': case.id(), 'reason': reason} for case, reason in result.skipped]
    unexpected_skips = [row for row in skips if not platform_skip_reason(row['test'], platform)]
    success = (result.wasSuccessful() and result.testsRun == len(cases)
               and not unexpected_skips and not result.expectedFailures)
    report = {
        'format': 'hots-offline-unit-regression-v1',
        'scope': 'source-and-fixture tests; no client playback or simulation qualification',
        'platform': platform,
        'module_count': len(modules),
        'modules': modules,
        'discovered_tests': len(cases),
        'tests_run': result.testsRun,
        'failures': [case.id() for case, _ in result.failures],
        'errors': [case.id() for case, _ in result.errors],
        'expected_failures': [case.id() for case, _ in result.expectedFailures],
        'unexpected_successes': [case.id() for case in result.unexpectedSuccesses],
        'skips': skips,
        'unexpected_skips': unexpected_skips,
        'successful': success,
    }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    require_runtime(ROOT)
    modules, cases = discover_tests(ROOT)
    report = run_corpus(modules, cases, sys.platform)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({key: report[key] for key in (
        'module_count', 'discovered_tests', 'tests_run', 'successful')}))
    return 0 if report['successful'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
