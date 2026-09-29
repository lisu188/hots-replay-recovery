from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from migrate_replay import BitVector, SemanticDecoder
from mpq_reader import MPQArchive
from protocol_loader import load_protocol
from repair_control_masks import DONOR_DIGEST, EXPECTED_INPUT, EXPECTED_REFERENCE, SOURCE_DIGEST, integrity, masks, observe_reference, repair, transform, validate_observation


def observation():
    return {'format': 'hots-control-mask-observation-v1', 'reference_sha256': DONOR_DIGEST,
            'declared_build': 98285, 'schema_build': 96477, 'full_reference_roundtrip': True,
            'masks': [list(value) for value in EXPECTED_REFERENCE]}


def initial():
    slots = [{'m_allowedControls': BitVector(*value), 'unchanged': [i, {'value': i + 1}]} for i, value in enumerate(EXPECTED_INPUT)]
    return {'m_syncLobbyState': {'m_gameDescription': {'m_slotDescriptions': slots,
            'm_gameOptions': {'m_ammId': 50001}}, 'unchanged': 'lobby'}, 'unchanged': b'header'}


class ObservationTests(unittest.TestCase):
    def test_accepts_exact_measured_masks(self):
        self.assertEqual([(value.length, value.value) for value in validate_observation(observation())], EXPECTED_REFERENCE)

    def test_rejects_unknown_format(self):
        value = observation()
        value['format'] = 'unknown'
        with self.assertRaises(ValueError):
            validate_observation(value)

    def test_rejects_unknown_reference(self):
        value = observation()
        value['reference_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            validate_observation(value)

    def test_rejects_different_build(self):
        value = observation()
        value['declared_build'] = 98297
        with self.assertRaises(ValueError):
            validate_observation(value)

    def test_rejects_boolean_build(self):
        value = observation()
        value['declared_build'] = True
        with self.assertRaises(ValueError):
            validate_observation(value)

    def test_requires_completed_reference_roundtrip(self):
        for marker in (None, False, 1, 'true'):
            with self.subTest(marker=marker):
                value = observation()
                value['full_reference_roundtrip'] = marker
                with self.assertRaises(ValueError):
                    validate_observation(value)

    def test_rejects_wrong_count(self):
        value = observation()
        value['masks'].pop()
        with self.assertRaises(ValueError):
            validate_observation(value)

    def test_rejects_wrong_mask_values(self):
        value = observation()
        value['masks'][10][1] = 29
        with self.assertRaises(ValueError):
            validate_observation(value)

    def test_rejects_noninteger_mask(self):
        for marker in (True, 10.0, '10'):
            with self.subTest(marker=marker):
                value = observation()
                value['masks'][0][0] = marker
                with self.assertRaises(ValueError):
                    validate_observation(value)

    def test_rejects_nonlist_representation(self):
        value = observation()
        value['masks'][0] = (10, 1023)
        with self.assertRaises(ValueError):
            validate_observation(value)

    def test_reference_hash_checked_before_decode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'wrong.StormReplay'
            path.write_bytes(b'not donor')
            with patch('repair_control_masks.inspect_reference') as inspect:
                with self.assertRaises(ValueError):
                    observe_reference(path)
                inspect.assert_not_called()


class TransformTests(unittest.TestCase):
    def test_changes_exactly_sixteen_control_masks(self):
        source = initial()
        changed, changes = transform(source, observation())
        self.assertEqual(len(changes), 16)
        self.assertEqual([(value.length, value.value) for value in masks(changed)], EXPECTED_REFERENCE)
        for slot, original_slot in zip(changed['m_syncLobbyState']['m_gameDescription']['m_slotDescriptions'], source['m_syncLobbyState']['m_gameDescription']['m_slotDescriptions'], strict=True):
            slot['m_allowedControls'] = original_slot['m_allowedControls']
        self.assertEqual(changed, source)

    def test_source_is_not_mutated(self):
        source = initial()
        unchanged = copy.deepcopy(source)
        changed, _ = transform(source, observation())
        changed['m_syncLobbyState']['m_gameDescription']['m_slotDescriptions'][0]['unchanged'][1]['value'] = -1
        self.assertEqual(source, unchanged)

    def test_leading_ten_bits_are_preserved(self):
        changed, changes = transform(initial(), observation())
        for old, new in zip(EXPECTED_INPUT, masks(changed), strict=True):
            self.assertEqual(old[1] >> 5, new.value)
        self.assertTrue(all(change['removed_bits'] == 5 for change in changes))

    def test_removed_permissions_are_explicit_not_claimed_lossless(self):
        _, changes = transform(initial(), observation())
        self.assertEqual([change['removed_suffix_value'] for change in changes], [31] * 10 + [0] * 6)

    def test_no_matchmaking_change(self):
        changed, _ = transform(initial(), observation())
        self.assertEqual(changed['m_syncLobbyState']['m_gameDescription']['m_gameOptions']['m_ammId'], 50001)

    def test_rejects_already_converted_masks(self):
        changed, _ = transform(initial(), observation())
        with self.assertRaises(ValueError):
            transform(changed, observation())

    def test_rejects_changed_source_mask(self):
        value = initial()
        value['m_syncLobbyState']['m_gameDescription']['m_slotDescriptions'][0]['m_allowedControls'] = BitVector(15, 32766)
        with self.assertRaises(ValueError):
            transform(value, observation())

    def test_rejects_missing_slots(self):
        value = initial()
        value['m_syncLobbyState']['m_gameDescription']['m_slotDescriptions'].pop()
        with self.assertRaises(ValueError):
            masks(value)

    def test_rejects_invalid_logical_values(self):
        for vector in (BitVector(0, 0), BitVector(256, 0), BitVector(10, -1), BitVector(10, 1024), BitVector(True, 0), BitVector(10, True), (10, 1)):
            with self.subTest(vector=vector):
                value = initial()
                value['m_syncLobbyState']['m_gameDescription']['m_slotDescriptions'][0]['m_allowedControls'] = vector
                with self.assertRaises(ValueError):
                    masks(value)


class OutputGuardTests(unittest.TestCase):
    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            with self.assertRaises(FileExistsError):
                repair(path / 'missing', path, observation())

    def test_source_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source'
            path.write_bytes(b'source')
            with self.assertRaises(FileExistsError):
                repair(path, path, observation())
            self.assertEqual(path.read_bytes(), b'source')

    def test_wrong_source_leaves_no_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            source = path / 'source'
            source.write_bytes(b'source')
            with self.assertRaises(ValueError):
                repair(source, path / 'result', observation())
            self.assertFalse((path / 'result').exists())


class NativeFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(__file__).parent / 'client-checkpoints/98285-native-r3/TEN_GREYMANE_client98285_NATIVE_R3_EXPERIMENTAL.StormReplay'
        if not cls.source.is_file():
            raise RuntimeError('Restore the hash-bound R3 fixture before running these tests')
        import hashlib
        if hashlib.sha256(cls.source.read_bytes()).hexdigest() != SOURCE_DIGEST:
            raise RuntimeError('R3 test fixture digest mismatch')

    def test_real_r3_masks_have_the_measured_difference(self):
        p = load_protocol(96477)
        archive = MPQArchive(self.source)
        try:
            source = SemanticDecoder(archive.read_file('replay.initData'), p.typeinfos).instance(p.replay_initdata_typeid)
        finally:
            archive.close()
        self.assertEqual([(v.length, v.value) for v in masks(source)], EXPECTED_INPUT)
        changed, changes = transform(source, observation())
        self.assertEqual([(v.length, v.value) for v in masks(changed)], EXPECTED_REFERENCE)
        self.assertEqual(len(changes), 16)

    def test_all_available_checksums_pass(self):
        result = integrity(self.source)
        self.assertTrue(result['all_available_checksums_passed'])
        self.assertEqual(len(result['member_verification_flags']), 14)
        self.assertFalse(any(result['raw_table_results'].values()))

    def test_absent_native_library_is_an_error(self):
        with patch('repair_control_masks.ctypes.util.find_library', return_value=None):
            with self.assertRaises(RuntimeError):
                integrity(self.source)

    def test_corrupt_header_checksum_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'corrupt.StormReplay'
            raw = bytearray(self.source.read_bytes())
            import struct
            base = struct.unpack_from('<I', raw, 8)[0]
            raw[base + 192] ^= 1
            path.write_bytes(raw)
            with self.assertRaises(ValueError):
                integrity(path)

    def test_corrupt_payload_raw_checksum_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'corrupt.StormReplay'
            raw = bytearray(self.source.read_bytes())
            archive = MPQArchive(self.source)
            try:
                block = archive.block_table[archive.get_hash_table_entry('replay.initData').block_table_index]
                raw[archive.header['offset'] + block.offset + block.archived_size] ^= 1
            finally:
                archive.close()
            path.write_bytes(raw)
            with self.assertRaises(ValueError):
                integrity(path)


if __name__ == '__main__':
    unittest.main()
