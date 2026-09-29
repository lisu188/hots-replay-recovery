import struct
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import repair_resumable_events as r


class CodecTests(unittest.TestCase):
    def setUp(self):
        self.old = r.Record(61, 1, 1, b'Player', 0xff245cff)
        self.new = replace(self.old, legacy_color=None)

    def test_legacy_fixture_byte_order(self):
        raw = bytes.fromhex('3d0000000101ff5c24ff0600') + b'Player'
        self.assertEqual(r.encode([self.old], True), raw)
        self.assertEqual(r.decode(raw, True), [self.old])

    def test_modern_fixture_byte_order(self):
        raw = bytes.fromhex('3d00000001010600') + b'Player'
        self.assertEqual(r.encode([self.new], False), raw)
        self.assertEqual(r.decode(raw, False), [self.new])

    def test_legacy_fixture_rejected_by_modern_layout(self):
        with self.assertRaises(ValueError): r.decode(r.encode([self.old], True), False)

    def test_modern_fixture_rejected_by_legacy_layout(self):
        with self.assertRaises(ValueError): r.decode(r.encode([self.new], False), True)

    def test_empty_stream_is_distinct_from_missing(self):
        self.assertEqual(r.decode(b'', True), [])
        self.assertEqual(r.encode([], False), b'')
        with self.assertRaises(ValueError): r.decode(None, False)

    def test_explicit_boolean_layout_required(self):
        with self.assertRaises(ValueError): r.decode(b'', 1)
        with self.assertRaises(ValueError): r.encode([], 0)

    def test_all_observed_kinds_roundtrip(self):
        for kind in r.KINDS:
            with self.subTest(kind=kind):
                row = replace(self.old, kind=kind)
                self.assertEqual(r.decode(r.encode([row], True), True), [row])

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError): r.encode([replace(self.old, kind=4)], True)

    def test_boolean_kind_rejected(self):
        with self.assertRaises(ValueError): r.encode([replace(self.old, kind=True)], True)

    def test_boolean_user_rejected(self):
        with self.assertRaises(ValueError): r.encode([replace(self.old, user_id=False)], True)

    def test_unknown_user_rejected(self):
        with self.assertRaises(ValueError): r.encode([replace(self.old, user_id=17)], True)

    def test_system_record_roundtrip(self):
        row = r.Record(610, 5, 16, b'', 0xffffffff)
        self.assertEqual(r.decode(r.encode([row], True), True), [row])

    def test_negative_loop_rejected(self):
        with self.assertRaises(ValueError): r.encode([replace(self.old, gameloop=-1)], True)

    def test_large_loop_rejected(self):
        with self.assertRaises(ValueError): r.encode([replace(self.old, gameloop=2**32)], True)

    def test_boolean_loop_rejected(self):
        with self.assertRaises(ValueError): r.encode([replace(self.old, gameloop=True)], True)

    def test_modern_encoder_cannot_silently_drop_color(self):
        with self.assertRaises(ValueError): r.encode([self.old], False)

    def test_legacy_encoder_requires_color(self):
        with self.assertRaises(ValueError): r.encode([self.new], True)

    def test_color_bounds_checked(self):
        for color in (-1, 2**32, True):
            with self.subTest(color=color):
                with self.assertRaises(ValueError): r.encode([replace(self.old, legacy_color=color)], True)

    def test_utf8_name_bytes_preserved(self):
        row = replace(self.old, name='Żółw'.encode())
        self.assertEqual(r.decode(r.encode([row], True), True), [row])

    def test_invalid_utf8_rejected(self):
        with self.assertRaises(ValueError): r.encode([replace(self.old, name=b'\xff')], True)

    def test_name_type_checked(self):
        with self.assertRaises(ValueError): r.encode([replace(self.old, name='Player')], True)

    def test_name_size_checked(self):
        with self.assertRaises(ValueError): r.encode([replace(self.old, name=b'a' * (r.MAX_NAME_BYTES + 1))], True)

    def test_truncated_headers_rejected(self):
        for legacy in (False, True):
            raw = r.encode([self.old if legacy else self.new], legacy)
            for size in range(1, 12 if legacy else 8):
                with self.subTest(legacy=legacy, size=size):
                    with self.assertRaises(ValueError): r.decode(raw[:size], legacy)

    def test_truncated_name_rejected(self):
        with self.assertRaises(ValueError): r.decode(r.encode([self.old], True)[:-1], True)

    def test_trailing_garbage_not_ignored(self):
        with self.assertRaises(ValueError): r.decode(r.encode([self.old], True) + b'\0', True)

    def test_declared_name_length_bounded(self):
        raw = struct.pack('<IBBH', 61, 1, 1, r.MAX_NAME_BYTES + 1) + b'a' * (r.MAX_NAME_BYTES + 1)
        with self.assertRaises(ValueError): r.decode(raw, False)

    def test_name_length_cannot_cross_end(self):
        raw = struct.pack('<IBBH', 61, 1, 1, 100) + b'ab'
        with self.assertRaises(ValueError): r.decode(raw, False)

    def test_decode_size_limit(self):
        with self.assertRaises(ValueError): r.decode(b'\0' * (r.MAX_BYTES + 1), False)

    def test_encode_size_limit(self):
        with patch.object(r, 'MAX_BYTES', 4):
            with self.assertRaises(ValueError): r.encode([self.new], False)

    def test_record_limit_enforced_both_ways(self):
        with patch.object(r, 'MAX_RECORDS', 1):
            with self.assertRaises(ValueError): r.encode([self.new, self.new], False)
            with self.assertRaises(ValueError): r.decode(r.encode([self.new], False) * 2, False)

    def test_nonrecord_rejected(self):
        with self.assertRaises(ValueError): r.encode([{}], False)


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.rows = [r.Record(610, 5, 16, b'', 0xffffffff),
                     r.Record(61, 1, 1, b'Player', 0xff245cff),
                     r.Record(63, 2, 6, b'Red', 0xffff0000),
                     r.Record(19731, 3, 16, b'', 0xffffffff)]
        self.raw = r.encode(self.rows, True)

    def test_only_color_changes(self):
        raw, _ = r.migrate(self.raw)
        self.assertEqual(r.decode(raw, False), [replace(row, legacy_color=None) for row in self.rows])

    def test_four_bytes_removed_per_record(self):
        raw, changes = r.migrate(self.raw)
        self.assertEqual(len(self.raw) - len(raw), 4 * len(self.rows))
        self.assertEqual(len(changes), len(self.rows))

    def test_nonchronological_file_order_is_preserved(self):
        raw, _ = r.migrate(self.raw)
        self.assertEqual([row.gameloop for row in r.decode(raw, False)], [610, 61, 63, 19731])

    def test_audit_reconstructs_exact_source(self):
        raw, changes = r.migrate(self.raw)
        modern = r.decode(raw, False)
        old = [replace(row, legacy_color=change['before_u32_le']) for row, change in zip(modern, changes)]
        self.assertEqual(r.encode(old, True), self.raw)

    def test_audit_does_not_publish_names(self):
        _, changes = r.migrate(self.raw)
        self.assertNotIn('Player', str(changes))
        self.assertEqual(changes[1]['path'], '/replay.resumable.events/1/legacy_color')

    def test_deterministic_migration(self):
        self.assertEqual(r.migrate(self.raw), r.migrate(self.raw))

    def test_empty_migration(self):
        self.assertEqual(r.migrate(b''), (b'', []))

    def test_summary_counts_file_order_decreases(self):
        result = r.summarize(self.raw, True)
        self.assertEqual(result['order_decreases'], 1)
        self.assertEqual(result['records'], 4)
        self.assertNotIn('client_playback_validated', result)


class GuardTests(unittest.TestCase):
    def test_invalid_source_rejected_before_optional_dependencies(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / 'source'
            source.write_bytes(b'invalid')
            with self.assertRaises(ValueError): r.repair(source, Path(root) / 'output')
            self.assertFalse((Path(root) / 'output').exists())

    def test_existing_output_is_not_touched(self):
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / 'output'
            output.write_bytes(b'original')
            with self.assertRaises(FileExistsError): r.repair(Path(root) / 'missing', output)
            self.assertEqual(output.read_bytes(), b'original')

    def test_directory_source_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError): r.repair(Path(root), Path(root) / 'output')


if __name__ == '__main__':
    unittest.main()
