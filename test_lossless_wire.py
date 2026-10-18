"""Independent wire literals and refusal tests; no private fixtures are embedded."""
from dataclasses import replace
import unittest
from unittest.mock import patch

import lossless_wire as wire
from lossless_wire import Node, WireError, parse, encode, clone, to_generic
from depot_s2mh_wire import Reader


class LosslessWireTests(unittest.TestCase):
    def test_all_tags_and_map_order_from_literal(self):
        raw = (b'\x05\x08\x0e\x00\x04\x06\x09\x09\x05'
               b'\x02\x01\x12\x80\xff'
               b'\x08\x03\x03\x04\x01\x07ABCD'
               b'\x06\x08abcdefgh')
        node = parse(raw)
        self.assertEqual([key for key, _ in node.value], [7, 1, 4, 3])
        self.assertEqual(node.field(7).value[1].value, -2)
        self.assertEqual(node.field(4).value[0], -1)
        self.assertEqual(node.field(4).value[1].value.tag, 7)
        self.assertEqual(node.field(3).tag, 8)
        self.assertEqual(encode(node), raw)
        generic = Reader(raw)
        self.assertEqual(to_generic(node), generic.read())
        self.assertEqual(generic.pos, len(raw))

    def test_blob_and_fixed_tags_stay_distinct(self):
        for raw in (b'\x02\x08ABCD', b'\x07ABCD', b'\x08ABCDEFGH'):
            with self.subTest(raw=raw):
                node = parse(raw)
                self.assertEqual(node.tag, raw[0])
                self.assertEqual(encode(node), raw)

    def test_optional_absent_and_present_empty_array_stay_distinct(self):
        absent, present = b'\x04\x00', b'\x04\x01\x00\x00'
        self.assertIsNone(parse(absent).value)
        self.assertEqual(parse(present).value, Node(0, []))
        self.assertNotEqual(encode(parse(absent)), encode(parse(present)))

    def test_nonminimal_integer_spelling_and_negative_zero_retained(self):
        for raw, expected in ((b'\x09\x80\x00', 0),
                              (b'\x09\x01', 0),
                              (b'\x09\x85\x00', -2)):
            with self.subTest(raw=raw):
                self.assertEqual(parse(raw).value, expected)
                self.assertEqual(encode(parse(raw)), raw)

    def test_nonminimal_count_choice_and_map_key_retained(self):
        literals = [b'\x00\x80\x00', b'\x02\x80\x00', b'\x01\x01',
                    b'\x03\x81\x00\x06\x00',
                    b'\x05\x82\x00\x80\x00\x06\x01']
        for raw in literals:
            with self.subTest(raw=raw):
                self.assertEqual(encode(parse(raw)), raw)

    def test_changed_integer_uses_canonical_signed_magnitude(self):
        node = parse(b'\x09\x85\x00')
        node.value = -3
        self.assertEqual(encode(node), b'\x09\x07')
        node.value = 3
        self.assertEqual(encode(node), b'\x09\x06')

    def test_changed_array_and_blob_count_reencoded(self):
        node = parse(b'\x00\x80\x00')
        node.value.append(Node(6, 255))
        self.assertEqual(encode(node), b'\x00\x02\x06\xff')
        blob = parse(b'\x02\x82\x00A')
        blob.value = b'BC'
        self.assertEqual(encode(blob), b'\x02\x04BC')

    def test_clone_and_existing_field_edit_leave_source_unchanged(self):
        raw = b'\x05\x04\x04\x09\x06\x00\x07ABCD'
        original = parse(raw)
        modified = clone(original)
        modified.field(2).value = 4
        modified.set_field(0, Node(7, b'WXYZ'))
        self.assertEqual(encode(original), raw)
        self.assertEqual(encode(modified), b'\x05\x04\x04\x09\x08\x00\x07WXYZ')
        with self.assertRaises(WireError): modified.set_field(99, Node(6, 0))

    def test_explicit_map_reordering_retains_key_spellings(self):
        raw = b'\x05\x04\x82\x00\x06\x01\x00\x06\x02'
        node = parse(raw)
        node.value.reverse()
        self.assertEqual(encode(node), b'\x05\x04\x00\x06\x02\x82\x00\x06\x01')

    def test_nonzero_unused_bitarray_bits_are_not_erased(self):
        raw = b'\x01\x02\xff'
        self.assertEqual(parse(raw).value, (1, b'\xff'))
        self.assertEqual(encode(parse(raw)), raw)

    def test_every_truncated_prefix_refused(self):
        raw = b'\x05\x04\x00\x03\x02\x02\x06ABC\x02\x04\x01\x08ABCDEFGH'
        self.assertEqual(encode(parse(raw)), raw)
        for size in range(len(raw)):
            with self.subTest(size=size), self.assertRaises(WireError): parse(raw[:size])

    def test_trailing_unknown_tag_and_invalid_optional_refused(self):
        for raw in (b'\x06\x00\x00', b'\x0a', b'\x04\x02'):
            with self.subTest(raw=raw), self.assertRaises(WireError): parse(raw)

    def test_duplicate_keys_including_negative_zero_refused(self):
        for raw in (b'\x05\x04\x00\x06\x01\x00\x06\x02',
                    b'\x05\x04\x01\x06\x01\x00\x06\x02'):
            with self.subTest(raw=raw), self.assertRaises(WireError): parse(raw)
        with self.assertRaises(WireError): encode(Node(5, [(1, Node(6, 1)), (1, Node(6, 2))]))

    def test_negative_and_oversized_counts_refused(self):
        with self.assertRaises(WireError): parse(b'\x00\x03')
        with patch.object(wire, 'MAX_COUNT', 2):
            with self.assertRaises(WireError): parse(b'\x00\x06')
            with self.assertRaises(WireError): encode(Node(0, [Node(6, 0)]*3))

    def test_overlong_and_truncated_varints_refused(self):
        for raw in (b'\x09'+b'\x80'*10+b'\x00', b'\x09\x80'):
            with self.subTest(raw=raw), self.assertRaises(WireError): parse(raw)

    def test_signed_magnitude_extrema_and_overflow(self):
        maximum = wire.MAX_VINT_MAGNITUDE
        for value in (maximum, -maximum, 0, -1, 1):
            self.assertEqual(parse(encode(Node(9, value))).value, value)
        for value in (maximum+1, -maximum-1, True, 1.0):
            with self.subTest(value=value), self.assertRaises(WireError): encode(Node(9, value))

    def test_byte_count_node_and_depth_budgets(self):
        raw = b'\x00\x06'+b'\x06\x00'*3
        with patch.object(wire, 'MAX_BYTES', 7):
            with self.assertRaises(WireError): parse(raw)
            with self.assertRaises(WireError): encode(Node(0, [Node(6, 0)]*3))
        with patch.object(wire, 'MAX_NODES', 3):
            with self.assertRaises(WireError): parse(raw)
            with self.assertRaises(WireError): encode(Node(0, [Node(6, 0)]*3))
        with patch.object(wire, 'MAX_DEPTH', 1):
            with self.assertRaises(WireError): parse(b'\x04\x01\x04\x01\x04\x00')
            with self.assertRaises(WireError): encode(Node(4, Node(4, Node(4, None))))

    def test_malformed_node_value_types_and_widths_refused(self):
        nodes = [Node(True, 0), Node(10, 0), Node(0, ()), Node(1, (9, b'A')),
                 Node(1, (True, b'A')), Node(2, bytearray(b'A')), Node(3, [0, Node(6, 0)]),
                 Node(4, 0), Node(5, {}), Node(5, [('0', Node(6, 0))]),
                 Node(5, [(0,)]), Node(6, -1), Node(6, 256), Node(6, False),
                 Node(7, b'ABC'), Node(8, b'ABCDE'), Node(9, '1')]
        for node in nodes:
            with self.subTest(tag=node.tag), self.assertRaises(WireError): encode(node)
        with self.assertRaises(WireError): parse(bytearray(b'\x06\x00'))

    def test_corrupted_retained_spelling_refused(self):
        node = parse(b'\x09\x02')
        node._spellings['value'] = replace(node._spellings['value'], raw=b'\x04')
        with self.assertRaises(WireError): encode(node)

    def test_cycles_refused_but_shared_nodes_supported(self):
        child = Node(6, 1)
        self.assertEqual(encode(Node(0, [child, child])), b'\x00\x04\x06\x01\x06\x01')
        node = Node(0, [])
        node.value.append(node)
        with self.assertRaises(WireError): encode(node)

    def test_field_helper_refuses_malformed_or_nonstruct_nodes(self):
        for node in (Node(6, 0), Node(5, [(0,)]), Node(5, [(0, Node(6, 1)), (0, Node(6, 2))])):
            with self.subTest(node=node), self.assertRaises(WireError): node.field(0)


if __name__ == '__main__':
    unittest.main()
