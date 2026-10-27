"""Independent wire controls and official-oracle tests; no private header literals."""
import copy
from dataclasses import FrozenInstanceError
import importlib
import os
from pathlib import Path
import tempfile
import unittest

import lossless_wire as wire
import native_replay_header as header
from protocol_loader import load_protocol
from heroprotocol.decoders import VersionedDecoder

SCHEMA = os.environ.get('HOTS_HEADER879_SCHEMA_PATH')


def minimal():
    integer = lambda x: wire.Node(9, x)
    version = wire.Node(5, [(i, integer(value)) for i, value in enumerate((1, 2, 57, 0, 98348, 98348))])
    digest = lambda ch: wire.Node(5, [(1, wire.Node(2, ch * 16))])
    return wire.Node(5, [(0, wire.Node(2, b'SYNTHETIC')), (1, version),
                         (2, integer(2)), (3, integer(16)), (4, wire.Node(6, 0)),
                         (5, digest(b'R')), (6, integer(98348)), (7, digest(b'H'))])


def decode(raw, **kwargs):
    return header.decode_header879(raw, schema_path=SCHEMA, **kwargs)


def official(raw, build=96477):
    protocol = load_protocol(build)
    decoder = VersionedDecoder(raw, protocol.typeinfos)
    value = decoder.instance(protocol.replay_header_typeid)
    if not decoder.done() or decoder.used_bits() != len(raw) * 8:
        raise ValueError('Independent official EOF differs')
    return value


class Header879Tests(unittest.TestCase):
    def test_pinned_official_decoder_accepts_exact_LF_and_CRLF_sources(self):
        decoder = importlib.import_module('heroprotocol.decoders')
        canonical = Path(decoder.__file__).read_bytes().replace(b'\r\n', b'\n')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'decoders.py'
            for raw in (canonical, canonical.replace(b'\n', b'\r\n')):
                with self.subTest(source_bytes=len(raw)):
                    path.write_bytes(raw)
                    self.assertEqual(header._pinned(path, header.DECODER_PIN,
                                                   alternates=header.DECODER_ALTERNATE_PINS), raw)

    def test_pinned_official_decoder_refuses_unreviewed_source_variants(self):
        decoder = importlib.import_module('heroprotocol.decoders')
        canonical = Path(decoder.__file__).read_bytes().replace(b'\r\n', b'\n')
        refused = (canonical + b'# changed\n', canonical[:-1],
                   canonical.replace(b'\n', b'\r\n', 1), b'X' * 9513)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'decoders.py'
            for raw in refused:
                with self.subTest(source_bytes=len(raw)):
                    path.write_bytes(raw)
                    with self.assertRaises(header.HeaderError):
                        header._pinned(path, header.DECODER_PIN,
                                       alternates=header.DECODER_ALTERNATE_PINS)

    def test_independent_partial_literal_and_missing_paths(self):
        raw = b'\x05\x04\x00\x02\x02A\x04\x09\x04'
        view = decode(raw)
        self.assertEqual(view.value, {0: b'A', 2: 2})
        self.assertIn((1,), view.missing_paths)
        self.assertEqual(header.encode_header879(view), raw)

    def test_complete_synthetic_projection_and_source_inverse(self):
        raw = wire.encode(minimal())
        view = decode(raw)
        self.assertEqual(view.value[1][4], 98348)
        self.assertEqual(view.missing_paths, ())
        self.assertEqual(view.unknown_paths, ())
        self.assertEqual(header.encode_header879(view), raw)
        for build in (41810, 96477):
            self.assertEqual(header.encode_header879(decode(raw, official_build=build)), raw)
            self.assertEqual(official(raw, build)['m_version']['m_build'], 98348)

    def test_edited_bytes_have_independent_official_projection_and_exact_reverse(self):
        raw = wire.encode(minimal())
        source = decode(raw)
        edited = header.replace_existing_int(source, (1, 4), 41810)
        changed = header.encode_header879(edited)
        for build in (41810, 96477):
            expected = copy.deepcopy(official(raw, build))
            expected['m_version']['m_build'] = 41810
            self.assertEqual(official(changed, build), expected)
        self.assertEqual(header.encode_header879(source), raw)
        self.assertEqual(header.encode_header879(header.replace_existing_int(edited, (1, 4), 98348)), raw)

    def test_nonminimal_integer_negative_zero_and_key_spellings_survive_reverse(self):
        raw = b'\x05\x82\x00\x82\x00\x05\x82\x00\x88\x00\x09\x81\x00'
        source = decode(raw)
        self.assertEqual(source.value, {1: {4: 0}})
        edited = header.replace_existing_int(source, (1, 4), 1)
        expected = copy.deepcopy(official(raw))
        expected['m_version']['m_build'] = 1
        self.assertEqual(official(header.encode_header879(edited)), expected)
        restored = header.replace_existing_int(edited, (1, 4), 0)
        self.assertEqual(header.encode_header879(restored), raw)

    def test_unknown_field_order_and_nonminimal_spellings_retained(self):
        raw = b'\x05\x84\x00\xc6\x01\x09\x81\x00\x04\x09\x00'
        source = decode(raw)
        self.assertEqual(source.unknown_paths, ((99,),))
        self.assertEqual(source.value, {2: 0})
        self.assertEqual(header.encode_header879(source), raw)
        edited = header.replace_existing_int(source, (2,), 1)
        self.assertEqual(official(header.encode_header879(edited))['m_type'], 1)
        self.assertEqual(header.encode_header879(header.replace_existing_int(edited, (2,), 0)), raw)

    def test_nested_deprecated_optional_is_preserved_but_not_invented(self):
        tree = minimal()
        tree.field(5).value.insert(0, (0, wire.Node(4, None)))
        raw = wire.encode(tree)
        source = decode(raw)
        self.assertEqual(source.unknown_paths, ((5, 0),))
        self.assertIsNone(official(raw)['m_ngdpRootKey']['m_dataDeprecated'])
        self.assertEqual(header.encode_header879(source), raw)
        self.assertNotIn(0, source.value[5])

    def test_signature32_accepted33_refused_while_official_accepts(self):
        for length in (32, 33):
            tree = minimal()
            tree.field(0).value = b'X' * length
            raw = wire.encode(tree)
            self.assertEqual(len(official(raw)['m_signature']), length)
            if length == 32:
                self.assertEqual(header.encode_header879(decode(raw)), raw)
            else:
                with self.assertRaises(header.HeaderError):
                    decode(raw)

    def test_enum3_accepted4_refused_while_official_accepts(self):
        source = decode(wire.encode(minimal()))
        self.assertEqual(header.replace_existing_int(source, (2,), 3).value[2], 3)
        tree = minimal()
        tree.field(2).value = 4
        raw = wire.encode(tree)
        self.assertEqual(official(raw)['m_type'], 4)
        with self.assertRaises(header.HeaderError):
            decode(raw)
        with self.assertRaises(header.HeaderError):
            header.replace_existing_int(source, (2,), 4)

    def test_unsigned_integer_boundaries_and_no_positive_build_policy(self):
        source = decode(wire.encode(minimal()))
        for path, maximum in (((1, 0), 255), ((1, 4), 2**32-1)):
            for value in (0, maximum):
                self.assertEqual(header.replace_existing_int(source, path, value).value[1][path[1]], value)
            for value in (-1, maximum+1, True):
                with self.assertRaises(header.HeaderError):
                    header.replace_existing_int(source, path, value)

    def test_fixed_digest_length(self):
        for length in (15, 17):
            tree = minimal()
            tree.field(7).field(1).value = b'H' * length
            with self.assertRaises(header.HeaderError):
                decode(wire.encode(tree))

    def test_missing_unknown_scalar_and_bool_edit_paths_refused(self):
        source = decode(b'\x05\x02\x04\x09\x04')
        for path in ((1, 4), (99,), (2, 0)):
            with self.assertRaises(header.HeaderError):
                header.replace_existing_int(source, path, 1)
        full = decode(wire.encode(minimal()))
        with self.assertRaises(header.HeaderError):
            header.replace_existing_int(full, (4,), 1)
        self.assertEqual(header.encode_header879(source), b'\x05\x02\x04\x09\x04')

    def test_duplicate_known_unknown_and_negative_zero_aliases_refused(self):
        literals = [b'\x05\x04\x04\x09\x00\x04\x09\x02',
                    b'\x05\x04\x00\x02\x00\x01\x02\x00',
                    b'\x05\x04\xc6\x01\x09\x00\xc6\x01\x09\x02']
        for raw in literals:
            with self.subTest(raw_length=len(raw)), self.assertRaises(header.HeaderError):
                decode(raw)

    def test_every_truncated_prefix_and_trailing_byte_refused(self):
        raw = wire.encode(minimal())
        for size in range(len(raw)):
            with self.subTest(size=size), self.assertRaises(header.HeaderError):
                decode(raw[:size])
        for suffix in (b'\x00', b'\x09\x00'):
            with self.assertRaises(header.HeaderError):
                decode(raw + suffix)

    def test_byte_cap_type_and_wrong_root_tag(self):
        for raw in (b'', bytearray(b'\x05\x00'), b'\x00\x00', b'X' * 4097):
            with self.assertRaises(header.HeaderError):
                decode(raw)

    def test_noncanonical_true_bool_is_source_preserved(self):
        tree = minimal()
        tree.field(4).value = 255
        raw = wire.encode(tree)
        self.assertTrue(decode(raw).value[4])
        self.assertTrue(official(raw)['m_useScaledTime'])
        self.assertEqual(header.encode_header879(decode(raw)), raw)

    def test_public_value_copy_and_frozen_view(self):
        raw = wire.encode(minimal())
        source = decode(raw)
        value = source.value
        value[1][4] = 0
        self.assertEqual(source.value[1][4], 98348)
        self.assertEqual(header.encode_header879(source), raw)
        with self.assertRaises(FrozenInstanceError):
            source.source_sha256 = 'changed'

    def test_schema_and_oracle_pins_required(self):
        with self.assertRaises(header.HeaderError):
            decode(wire.encode(minimal()), official_build=97771)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'schema.json'
            path.write_bytes(b'{}')
            with self.assertRaises(header.HeaderError):
                header.decode_header879(wire.encode(minimal()), schema_path=path)


if __name__ == '__main__':
    unittest.main()
