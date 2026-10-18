"""Independent physical-bit fixtures; all values are invented test data."""
from dataclasses import replace
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

import native_startgame as codec


class Fixture:
    def __init__(self, overrides=None):
        self.records = codec._schema().records
        self.overrides = overrides or {}
        self.physical = []
        self.spans = {}
        self.alignment = []
        self.write(codec.ROOT_TYPE)
        self.payload_end = len(self.physical)
        self.physical += [0]*(-len(self.physical) % 8)
        self.raw = self.pack(self.physical)

    @staticmethod
    def pack(bits):
        result = bytearray((len(bits)+7)//8)
        for index, bit in enumerate(bits):
            result[index//8] |= bit << (index % 8)
        return bytes(result)

    def bits(self, value, width):
        if not 0 <= value < (1 << width):
            raise ValueError('Fixture scalar cannot fit')
        remaining = width
        while remaining:
            count = min(remaining, 8-len(self.physical) % 8)
            remaining -= count
            chunk = value >> remaining
            self.physical.extend((chunk >> bit) & 1 for bit in range(count))

    def blob(self, value):
        padding = (-len(self.physical)) % 8
        if padding:
            self.alignment.append((len(self.physical), padding))
        self.physical += [0]*padding
        for byte in value:
            self.bits(byte, 8)

    def write(self, identifier, path=''):
        record = self.records[identifier]
        kind = record['kind']
        bound = record.get('bounds')
        start = len(self.physical)
        if kind == 'USER':
            self.write(record['element_type'], path)
        elif kind == 'STRUCT':
            for name, child in zip(record['field_names'], record['field_types']):
                self.write(child, path+'/'+name)
        elif kind == 'OPTIONAL':
            present = self.overrides.get(path, 0)
            self.bits(present, 1)
            if present:
                self.write(record['element_type'], path+'/value')
        elif kind == 'ARRAY':
            count = self.overrides.get(path, bound['min'])
            self.bits(count-bound['min'], bound['bits'])
            for index in range(count):
                self.write(record['element_type'], path+'/'+str(index))
        elif kind == 'CHOICE':
            tag = self.overrides.get(path, record['tags'][0])
            self.bits(tag-bound['min'], bound['bits'])
            index = record['tags'].index(tag)
            self.write(record['field_types'][index], path+'/'+record['field_names'][index])
        elif kind in ('STRING', 'ASCII_STRING', 'BLOB'):
            value = self.overrides.get(path, b'a'*bound['min'])
            self.bits(len(value)-bound['min'], bound['bits']+(2 if kind == 'STRING' else 0))
            self.blob(value)
        elif kind == 'BIT_ARRAY':
            count = self.overrides.get(path, bound['min'])
            self.bits(count-bound['min'], bound['bits'])
            for index in range(0, count, 64):
                self.bits(0, min(64, count-index))
        elif kind in ('INT', 'ENUM'):
            default = record['tags'][0] if kind == 'ENUM' else max(0, bound['min'])
            self.bits(self.overrides.get(path, default)-bound['min'], bound['bits'])
        elif kind in ('BOOL', 'FOURCC', 'REAL32', 'REAL64'):
            self.bits(self.overrides.get(path, 0), {'BOOL': 1, 'FOURCC': 32, 'REAL32': 32, 'REAL64': 64}[kind])
        elif kind != 'NULL':
            raise AssertionError('Uncovered fixture kind')
        if kind != 'USER':
            self.spans[path] = (start, len(self.physical))

    def decode(self):
        return codec.decode_startgame(self.raw, codec.PROFILE)

    def mutate_scalar(self, start, width, value):
        other = object.__new__(Fixture)
        other.physical = list(self.physical[:start])
        other.bits(value, width)
        return self.pack(other.physical+self.physical[start+width:])


class NativeStartGameTests(unittest.TestCase):
    def test_pinned_closure_is_closed_and_online_root_has_25_fields(self):
        records = codec._schema().records
        self.assertEqual(len(records), 513)
        self.assertEqual(tuple(records[5917]['field_names']), codec.ROOT_FIELDS)
        self.assertEqual(records[5917]['tags'], list(range(-25, 0)))
        reached = set()
        def visit(identifier):
            if identifier in reached:
                return
            reached.add(identifier)
            record = records[identifier]
            for child in record.get('field_types', [])+([record['element_type']] if 'element_type' in record else []):
                visit(child)
        visit(5917)
        visit(5962)  # The pinned selected file includes both roots, codec permits online only.
        self.assertEqual(reached, set(records))

    def test_minimal_fixture_whole_EOF_and_safe_summary(self):
        fixture = Fixture()
        value = fixture.decode()
        self.assertEqual(value.payload_end_bit, fixture.payload_end)
        self.assertEqual(value.payload_end_bit+value.padding_bits, len(fixture.raw)*8)
        self.assertEqual(codec.encode_startgame(value), fixture.raw)
        self.assertEqual(value.summary()['named_root_fields'], 25)
        self.assertEqual(value.summary()['root_field_spans'][0]['start_bit'], 0)
        self.assertFalse(value.summary()['archive_build_root_or_full_replay_compatibility_claimed'])

    def test_nonempty_native_branches_not_supported_by_old_opaque_groups(self):
        fixture = Fixture({
            '/m_ammHandle': 1, '/m_ladderStats': 1, '/m_ladderStats/value': 1,
            '/m_ladderStats/value/0/m_seasonRating': 1, '/m_races': 1, '/m_races/value': 2,
            '/m_clientUnlockableInfoList': 1, '/m_clientUnlockableInfoList/0/m_handleList': 2,
            '/m_clientUnlockableInfoList/0/m_overrides': 1,
            '/m_achievementTags': 2, '/m_clientLicensesList': 1,
            '/m_clientLicensesList/0/m_licenses': 2, '/m_tournamentInfo': 1,
            '/m_heroMasteryTiers': 2, '/m_heroMasteryTiers/0/m_playerTiers': 3,
            '/m_rejoinSaveCacheHandle': 1, '/m_rejoinSaveElapsedGameLoops': 1})
        value = fixture.decode()
        self.assertEqual(codec.encode_startgame(value), fixture.raw)
        self.assertEqual(value.field('/m_ammHandle').end_bit-value.field('/m_ammHandle').start_bit, 121)
        self.assertEqual(value.field('/m_ladderStats/value/0').end_bit-value.field('/m_ladderStats/value/0').start_bit, 70)
        self.assertEqual(value.field('/m_clientUnlockableInfoList/0/m_overrides', 'ARRAY').value, 1)
        self.assertEqual(value.field('/m_clientLicensesList/0').end_bit-value.field('/m_clientLicensesList/0').start_bit, 112)
        self.assertEqual(value.field('/m_heroMasteryTiers/0').end_bit-value.field('/m_heroMasteryTiers/0').start_bit, 61)

    def test_nonempty_matrix_mapinfo_and_client_lists_are_bounded(self):
        fixture = Fixture({'/StartGameRequest/m_mapInfoList': 1,
            '/StartGameRequest/m_resourceMap': 2, '/StartGameRequest/m_accessMatrix': 2,
            '/StartGameRequest/m_disabledHeroList': 1, '/m_clientInfoList': 1})
        value = fixture.decode()
        self.assertEqual(value.summary()['safe_array_counts']['/StartGameRequest/m_accessMatrix'], 2)
        self.assertEqual(value.field('/StartGameRequest/m_accessMatrix').end_bit-
                         value.field('/StartGameRequest/m_accessMatrix').start_bit, 32+2*16*16)
        self.assertEqual(codec.encode_startgame(value), fixture.raw)

    def test_UTF8_private_author_is_not_in_repr_or_summary(self):
        path = '/StartGameRequest/m_mapInfoList/0/m_authorRealName'
        sentinel = 'PrivateAuthorŻółw'.encode('utf-8')
        fixture = Fixture({'/StartGameRequest/m_mapInfoList': 1, path: 1,
                           path+'/value/m_givenName': sentinel})
        value = fixture.decode()
        field = value.field(path+'/value/m_givenName')
        self.assertEqual(field.value, sentinel)
        for output in (repr(value), repr(field), repr(value.tokens), json.dumps(value.summary())):
            self.assertNotIn('PrivateAuthor', output)

    def test_invalid_UTF8_character_bound_and_alignment_rejected(self):
        path = '/StartGameRequest/m_mapInfoList/0/m_authorToonName/m_name'
        for text in (b'\xff\xff', 'é'.encode('utf-8')):
            fixture = Fixture({'/StartGameRequest/m_mapInfoList': 1, path: text})
            with self.subTest(text=text), self.assertRaises(codec.LayerError):
                fixture.decode()
        fixture = Fixture()
        self.assertTrue(fixture.alignment)
        bad = fixture.mutate_scalar(fixture.alignment[0][0], 1, 1)
        with self.assertRaisesRegex(codec.LayerError, 'alignment'):
            codec.decode_startgame(bad, codec.PROFILE)

    def test_truncation_extra_EOF_byte_and_nonzero_EOF_padding_rejected(self):
        fixture = Fixture()
        for bad in (fixture.raw[:-1], fixture.raw+b'\0'):
            with self.subTest(size=len(bad)), self.assertRaises(codec.LayerError):
                codec.decode_startgame(bad, codec.PROFILE)
        self.assertNotEqual(fixture.payload_end % 8, 0)
        bad = fixture.mutate_scalar(fixture.payload_end, 1, 1)
        with self.assertRaisesRegex(codec.LayerError, 'EOF alignment'):
            codec.decode_startgame(bad, codec.PROFILE)

    def test_same_width_scalar_and_blob_mutations_are_readonly_rejected(self):
        value = Fixture().decode()
        for blob in (False, True):
            tokens = list(value.tokens)
            if blob:
                index = next(index for index, token in enumerate(tokens) if token.width is None and token.value)
            else:
                index = next(index for index, token in enumerate(tokens) if token.width == 32)
            token = tokens[index]
            changed = bytes([token.value[0]^1])+token.value[1:] if blob else token.value^1
            tokens[index] = replace(token, value=changed)
            with self.subTest(blob=blob), self.assertRaisesRegex(codec.LayerError, 'Read-only'):
                codec.encode_startgame(replace(value, tokens=tuple(tokens)))

    def test_wrong_source_profile_extent_and_types_are_refused(self):
        fixture = Fixture()
        value = fixture.decode()
        for bad in (replace(value, source=value.source+b'\0'), replace(value, padding_bits=True),
                    replace(value, payload_end_bit=value.payload_end_bit-1), replace(value, profile='offline-start-98348')):
            with self.assertRaises(codec.LayerError):
                codec.encode_startgame(bad)
        for raw, profile in ((bytearray(fixture.raw), codec.PROFILE), (b'', codec.PROFILE),
                             (fixture.raw, 'offline-start-98348'), (fixture.raw, 'clientinfo-98348')):
            with self.assertRaises(codec.LayerError):
                codec.decode_startgame(raw, profile)

    def test_separate_field_and_wire_caps_include_pending_recursive_parents(self):
        fixture = Fixture()
        value = fixture.decode()
        self.assertGreater(len(value.fields), len(value.tokens))
        with patch.object(codec, 'MAX_FIELDS', len(value.fields)-1):
            with self.assertRaisesRegex(codec.LayerError, 'field/depth'):
                fixture.decode()
        with patch.object(codec, 'MAX_WIRE_TOKENS', len(value.tokens)-1):
            with self.assertRaisesRegex(codec.LayerError, 'wire-token'):
                fixture.decode()
        with patch.object(codec, 'MAX_DEPTH', 1):
            with self.assertRaisesRegex(codec.LayerError, 'field/depth'):
                fixture.decode()

    def test_native_and_generic_array_count_limits_reject_before_payload(self):
        fixture = Fixture()
        for path, bits, value in (('/m_heroMasteryTiers', 10, 513),
                                   ('/StartGameRequest/m_resourceMap', 16, 32769)):
            bad = fixture.mutate_scalar(fixture.spans[path][0], bits, value)
            with self.subTest(path=path), self.assertRaisesRegex(codec.LayerError, 'array exceeds'):
                codec.decode_startgame(bad, codec.PROFILE)

    def test_scalar_string_and_choice_budgets_reject_malformed_data(self):
        fixture = Fixture()
        path = '/StartGameRequest/StartRequest/m_workingSet/m_specialScope'
        bad = fixture.mutate_scalar(fixture.spans[path][0], 5, 31)
        with self.assertRaisesRegex(codec.LayerError, 'scalar outside'):
            codec.decode_startgame(bad, codec.PROFILE)
        with patch.object(codec, 'MAX_STRING', 3):
            with self.assertRaisesRegex(codec.LayerError, 'string/blob exceeds'):
                fixture.decode()
        fixture = Fixture({'/m_clientInfoList': 1})
        path = '/m_clientInfoList/0/m_talkerInfo/m_id/m_id'
        bad = fixture.mutate_scalar(fixture.spans[path][0], 2, 3)
        with self.assertRaisesRegex(codec.LayerError, 'choice tag'):
            codec.decode_startgame(bad, codec.PROFILE)

    def test_schema_and_shared_type_file_pins_are_enforced(self):
        fixture = Fixture()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'schema.json'
            path.write_bytes(b'{}')
            with self.assertRaisesRegex(codec.LayerError, 'Pinned'):
                codec.decode_startgame(fixture.raw, codec.PROFILE, schema_path=path)
            path.write_bytes(b' '*(codec.MAX_SCHEMA_BYTES+1))
            with self.assertRaisesRegex(codec.LayerError, 'size or file type'):
                codec.decode_startgame(fixture.raw, codec.PROFILE, schema_path=path)
            path.write_bytes(b'fake shared source')
            with patch.object(codec.shared, '__file__', str(path)):
                with self.assertRaisesRegex(codec.LayerError, 'Pinned'):
                    fixture.decode()
            with patch.object(Path, 'is_symlink', return_value=True):
                with self.assertRaisesRegex(codec.LayerError, 'symlink'):
                    fixture.decode()

    def test_ASCII_endpoint_BIT_ARRAY_and_REAL64_primitive_branches(self):
        talker = '/m_clientInfoList/0/m_talkerInfo/m_id/m_id'
        endpoint = talker+'/datagramConnectionEndPoint/m_endPoint/m_id'
        target = endpoint+'/playerTarget/m_playerTarget'
        mail = target+'/accountMail'
        restrict = '/StartGameRequest/StartRequest/m_workingSet/m_indexRestrictions'
        bitfield = restrict+'/0/m_data/AllSlots/m_byIndex'
        overrides = {'/m_clientInfoList': 1, talker: 1, endpoint: 0, target: 2,
                     mail: b'invented-ascii-fixture', '/m_clientInfoList/0/m_rating': 1,
                     '/m_clientInfoList/0/m_rating/value': 0x3ff0000000000000,
                     restrict: 1, restrict+'/0/m_data': 0, bitfield: 65}
        fixture = Fixture(overrides)
        value = fixture.decode()
        self.assertEqual(value.field(mail).kind, 'ASCII_STRING')
        self.assertEqual(value.field('/m_clientInfoList/0/m_rating/value').kind, 'REAL64')
        field = value.field(bitfield)
        self.assertEqual((field.kind, field.value, field.end_bit-field.start_bit), ('BIT_ARRAY', 65, 12+65))
        self.assertEqual(codec.encode_startgame(value), fixture.raw)
        invalid_ASCII = Fixture({**overrides, mail: b'\xffxx'})
        with self.assertRaisesRegex(codec.LayerError, 'encoding'):
            invalid_ASCII.decode()
        bad = fixture.mutate_scalar(fixture.spans[bitfield][0], 12, 2049)
        with self.assertRaisesRegex(codec.LayerError, 'bit array exceeds'):
            codec.decode_startgame(bad, codec.PROFILE)


if __name__ == '__main__':
    unittest.main()
