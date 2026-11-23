import unittest

from map_startup_identity import (
    BIRTH,
    match_startup,
    parse_objects,
    predict_startup,
    verify_startup,
    reconstruct_startup,
)


def layout(*pairs):
    nodes = "".join(
        f'<ObjectUnit Id="{i}" UnitType="Shrine" Position="{x},20,0"/>'
        for i, x in pairs
    )
    return parse_objects(f"<PlacedObjects>{nodes}</PlacedObjects>".encode())


def birth(x, index, loop=0, recycle=1):
    return dict(
        _event=BIRTH,
        _gameloop=loop,
        m_x=x,
        m_y=20,
        m_unitTypeName=b"Shrine",
        m_unitTagIndex=index,
        m_unitTagRecycle=recycle,
    )


class StartupIdentityTests(unittest.TestCase):
    def test_birth_order_and_document_order_are_independent(self):
        rows = layout((101, "92.98"), (8, "3.5"), (20, "12.0"))
        events = [birth(92, 2), birth(3, 82, loop=1), birth(12, 1), birth(3, 0)]
        anchors, report = match_startup(rows, events)
        self.assertEqual(
            [(a.object_id, a.index, a.event_offset) for a in anchors],
            [(8, 0, 3), (20, 1, 2), (101, 2, 0)],
        )
        self.assertEqual(report["fractional_verified"], 2)
        self.assertEqual(report["excluded"], {})

    def test_tag_does_not_break_an_ambiguous_match(self):
        # Each row can match either observed birth. Distinct tag indices must not break the tie.
        rows = layout((1, "2.3"), (2, "2.8"))
        anchors, report = match_startup(rows, [birth(2, 0), birth(3, 1)])
        self.assertEqual(anchors, [])
        self.assertEqual(report["excluded"], {"ambiguous_location": 2})

    def test_single_candidate_claimed_by_two_rows(self):
        anchors, report = match_startup(layout((1, "2.3"), (2, "2.8")), [birth(2, 0)])
        self.assertFalse(anchors)
        self.assertEqual(report["excluded"], {"ambiguous_location": 2})

    def test_missing_row_keeps_its_rank_and_later_births_are_ignored(self):
        anchors, report = match_startup(
            layout((3, "1"), (9, "19")), [birth(1, 0, loop=1), birth(19, 1)]
        )
        self.assertEqual([a.index for a in anchors], [1])
        self.assertEqual(report["excluded"], {"missing_birth": 1})

    def test_blind_pair_must_agree_with_floor_and_rank(self):
        rows = layout((1, "2.99"), (2, "6"), (3, "11"))
        events = [birth(3, 0), birth(6, 7), birth(11, 2, recycle=2)]
        with self.assertRaisesRegex(ValueError, "Contradictory"):
            match_startup(rows, events)
        anchors, report = match_startup(rows, events, strict=False)
        self.assertEqual(anchors, [])
        self.assertEqual(
            report["excluded"],
            {"coordinate_projection_disagrees": 1, "index_or_recycle_disagrees": 2},
        )

    def test_repeated_tag_and_negative_positions_stay_unresolved(self):
        rows = layout((7, "-1.5"), (8, "4"), (9, "9"))
        anchors, report = match_startup(
            rows, [birth(-2, 0), birth(4, 1), birth(9, 1)], strict=False
        )
        self.assertFalse(anchors)
        self.assertEqual(
            report["excluded"],
            {"repeated_startup_tag": 2, "unsupported_negative_coordinate": 1},
        )

    def test_invalid_or_duplicate_authored_ids(self):
        for pairs in [((7, "4"), (7, "5")), ((-1, "2"),), ((8, "NaN"),), ((8, "Inf"),)]:
            with self.subTest(pairs=pairs), self.assertRaises(ValueError):
                layout(*pairs)

    def test_predictions_are_independent_of_both_tag_fields(self):
        rows = layout((8, "10.5"), (4, "16.7"))
        events = [birth(10, 1), birth(16, 0)]
        masked = [
            {
                k: v
                for k, v in e.items()
                if k not in ("m_unitTagIndex", "m_unitTagRecycle")
            }
            for e in events
        ]
        predictions, report = predict_startup(rows, masked)
        self.assertEqual(
            [(a.object_id, a.index, a.recycle) for a in predictions],
            [(4, 0, 1), (8, 1, 1)],
        )
        wrong = [birth(10, 0), birth(16, 1)]
        self.assertEqual(predict_startup(rows, wrong), (predictions, report))
        with self.assertRaisesRegex(ValueError, "index_or_recycle_disagrees"):
            verify_startup(predictions, wrong, report)
        accepted, audit = verify_startup(predictions, wrong, report, strict=False)
        self.assertEqual(accepted, [])
        self.assertEqual(audit["contradictions"], {"index_or_recycle_disagrees": 2})

    def test_masked_reconstruction_accounts_for_unassigned_births(self):
        events = [birth(4, 0), birth(99, 700), birth(4, 5, loop=6)]
        actual, anchors, audit = reconstruct_startup(layout((4, "4")), events)
        self.assertEqual(actual, events)
        self.assertIsNot(actual[0], events[0])
        self.assertIsNot(actual[1], events[1])
        self.assertEqual(len(anchors), 1)
        self.assertEqual(audit["masked_birth_tags"], 2)
        self.assertEqual(audit["tags_restored_from_map_predictions"], 1)
        self.assertEqual(audit["unmatched_tags_restored_from_original"], 1)


if __name__ == "__main__":
    unittest.main()
