"""Offline contract tests for the pinned native MapInfo reader.

The fixture producer writes physical bits independently of the library writer.
All values are invented test data; no replay, PE or personal data is loaded.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import native_mapinfo as codec


class Fixture:
    """Small schema-driven fixture writer with independently packed bits."""
    def __init__(self, overrides=None, start=0):
        self.records = codec._schema().records
        self.overrides = overrides or {}
        self.physical = [1] * start
        self.spans = {}
        self.start = start
        self.write(codec.ROOT_TYPE)
        self.end = len(self.physical)
        self.physical += [1] * 19
        self.raw = self.pack(self.physical)

    @staticmethod
    def pack(bits):
        raw = bytearray((len(bits) + 7) // 8)
        for at, value in enumerate(bits):
            raw[at // 8] |= value << (at % 8)
        return bytes(raw)

    def bits(self, value, width):
        # The wire consumes the low physical bits of each byte as a BE chunk.
        if not 0 <= value < (1 << width):
            raise ValueError('Fixture value outside width')
        left = width
        while left:
            count = min(left, 8 - len(self.physical) % 8)
            left -= count
            chunk = (value >> left) & ((1 << count) - 1)
            self.physical += [(chunk >> bit) & 1 for bit in range(count)]

    def blob(self, data):
        self.physical += [0] * (-len(self.physical) % 8)
        for value in data:
            self.bits(value, 8)

    def write(self, identifier, path=''):
        record = self.records[identifier]
        kind = record['kind']
        bound = record.get('bounds')
        start = len(self.physical)
        if kind == 'USER':
            self.write(record['element_type'], path)
        elif kind == 'STRUCT':
            for name, child in zip(record['field_names'], record['field_types']):
                self.write(child, path + '/' + name)
        elif kind == 'OPTIONAL':
            present = self.overrides.get(path, 0)
            self.bits(present, 1)
            if present:
                self.write(record['element_type'], path + '/value')
        elif kind == 'ARRAY':
            count = self.overrides.get(path, bound['min'])
            self.bits(count - bound['min'], bound['bits'])
            for index in range(count):
                self.write(record['element_type'], path + '/' + str(index))
        elif kind in ('STRING', 'BLOB'):
            data = self.overrides.get(path, b'a' * bound['min'])
            self.bits(len(data) - bound['min'], bound['bits'] + (2 if kind == 'STRING' else 0))
            self.blob(data)
        elif kind in ('INT', 'ENUM'):
            default = record['tags'][0] if kind == 'ENUM' else max(0, bound['min'])
            value = self.overrides.get(path, default)
            self.bits(value - bound['min'], bound['bits'])
        elif kind in ('BOOL', 'FOURCC'):
            self.bits(self.overrides.get(path, 0), 1 if kind == 'BOOL' else 32)
        else:
            raise AssertionError('Unexpected kind in selected closure: ' + kind)
        if kind != 'USER':
            self.spans[path] = (start, len(self.physical))

    def decode(self):
        return codec.decode_mapinfo(self.raw, self.start, codec.PROFILE)

    def with_bits(self, start, width, value):
        # Reuse only physical packing: splice a scalar encoded at its real offset.
        other = object.__new__(Fixture)
        other.physical = list(self.physical[:start])
        other.bits(value, width)
        return self.pack(other.physical + self.physical[start + width:])


class MapInfoTests(unittest.TestCase):
    def test_authenticated_schema_is_complete_closed_and_exactly_32_fields(self):
        records = codec._schema().records
        self.assertEqual(len(records), 191)
        root = records[5852]
        self.assertEqual(root['name'], 'Battlenet::Event::S2Maps::S2MapInfo')
        self.assertEqual(root['tags'], list(range(-32, 0)))
        self.assertEqual(len(root['field_names']), 32)
        self.assertEqual(root['field_names'][-2:], ['m_addMultiMod', 'm_requiredPermissions'])
        visited = set()
        def visit(identifier):
            if identifier in visited:
                return
            visited.add(identifier)
            record = records[identifier]
            for child in record.get('field_types', []) + ([record['element_type']] if 'element_type' in record else []):
                visit(child)
        visit(5852)
        self.assertEqual(visited, set(records))
        permission = records[1828]['bounds']
        self.assertEqual((permission['bits'], permission['max']), (31, 2147483647))

    def test_all_eight_partial_starts_preserve_prefix_and_mask_suffix(self):
        for start in range(8, 16):
            with self.subTest(start=start):
                fixture = Fixture(start=start)
                info = fixture.decode()
                self.assertEqual(info.end_bit, fixture.end)
                output = codec.encode_mapinfo(info)
                expected = bytearray(fixture.raw[start // 8:(fixture.end + 7) // 8])
                if fixture.end % 8:
                    expected[-1] &= (1 << (fixture.end % 8)) - 1
                self.assertEqual(output, bytes(expected))
                self.assertEqual(info.summary()['last_two_named_widths'], [1, 31])

    def test_nonzero_identity_is_handle_pair_not_semantic_map_version(self):
        fixture = Fixture({'/m_handle/m_id': 41234, '/m_handle/m_version': 701,
                           '/m_mapVersion/m_major': 4, '/m_mapVersion/m_minor': 9})
        info = fixture.decode()
        self.assertEqual(info.identity, (41234, 701))
        self.assertEqual(info.field('/m_mapVersion').value, {'m_major': 4, 'm_minor': 9})

    def test_nonempty_permissions_dependencies_and_optional_utf8_are_private(self):
        sentinel = 'PrivateAuthorŻółw'.encode('utf-8')
        fixture = Fixture({'/m_authorRealName': 1,
                           '/m_authorRealName/value/m_givenName': sentinel,
                           '/m_authorRealName/value/m_surname': b'SyntheticSurname',
                           '/m_clusterParent': 1, '/m_clusterChildren': 2,
                           '/m_extraDependencies': 2, '/m_requiredPermissions': 3,
                           '/m_addMultiMod': 1, '/m_arcadeGameInfo': 1,
                           '/m_arcadeGameInfo/value/m_howToPlaySections': 1}, start=5)
        info = fixture.decode()
        self.assertEqual(info.end_bit, fixture.end)
        self.assertEqual(info.summary()['required_permission_count'], 3)
        # Permission::Handle is the full namespace/program/id triple (96 bits).
        self.assertEqual(info.summary()['last_two_named_widths'], [1, 31 + 3 * 96])
        private_field = info.field('/m_authorRealName/value/m_givenName')
        self.assertEqual(private_field.value, sentinel)
        for public in (repr(info), repr(private_field), repr(info.tokens), json.dumps(info.summary())):
            self.assertNotIn('PrivateAuthor', public)
            self.assertNotIn('SyntheticSurname', public)

    def test_readonly_encoder_rejects_same_width_scalar_mutation(self):
        info = Fixture().decode()
        tokens = list(info.tokens)
        index = next(i for i, token in enumerate(tokens) if token.width == 32)
        tokens[index] = replace(tokens[index], value=tokens[index].value ^ 1)
        with self.assertRaisesRegex(codec.LayerError, 'Read-only'):
            codec.encode_mapinfo(replace(info, tokens=tuple(tokens)))

    def test_readonly_encoder_rejects_same_length_blob_mutation(self):
        info = Fixture().decode()
        tokens = list(info.tokens)
        index = next(i for i, token in enumerate(tokens) if token.width is None and token.value)
        tokens[index] = replace(tokens[index], value=bytes([tokens[index].value[0] ^ 1]) + tokens[index].value[1:])
        with self.assertRaisesRegex(codec.LayerError, 'Read-only'):
            codec.encode_mapinfo(replace(info, tokens=tuple(tokens)))

    def test_invalid_profile_source_extent_and_clientinfo_masquerade_rejected(self):
        info = Fixture().decode()
        for changed in (replace(info, profile='clientinfo-98348'),
                        replace(info, source=info.source + b'\0'),
                        replace(info, end_bit=info.end_bit - 1),
                        replace(info, start_bit=True)):
            with self.subTest(changed=type(changed).__name__), self.assertRaises(codec.LayerError):
                codec.encode_mapinfo(changed)
        client = codec.shared.ClientInfo(info.profile, info.start_bit, info.end_bit,
                                        info.fields, info.tokens, info.source, info.source_sha256)
        with self.assertRaises(codec.LayerError):
            codec.encode_mapinfo(client)

    def test_wrong_profile_nonbytes_and_invalid_start_rejected(self):
        raw = Fixture().raw
        for data, start, profile in ((raw, 0, 'current-observed'), (bytearray(raw), 0, codec.PROFILE),
                                     (raw, True, codec.PROFILE), (raw, -1, codec.PROFILE),
                                     (raw, len(raw) * 8, codec.PROFILE)):
            with self.subTest(start=start, profile=profile), self.assertRaises(codec.LayerError):
                codec.decode_mapinfo(data, start, profile)

    def test_truncation_and_nonzero_alignment_padding_rejected(self):
        fixture = Fixture(start=3)
        with self.assertRaises(codec.LayerError):
            codec.decode_mapinfo(fixture.raw[:fixture.end // 8 - 1], 3, codec.PROFILE)
        field = fixture.decode().field('/m_authorToonName/m_name')
        data_start = field.start_bit + 7  # Toon::Name uses five count bits plus two UTF8 byte bits.
        self.assertNotEqual(data_start % 8, 0)
        malformed = fixture.with_bits(data_start, 1, 1)
        with self.assertRaisesRegex(codec.LayerError, 'alignment'):
            codec.decode_mapinfo(malformed, 3, codec.PROFILE)

    def test_invalid_utf8_and_native_character_count_rejected(self):
        for text in (b'\xff\xff', 'é'.encode('utf-8')):
            fixture = Fixture({'/m_authorToonName/m_name': text})
            with self.subTest(text=text), self.assertRaises(codec.LayerError):
                fixture.decode()

    def test_count_limits_reject_before_element_decode(self):
        fixture = Fixture()
        count_start = fixture.spans['/m_requiredPermissions'][0]
        hostile = fixture.with_bits(count_start, 31, codec.shared.MAX_ARRAY + 1)
        with self.assertRaisesRegex(codec.LayerError, 'array exceeds'):
            codec.decode_mapinfo(hostile, 0, codec.PROFILE)
        children_start = fixture.spans['/m_clusterChildren'][0]
        hostile = fixture.with_bits(children_start, 12, 2049)
        with self.assertRaisesRegex(codec.LayerError, 'array exceeds'):
            codec.decode_mapinfo(hostile, 0, codec.PROFILE)

    def test_post_recursion_field_budget_and_wire_budget_are_independent(self):
        fixture = Fixture()
        info = fixture.decode()
        self.assertGreater(len(info.fields), len(info.tokens))
        with patch.object(codec.shared, 'MAX_TOKENS', len(info.fields) - 1):
            with self.assertRaisesRegex(codec.LayerError, 'field budget'):
                fixture.decode()
        with patch.object(codec.shared, 'MAX_TOKENS', 1):
            decoder = codec.shared._Decoder(codec._schema(), fixture.raw, 0)
            decoder.tokens.append(codec.shared.WireToken(0, 0))
            with self.assertRaisesRegex(codec.LayerError, 'wire-token budget'):
                decoder.decode(codec.ROOT_TYPE)

    def test_schema_mutation_oversize_and_symlink_are_refused(self):
        raw = Fixture().raw
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'schema.json'
            path.write_bytes(b'{}')
            with self.assertRaisesRegex(codec.LayerError, 'Pinned'):
                codec.decode_mapinfo(raw, 0, codec.PROFILE, schema_path=path)
            path.write_bytes(b' ' * (codec.MAX_SCHEMA_BYTES + 1))
            with self.assertRaisesRegex(codec.LayerError, 'size or type'):
                codec.decode_mapinfo(raw, 0, codec.PROFILE, schema_path=path)
            link = Path(temporary) / 'link.json'
            try:
                link.symlink_to(path)
            except OSError:
                return  # Windows may not grant symlink creation; other guards still ran.
            with self.assertRaisesRegex(codec.LayerError, 'symlink'):
                codec.decode_mapinfo(raw, 0, codec.PROFILE, schema_path=link)


if __name__ == '__main__':
    unittest.main()
