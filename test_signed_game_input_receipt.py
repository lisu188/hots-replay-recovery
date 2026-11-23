"""Negative tests for detached top-level SignedAnnouncer receipt summaries."""

import unittest
from verify_signed_game_inputs import verify_totals


class SignedReceiptTest(unittest.TestCase):
    def test_all_totals_reject_replacement_and_removal(self):
        report = dict(build=98348, source_game_bytes=50, source_events=7, included=2, omitted=5,
                      last_source_event_loop=21, overlap_ordinals=1)
        joined = dict(independently_joined_inputs=2,unrepresented=5)
        ledger = [[0,1,5,["opening"]],[6,21,27,["opening","point_session"]]]
        verify_totals(report,joined,ledger,50,21)
        for key in report:
            for replacement in (report[key]+1, None, True):
                with self.subTest(field=key,replacement=replacement), self.assertRaises(ValueError):
                    verify_totals({**report,key:replacement},joined,ledger,50,21)
            with self.subTest(field=key,missing=True), self.assertRaises(ValueError):
                verify_totals({k:v for k,v in report.items() if k!=key},joined,ledger,50,21)


if __name__=="__main__":
    unittest.main()
