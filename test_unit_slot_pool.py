import unittest

from unit_slot_pool import GENERATION_MASK, SLOT_LIMIT, UnitSlotPool


class TestUnitSlotPool(unittest.TestCase):
    def test_batch_order_and_generation(self):
        pool = UnitSlotPool()
        a, b, c = (pool.allocate() for _ in range(3))
        self.assertEqual([a, b, c], [(0, 1), (1, 1), (2, 1)])
        pool.retire(b)
        pool.retire(a)
        self.assertEqual(pool.allocate(), (3, 1))
        pool.drain()
        self.assertEqual(pool.allocate(), (1, 2))
        pool.retire(c)
        pool.drain()
        self.assertEqual([pool.allocate(), pool.allocate()], [(2, 2), (0, 2)])
        with self.assertRaises(ValueError):
            pool.retire(b)

    def test_full_pool_needs_drain(self):
        pool = UnitSlotPool()
        slots = [pool.allocate() for _ in range(SLOT_LIMIT)]
        self.assertEqual(slots[-1], (1022, 1))
        pool.retire(slots[0])
        self.assertIsNone(pool.allocate())
        pool.drain()
        self.assertEqual(pool.allocate(), (0, 2))

    def test_exhausted_generation_is_quarantined(self):
        pool = UnitSlotPool()
        pool.allocate()
        pool._generations[0] = GENERATION_MASK - 1
        pool.retire((0, GENERATION_MASK - 1))
        pool.drain()
        self.assertEqual(pool.allocate(), (1, 1))
