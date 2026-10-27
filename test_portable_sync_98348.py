"""Focused synthetic wire checks; no private replay, PE or client reads.

The oracles below are literal, hand-laid-out bytes, not codec-generated data.
For example delta64/event2/u16=0x1234 is 01 40 13 1a 00: the low two
bits choose the 14-bit delta, and the final byte retains seven alignment bits.
"""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from portable_sync_98348 import (  # noqa: E402
    MAX_U32, SyncFormatError, SyncRecord, canonical_delta_variant,
    decode_sync, encode_sync,
)


class PortableSyncWireTests(unittest.TestCase):
    def test_delta_thresholds_and_noncanonical_wide_choices(self):
        # One event2, value0x1234 per vector; every width and transition is
        # independently specified. Wide encodings of1 must remain wide.
        vectors = (
            (0, 0, '00 13 1a 00'),
            (63, 0, 'fc 13 1a 00'),
            (64, 1, '01 40 13 1a 00'),
            (16383, 1, 'fd ff 13 1a 00'),
            (16384, 2, '02 40 00 13 1a 00'),
            (4194303, 2, 'fe ff ff 13 1a 00'),
            (4194304, 3, '03 10 00 00 14 46 04'),
            (MAX_U32, 3, 'ff ff ff ff 17 46 04'),
            (1, 1, '01 01 13 1a 00'),
            (1, 2, '02 00 01 13 1a 00'),
            (1, 3, '03 00 00 00 15 46 04'),
        )
        for delta, variant, literal in vectors:
            with self.subTest(delta=delta, variant=variant):
                raw = bytes.fromhex(literal)
                records = decode_sync(raw)
                self.assertEqual(len(records), 1)
                record = records[0]
                self.assertEqual((record.gameloop, record.delta, record.delta_variant,
                                  record.event_id, record.words, record.value_u16),
                                 (delta, delta, variant, 2, None, 0x1234))
                expected = SyncRecord(delta, delta, variant, 2, None, 0x1234)
                self.assertEqual(encode_sync([expected]), raw)
                self.assertEqual(encode_sync(records), raw)
        for delta, variant in ((0, 0), (63, 0), (64, 1), (16383, 1),
                               (16384, 2), (4194303, 2), (4194304, 3),
                               (MAX_U32, 3), (1, 0)):
            self.assertEqual(canonical_delta_variant(delta), variant)

    def test_both_payloads_and_consecutive_record_offsets(self):
        # First word0x01234567 straddles four full/partial wire bytes. These
        # asymmetric values catch reversed chunk order and count misalignment.
        raw = bytes.fromhex('04 00 01 91 a2 b3 ab e6 01 01 40 13 1a 00')
        first, second = decode_sync(raw)
        self.assertEqual((first.gameloop, first.delta, first.event_id,
                          first.words, first.value_u16),
                         (1, 1, 1, (0x01234567,), 0xabcd))
        self.assertEqual((first.start_bit, first.payload_end_bit, first.end_bit),
                         (0, 65, 72))
        self.assertEqual((second.gameloop, second.delta, second.event_id,
                          second.words, second.value_u16),
                         (65, 64, 2, None, 0x1234))
        self.assertEqual((second.start_bit, second.payload_end_bit, second.end_bit),
                         (72, 105, 112))
        expected = [SyncRecord(1, 1, 0, 1, (0x01234567,), 0xabcd),
                    SyncRecord(65, 64, 1, 2, None, 0x1234)]
        self.assertEqual(encode_sync(expected), raw)

    def test_array255_literal_and_reject256(self):
        # 8+1+8+255*32+16=8193 payload bits, padded to1025 bytes. The count
        # low bit shares byte2 with the first zero word; all later bits are0.
        raw = bytes.fromhex('00 fe 01') + bytes(1022)
        record, = decode_sync(raw)
        self.assertEqual(record.words, (0,) * 255)
        self.assertEqual((record.value_u16, record.payload_end_bit, record.end_bit),
                         (0, 8193, 8200))
        self.assertEqual(encode_sync([SyncRecord(0, 0, 0, 1, (0,) * 255, 0)]), raw)
        with self.assertRaisesRegex(SyncFormatError, 'count bound'):
            encode_sync([replace(record, words=(0,) * 256)])

    def test_every_nonempty_truncated_prefix_is_rejected(self):
        # Every proper nonempty byte prefix of this single event is invalid.
        # Empty input is a valid empty member rather than a truncated event.
        raw = bytes.fromhex('04 00 01 91 a2 b3 ab e6 01')
        self.assertEqual(decode_sync(b''), ())
        for length in range(1, len(raw)):
            with self.subTest(length=length):
                with self.assertRaisesRegex(SyncFormatError, 'Truncated'):
                    decode_sync(raw[:length])
        with self.assertRaisesRegex(SyncFormatError, 'Truncated'):
            decode_sync(raw + b'\x00')

    def test_u16_and_u32_extrema_and_rejected_values(self):
        zero = SyncRecord(0, 0, 0, 2, None, 0)
        self.assertEqual(encode_sync([zero]), bytes.fromhex('00 01 00 00'))
        self.assertEqual(encode_sync([replace(zero, value_u16=65535)]),
                         bytes.fromhex('00 ff ff 01'))
        maximum_word_raw = bytes.fromhex('04 00 ff ff ff ff ff ff 01')
        maximum = SyncRecord(1, 1, 0, 1, (MAX_U32,), 65535)
        self.assertEqual(encode_sync([maximum]), maximum_word_raw)
        decoded, = decode_sync(maximum_word_raw)
        self.assertEqual((decoded.words, decoded.value_u16), ((MAX_U32,), 65535))
        for value in (-1, 65536, True):
            with self.subTest(u16=value):
                with self.assertRaises(SyncFormatError):
                    encode_sync([replace(zero, value_u16=value)])
        for value in (-1, MAX_U32 + 1, True):
            with self.subTest(word=value):
                with self.assertRaises(SyncFormatError):
                    encode_sync([replace(maximum, words=(value,))])
                with self.assertRaises(SyncFormatError):
                    canonical_delta_variant(value)

    def test_nonzero_padding_is_preserved(self):
        for literal, frame, variant, padding, payload_end in (
            ('01 40 13 1a aa', 64, 1, 0x55, 33),
            ('03 10 00 00 14 46 fc', 4194304, 3, 0x1f, 51),
        ):
            with self.subTest(variant=variant):
                raw = bytes.fromhex(literal)
                record, = decode_sync(raw)
                self.assertEqual((record.delta_variant, record.padding_value,
                                  record.payload_end_bit),
                                 (variant, padding, payload_end))
                self.assertEqual((record.gameloop, record.value_u16), (frame, 0x1234))
                self.assertEqual(encode_sync([record]), raw)
        normal = SyncRecord(64, 64, 1, 2, None, 0x1234)
        for padding in (-1, 128, True):
            with self.subTest(padding=padding):
                with self.assertRaises(SyncFormatError):
                    encode_sync([replace(normal, padding_value=padding)])

    def test_frame_overflow_rejected_for_both_directions(self):
        maximum_raw = bytes.fromhex('ff ff ff ff 17 46 04')
        next_raw = bytes.fromhex('04 13 1a 00')
        maximum, = decode_sync(maximum_raw)
        self.assertEqual(maximum.gameloop, MAX_U32)
        with self.assertRaisesRegex(SyncFormatError, 'wrap u32'):
            decode_sync(maximum_raw + next_raw)
        with self.assertRaisesRegex(SyncFormatError, 'wrap u32'):
            encode_sync([maximum, SyncRecord(0, 1, 0, 2, None, 0x1234)])

    def test_encoder_frame_choice_and_payload_shape_guards(self):
        record = SyncRecord(1, 1, 0, 2, None, 0x1234)
        with self.assertRaisesRegex(SyncFormatError, 'disagrees'):
            encode_sync([replace(record, gameloop=2)])
        with self.assertRaisesRegex(SyncFormatError, 'delta outside bounds'):
            encode_sync([replace(record, gameloop=64, delta=64)])
        for variant in (-1, 4, True):
            with self.subTest(variant=variant):
                with self.assertRaises(SyncFormatError):
                    encode_sync([replace(record, delta_variant=variant)])
        with self.assertRaisesRegex(SyncFormatError, 'no word vector'):
            encode_sync([replace(record, words=())])
        with self.assertRaisesRegex(SyncFormatError, 'count bound'):
            encode_sync([replace(record, event_id=1)])


if __name__ == '__main__':
    unittest.main(verbosity=2)
