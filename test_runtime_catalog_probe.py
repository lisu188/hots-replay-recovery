import copy
import hashlib
import json
import os
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import runtime_catalog_probe as p


def bank(meta, entries=None, valid=None):
    root = ET.Element('Bank', {'version': '1'})
    sections = {'meta': {'format': 'hots-runtime-catalog-v1', 'token': p.TOKEN,
                'session': '123_456', 'expected_build': p.BUILD, 'base_map_sha256': p.MAP_SHA256,
                'complete': 1, **meta}}
    if entries is not None:
        sections['entries'] = entries
    if valid is not None:
        sections['valid'] = valid
    for section, values in sections.items():
        node = ET.SubElement(root, 'Section', {'name': section})
        for key, value in values.items():
            k = ET.SubElement(node, 'Key', {'name': key})
            ET.SubElement(k, 'Value', {'int' if type(value) is int else 'string': str(value)})
    return ET.tostring(root)


def fixture(count=2):
    result = {p.TOKEN + '_Manifest.StormBank': bank({'catalog': 'Manifest', 'Unit': count, 'Abil': count})}
    for label, cid in [('Unit', 1), ('Abil', 2)]:
        for part, first in enumerate(range(1, count + 1, p.CHUNK)):
            last = min(count, first + p.CHUNK - 1)
            result[f'{p.TOKEN}_{label}_{part}.StormBank'] = bank(
                {'catalog': label, 'catalog_id': cid, 'count': count, 'part': part, 'first': first, 'last': last},
                {str(i): f'{label}{i}' for i in range(first, last + 1)},
                {str(i): 1 for i in range(first, last + 1)})
    return result


def mutate(raw, section, key, value):
    root = ET.fromstring(raw)
    k = root.find(f"Section[@name='{section}']/Key[@name='{key}']/Value")
    k.attrib.clear()
    k.set('int' if type(value) is int else 'string', str(value))
    return ET.tostring(root)


class ScriptTests(unittest.TestCase):
    source = b'include "TriggerLibs/NativeLib"\nvoid InitMap () {\n InitLibs();\n InitGlobals();\n InitTriggers();\n}\n'

    def test_original_initializer_is_preserved(self):
        result = p.instrument_script(self.source)
        self.assertTrue(result.startswith(self.source.replace(b'InitMap', b'HRC_OriginalInitMap')))
        self.assertEqual(result.count(b'void InitMap ('), 1)

    def test_bank_names_are_dedicated(self):
        source = p.galaxy_source()
        self.assertIn(p.TOKEN, source)
        self.assertNotIn('PlayerSettings', source)
        self.assertNotIn('BankDelete', source)

    def test_no_catalog_index_filtering(self):
        source = p.galaxy_source()
        self.assertLess(source.index('BankValueSetFromString(output, "entries"'), source.index('if (CatalogEntryIsValid'))
        self.assertIn('index <= last', source)
        self.assertIn('first = 1;', source)

    def test_unexpected_initializer_is_rejected(self):
        with self.assertRaises(ValueError):
            p.instrument_script(b'void InitMap () { other(); }')

    def test_duplicate_initializer_is_rejected(self):
        with self.assertRaises(ValueError):
            p.instrument_script(self.source + self.source)

    def test_preinstrumented_script_is_rejected(self):
        with self.assertRaises(ValueError):
            p.instrument_script(p.instrument_script(self.source))

    def test_oversized_script_is_rejected(self):
        with self.assertRaises(ValueError):
            p.instrument_script(b' ' * (1024 * 1024 + 1))

    def test_extra_suffix_is_rejected(self):
        with self.assertRaises(ValueError):
            p.instrument_script(self.source + b'void other() {}')

    def test_no_replay_or_desync_modification(self):
        s = p.galaxy_source()
        self.assertNotIn('replay.sync', s)
        self.assertNotIn('CatalogFieldValueSet', s)
        self.assertNotIn('Synchronous', s)


class PreloadTests(unittest.TestCase):
    def test_original_preloads_preserved(self):
        root = ET.fromstring(p.instrument_banks(b'<BankList><Bank Name="PlayerSettings" Player="1"/></BankList>'))
        self.assertEqual(root[0].attrib, {'Name': 'PlayerSettings', 'Player': '1'})
        self.assertEqual(len(root), 130)

    def test_no_duplicate_output_names(self):
        root = ET.fromstring(p.instrument_banks(b'<BankList/>'))
        names = [n.attrib['Name'] for n in root]
        self.assertEqual(len(set(names)), len(names))
        self.assertTrue(all(n.startswith(p.TOKEN) for n in names))

    def test_existing_probe_preload_rejected(self):
        raw = f'<BankList><Bank Name="{p.TOKEN}_Unit_0" Player="1"/></BankList>'.encode()
        with self.assertRaises(ValueError):
            p.instrument_banks(raw)

    def test_entities_rejected(self):
        with self.assertRaises(ValueError):
            p.instrument_banks(b'<!DOCTYPE x [<!ENTITY x "x">]><BankList/>')

    def test_wrong_root_rejected(self):
        with self.assertRaises(ValueError):
            p.instrument_banks(b'<Bank/>')

    def test_wrong_preload_element_rejected(self):
        with self.assertRaises(ValueError):
            p.instrument_banks(b'<BankList><Wrong/></BankList>')


class BankTests(unittest.TestCase):
    def setUp(self):
        self.files = fixture()
        self.unit = p.TOKEN + '_Unit_0.StormBank'
        self.abil = p.TOKEN + '_Abil_0.StormBank'
        self.manifest = p.TOKEN + '_Manifest.StormBank'
        self.anchors = {'Unit1': 1, 'Unit2': 2}

    def test_complete_synthetic_export_not_playback_claim(self):
        r = p.combine_banks(self.files, self.anchors)
        self.assertTrue(r['all_unit_anchors_match'])
        self.assertFalse(r['client_playback_validated'])
        self.assertFalse(r['actual_build_verified'])
        self.assertFalse(r['ability_indices_independently_validated'])
        self.assertFalse(r['catalog_context_equivalence_proven'])
        self.assertFalse(r['automatically_applied_to_replay'])

    def test_multiple_chunks_preserve_native_indices(self):
        r = p.combine_banks(fixture(258), {'Unit258': 258})
        self.assertEqual(r['catalogs']['Unit'][-1]['index'], 258)
        self.assertEqual(len(r['catalogs']['Unit']), 258)

    def test_unknown_anchor_prevents_acceptance(self):
        r = p.combine_banks(self.files, {'Unit1': 2})
        self.assertFalse(r['all_unit_anchors_match'])
        self.assertEqual(len(r['anchor_mismatches']), 1)

    def test_invalid_entry_retains_its_index(self):
        self.files[self.unit] = mutate(self.files[self.unit], 'valid', '2', 0)
        r = p.combine_banks(self.files, {'Unit1': 1})
        self.assertEqual(r['catalogs']['Unit'][1], {'index': 2, 'id': 'Unit2', 'valid': False})

    def test_invalid_entry_cannot_satisfy_anchor(self):
        self.files[self.unit] = mutate(self.files[self.unit], 'valid', '2', 0)
        self.assertFalse(p.combine_banks(self.files, self.anchors)['all_unit_anchors_match'])

    def test_manifest_required(self):
        del self.files[self.manifest]
        with self.assertRaises(ValueError):
            p.combine_banks(self.files, self.anchors)

    def test_empty_export_rejected(self):
        with self.assertRaises(ValueError):
            p.combine_banks({}, self.anchors)

    def test_missing_chunk_rejected(self):
        del self.files[self.unit]
        with self.assertRaises(ValueError):
            p.combine_banks(self.files, self.anchors)

    def test_mixed_sessions_rejected(self):
        self.files[self.unit] = mutate(self.files[self.unit], 'meta', 'session', '999_888')
        with self.assertRaises(ValueError):
            p.combine_banks(self.files, self.anchors)

    def test_unfinished_bank_rejected(self):
        self.files[self.unit] = mutate(self.files[self.unit], 'meta', 'complete', 0)
        with self.assertRaises(ValueError):
            p.combine_banks(self.files, self.anchors)

    def test_wrong_expected_build_rejected(self):
        self.files[self.unit] = mutate(self.files[self.unit], 'meta', 'expected_build', 98297)
        with self.assertRaises(ValueError):
            p.combine_banks(self.files, self.anchors)

    def test_wrong_map_rejected(self):
        self.files[self.unit] = mutate(self.files[self.unit], 'meta', 'base_map_sha256', '0' * 64)
        with self.assertRaises(ValueError):
            p.combine_banks(self.files, self.anchors)

    def test_count_bound_enforced(self):
        self.files[self.manifest] = mutate(self.files[self.manifest], 'meta', 'Unit', p.MAX_ENTRIES + 1)
        with self.assertRaises(ValueError):
            p.combine_banks(self.files, self.anchors)

    def test_stale_extra_file_rejected(self):
        self.files['unrelated.StormBank'] = self.files[self.unit]
        with self.assertRaises(ValueError):
            p.combine_banks(self.files, self.anchors)

    def test_duplicate_bank_key_rejected(self):
        raw = self.files[self.unit].replace(b'</Section>', b'<Key name="token"><Value string="x"/></Key></Section>', 1)
        with self.assertRaises(ValueError):
            p.parse_bank(raw)

    def test_duplicate_section_rejected(self):
        raw = self.files[self.unit].replace(b'</Bank>', b'<Section name="meta"/></Bank>')
        with self.assertRaises(ValueError):
            p.parse_bank(raw)

    def test_unsupported_typed_value_rejected(self):
        with self.assertRaises(ValueError):
            p.parse_bank(self.files[self.unit].replace(b'int="1"', b'fixed="1"', 1))

    def test_string_integer_substitution_rejected(self):
        self.files[self.unit] = mutate(self.files[self.unit], 'meta', 'expected_build', '98285')
        with self.assertRaises(ValueError):
            p.combine_banks(self.files, self.anchors)

    def test_duplicate_identifier_rejected(self):
        self.files[self.unit] = mutate(self.files[self.unit], 'entries', '2', 'Unit1')
        with self.assertRaises(ValueError):
            p.combine_banks(self.files, self.anchors)

    def test_missing_index_rejected(self):
        root = ET.fromstring(self.files[self.unit])
        section = root.find("Section[@name='entries']")
        section.remove(section[0])
        self.files[self.unit] = ET.tostring(root)
        with self.assertRaises(ValueError):
            p.combine_banks(self.files, self.anchors)

    def test_nonboolean_validity_rejected(self):
        self.files[self.unit] = mutate(self.files[self.unit], 'valid', '2', 2)
        with self.assertRaises(ValueError):
            p.combine_banks(self.files, self.anchors)

    def test_empty_anchors_rejected(self):
        with self.assertRaises(ValueError):
            p.combine_banks(self.files, {})

    def test_empty_names_are_retained(self):
        self.files[self.unit] = mutate(self.files[self.unit], 'entries', '2', '')
        self.files[self.unit] = mutate(self.files[self.unit], 'valid', '2', 0)
        r = p.combine_banks(self.files, {'Unit1': 1})
        self.assertEqual(r['catalogs']['Unit'][1]['id'], '')

    def test_catalog_ids_must_be_distinct(self):
        self.files[self.abil] = mutate(self.files[self.abil], 'meta', 'catalog_id', 1)
        with self.assertRaises(ValueError):
            p.combine_banks(self.files, self.anchors)

    def test_entities_rejected(self):
        with self.assertRaises(ValueError):
            p.parse_bank(b'<!DOCTYPE Bank [<!ENTITY x "x">]><Bank/>')

    def test_oversized_bank_rejected(self):
        with self.assertRaises(ValueError):
            p.parse_bank(b' ' * (4 * 1024 * 1024 + 1))

    def test_synthetic_fixture_does_not_mutate(self):
        before = copy.deepcopy(self.files)
        p.combine_banks(self.files, self.anchors)
        self.assertEqual(before, self.files)


class BuildGuards(unittest.TestCase):
    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t)
            with self.assertRaises(FileExistsError):
                p.build_probe(path / 'absent', path)

    def test_hash_rejection_before_native_loading(self):
        with tempfile.TemporaryDirectory() as t:
            source = Path(t) / 'bad.s2ma'
            source.write_bytes(b'bad')
            out = Path(t) / 'output'
            with self.assertRaises(ValueError):
                p.build_probe(source, out, 'not-a-library')
            self.assertFalse(out.exists())

    def test_native_library_required(self):
        with self.assertRaises(OSError):
            p.Storm('/absent/libstorm.so')


if __name__ == '__main__':
    unittest.main()
