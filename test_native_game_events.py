import unittest
from unittest.mock import patch

import native_game_events as game


class NativeGameEventsTests(unittest.TestCase):
    def empty(self, delta=0, user_id=0):
        return game.GameEvent(delta, user_id, 5, ())

    def chat(self, text):
        return game.GameEvent(0, 0, 32, (text,))

    def roundtrip(self, event):
        raw = game.encode_game_events([event])
        decoded = list(game.iter_game_events(raw))
        self.assertEqual(len(decoded), 1)
        self.assertEqual(decoded[0].event, event)
        self.assertEqual(decoded[0].aligned_end_bit, len(raw) * 8)
        return decoded[0]

    def test_known_empty_event_bytes(self):
        self.assertEqual(game.encode_game_events([self.empty()]), b'\0\0\x05')
        self.assertEqual(list(game.iter_game_events(b'\0\0\x05'))[0].event, self.empty())

    def test_user16_known_wire_and_user17_native_rejection(self):
        self.assertEqual(game.encode_game_events([self.empty(user_id=16)]), b'\0\x10\x05')
        with self.assertRaisesRegex(game.GameEventsError, 'native bounds type891'):
            list(game.iter_game_events(b'\0\x11\x05'))
        with self.assertRaises(game.GameEventsError):
            game.encode_game_events([self.empty(user_id=17)])

    def test_all_delta_width_boundaries(self):
        for value, tag in ((0, 0), (63, 0), (64, 1), (16383, 1), (16384, 2),
                           (4194303, 2), (4194304, 3), (0xffffffff, 3)):
            with self.subTest(delta=value):
                self.assertEqual(self.roundtrip(self.empty(value)).delta_tag, tag)

    def test_nonminimal_delta_is_read_but_writer_chooses_minimal(self):
        # tag1 + fourteen zero delta bits, userid0, ID5, four final pad bits.
        raw = b'\x01\0\0\x05'
        event = list(game.iter_game_events(raw))[0]
        self.assertEqual(event.delta_tag, 1)
        self.assertEqual(event.event, self.empty())
        self.assertEqual(game.encode_game_events([event.event]), b'\0\0\x05')

    def test_native_enum_hole_and_unbound_admitted_payload(self):
        for raw, reason in ((b'\0\x20\x0f', 'ENUM membership'),
                            (b'\0\x20\x07', 'unsupported native payload ID')):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(game.GameEventsError, reason):
                    list(game.iter_game_events(raw))
        with self.assertRaisesRegex(game.GameEventsError, 'unsupported native payload ID'):
            game.encode_game_events([game.GameEvent(0, 0, 23, ())])

    def test_truncated_header_and_truncated_string(self):
        for raw in (b'\0', b'\0\0', b'\x03'):
            with self.assertRaises(game.GameEventsError):
                list(game.iter_game_events(raw))
        raw = game.encode_game_events([self.chat(b'AB')])
        with self.assertRaisesRegex(game.GameEventsError, 'truncated STRING'):
            list(game.iter_game_events(raw[:-1]))

    def test_discarded_padding_has_separate_canonical_contract(self):
        decoded = list(game.iter_game_events(b'\0\0\xf5'))[0]
        self.assertEqual(decoded.event, self.empty())
        self.assertEqual(decoded.discarded_padding_bits, 4)
        self.assertEqual(decoded.nonzero_padding_spans, 1)
        self.assertEqual(game.encode_game_events([decoded.event]), b'\0\0\x05')

    def test_native_string_multibyte_character_limit(self):
        self.roundtrip(self.chat('zażółć'.encode('utf-8')))
        self.roundtrip(self.chat(b'\xf0\x9f\x98\x80' * 255))
        with self.assertRaisesRegex(game.GameEventsError, 'sequence bounds'):
            game.encode_game_events([self.chat(b'A' * 256)])

    def test_native_string_invalid_sequences_and_nul(self):
        for raw in (b'\0', b'\xff', b'\xc0\x80', b'\xed\xa0\x80', b'\xf4\x90\x80\x80', b'\xc2'):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(game.GameEventsError, 'native STRING encoding'):
                    game.encode_game_events([self.chat(raw)])

    def test_encoded_string_limit_precedes_sequence_scan(self):
        with patch.object(game, '_string_count', side_effect=AssertionError('unexpected sequence scan')):
            with self.assertRaisesRegex(game.GameEventsError, 'native bounds'):
                game.encode_game_events([self.chat(b'A' * 1021)])

    def test_selection_null_and_bit_array_branches(self):
        for removal in (game.Choice(0, None), game.Choice(1, (0, 0)),
                        game.Choice(1, (32, 0xffffffff)), game.Choice(2, (0, 31))):
            payload = (10, (31, removal, (), ()))
            self.roundtrip(game.GameEvent(0, 16, 28, payload))
        for removal in (game.Choice(0, 0), game.Choice(1, (33, 0)),
                        game.Choice(1, (3, 8)), game.Choice(4, None)):
            with self.assertRaises(game.GameEventsError):
                game.encode_game_events([game.GameEvent(0, 0, 28, (0, (0, removal, (), ())))])

    def test_invalid_exact_types_and_shapes(self):
        for event in (self.empty(True), self.empty(user_id=True),
                      game.GameEvent(0, 0, True, ()), game.GameEvent(0, 0, 5, []),
                      self.chat('text'), game.GameEvent(0, 0, 110, ())):
            with self.assertRaises(game.GameEventsError):
                game.encode_game_events([event])
        for raw in (bytearray(b'\0\0\x05'), memoryview(b'\0\0\x05')):
            with self.assertRaises(game.GameEventsError):
                list(game.iter_game_events(raw))

    def test_profile_is_fixed(self):
        with self.assertRaises(game.GameEventsError):
            list(game.iter_game_events(b'', profile='anything'))
        with self.assertRaises(game.GameEventsError):
            game.encode_game_events([], profile=98348)

    def test_empty_member_and_multiple_frames(self):
        self.assertEqual(list(game.iter_game_events(b'')), [])
        self.assertEqual(game.encode_game_events([]), b'')
        events = [self.empty(63, 16), self.chat(b'A'), self.empty(64)]
        self.assertEqual([d.event for d in game.iter_game_events(game.encode_game_events(iter(events)))], events)

    def test_event_and_node_budgets_are_enforced(self):
        events = [self.empty()] * 3
        raw = game.encode_game_events(events)
        with patch.object(game, 'MAX_EVENTS', 2):
            with self.assertRaisesRegex(game.GameEventsError, 'event budget'):
                game.encode_game_events(events)
            with self.assertRaisesRegex(game.GameEventsError, 'event budget'):
                list(game.iter_game_events(raw))
        with patch.object(game, 'MAX_NODES', 1):
            with self.assertRaisesRegex(game.GameEventsError, 'node/depth budget'):
                list(game.iter_game_events(raw))

    def test_byte_budgets_and_value_free_diagnostics(self):
        with patch.object(game, 'MAX_MEMBER_BYTES', 2):
            with self.assertRaises(game.GameEventsError):
                list(game.iter_game_events(b'\0\0\x05'))
            with self.assertRaises(game.GameEventsError):
                game.encode_game_events([self.empty()])
        secret = 'payload-sentinel'
        with self.assertRaises(game.GameEventsError) as caught:
            game.encode_game_events([self.chat(secret)])
        self.assertNotIn(secret, str(caught.exception))
        self.assertNotIn(secret, repr(self.chat(secret)))


if __name__ == '__main__':
    unittest.main()
