"""Synthetic extension/privacy/budget fixtures; no real game/player data."""
from io import BytesIO
from pathlib import Path
import tempfile
import unittest

from audit_expanded_account_vectors import Budget,CountedFile,MAX_DISTINCT,MAX_READS,MAX_AVAILABILITY,assess_extended
from audit_repeated_account_vectors import PrivateControl,assess
from test_audit_repeated_account_vectors import synthetic_pair


class ExpandedAlgorithmTests(unittest.TestCase):
    def test_frozen_small_baseline_matches_exactly(self):
        controls=synthetic_pair()
        self.assertEqual(assess_extended(controls),assess(controls))

    def test_thirteen_case_baseline_matches_exactly(self):
        controls=[PrivateControl({0:'synthetic-'+str(index)},(bytes((index+1,0)),)+(bytes(2),)*15) for index in range(13)]
        self.assertEqual(assess_extended(controls),assess(controls))

    def test_twenty_one_case_extension_is_bounded_and_counted(self):
        controls=[PrivateControl({0:'synthetic-'+str(index)},(bytes((index+1,0)),)+(bytes(2),)*15) for index in range(21)]
        report=assess_extended(controls)
        self.assertEqual(report['control_cases'],21)
        self.assertEqual(report['cross_replay_pairs_considered'],210)
        self.assertEqual(report['presence_constraint_aggregate']['distinct_active_arrangements_enumerated'],1)
        with self.assertRaises(ValueError):assess_extended(controls+[controls[0]])

    def test_inconsistent_column_lengths_across_extension_refused(self):
        controls=synthetic_pair()+[PrivateControl({0:'extra'},(b'\x01\0\0\0',)+(bytes(4),)*15)]
        with self.assertRaises(ValueError):assess_extended(controls)

    def test_extension_keeps_frozen_private_renaming_invariance(self):
        controls=synthetic_pair()
        renamed=[PrivateControl({15-slot:('new-private',account) for slot,account in control.accounts_by_position.items()},tuple(reversed(control.columns))) for control in controls]
        self.assertEqual(assess_extended(controls),assess_extended(renamed))


class ReadBudgetTests(unittest.TestCase):
    def test_repeated_overlapping_file_reads_are_all_counted(self):
        budget=Budget(30);reader=CountedFile(BytesIO(bytes(10)),budget)
        self.assertEqual(len(reader.read(8)),8)
        reader.seek(0)
        self.assertEqual(len(reader.read(8)),8)
        self.assertEqual(budget.counts['MPQ_file_reads'],16)

    def test_end_of_file_counts_actual_bytes_not_requested_bound(self):
        budget=Budget(30);reader=CountedFile(BytesIO(bytes(5)),budget)
        self.assertEqual(len(reader.read(10)),5)
        self.assertEqual(budget.counts['MPQ_file_reads'],5)

    def test_oversize_read_is_refused_before_stream_IO(self):
        budget=Budget(4);stream=BytesIO(bytes(10));reader=CountedFile(stream,budget)
        with self.assertRaises(ValueError):reader.read(5)
        self.assertEqual(stream.tell(),0)
        self.assertEqual(sum(budget.counts.values()),0)

    def test_unbounded_read_and_negative_accounting_refused(self):
        reader=CountedFile(BytesIO(bytes(10)),Budget())
        with self.assertRaises(ValueError):reader.read()
        with self.assertRaises(ValueError):Budget().add('bad',-1)
        for limit in (0,MAX_READS+1,True):
            with self.assertRaises(ValueError):Budget(limit)

    def test_distinct_paths_count_once_and_cap_refuses(self):
        budget=Budget();path=Path('synthetic-never-opened')
        budget.register(path,10);budget.register(path,10)
        self.assertEqual(sum(budget.distinct.values()),10)
        with self.assertRaises(ValueError):budget.register(Path('different-synthetic-never-opened'),MAX_DISTINCT)
        self.assertEqual(sum(budget.distinct.values()),10)

    def test_availability_budget_counts_decoded_rows(self):
        budget=Budget();budget.add_availability(32)
        with self.assertRaises(ValueError):budget.add_availability(MAX_AVAILABILITY)
        self.assertEqual(budget.availability,32)

    def test_metadata_and_guard_reads_share_budget(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.dat';path.write_bytes(bytes(10))
            budget=Budget(25)
            budget.read(path,100,'provenance_metadata');budget.read(path,100,'guard_rehash_reads')
            self.assertEqual(sum(budget.counts.values()),20)
            with self.assertRaises(ValueError):budget.read(path,100,'guard_rehash_reads')


if __name__=='__main__':unittest.main()
