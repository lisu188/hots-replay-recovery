"""Independent physical-bit and value tests; all payloads are synthetic.

The oracle reads only the fixed public schema metadata. It does not call the
codec's bit, count, alignment, reader, writer or string-validation helpers.
Direct typed tests cover both roots' 513-type closure; the public API remains
restricted to online5917. No replay, game client or network is accessed.
"""
import copy
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
import unittest

import native_lobby_values as codec


RECORDS = codec._records()
RECORDS_SHA = 'f1036e04c503b36ca95c8fbcf72e96c9d7af7a4d91559a95ab5f01271ec2c3f3'
ALL_KINDS = {'USER', 'INT', 'ASCII_STRING', 'STRING', 'STRUCT', 'FOURCC',
             'BLOB', 'ENUM', 'BOOL', 'ARRAY', 'BIT_ARRAY', 'CHOICE',
             'OPTIONAL', 'NULL', 'REAL32', 'REAL64'}


def invented(type_id=5917, populated=False):
    """Construct explicit invented values, without using either implementation."""
    record = RECORDS[type_id]
    kind = record['kind']
    bound = record.get('bounds')
    child = lambda identifier: invented(identifier, populated)
    if kind == 'USER':
        return child(record['element_type'])
    if kind == 'STRUCT':
        return tuple(child(identifier) for identifier in record['field_types'])
    if kind == 'ARRAY':
        length = max(bound['min'], min(bound['max'], int(populated)))
        return tuple(child(record['element_type']) for _ in range(length))
    if kind == 'OPTIONAL':
        return child(record['element_type']) if populated else None
    if kind == 'CHOICE':
        tag = record['tags'][-1 if populated else 0]
        return tag, child(record['field_types'][record['tags'].index(tag)])
    if kind == 'BOOL':
        return bool(populated)
    if kind == 'INT':
        return bound['min'] + min(bound['max'] - bound['min'], int(populated))
    if kind == 'ENUM':
        return record['tags'][-1 if populated else 0]
    if kind in ('STRING', 'ASCII_STRING', 'BLOB'):
        length = max(bound['min'], min(bound['max'], int(populated)))
        return (b'\xfe' if kind == 'BLOB' else b'x') * length
    if kind == 'BIT_ARRAY':
        length = max(bound['min'], min(bound['max'], 13 if populated else 0))
        return length, 0x1555 & ((1 << length) - 1)
    if kind == 'FOURCC':
        return b'TEST'
    if kind == 'REAL32':
        return 0x80000000 if populated else 0
    if kind == 'REAL64':
        return 0x7ff8000012345678 if populated else 0
    if kind == 'NULL':
        return None
    raise AssertionError('Uncovered schema kind')


class PhysicalOracle:
    """Place physical bits directly, low bit first within each byte chunk."""
    def __init__(self):
        self.physical = []
        self.alignment = []

    def bits(self, value, width):
        assert type(value) is int and 0 <= value < (1 << width)
        while width:
            count = min(width, 8 - len(self.physical) % 8)
            width -= count
            chunk = value >> width
            self.physical.extend((chunk >> index) & 1 for index in range(count))

    def octets(self, value):
        width = (-len(self.physical)) % 8
        if width:
            self.alignment.append((len(self.physical), width))
        self.physical.extend([0] * width)
        for byte in value:
            self.physical.extend((byte >> index) & 1 for index in range(8))

    def write(self, value, type_id=5917):
        record = RECORDS[type_id]
        kind = record['kind']
        bound = record.get('bounds')
        if kind == 'USER':
            self.write(value, record['element_type'])
        elif kind == 'STRUCT':
            for item, child in zip(value, record['field_types']):
                self.write(item, child)
        elif kind == 'ARRAY':
            self.bits(len(value) - bound['min'], bound['bits'])
            for item in value:
                self.write(item, record['element_type'])
        elif kind == 'OPTIONAL':
            self.bits(int(value is not None), 1)
            if value is not None:
                self.write(value, record['element_type'])
        elif kind == 'CHOICE':
            tag, item = value
            self.bits(tag - bound['min'], bound['bits'])
            self.write(item, record['field_types'][record['tags'].index(tag)])
        elif kind == 'BOOL':
            self.bits(int(value), 1)
        elif kind in ('INT', 'ENUM'):
            self.bits(value - bound['min'], bound['bits'])
        elif kind in ('REAL32', 'REAL64'):
            self.bits(value, 32 if kind == 'REAL32' else 64)
        elif kind == 'FOURCC':
            self.bits(int.from_bytes(value, 'big'), 32)
        elif kind == 'BIT_ARRAY':
            length, pattern = value
            self.bits(length - bound['min'], bound['bits'])
            self.bits(pattern, length)
        elif kind in ('STRING', 'ASCII_STRING', 'BLOB'):
            self.bits(len(value) - bound['min'],
                      bound['bits'] + (2 if kind == 'STRING' else 0))
            self.octets(value)
        elif kind != 'NULL':
            raise AssertionError('Uncovered oracle kind')

    @property
    def payload_end(self):
        return len(self.physical)

    @property
    def raw(self):
        return self.pack(self.physical)

    @staticmethod
    def pack(bits):
        raw = bytearray((len(bits) + 7) // 8)
        for index, bit in enumerate(bits):
            raw[index // 8] |= bit << (index % 8)
        return bytes(raw)


class NativeLobbyValuesTests(unittest.TestCase):
    def test_destination_bit_oracle_and_wrong_order_negative_controls(self):
        # Derive each source bit from its absolute destination segment. This
        # does not consume chunks or reuse PhysicalOracle's loop above.
        def direct(tokens):
            raw = bytearray((sum(width for _, width in tokens) + 7) // 8)
            start = 0
            for value, width in tokens:
                end = start + width
                for destination in range(start, end):
                    first = max(start, destination // 8 * 8)
                    last = min(end, destination // 8 * 8 + 8)
                    source = end - last + destination - first
                    raw[destination // 8] |= ((value >> source) & 1) << (destination % 8)
                start = end
            return bytes(raw)

        self.assertEqual(direct([(0x123, 12)]), b'\x12\x03')
        self.assertNotEqual(direct([(0x123, 12)]), b'\x23\x01')
        self.assertEqual(direct([(6, 3)]), b'\x06')
        self.assertNotEqual(direct([(6, 3)]), b'\x03')
        writer = codec._Writer(RECORDS)
        for offset in range(8):
            for width in range(65):
                mask = (1 << width) - 1
                for value in {0, mask, mask & 0x55aa993366cc0ff0}:
                    tokens = [((1 << offset) - 1, offset), (value, width)]
                    writer._raw.clear()
                    writer.bit = 0
                    writer._finished = writer._failed = False
                    for part, size in tokens:
                        writer.bits(part, size)
                    self.assertEqual(writer.finish(), direct(tokens))

    def assertExact(self, actual, expected):
        self.assertIs(type(actual), type(expected))
        if type(expected) is tuple:
            self.assertEqual(len(actual), len(expected))
            for left, right in zip(actual, expected):
                self.assertExact(left, right)
        else:
            self.assertEqual(actual, expected)

    def assertTyped(self, value, type_id, offset=0):
        oracle = PhysicalOracle()
        oracle.bits((1 << offset) - 1, offset)
        oracle.write(value, type_id)
        writer = codec._Writer(RECORDS)
        writer.bits((1 << offset) - 1, offset)
        writer.write(value, type_id)
        self.assertEqual(writer.bit, oracle.payload_end)
        self.assertEqual(writer.finish(), oracle.raw)
        self.assertEqual(writer.bit, oracle.payload_end)
        reader = codec._Reader(oracle.raw, RECORDS)
        self.assertEqual(reader.bits(offset), (1 << offset) - 1)
        self.assertExact(reader.read(type_id), value)
        self.assertEqual(reader.bit, oracle.payload_end)
        reader.finish()
        return oracle

    def rejectWrite(self, value, type_id):
        writer = codec._Writer(RECORDS)
        with self.assertRaises(codec.LobbyError) as error:
            writer.write(value, type_id)
        self.assertNotIn('PRIVATE-SENTINEL', str(error.exception))
        with self.assertRaises(codec.LobbyError):
            writer.finish()
        with self.assertRaises(codec.LobbyError):
            writer.write(invented(type_id), type_id)

    def rejectRead(self, raw, type_id):
        reader = codec._Reader(raw, RECORDS)
        with self.assertRaises(codec.LobbyError):
            reader.read(type_id)
        with self.assertRaises(codec.LobbyError):
            reader.finish()

    def test_complete_pinned_513_type_metadata(self):
        canonical = json.dumps(RECORDS, sort_keys=True, separators=(',', ':'),
                               ensure_ascii=True).encode('ascii')
        self.assertEqual(len(canonical), 74396)
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), RECORDS_SHA)
        self.assertEqual(len(RECORDS), 513)
        self.assertEqual({record['kind'] for record in RECORDS.values()}, ALL_KINDS)
        self.assertEqual(RECORDS[5917]['kind'], 'STRUCT')

    def test_independent_bits_all_offsets_widths_onehot_and_mixed(self):
        # Reuse only primitive state: schema validation/deepcopy need not occur
        # once for every one-hot bit. The oracle never reads codec state.
        writer = codec._Writer(RECORDS)
        reader = codec._Reader(b'', RECORDS)
        for offset in range(8):
            for width in range(65):
                mask = (1 << width) - 1
                vectors = {0, mask, mask & 0x96a55aa53cc3f00f}
                vectors.update(1 << position for position in range(width))
                for value in vectors:
                    oracle = PhysicalOracle()
                    oracle.bits((1 << offset) - 1, offset)
                    oracle.bits(value, width)
                    writer._raw = bytearray()
                    writer.bit = 0
                    writer._finished = writer._failed = False
                    writer.bits((1 << offset) - 1, offset)
                    writer.bits(value, width)
                    raw = writer.finish()
                    self.assertEqual(raw, oracle.raw, (offset, width, value))
                    reader.raw, reader.bit = oracle.raw, 0
                    reader._finished = reader._failed = False
                    self.assertEqual(reader.bits(offset), (1 << offset) - 1)
                    self.assertEqual(reader.bits(width), value, (offset, width, value))
                    reader.finish()

    def test_fixed_physical_vector_d39124(self):
        writer = codec._Writer(RECORDS)
        writer.bits(3, 2)
        writer.bits(0x349124, 22)
        self.assertEqual(writer.finish(), bytes.fromhex('d39124'))
        # First two low physical bits are 3; the next chunks are 34 / 91 / 24.
        reader = codec._Reader(bytes.fromhex('d39124'), RECORDS)
        self.assertEqual(reader.bits(2), 3)
        self.assertEqual(reader.bits(22), 0x349124)
        reader.finish()

    def test_all_513_declared_types_against_oracle(self):
        for type_id in sorted(RECORDS):
            with self.subTest(type_id=type_id, kind=RECORDS[type_id]['kind']):
                self.assertTyped(invented(type_id), type_id)

    def test_populated_online_root_against_oracle_and_public_values(self):
        value = invented(populated=True)
        oracle = self.assertTyped(value, 5917)
        self.assertEqual(codec.encode_lobby_values(value), oracle.raw)
        decoded = codec.decode_lobby_values(oracle.raw)
        self.assertExact(decoded.value, value)
        self.assertEqual(decoded.payload_end_bit, oracle.payload_end)
        self.assertEqual(decoded.source_sha256, hashlib.sha256(oracle.raw).hexdigest())
        self.assertEqual(codec.reencode_lobby_source(decoded), oracle.raw)

    def test_all_choice_tags_preserve_declared_width_and_child(self):
        for type_id, record in RECORDS.items():
            if record['kind'] != 'CHOICE':
                continue
            for tag, child in zip(record['tags'], record['field_types']):
                with self.subTest(type_id=type_id, tag=tag):
                    value = tag, invented(child, populated=True)
                    self.assertTyped(value, type_id, offset=3)
        self.assertEqual(self.assertTyped((0, None), 925).payload_end, 2)
        oracle = PhysicalOracle()
        oracle.write(invented(935), 935)
        self.assertEqual(self.assertTyped((0, invented(935)), 934).payload_end,
                         oracle.payload_end)

    def test_unused_choice_tags_and_wrong_tag_types_rejected(self):
        for type_id, bad_tags in ((248, (2, 255)), (925, (3,)),
                                  (937, (6, 7)), (934, (1,))):
            record = RECORDS[type_id]
            for tag in bad_tags:
                self.rejectWrite((tag, None), type_id)
                if tag < (1 << record['bounds']['bits']):
                    oracle = PhysicalOracle()
                    oracle.bits(tag, record['bounds']['bits'])
                    self.rejectRead(oracle.raw, type_id)
        for value in ((True, None), (0.0, None), [0, None], (0,), (0, None, None)):
            self.rejectWrite(value, 925)

    def test_ascii_full_native_domain_and_length_edges(self):
        for value in (b'\x01A~', b'\x01\x1f~', bytes(range(1, 127)), b'~' * 320):
            self.assertTyped(value, 2, offset=1)
        for value in (b'AA', b'A' * 321, b'\0AA', b'A\x7fB', b'A\x80B',
                      b'A\xc3\xa9', 'PRIVATE-SENTINEL', bytearray(b'AAA')):
            self.rejectWrite(value, 2)
        for value in (b'\0AA', b'A\x7fB', b'A\x80B'):
            oracle = PhysicalOracle()
            oracle.write(value, 2)
            self.rejectRead(oracle.raw, 2)
        oracle = PhysicalOracle()
        oracle.bits(318, 9)  # Declared length 321, above the limit of 320.
        self.rejectRead(oracle.raw, 2)

    def test_raw_real_signed_zero_infinity_and_nan_payloads(self):
        cases = ((1839, 32), (1855, 32), (1849, 64))
        for type_id, width in cases:
            values = ((0, 0x80000000, 0x7f800000, 0x7fc01234, 0x7fa00001,
                       1, 0xffffffff) if width == 32 else
                      (0, 0x8000000000000000, 0x7ff0000000000000,
                       0x7ff8000012345678, 0x7ff0000000000001, 1,
                       0xffffffffffffffff))
            for value in values:
                self.assertTyped(value, type_id, offset=5)
            for value in (-1, 1 << width, True, 0.0, float('nan')):
                self.rejectWrite(value, type_id)

    def test_null_is_none_and_consumes_zero_bits(self):
        for offset in range(8):
            self.assertEqual(self.assertTyped(None, 926, offset).payload_end, offset)
        for value in (False, 0, b'', (), 'PRIVATE-SENTINEL'):
            self.rejectWrite(value, 926)

    def test_native_string_sequences_and_encoded_byte_length(self):
        # 32 four-byte scalars are 32 native sequences but 128 encoded octets.
        self.assertTyped(b'\xf4\x8f\xbf\xbf' * 32, 3, offset=3)
        self.assertTyped(b'\xc3\xa9' * 32, 3)
        for value in (b'\0', b'A\0B', b'\xc0\x80', b'\xed\xa0\x80',
                      b'\xf4\x90\x80\x80', b'\xe2\x82', b'x' * 33):
            self.rejectWrite(value, 3)
            oracle = PhysicalOracle()
            oracle.write(value, 3)
            self.rejectRead(oracle.raw, 3)

    def test_bit_array_large_patterns_and_exact_bounds(self):
        for length in (0, 1, 7, 8, 63, 64, 65, 2048):
            pattern = ((1 << (length - 1)) | 1) if length else 0
            self.assertTyped((length, pattern), 164, offset=7)
        for value in ((-1, 0), (2049, 0), (3, 8), (0, 1), (True, 0),
                      (3, True), [3, 0], (3,), (3, 0, 1)):
            self.rejectWrite(value, 164)

    def test_scalar_integer_enum_bool_and_fourcc_type_guards(self):
        for type_id, record in RECORDS.items():
            kind = record['kind']
            if kind == 'INT':
                bound = record['bounds']
                self.assertTyped(bound['min'], type_id)
                self.assertTyped(bound['max'], type_id)
                for value in (bound['min'] - 1, bound['max'] + 1, True, 0.0):
                    self.rejectWrite(value, type_id)
            elif kind == 'ENUM':
                for tag in set(record['tags']):
                    self.assertTyped(tag, type_id)
                self.rejectWrite(True, type_id)
                bad = next((tag for tag in range(record['bounds']['min'],
                    min(record['bounds']['max'] + 1, 64)) if tag not in record['tags']), None)
                if bad is not None:
                    self.rejectWrite(bad, type_id)
                    oracle = PhysicalOracle()
                    oracle.bits(bad - record['bounds']['min'], record['bounds']['bits'])
                    self.rejectRead(oracle.raw, type_id)
        boolean = next(i for i, r in RECORDS.items() if r['kind'] == 'BOOL')
        fourcc = next(i for i, r in RECORDS.items() if r['kind'] == 'FOURCC')
        for value in (0, 1, None, b''):
            self.rejectWrite(value, boolean)
        for value in (b'abc', b'abcde', 'ABCD', bytearray(b'ABCD'), 0):
            self.rejectWrite(value, fourcc)

    def test_struct_array_and_optional_shape_is_exact(self):
        self.rejectWrite(list(invented()), 5917)
        self.rejectWrite(invented() + (None,), 5917)
        array = next(i for i, r in RECORDS.items() if r['kind'] == 'ARRAY')
        self.rejectWrite(list(invented(array)), array)
        self.assertTyped(None, 1840)
        self.assertTyped(0x80000000, 1840)
        self.rejectWrite(False, 1840)

    def test_internal_padding_source_preserved_and_canonicalized(self):
        value = invented(populated=True)
        oracle = PhysicalOracle()
        oracle.write(value)
        self.assertTrue(oracle.alignment)
        start, width = oracle.alignment[0]
        self.assertGreater(width, 0)
        changed = bytearray(oracle.raw)
        changed[start // 8] ^= 1 << (start % 8)
        source = bytes(changed)
        decoded = codec.decode_lobby_values(source)
        self.assertExact(decoded.value, value)
        self.assertNotEqual(source, oracle.raw)
        self.assertEqual(codec.encode_lobby_values(decoded.value), oracle.raw)
        self.assertEqual(codec.reencode_lobby_source(decoded), source)
        self.assertEqual(decoded.source_sha256, hashlib.sha256(source).hexdigest())

    def test_public_whole_member_eof_and_quarantine(self):
        oracle = PhysicalOracle()
        oracle.write(invented(populated=True))
        for raw in (b'', oracle.raw[:-1], oracle.raw + b'\0',
                    oracle.raw + b'PRIVATE-SENTINEL'):
            with self.assertRaises(codec.LobbyError) as error:
                codec.decode_lobby_values(raw)
            self.assertNotIn('PRIVATE-SENTINEL', str(error.exception))
        if oracle.payload_end % 8:
            changed = bytearray(oracle.raw)
            changed[-1] |= 1 << (oracle.payload_end % 8)
            with self.assertRaisesRegex(codec.LobbyError, 'nonzero EOF padding'):
                codec.decode_lobby_values(bytes(changed))
        # A direct BOOL has seven EOF bits, independently of root alignment.
        boolean = next(i for i, r in RECORDS.items() if r['kind'] == 'BOOL')
        reader = codec._Reader(b'\x81', RECORDS)
        self.assertIs(reader.read(boolean), True)
        for _ in range(2):
            with self.assertRaises(codec.LobbyError):
                reader.finish()

    def test_schema_pinning_and_detached_record_storage(self):
        records = copy.deepcopy(RECORDS)
        writer = codec._Writer(records)
        reader = codec._Reader(b'', records)
        records[926]['kind'] = 'REAL64'
        writer.write(None, 926)
        self.assertEqual(writer.finish(), b'')
        self.assertIsNone(reader.read(926))
        reader.finish()
        for factory in (lambda: codec._Writer(records),
                        lambda: codec._Reader(b'', records)):
            with self.assertRaises(codec.LobbyError):
                factory()

    def test_budgets_and_invalid_type_or_depth_are_refused(self):
        for factory in (lambda: codec._Writer(RECORDS),
                        lambda: codec._Reader(b'', RECORDS)):
            for bad_type in (True, 5917.0, -1, 999999, 'PRIVATE-SENTINEL'):
                state = factory()
                with self.assertRaises(codec.LobbyError):
                    state.write(None, bad_type) if hasattr(state, 'write') else state.read(bad_type)
            for depth in (-1, 129, True, 0.0):
                state = factory()
                with self.assertRaises(codec.LobbyError):
                    state.write(None, 926, depth) if hasattr(state, 'write') else state.read(926, depth)
            for attribute, limit in (('nodes', codec.MAX_NODES),
                                     ('array_elements', codec.MAX_ARRAY_ELEMENTS)):
                state = factory()
                setattr(state, attribute, limit)
                with self.assertRaises(codec.LobbyError):
                    if attribute == 'nodes':
                        state.write(None, 926) if hasattr(state, 'write') else state.read(926)
                    else:
                        state.array(1)
            state = factory()
            with self.assertRaises(codec.LobbyError):
                state.array(codec.MAX_ARRAY + 1)
        writer = codec._Writer(RECORDS)
        writer.bit = codec.MAX_MEMBER_BYTES * 8
        with self.assertRaises(codec.LobbyError):
            writer.bits(0, 1)
        with self.assertRaises(codec.LobbyError):
            codec.decode_lobby_values(bytes(codec.MAX_MEMBER_BYTES + 1))

    def test_public_profile_input_and_surface_guards(self):
        value = invented()
        raw = codec.encode_lobby_values(value)
        decoded = codec.decode_lobby_values(raw)
        for profile in ('', 'PRIVATE-SENTINEL', 5917, True, None):
            for fn, argument in ((codec.decode_lobby_values, raw),
                                 (codec.encode_lobby_values, value),
                                 (codec.reencode_lobby_source, decoded)):
                with self.assertRaises(codec.LobbyError) as error:
                    fn(argument, profile=profile)
                self.assertNotIn('PRIVATE-SENTINEL', str(error.exception))
        for wrong in (bytearray(raw), memoryview(raw), 'PRIVATE-SENTINEL', None):
            with self.assertRaises(codec.LobbyError):
                codec.decode_lobby_values(wrong)
        with self.assertRaises(codec.LobbyError):
            codec.encode_lobby_values(invented(5962))
        for keyword in ('type_id', 'offset', 'schema', 'string_count', 'context'):
            with self.assertRaises(TypeError):
                codec.decode_lobby_values(raw, **{keyword: None})
            with self.assertRaises(TypeError):
                codec.encode_lobby_values(value, **{keyword: None})

    def test_decoded_immutable_and_tampering_refused(self):
        raw = codec.encode_lobby_values(invented())
        decoded = codec.decode_lobby_values(raw)
        with self.assertRaises(FrozenInstanceError):
            decoded.value = ()
        self.assertNotIn(repr(decoded.value), repr(decoded))
        for changed in (replace(decoded, value=()),
                        replace(decoded, payload_end_bit=True),
                        replace(decoded, source_sha256='PRIVATE-SENTINEL'),
                        replace(decoded, _source=raw + b'\0')):
            with self.assertRaises(codec.LobbyError) as error:
                codec.reencode_lobby_source(changed)
            self.assertNotIn('PRIVATE-SENTINEL', str(error.exception))
        summary = decoded.summary()
        self.assertNotIn('value', summary)
        self.assertNotIn('PRIVATE-SENTINEL', repr(summary))

    def test_source_reproduction_refuses_bool_equal_to_integer(self):
        raw = codec.encode_lobby_values(invented())
        decoded = codec.decode_lobby_values(raw)

        def replace_zero(value):
            if type(value) is int and value == 0:
                return False, True
            if type(value) is tuple:
                for index, child in enumerate(value):
                    changed, found = replace_zero(child)
                    if found:
                        return value[:index] + (changed,) + value[index + 1:], True
            return value, False

        changed, found = replace_zero(decoded.value)
        self.assertTrue(found)
        self.assertEqual(changed, decoded.value)  # Python equality alone is insufficient.
        with self.assertRaises(codec.LobbyError):
            codec.reencode_lobby_source(replace(decoded, value=changed))


if __name__ == '__main__':
    unittest.main(verbosity=2)
