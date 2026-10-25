"""Public native775 API guards with synthetic values; no replay or client IO."""
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import native_setup as n
from test_native_setup_writer import minimal, RECORDS


def nonzero_internal_padding():
    """Record exactly one native alignment operation and flip a discarded bit."""
    source = n.encode_setup_values(minimal(775))
    spans = []
    original = n._reader.Reader.align

    def observe(reader):
        if reader.bit % 8:
            spans.append(reader.bit)
        return original(reader)

    with patch.object(n._reader.Reader, 'align', observe):
        n.decode_setup(source)
    assert spans
    changed = bytearray(source)
    changed[spans[0] // 8] ^= 1 << (spans[0] % 8)
    return source, bytes(changed)


class NativeSetupTests(unittest.TestCase):
    def setUp(self):
        self.value = minimal(775)
        self.raw = n.encode_setup_values(self.value)

    def test_root_value_and_exact_source(self):
        setup = n.decode_setup(self.raw)
        self.assertEqual(setup.value, self.value)
        self.assertEqual(n.reencode_setup_source(setup), self.raw)
        self.assertEqual(setup.source_sha256, hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(n.encode_setup_values(setup.value), self.raw)

    def test_nonzero_internal_padding_preserved_only_by_source_operation(self):
        canonical, source = nonzero_internal_padding()
        setup = n.decode_setup(source)
        self.assertEqual(setup.value, n.decode_setup(canonical).value)
        self.assertNotEqual(source, canonical)
        self.assertEqual(n.encode_setup_values(setup.value), canonical)
        self.assertEqual(n.reencode_setup_source(setup), source)
        self.assertEqual(setup.summary()['nonzero_internal_padding_spans'], 1)

    def test_payload_cursor_kept_before_finish(self):
        setup = n.decode_setup(self.raw)
        reader = n._reader.Reader(self.raw, n._records(), n._string.count_native_string_sequences)
        reader.read()
        payload = reader.bit
        reader.finish()
        self.assertEqual(setup.payload_end_bit, payload)
        self.assertGreaterEqual(reader.bit, payload)
        self.assertEqual(setup.summary()['EOF_alignment_padding_bits'], len(self.raw) * 8 - payload)

    def test_trailing_and_truncated_whole_members_rejected(self):
        for raw in (b'', self.raw[:-1], self.raw + b'\0', self.raw + b'PRIVATE-SENTINEL'):
            with self.assertRaises(n.SetupError) as error:
                n.decode_setup(raw)
            self.assertNotIn('PRIVATE-SENTINEL', str(error.exception))

    def test_nonzero_final_padding_rejected(self):
        # Populated declared arrays/optionals exercise an unaligned EOF.
        from test_native_setup_official import synthetic_value
        value = synthetic_value(RECORDS)
        raw = n.encode_setup_values(value)
        setup = n.decode_setup(raw)
        if setup.payload_end_bit % 8 == 0:
            self.fail('Synthetic root must exercise EOF padding')
        changed = bytearray(raw)
        changed[-1] |= 1 << (setup.payload_end_bit % 8)
        with self.assertRaisesRegex(n.SetupError, 'nonzero EOF padding'):
            n.decode_setup(bytes(changed))

    def test_member_type_and_size_guards(self):
        for raw in (bytearray(self.raw), memoryview(self.raw), 'PRIVATE-SENTINEL',
                    bytes(n.MAX_MEMBER_BYTES + 1), None):
            with self.assertRaises(n.SetupError) as error:
                n.decode_setup(raw)
            self.assertNotIn('PRIVATE-SENTINEL', str(error.exception))

    def test_only_exact_profile_and_root_value_allowed(self):
        setup = n.decode_setup(self.raw)
        for profile in ('', 'PRIVATE-SENTINEL', 775, True, None):
            for fn, arg in ((n.decode_setup, self.raw), (n.encode_setup_values, self.value),
                            (n.reencode_setup_source, setup)):
                with self.assertRaises(n.SetupError) as error:
                    fn(arg, profile=profile)
                self.assertNotIn('PRIVATE-SENTINEL', str(error.exception))
        for value in (list(self.value), None, self.value + (None,)):
            with self.assertRaises(n.SetupError):
                n.encode_setup_values(value)

    def test_frozen_repr_and_summary_do_not_expose_values(self):
        setup = n.decode_setup(self.raw)
        with self.assertRaises(FrozenInstanceError):
            setup.value = ()
        self.assertNotIn(repr(self.value), repr(setup))
        summary = setup.summary()
        self.assertNotIn('value', summary)
        self.assertNotIn('_source', summary)
        self.assertEqual(summary['root_type_id'], 775)
        self.assertFalse(summary['names_authenticated'])
        self.assertFalse(summary['simulation_or_historical_conversion_proven'])
        self.assertEqual(summary['decoded_nodes'], sum(summary['kind_counts'].values()))
        json.dumps(summary)

    def test_forged_metadata_and_values_refused(self):
        setup = n.decode_setup(self.raw)
        variants = [replace(setup, payload_end_bit=True),
                    replace(setup, payload_end_bit=setup.payload_end_bit + 1),
                    replace(setup, source_sha256='0' * 64),
                    replace(setup, _statistics=()), replace(setup, value=()),
                    replace(setup, _source=self.raw + b'\0')]
        for altered in variants:
            with self.assertRaises(n.SetupError):
                n.reencode_setup_source(altered)
            with self.assertRaises(n.SetupError):
                altered.summary()
        with self.assertRaises(n.SetupError):
            n.reencode_setup_source(None)

    def test_forged_int_bool_equality_refused(self):
        setup = n.decode_setup(self.raw)

        def change(value):
            if type(value) is bool:
                return int(value), True
            if type(value) is tuple:
                for i, child in enumerate(value):
                    changed, found = change(child)
                    if found:
                        return value[:i] + (changed,) + value[i + 1:], True
            return value, False

        altered, found = change(setup.value)
        self.assertTrue(found)
        self.assertEqual(altered, setup.value)
        with self.assertRaisesRegex(n.SetupError, 'changed'):
            n.reencode_setup_source(replace(setup, value=altered))

    def test_dependency_size_hash_and_symlink_guards(self):
        path = Path(n.__file__).with_name('native_setup_schema_98348.json')
        with patch.object(Path, 'is_symlink', return_value=True):
            with self.assertRaisesRegex(n.SetupError, 'symlink'):
                n.decode_setup(self.raw)
        with self.assertRaisesRegex(n.SetupError, 'size'):
            n._pinned_file(path.name, 1, '0' * 64)
        with self.assertRaisesRegex(n.SetupError, 'pin'):
            n._pinned_file(path.name, path.stat().st_size, '0' * 64)
        with self.assertRaisesRegex(n.SetupError, 'unavailable'):
            n._pinned_file('missing-setup-test-dependency.json', 1, '0' * 64)

    def test_reader_and_writer_use_fresh_schema_per_call(self):
        records = n._records()
        records[775]['field_types'][0] = -1
        self.assertEqual(n.decode_setup(self.raw).value, self.value)
        self.assertEqual(n.encode_setup_values(self.value), self.raw)

    def test_no_arbitrary_offsets_roots_schemas_or_callbacks(self):
        for keyword in ('type_id', 'offset', 'schema', 'string_count'):
            with self.assertRaises(TypeError):
                n.decode_setup(self.raw, **{keyword: None})
            with self.assertRaises(TypeError):
                n.encode_setup_values(self.value, **{keyword: None})

    def test_official_foreign_keys_and_values_do_not_execute_private_methods(self):
        from test_native_setup_official import official_table, OfficialBitOracle

        class Foreign:
            def __hash__(self):
                return hash('m_syncLobbyState')

            def __eq__(self, other):
                raise RuntimeError('PRIVATE-SENTINEL')

        table = official_table()
        setup = n.decode_setup(self.raw)
        official = OfficialBitOracle(self.raw, table).read()
        cases = [{Foreign(): {}}, {'m_syncLobbyState': {Foreign(): 0}},
                 {'m_syncLobbyState': Foreign()}, {'m_syncLobbyState': [Foreign()]}]
        for value in cases:
            with self.assertRaises(n.SetupError) as error:
                n.compare_setup_with_official(setup, value, table)
            self.assertNotIn('PRIVATE-SENTINEL', str(error.exception))
        self.assertEqual(n.compare_setup_with_official(setup, official, table), 100)

    def test_official_value_cycle_and_container_budget_rejected(self):
        from test_native_setup_official import official_table
        cycle = []
        cycle.append(cycle)
        setup = n.decode_setup(self.raw)
        for value in (cycle, [None] * 100001):
            with self.assertRaisesRegex(n.SetupError, 'value budget'):
                n.compare_setup_with_official(setup, value, official_table())


if __name__ == '__main__':
    unittest.main(verbosity=2)
