"""Synthetic native775/official71 projection tests without heroprotocol imports.

The selected official table is public protocol metadata from Blizzard's
protocol96477.py, source SHA-256
e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84.
Its upstream copyright is 2015-2021 Blizzard Entertainment, MIT license.
No replay data or player values are retained in these tests.
"""
import copy
import hashlib
import json
from pathlib import Path
import unittest

import native_setup


HERE = Path(__file__).resolve().parent
TABLE_SHA256 = '3f7f2c49851c56db66a7b96cdb98db2e55a48fd8bba85dfd3f3678af59d42233'
SCHEMA_SHA256 = '0c9e5d80f745d9e8d7191e3bc3039fb9e07e1d2c5e83c0bbbeb081216e23395e'


def official_table():
    raw = (HERE / 'test_native_setup_official_schema.json').read_bytes()
    if len(raw) != 13856 or hashlib.sha256(raw).hexdigest() != TABLE_SHA256:
        raise AssertionError('official test metadata pin')
    # The only dictionaries in Blizzard's table are choice tag maps. Restore
    # their integer keys so canonical sort order remains the upstream order.
    return json.loads(raw, object_pairs_hook=lambda pairs: {
        int(key): value for key, value in pairs})


def native_records():
    raw = (HERE / 'native_setup_schema_98348.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != SCHEMA_SHA256:
        raise AssertionError('native test metadata pin')
    return {record['id']: record for record in json.loads(raw)['records']}


def synthetic_value(records, type_id=775, populated=True):
    """Choose valid synthetic native values, with every optional/array visited."""
    record = records[type_id]
    kind = record['kind']
    child = lambda item: synthetic_value(records, item, populated)
    if kind == 'USER':
        return child(record['element_type'])
    if kind == 'STRUCT':
        return tuple(child(item) for item in record['field_types'])
    if kind == 'ARRAY':
        bounds = record['bounds']
        length = max(bounds['min'], min(bounds['max'], int(populated)))
        return tuple(child(record['element_type']) for _ in range(length))
    if kind == 'OPTIONAL':
        return child(record['element_type']) if populated else None
    if kind == 'BOOL':
        return bool(populated)
    if kind == 'INT':
        bounds = record['bounds']
        return bounds['min'] + min(bounds['max'] - bounds['min'], type_id + 1 if populated else 0)
    if kind == 'ENUM':
        return record['tags'][-1 if populated else 0]
    if kind == 'FOURCC':
        return b'TEST'
    if kind == 'BIT_ARRAY':
        bounds = record['bounds']
        length = max(bounds['min'], min(bounds['max'], 13 if populated else 0))
        return length, 0x1555 & ((1 << length) - 1)
    if kind == 'BLOB':
        bounds = record['bounds']
        length = max(bounds['min'], min(bounds['max'], int(populated)))
        return bytes(index % 256 for index in range(length))
    if kind == 'STRING':
        bounds = record['bounds']
        length = max(bounds['min'], min(bounds['max'], 5 if populated else 0))
        return b'x' * length
    raise AssertionError('uncovered native test kind')


class OfficialBitOracle:
    """Independent official-table interpreter, with direct per-bit placement.

    This test helper never inspects native types or native reader/writer state.
    It supports only the operations reachable from official root71. It does
    not claim to replace Blizzard's full protocol implementation.
    """
    def __init__(self, raw, table):
        self.raw = raw
        self.table = table
        self.position = 0
        self.operations = set()

    def bits(self, width):
        start, end = self.position, self.position + width
        if end > len(self.raw) * 8:
            raise AssertionError('truncated official test vector')
        result = 0
        for destination in range(start, end):
            segment_start = max(start, destination // 8 * 8)
            segment_end = min(end, destination // 8 * 8 + 8)
            source_shift = end - segment_end + destination - segment_start
            bit = (self.raw[destination // 8] >> (destination % 8)) & 1
            result |= bit << source_shift
        self.position = end
        return result

    def integer(self, bounds):
        return bounds[0] + self.bits(bounds[1])

    def read(self, type_id=71):
        operation, args = self.table[type_id]
        self.operations.add(operation)
        if operation == '_struct':
            return {name: self.read(child) for name, child, tag in args[0]}
        if operation == '_array':
            return [self.read(args[1]) for _ in range(self.integer(args[0]))]
        if operation == '_optional':
            return self.read(args[0]) if self.bits(1) else None
        if operation == '_bool':
            return bool(self.bits(1))
        if operation == '_int':
            return self.integer(args[0])
        if operation == '_blob':
            length = self.integer(args[0])
            self.position += (-self.position) % 8
            start = self.position // 8
            self.position += length * 8
            if self.position > len(self.raw) * 8:
                raise AssertionError('truncated official test octets')
            return self.raw[start:start + length]
        if operation == '_bitarray':
            length = self.integer(args[0])
            return length, self.bits(length)
        if operation == '_fourcc':
            return self.bits(32).to_bytes(4, 'big')
        raise AssertionError('operation outside official root71 closure')


class OfficialProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = official_table()
        cls.records = native_records()
        cls.native_value = synthetic_value(cls.records)
        cls.raw = native_setup.encode_setup_values(cls.native_value)
        cls.decoded = native_setup.decode_setup(cls.raw)
        cls.oracle = OfficialBitOracle(cls.raw, cls.table)
        cls.official_value = cls.oracle.read()

    def rejected(self, value=None, table=None):
        if value is None:
            value = self.official_value
        if table is None:
            table = self.table
        with self.assertRaises(ValueError) as raised:
            native_setup.compare_setup_with_official(self.decoded, value, table)
        # The errors must not echo even synthetic supplied field values.
        self.assertNotIn('PRIVATE_SYNTHETIC_MARKER', str(raised.exception))

    def test_pinned_official_table_and_wrapper(self):
        self.assertEqual(len(self.table), 213)
        self.assertEqual(self.table[71], ['_struct', [[['m_syncLobbyState', 70, -1]]]])
        canonical = json.dumps(self.table, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), TABLE_SHA256)

    def test_independent_official_decoder_matches_populated_native_root(self):
        self.assertEqual(self.decoded.value, self.native_value)
        self.assertEqual(self.oracle.position, self.decoded.payload_end_bit)
        self.assertEqual(self.oracle.operations, {
            '_struct', '_array', '_optional', '_bool', '_int', '_blob', '_bitarray', '_fourcc',
        })
        compared = native_setup.compare_setup_with_official(self.decoded, self.official_value, self.table)
        self.assertEqual(compared, 237)
        self.assertEqual((len(self.raw), self.decoded.payload_end_bit), (321, 2565))
        self.assertEqual(self.decoded.summary()['observed_type_count'], 200)
        self.assertEqual(native_setup.reencode_setup_source(self.decoded), self.raw)

    def test_independent_official_decoder_matches_empty_arrays_and_absent_optionals(self):
        value = synthetic_value(self.records, populated=False)
        raw = native_setup.encode_setup_values(value)
        decoded = native_setup.decode_setup(raw)
        oracle = OfficialBitOracle(raw, self.table)
        official = oracle.read()
        self.assertEqual(oracle.position, decoded.payload_end_bit)
        compared = native_setup.compare_setup_with_official(decoded, official, self.table)
        self.assertEqual(compared, 100)
        self.assertEqual((len(raw), decoded.payload_end_bit), (52, 416))

    def test_official_dictionary_insertion_order_does_not_change_field_identity(self):
        official = copy.deepcopy(self.official_value)
        inner = official['m_syncLobbyState']
        official['m_syncLobbyState'] = dict(reversed(list(inner.items())))
        expected = native_setup.compare_setup_with_official(self.decoded, self.official_value, self.table)
        self.assertEqual(native_setup.compare_setup_with_official(self.decoded, official, self.table), expected)

    def test_rejects_changed_or_missing_outer_key_and_extra_field(self):
        self.rejected({'PRIVATE_SYNTHETIC_MARKER': self.official_value['m_syncLobbyState']})
        self.rejected({})
        value = copy.deepcopy(self.official_value)
        value['PRIVATE_SYNTHETIC_MARKER'] = None
        self.rejected(value)

    def test_rejects_inner_field_missing_extra_or_renamed(self):
        for mode in ('missing', 'extra', 'renamed'):
            value = copy.deepcopy(self.official_value)
            inner = value['m_syncLobbyState']['m_gameDescription']
            if mode == 'missing':
                del inner['m_randomValue']
            elif mode == 'extra':
                inner['PRIVATE_SYNTHETIC_MARKER'] = 7
            else:
                inner['PRIVATE_SYNTHETIC_MARKER'] = inner.pop('m_randomValue')
            self.rejected(value)

    def test_rejects_wrong_leaf_types_and_values(self):
        for replacement in (True, False, 123456789, b'PRIVATE_SYNTHETIC_MARKER', 'PRIVATE_SYNTHETIC_MARKER'):
            value = copy.deepcopy(self.official_value)
            value['m_syncLobbyState']['m_gameDescription']['m_randomValue'] = replacement
            self.rejected(value)

    def test_rejects_equal_integer_bool_values_in_both_directions(self):
        # Native775's declaration-order root: users, description, lobby. The
        # first description field is the u32 random value. Force it to one so
        # equality alone would incorrectly accept Python's True == 1.
        value = list(self.native_value)
        description = list(value[1])
        description[0] = 1
        value[1] = tuple(description)
        raw = native_setup.encode_setup_values(tuple(value))
        decoded = native_setup.decode_setup(raw)
        official = OfficialBitOracle(raw, self.table).read()
        official['m_syncLobbyState']['m_gameDescription']['m_randomValue'] = True
        with self.assertRaises(ValueError):
            native_setup.compare_setup_with_official(decoded, official, self.table)
        official = copy.deepcopy(self.official_value)
        official['m_syncLobbyState']['m_gameDescription']['m_gameOptions']['m_lockTeams'] = 1
        self.rejected(official)

    def test_rejects_array_tuple_and_optional_presence_changes(self):
        value = copy.deepcopy(self.official_value)
        value['m_syncLobbyState']['m_userInitialData'] = tuple(value['m_syncLobbyState']['m_userInitialData'])
        self.rejected(value)
        value = copy.deepcopy(self.official_value)
        value['m_syncLobbyState']['m_userInitialData'][0]['m_clanTag'] = None
        self.rejected(value)

    def test_rejects_changed_schema_even_outside_root_closure(self):
        table = copy.deepcopy(self.table)
        table[0][1][0][1] += 1
        self.rejected(table=table)
        table = copy.deepcopy(self.table)
        table[212][0] = '_null'
        self.rejected(table=table)
        self.rejected(table=self.table[:-1])
        self.rejected(table=self.table + [['_bool', []]])

    def test_rejects_changed_official_field_order_and_wrapper_target(self):
        table = copy.deepcopy(self.table)
        fields = table[70][1][0]
        fields[0], fields[1] = fields[1], fields[0]
        self.rejected(table=table)
        table = copy.deepcopy(self.table)
        table[71][1][0][0][1] = 69
        self.rejected(table=table)


if __name__ == '__main__':
    unittest.main()
