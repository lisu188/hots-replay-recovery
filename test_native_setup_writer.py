"""Independent bit oracle and strict-input tests; synthetic data only."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
D = HERE.parent


def load(name, path, expected=None):
    if expected and hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('Test dependency pin')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


m = load('setup775_writer_tested', HERE / '_native_setup_writer.py',
         'd6dcfadf4bbbfadce361c7939e50172afdf9ba1a0ac0537716e817872e45adb7')
rmod = load('setup775_reader_tested', HERE / '_native_setup_reader.py',
            '0ed16f26148d940680c89a80bb82220a34081a1de745bb34ca148be1b9c58a39')
s = load('setup775_string_tested', HERE / '_native_setup_string.py',
         '56087d34ad3569cb20a01d1831e15697432840d22c2a008c83a267bd65dcea69')
PROFILE = HERE / 'native_setup_schema_98348.json'
RECORDS = rmod.load_profile(PROFILE.read_bytes())


def writer(records=RECORDS):
    return m.Writer(records, s.count_native_string_sequences)


def per_bit_oracle(tokens):
    """Direct destination-bit mapping, no production chunk/mask algorithm."""
    output = bytearray((sum(width for _, width in tokens) + 7) // 8)
    start = 0
    for value, width in tokens:
        end = start + width
        for destination in range(start, end):
            # Every byte intersection is an independent little-bit-position
            # segment of the high-first integer. Derive each bit's source
            # position directly, rather than consuming source chunks.
            segment_start = max(start, destination // 8 * 8)
            segment_end = min(end, destination // 8 * 8 + 8)
            source_shift = (end - segment_end) + (destination - segment_start)
            output[destination // 8] |= ((value >> source_shift) & 1) << (destination % 8)
        start = end
    return bytes(output)


def minimal(type_id):
    record = RECORDS[type_id]
    kind = record['kind']
    if kind == 'USER':
        return minimal(record['element_type'])
    if kind == 'STRUCT':
        return tuple(minimal(child) for child in record['field_types'])
    if kind == 'ARRAY':
        return tuple(minimal(record['element_type']) for _ in range(record['bounds']['min']))
    if kind == 'OPTIONAL':
        return None
    if kind == 'BOOL':
        return False
    if kind == 'INT':
        return record['bounds']['min']
    if kind == 'ENUM':
        return record['tags'][0]
    if kind == 'FOURCC':
        return b'STAR'
    if kind == 'BIT_ARRAY':
        return record['bounds']['min'], 0
    if kind == 'BLOB':
        return bytes(record['bounds']['min'])
    if kind == 'STRING':
        return b'a' * record['bounds']['min']
    raise AssertionError('Uncovered kind')


class WriterTests(unittest.TestCase):
    def rejected(self, value, type_id):
        w = writer()
        with self.assertRaises(m.Rejected):
            w.write(value, type_id)
        with self.assertRaisesRegex(m.Rejected, 'discard rejected'):
            w.finish()

    def test_independent_per_bit_oracle_all_offsets_and_widths(self):
        for offset in range(8):
            prefix = 0x5A & ((1 << offset) - 1)
            for width in range(65):
                limit = (1 << width) - 1
                patterns = {0, limit, 0x5555555555555555 & limit,
                            0xAAAAAAAAAAAAAAAA & limit}
                patterns.update(1 << bit for bit in range(width))
                w = writer()
                # Reset only the primitive test fixture between independent
                # cases; schema validation is separately tested below.
                for value in patterns:
                    w._raw.clear()
                    w.bit = 0
                    w._finished = False
                    w.bits(prefix, offset)
                    w.bits(value, width)
                    self.assertEqual(w.bit, offset + width)
                    self.assertEqual(w.finish(), per_bit_oracle([(prefix, offset), (value, width)]))

    def test_manual_unaligned_vector(self):
        tokens = [(3, 3), (417, 9), (2340, 12)]
        w = writer()
        for value, width in tokens:
            w.bits(value, width)
        self.assertEqual(w.finish(), bytes.fromhex('d39124'))
        self.assertEqual(per_bit_oracle(tokens), bytes.fromhex('d39124'))

    def test_oracle_detects_wrong_chunk_order_control(self):
        self.assertEqual(per_bit_oracle([(0b110, 3)]), b'\x06')
        # A per-bit MSB-first placement at ascending low bit positions gives3.
        self.assertNotEqual(per_bit_oracle([(0b110, 3)]), b'\x03')
        self.assertEqual(per_bit_oracle([(0x123, 12)]), b'\x12\x03')
        self.assertNotEqual(per_bit_oracle([(0x123, 12)]), b'\x23\x01')

    def test_all200_types_and11_kind_coverage(self):
        types, kinds = set(), set()
        for type_id in RECORDS:
            value = minimal(type_id)
            w = writer()
            w.write(value, type_id)
            raw = w.finish()
            r = rmod.Reader(raw, RECORDS, s.count_native_string_sequences)
            self.assertEqual(r.read(type_id), value)
            self.assertEqual(r.bit, w.bit)
            self.assertEqual(r.kinds, w.kinds)
            self.assertEqual(r.types, w.types)
            self.assertEqual(r.bounds_checks, w.bounds_checks)
            r.finish()
            kinds.update(w.kinds)
            types.update(w.types)
        self.assertEqual(types, set(RECORDS))
        self.assertEqual(kinds, m.KINDS)

    def test_root775_minimal_value_roundtrip(self):
        value = minimal(775)
        w = writer()
        w.write(value)
        raw = w.finish()
        r = rmod.Reader(raw, RECORDS, s.count_native_string_sequences)
        self.assertEqual(r.read(), value)
        self.assertEqual(w.bit, r.bit)
        r.finish()

    def test_all_integer_and_enum_boundaries_against_oracle(self):
        for type_id, record in RECORDS.items():
            if record['kind'] not in ('INT', 'ENUM'):
                continue
            bounds = record['bounds']
            values = record.get('tags', [bounds['min'], bounds['max']])
            for value in values:
                w = writer()
                w.write(value, type_id)
                self.assertEqual(w.finish(), per_bit_oracle([(value - bounds['min'], bounds['bits'])]))
            self.rejected(bounds['min'] - 1, type_id)
            self.rejected(bounds['max'] + 1, type_id)
            self.rejected(True, type_id)

    def test_bool_exact_type_and_oracle(self):
        type_id = next(i for i, r in RECORDS.items() if r['kind'] == 'BOOL')
        for value in (False, True):
            w = writer()
            w.write(value, type_id)
            self.assertEqual(w.finish(), bytes([int(value)]))
        self.rejected(0, type_id)
        self.rejected(1, type_id)

    def test_optional_absent_present_all_declared_optional_types(self):
        for type_id, record in RECORDS.items():
            if record['kind'] != 'OPTIONAL':
                continue
            w = writer()
            w.write(None, type_id)
            self.assertEqual(w.finish(), b'\x00')
            value = minimal(record['element_type'])
            w = writer()
            w.write(value, type_id)
            r = rmod.Reader(w.finish(), RECORDS, s.count_native_string_sequences)
            self.assertEqual(r.read(type_id), value)
            self.assertEqual(r.bit, w.bit)
            self.assertEqual(w.finish()[0] & 1, 1)

    def test_bitarray_lengths_patterns_and_independent_oracle(self):
        for type_id, record in RECORDS.items():
            if record['kind'] != 'BIT_ARRAY':
                continue
            for length in {0, 1, record['bounds']['max']}:
                for pattern in {0, (1 << length) - 1}:
                    w = writer()
                    w.write((length, pattern), type_id)
                    self.assertEqual(w.finish(), per_bit_oracle([(length, record['bounds']['bits']), (pattern, length)]))
            for invalid in ((-1, 0), (0, 1), (1, -1), (1, 2), (True, 0), (1, True), [1, 1], (record['bounds']['max'] + 1, 0)):
                self.rejected(invalid, type_id)

    def test_fixed_blob_alignment_and_internal_padding(self):
        w = writer()
        w.bits(7, 3)
        w.write(bytes(range(40)), 66)
        self.assertEqual(w.finish(), b'\x07' + bytes(range(40)))
        self.assertEqual(w.bit, 328)
        self.assertEqual(w.padding_spans, 1)
        self.assertEqual(w.nonzero_padding_spans, 0)
        self.rejected(bytes(39), 66)
        self.rejected(bytes(41), 66)
        self.rejected(bytearray(40), 66)

    def test_discarded_source_padding_is_not_value_identity_proof(self):
        rows = []
        for first in (7, 255):
            r = rmod.Reader(bytes([first]) + bytes(range(40)), RECORDS, s.count_native_string_sequences)
            rows.append((r.bits(3), r.read(66), r.nonzero_padding_spans))
        self.assertEqual(rows[0][:2], rows[1][:2])
        self.assertEqual([row[2] for row in rows], [0, 1])
        w = writer()
        w.bits(rows[1][0], 3)
        w.write(rows[1][1], 66)
        self.assertEqual(w.finish()[0], 7)
        self.assertNotEqual(w.finish()[0], 255)

    def test_native_string_encoded_length_and_zero_alignment(self):
        for value in (b'', b'abc', b'\xc4\x85', b'\xf0\x9f\x98\x80' * 32):
            w = writer()
            w.bits(5, 3)
            w.write(value, 67)
            expected = bytearray(per_bit_oracle([(5, 3), (len(value), 8), (0, 5)]))
            expected.extend(value)
            self.assertEqual(w.finish(), bytes(expected))
            self.assertEqual(w.string_instances, 1)
            self.assertEqual(w.padding_spans, 1)
        for invalid in (b'\x00', b'\xc0\x80', b'\xf4\x90\x80\x80', b'\xc4', b'a' * 33):
            self.rejected(invalid, 67)

    def test_string_requires_native_counter_and_strict_count_result(self):
        with self.assertRaises(m.Rejected):
            m.Writer(RECORDS, None)
        for callback in (lambda raw: True, lambda raw: -1, lambda raw: 33):
            w = m.Writer(RECORDS, callback)
            with self.assertRaises(m.Rejected):
                w.write(b'a', 67)

    def test_fourcc_bytes_and_oracle(self):
        type_id = next(i for i, r in RECORDS.items() if r['kind'] == 'FOURCC')
        w = writer()
        w.bits(5, 3)
        w.write(b'STAR', type_id)
        self.assertEqual(w.finish(), per_bit_oracle([(5, 3), (0x53544152, 32)]))
        self.rejected(b'ABC', type_id)
        self.rejected(0x53544152, type_id)

    def test_array_count_max_and_rejection(self):
        record = RECORDS[107]
        child = minimal(record['element_type'])
        value = (child,) * record['bounds']['max']
        w = writer()
        w.write(value, 107)
        r = rmod.Reader(w.finish(), RECORDS, s.count_native_string_sequences)
        self.assertEqual(r.read(107), value)
        self.assertEqual(w.bit, r.bit)
        self.rejected((child,) * 17, 107)
        self.rejected([], 107)

    def test_struct_shape_and_unknown_type(self):
        type_id = next(i for i, r in RECORDS.items() if r['kind'] == 'STRUCT')
        value = minimal(type_id)
        self.rejected(list(value), type_id)
        self.rejected(value + (None,), type_id)
        self.rejected(None, -1)

    def test_profile_pin_and_input_record_mutation_isolated(self):
        altered = copy.deepcopy(RECORDS)
        altered[67]['bounds']['max'] = 1
        with self.assertRaises(m.Rejected):
            writer(altered)
        source = copy.deepcopy(RECORDS)
        w = writer(source)
        source[67]['bounds']['max'] = 0
        w.write(b'a', 67)
        self.assertEqual(w.finish(), b'\x01a')

    def test_research_budgets_and_rejected_writer_quarantine(self):
        for cap, limit, action in [
            ('MAX_OUTPUT_BYTES', 1, lambda w: w.bits(0, 9)),
            ('MAX_OUTPUT_BYTES', 1, lambda w: w.octets(b'ab')),
            ('MAX_NODES', 0, lambda w: w.write(minimal(775))),
            ('MAX_DEPTH', 0, lambda w: w.write(minimal(775))),
            ('MAX_ARRAY_ELEMENTS', 0, lambda w: w.write((minimal(RECORDS[107]['element_type']),), 107)),
        ]:
            with patch.object(m, cap, limit):
                w = writer()
                with self.assertRaises(m.Rejected):
                    action(w)
                with self.assertRaisesRegex(m.Rejected, 'discard rejected'):
                    w.finish()

    def test_invalid_bit_primitives(self):
        for value, width in ((True, 1), (1, 0), (-1, 1), (0, -1), (0, True)):
            with self.assertRaises(m.Rejected):
                writer().bits(value, width)

    def test_final_padding_preserves_payload_cursor_and_seals_writer(self):
        w = writer()
        w.bits(5, 3)
        self.assertEqual(w.finish(), b'\x05')
        self.assertEqual(w.bit, 3)
        self.assertEqual(w.finish(), b'\x05')
        with self.assertRaises(m.Rejected):
            w.bits(0, 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
