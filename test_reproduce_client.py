import base64
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from reproduce_client_candidate import ROOT, apply_edits, reproduce
from scripts.restore_artifact import read_base64

RECIPE = ROOT / 'client-checkpoints/98285/recipe.json'
EXPECTED = '2ecb09f353a30363ad59d04b04d439bb7f0ee623d832000d8d13f7a05dbb0486'


def edit(offset=1, before=b'bc', after=b'XY'):
    return {'offset': offset, 'before_base64': base64.b64encode(before).decode(),
            'after_base64': base64.b64encode(after).decode()}


class MemberPatchTests(unittest.TestCase):
    def test_changes_only_requested_bytes(self):
        self.assertEqual(apply_edits(b'abcdef', [edit()]), b'aXYdef')

    def test_empty_edit_list_preserves_bytes(self):
        self.assertEqual(apply_edits(b'abcdef', []), b'abcdef')

    def test_rejects_wrong_original_bytes(self):
        with self.assertRaises(ValueError):
            apply_edits(b'abcdef', [edit(before=b'XX')])

    def test_rejects_overlapping_or_reversed_edits(self):
        for edits in ([edit(), edit()], [edit(4, b'ef'), edit()]):
            with self.subTest(edits=edits), self.assertRaises(ValueError):
                apply_edits(b'abcdef', edits)

    def test_rejects_negative_boolean_and_out_of_bounds_offsets(self):
        for offset in (-1, True, 6, 2**40):
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                apply_edits(b'abcdef', [edit(offset)])

    def test_rejects_insertion_and_size_changes(self):
        for before, after in ((b'', b'x'), (b'bc', b'x'), (b'bc', b'')):
            with self.subTest(before=before, after=after), self.assertRaises(ValueError):
                apply_edits(b'abcdef', [edit(before=before, after=after)])

    def test_rejects_malformed_base64(self):
        value = edit()
        value['after_base64'] = '!!!!'
        with self.assertRaises(ValueError):
            apply_edits(b'abcdef', [value])

    def test_rejects_invalid_or_unbounded_edit_lists(self):
        for value in (None, {}, [edit()] * 10001):
            with self.assertRaises(ValueError):
                apply_edits(b'abcdef', value)


class CandidateReproductionTests(unittest.TestCase):
    def test_reproduces_exact_file_and_all_base64_parts(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'result'
            report = reproduce(RECIPE, output)
            path = output / 'TEN_GREYMANE_client98285_EXPERIMENTAL.StormReplay'
            raw = path.read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), EXPECTED)
            self.assertEqual(report['artifact']['sha256'], EXPECTED)
            self.assertFalse(report['client_playback_validated'])
            self.assertFalse(report['reference_revalidated_this_run'])
            encoded = ''.join(read_base64(path.with_name(path.name + '.base64')).split())
            self.assertEqual(base64.b64decode(encoded, validate=True), raw)

    def test_refuses_to_overwrite_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / 'keep.txt'
            marker.write_text('preserve')
            with self.assertRaises(FileExistsError):
                reproduce(RECIPE, Path(directory))
            self.assertEqual(marker.read_text(), 'preserve')

    def test_tampered_digests_publish_nothing(self):
        original = json.loads(RECIPE.read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for key in ('base_sha256', 'header_before_sha256', 'game_before_sha256',
                        'game_after_sha256', 'output_sha256'):
                recipe = copy.deepcopy(original)
                recipe[key] = '0' * 64
                source = root / (key + '.json')
                source.write_text(json.dumps(recipe))
                output = root / key
                with self.subTest(key=key), self.assertRaises(ValueError):
                    reproduce(source, output)
                self.assertFalse(output.exists())

    def test_recipe_cannot_claim_client_playback(self):
        recipe = json.loads(RECIPE.read_text())
        recipe['client_playback_validated'] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'recipe.json'
            path.write_text(json.dumps(recipe))
            with self.assertRaisesRegex(ValueError, 'cannot assert playback'):
                reproduce(path, Path(directory) / 'result')

    def test_recipe_rejects_path_injection_in_builds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for value in (True, '../96477', -1, 0, 2**32):
                recipe = json.loads(RECIPE.read_text())
                recipe['base_build'] = value
                path = root / 'recipe.json'
                path.write_text(json.dumps(recipe))
                with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'Invalid recipe build'):
                    reproduce(path, root / 'result')


if __name__ == '__main__':
    unittest.main()
