"""Boundary controls for the byte-only research reader; no PE/client input."""
import unittest
from inspect_embedded_string_table import ascii_nul_span,cstrings,occurrences

class SpanControls(unittest.TestCase):
    def test_maximal_includes_padding_but_stops_at_both_nonprintable_bytes(self):
        b=b'\x01\0alpha\0beta\0\0\xff'
        self.assertEqual(ascii_nul_span(b,4),(1,14))
        self.assertEqual(cstrings(b,1,14),[(2,7,b'alpha'),(8,12,b'beta')])

    def test_exact_file_boundary_is_a_real_boundary(self):
        self.assertEqual(ascii_nul_span(b'alpha\0',0,6),(0,6))

    def test_oversized_real_span_is_refused_not_truncated(self):
        with self.assertRaises(ValueError):ascii_nul_span(b'\x01'+b'a'*65+b'\x02',33,64)

    def test_missing_far_boundary_is_refused_within_cap(self):
        with self.assertRaises(ValueError):ascii_nul_span(b'a'*100,50,16)

    def test_nonprintable_anchor_and_invalid_numeric_bounds_rejected(self):
        for anchor,cap in ((0,10),(-1,10),(True,10),(1,0),(1,2**22)):
            with self.subTest(anchor=anchor,cap=cap):
                with self.assertRaises(ValueError):ascii_nul_span(b'\xffx\0',anchor,cap)

    def test_embedded_control_character_splits_similar_labels(self):
        b=b'\x01Map\0Namespace\x1fMapNamespace\0\x02'
        self.assertEqual(ascii_nul_span(b,5),(1,14))
        self.assertEqual(ascii_nul_span(b,17),(15,28))

    def test_tokenizer_does_not_assume_unterminated_bytes_are_a_valid_table(self):
        b=b'alpha\0omega'
        tokens=cstrings(b,0,len(b))
        self.assertEqual(tokens[-1],(6,11,b'omega'))
        self.assertEqual(b[tokens[-1][1]:tokens[-1][1]+1],b'')

    def test_ordered_offset_sequence_negative_control_and_match_cap(self):
        positive=b'\x00\x00\x00\x00\x06\x00\x00\x00\x0b\x00\x00\x00'
        corpus=b'x'+positive+b'xxxx'+positive+b'z'
        self.assertEqual(occurrences(corpus,positive),[1,17])
        self.assertEqual(occurrences(corpus,positive[4:]+positive[:4]),[])
        with self.assertRaises(ValueError):occurrences(corpus,positive,1)

if __name__=='__main__':unittest.main()
