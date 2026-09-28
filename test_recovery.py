import hashlib
import importlib.util
import os
import random
import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from types import SimpleNamespace

from migrate_replay import BitVector, SemanticDecoder, SemanticEncoder, adapt, decode_events, encode_events, SOURCE_SHA256
from mpq_reader import MPQArchive
from mpq_rebuild import rebuild_replay, verify_container
import protocol41810
import protocol44256

SOURCE = Path(os.environ.get('SOURCE_REPLAY_PATH', 'work/TEN_GREYMANE_source_41810.StormReplay'))


class BitVectorTests(unittest.TestCase):
    def test_all_byte_alignments(self):
        rng = random.Random(41810)
        for alignment in range(8):
            for length in (0, 1, 2, 3, 7, 8, 15, 31, 63, 127, 255):
                with self.subTest(alignment=alignment, length=length):
                    schema = [('_int', [(0, alignment)]), ('_bitarray', [(0, 8)])]
                    value = BitVector(length, rng.getrandbits(length))
                    encoder = SemanticEncoder(schema)
                    encoder.instance(0, 0)
                    encoder.instance(1, value)
                    decoder = SemanticDecoder(encoder.getvalue(), schema)
                    decoder.instance(0)
                    self.assertEqual(value, decoder.instance(1))

    def test_native_values_survive_length_field_width_change(self):
        for width in (4, 8):
            for alignment in range(8):
                schema = [('_int', [(0, alignment)]), ('_bitarray', [(0, width)])]
                encoder = SemanticEncoder(schema)
                encoder.instance(0, 0)
                encoder.instance(1, BitVector(15, 7))
                decoder = SemanticDecoder(encoder.getvalue(), schema)
                decoder.instance(0)
                self.assertEqual(decoder.instance(1), BitVector(15, 7))

    def test_zero_control_tail_is_preserved(self):
        p = SimpleNamespace(typeinfos=[('_bitarray', [(0, 4)])])
        audit = []
        result = adapt(BitVector(255, 896 << 240), p, 0, '/slot/m_allowedControls', audit)
        self.assertEqual(result, BitVector(15, 896))
        self.assertEqual(audit[0]['operation'], 'remove-zero-control-tail')

    def test_all_controls_restriction_is_audited(self):
        p = SimpleNamespace(typeinfos=[('_bitarray', [(0, 4)])])
        audit = []
        result = adapt(BitVector(255, (1 << 255) - 1), p, 0, '/slot/m_allowedControls', audit)
        self.assertEqual(result, BitVector(15, 32767))
        self.assertEqual(audit[0]['operation'], 'restrict-all-controls-to-target-domain')

    def test_nonzero_unrepresentable_flags_are_rejected(self):
        p = SimpleNamespace(typeinfos=[('_bitarray', [(0, 4)])])
        with self.assertRaises(ValueError):
            adapt(BitVector(255, 1 << 30), p, 0, '/slot/m_allowedControls', [])

    def test_selection_masks_are_not_silently_truncated(self):
        p = SimpleNamespace(typeinfos=[('_bitarray', [(0, 4)])])
        with self.assertRaises(ValueError):
            adapt(BitVector(31, 7), p, 0, '/m_removeMask', [])

    def test_nonempty_removed_fields_are_rejected(self):
        p = SimpleNamespace(typeinfos=[('_struct', [[]])])
        with self.assertRaises(ValueError):
            adapt({'m_licenses': [1]}, p, 0, '/slot', [])

    def test_unknown_added_fields_are_rejected(self):
        p = SimpleNamespace(typeinfos=[('_struct', [[('unknown', 1, 0)]]), ('_int', [(0, 8)])])
        with self.assertRaises(ValueError):
            adapt({}, p, 0, '/slot', [])

    def test_integer_overflow_is_rejected(self):
        p = SimpleNamespace(typeinfos=[('_int', [(0, 24)])])
        with self.assertRaises(ValueError):
            adapt(1 << 24, p, 0, '/flags', [])

    def test_negative_event_delta_is_rejected(self):
        with self.assertRaises(ValueError):
            encode_events([{'_gameloop': -1}], protocol44256, 'game')


@unittest.skipUnless(SOURCE.is_file(), 'Source replay is not restored')
class SourceTests(unittest.TestCase):
    def setUp(self):
        self.archive = MPQArchive(SOURCE)

    def tearDown(self):
        self.archive.close()

    def test_source_checksum(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(), SOURCE_SHA256)

    def test_actual_source_control_vectors(self):
        raw = self.archive.read_file('replay.initData')
        data = SemanticDecoder(raw, protocol41810.typeinfos).instance(protocol41810.replay_initdata_typeid)
        slots = data['m_syncLobbyState']['m_gameDescription']['m_slotDescriptions']
        self.assertEqual([s['m_allowedControls'] for s in slots[:10]], [BitVector(255, (1 << 255) - 1)] * 10)
        self.assertEqual([s['m_allowedControls'] for s in slots[10:]], [BitVector(255, 896 << 240)] * 6)
        encoder = SemanticEncoder(protocol41810.typeinfos)
        encoder.instance(protocol41810.replay_initdata_typeid, data)
        self.assertEqual(encoder.getvalue(), raw)

    def test_source_game_stream_roundtrip(self):
        raw = self.archive.read_file('replay.game.events')
        events = list(decode_events(raw, protocol41810, 'game'))
        self.assertEqual(len(events), 104257)
        rewritten = encode_events(events, protocol41810, 'game')
        self.assertEqual(rewritten, raw)
        self.assertEqual(list(decode_events(rewritten, protocol41810, 'game')), events)

    def test_rebuild_checksums_and_untouched_payloads(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'rebuilt.StormReplay'
            changed = {'replay.load.info': bytes(range(256)) * 100}
            rebuild_replay(SOURCE, output, self.archive.header['user_data_header']['content'], changed)
            self.assertTrue(all(verify_container(output).values()))
            other = MPQArchive(output)
            try:
                for name in self.archive.read_file('(listfile)').decode().splitlines():
                    self.assertEqual(other.read_file(name), changed.get(name, self.archive.read_file(name)))
                index = other.get_hash_table_entry('replay.load.info').block_table_index
                attrs = other.read_file('(attributes)')
                count = len(other.block_table)
                self.assertEqual(struct.unpack_from('<I', attrs, 8 + 4 * index)[0], zlib.crc32(changed['replay.load.info']))
                md5_start = 8 + 4 * count + 16 * index
                self.assertEqual(attrs[md5_start:md5_start + 16], hashlib.md5(changed['replay.load.info']).digest())
            finally:
                other.close()
            broken = bytearray(output.read_bytes())
            broken[1024 + 8] ^= 1
            output.write_bytes(broken)
            with self.assertRaises(ValueError):
                verify_container(output)

    def test_cannot_overwrite_original(self):
        with self.assertRaises(ValueError):
            rebuild_replay(SOURCE, SOURCE, b'', {})


@unittest.skipUnless(importlib.util.find_spec('heroprotocol'), 'Pinned Blizzard checkout not available')
class UpstreamTests(unittest.TestCase):
    def test_local_schemas_equal_blizzard(self):
        from importlib import import_module
        for build in (41810, 43905, 44256):
            local = import_module(f'protocol{build}')
            official = import_module(f'heroprotocol.versions.protocol{build}')
            for name in ('typeinfos', 'game_event_types', 'message_event_types', 'tracker_event_types', 'replay_initdata_typeid'):
                self.assertEqual(getattr(local, name), getattr(official, name), (build, name))


if __name__ == '__main__':
    unittest.main()
