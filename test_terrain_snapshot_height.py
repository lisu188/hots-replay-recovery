import struct
import unittest

from terrain_snapshot_height import Q, SyncTerrain


def make_grid(lows=(0, 1, 2, 8)):
    header = struct.pack("<4s15I", b"SMAP", 102, 2, 2, 0, 0, 0, Q, Q, Q, 0, 0, 0, 0, 0, 0)
    return header + b"".join(struct.pack("<HH", v, 17) for v in lows)


class TerrainTests(unittest.TestCase):
    def test_vertex_scale_and_exact_bilinear(self):
        grid = SyncTerrain(make_grid())
        self.assertEqual(grid.sample(0, 0), (0, 0))
        self.assertEqual(grid.sample(Q // 2, Q // 2), (44, 0))
        self.assertEqual(grid.sample(0, Q // 2), (16, 0))

    def test_inexact_sample_exposes_remainder(self):
        z, remainder = SyncTerrain(make_grid()).sample(1, 0)
        self.assertEqual(z, 0)
        self.assertGreater(remainder, 0)

    def test_grid_shape_sign_and_bounds(self):
        with self.assertRaises(ValueError):
            SyncTerrain(make_grid()[:-1])
        with self.assertRaises(ValueError):
            SyncTerrain(make_grid((65535, 0, 0, 0))).sample(0, 0)
        grid = SyncTerrain(make_grid())
        for x, y in ((-1, 0), (0, Q), (True, 0)):
            with self.assertRaises(ValueError):
                grid.sample(x, y)
