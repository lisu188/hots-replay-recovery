from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from decoders import BitPackedDecoder
from protocol_loader import load_protocol
from snapshot_wire import encode_point, fragment, generate, point_graph


class SnapshotWireTests(TestCase):
    def test_target_command_paths_share_known_point(self):
        _, roots, field, point = point_graph()
        self.assertEqual((roots[27], roots[105], field, point), (291, 555, 152, 157))

    def test_independent_roundtrip_at_every_phase_with_nonzero_neighbors(self):
        # Exercise unsigned coordinate bounds and asymmetric signed height endpoints.
        protocol = load_protocol(96477)
        for xyz in ((0, 1048575, -2147483648), (888888, 12345, 2147483647), (6144, 8192, -17)):
            observed = []
            for phase in range(8):
                blob = encode_point(*xyz, phase)
                self.assertEqual(len(blob), 9)
                suffix_width = (-phase) % 8
                prefix = (1 << phase) - 1
                suffix = (1 << suffix_width) - 1
                word = prefix | (int.from_bytes(blob, "little") << phase) | (suffix << (phase + 72))
                decoder = BitPackedDecoder(
                    word.to_bytes((phase + 72 + suffix_width) // 8, "little"), protocol.typeinfos
                )
                self.assertEqual(decoder._buffer.read_bits(phase), prefix)
                self.assertEqual(decoder.instance(90), dict(zip(("x", "y", "z"), xyz)))
                self.assertEqual(decoder.used_bits(), phase + 72)
                self.assertEqual(decoder._buffer.read_bits(suffix_width), suffix)
                self.assertTrue(decoder.done())
                observed.append(blob)
            if xyz[0] == 888888:
                self.assertGreater(len(set(observed)), 1)

    def test_invalid_fields_phases_and_truncated_spans(self):
        for args in (
            (-1, 1, 1, 0),
            (1, 1 << 20, 1, 0),
            (1, 1, 1 << 31, 0),
            (1, 1, 0, -1),
            (1, 1, 0, 8),
            (1, 1, 0, True),
        ):
            with self.subTest(args=args), self.assertRaises(ValueError):
                encode_point(*args)
        for start, size in ((-1, 1), (0, -1), (4, 5), (9, 0)):
            with self.subTest(start=start, size=size), self.assertRaises(ValueError):
                fragment(b"\xff", start, size)

    def test_reject_existing_output_and_no_partial_publication_on_invalid_input(self):
        with TemporaryDirectory() as folder:
            parent = Path(folder)
            invalid = parent / "invalid"
            invalid.write_bytes(b"invalid")
            existing = parent / "existing"
            existing.mkdir()
            marker = existing / "keep"
            marker.write_bytes(b"keep")
            with self.assertRaises(FileExistsError):
                generate(invalid, invalid, invalid, existing)
            self.assertEqual(marker.read_bytes(), b"keep")
            out = parent / "new"
            with self.assertRaises(ValueError):
                generate(invalid, invalid, invalid, out)
            self.assertFalse(out.exists())
