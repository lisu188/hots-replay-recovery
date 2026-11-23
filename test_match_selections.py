from unittest import TestCase, main

from match_selections import at, catalog, groups, remove_items


class SelectionTests(TestCase):
    def test_short_masks_use_low_bits(self):
        for n in range(1, 4):
            for bits in range(1 << n):
                data = list(range(4))
                self.assertEqual(
                    remove_items(data, {"Mask": (n, bits)}), [i for i in data if not bits & (1 << i)]
                )
                self.assertEqual(data, list(range(4)))

    def test_unconditional_clear_and_unknown_variants(self):
        self.assertEqual(remove_items([10, 20], {"ZeroIndices": []}), [])
        self.assertEqual(remove_items([10, 20], {"None": None}), [10, 20])
        for mask in ({"ZeroIndices": None}, {"OneIndices": [1]}, {"Mask": (4, 7)}, {"None": []}):
            with self.assertRaises(ValueError):
                remove_items([10, 20], mask)

    def test_added_tag_counts(self):
        with self.assertRaises(ValueError):
            list(groups({"m_addSubgroups": [{"m_count": 2}], "m_addUnitTags": [83]}))

    def test_target_build_catalog_isolation(self):
        rows = [
            dict(build=98285, sha256="old", observed=[["Hero", 17, 15, 1, 1, 2]]),
            dict(build=98348, sha256="new", observed=[["Hero", 28, 15, 1, 1, 3]]),
        ]
        links, refs = catalog(rows, 98348)
        self.assertEqual(links["Hero"], {28})
        self.assertEqual(refs["Hero", 15, 1, 1], {"new"})

    def test_timeline_identity(self):
        changes = [(50, True), (100, False), (150, True)]
        self.assertIsNone(at(changes, 49))
        self.assertEqual(at(changes, 120), (100, False))


if __name__ == "__main__":
    main()
