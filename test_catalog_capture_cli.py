import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import import_catalog_capture as c
import runtime_catalog_probe as p
from test_runtime_catalog_probe import bank, fixture


class CaptureCliTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.anchors = json.loads((Path(c.__file__).parent / 'observations/runtime-catalog-reference-anchors.json').read_text())['unit_anchors']
        count = max(self.anchors.values())
        self.files = fixture(count)
        names = {index: name for name, index in self.anchors.items()}
        for part, first in enumerate(range(1, count + 1, p.CHUNK)):
            last = min(count, first + p.CHUNK - 1)
            self.files[f'{p.TOKEN}_Unit_{part}.StormBank'] = bank(
                {'catalog': 'Unit', 'catalog_id': 1, 'count': count, 'part': part, 'first': first, 'last': last},
                {str(index): names.get(index, f'SyntheticUnit{index}') for index in range(first, last + 1)},
                {str(index): 1 for index in range(first, last + 1)})
        self.context = {
            'format': 'hots-runtime-probe-collection-v1', 'token': p.TOKEN, 'expected_build': p.BUILD,
            'map_sha256': c.PROBE_SHA256, 'launched_by_this_invocation': True,
            'launch_utc': '2026-09-29T13:00:00Z', 'graphics_log_fresh_for_launch': True,
            'observed_version_lines': ['<Version> 2.57.0.98285', '<DataBuild> B98285', 'Heroes of the Storm (B98285)'],
            'export_contents_validated': False, 'runtime_catalog_context_validated': False,
            'client_playback_validated': False,
        }

    def execute(self):
        self.context['input_banks'] = [{'name': n, 'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)} for n, b in self.files.items()]
        capture = self.root / 'capture.zip'
        with zipfile.ZipFile(capture, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, raw in self.files.items():
                archive.writestr(name, raw)
            archive.writestr(c.CONTEXT_NAME, json.dumps(self.context))
        output = self.root / 'result.json'
        result = subprocess.run([sys.executable, c.__file__, str(capture), '--output', str(output)], capture_output=True, text=True)
        return result, output

    def test_synthetic_full_anchor_capture_is_reviewable_not_authenticated(self):
        result, output = self.execute()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(output.read_text())
        self.assertEqual(report['reference_anchor_count'], 48)
        self.assertTrue(report['ready_for_unit_catalog_review'])
        self.assertFalse(report['evidence_is_authenticated'])
        self.assertFalse(report['actual_build_verified'])
        self.assertFalse(report['client_playback_validated'])

    def test_wrong_build_returns_diagnostic_report_and_exit_two(self):
        self.context['observed_version_lines'][0] = '<Version> 2.57.0.98297'
        result, output = self.execute()
        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(output.read_text())
        self.assertFalse(report['ready_for_unit_catalog_review'])
        self.assertIn('version_log_missing_conflicting_or_wrong', report['blocking_checks'])

    def test_missing_chunk_does_not_produce_successful_report(self):
        self.files.pop(p.TOKEN + '_Unit_0.StormBank')
        result, output = self.execute()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
