"""Reject memory-only accounting tricks and incomplete resource evidence."""
import copy
import json
import unittest

from verify_interval_storage import EVIDENCE, validate_pair, verify


class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((EVIDENCE/'results.json').read_text())

    def pair(self):
        return copy.deepcopy(next(r for r in self.data['records'] if r['name']=='directory_exact_budget'))

    def test_complete_evidence(self):
        self.assertEqual(verify(self.data)['status'],'ACCEPT_MEMORY_RELEASE')

    def test_missing_case(self):
        data=copy.deepcopy(self.data);data['records'].pop()
        with self.assertRaises(AssertionError):verify(data)

    def test_duplicate_case(self):
        data=copy.deepcopy(self.data);data['records'][-1]=data['records'][0]
        with self.assertRaises(AssertionError):verify(data)

    def test_clear_without_deallocation(self):
        row=self.pair()
        for key in ('live_heap_bytes','retained_bytes','live_blocks'):
            row['candidate'][key]=row['previous'][key]
        with self.assertRaises(AssertionError):validate_pair(row)

    def test_falsified_capacity_accounting(self):
        row=self.pair();row['candidate']['live_heap_bytes']=row['previous']['live_heap_bytes']
        with self.assertRaises(AssertionError):validate_pair(row)

    def test_budget_respended(self):
        row=self.pair();row['candidate']['indexed']+=1
        with self.assertRaises(AssertionError):validate_pair(row)

    def test_changed_answers(self):
        row=self.pair();row['candidate']['checksum']^=1
        with self.assertRaises(AssertionError):validate_pair(row)

    def test_missing_oracle_checks(self):
        row=self.pair();row['candidate']['oracle_checks']=0
        with self.assertRaises(AssertionError):validate_pair(row)

    def test_peak_growth(self):
        row=self.pair();row['candidate']['construction_peak_heap_bytes']=row['previous']['construction_peak_heap_bytes']+1
        with self.assertRaises(AssertionError):validate_pair(row)

    def test_changed_source(self):
        data=copy.deepcopy(self.data);data['builds']['candidate']['sources']['partitioned_reachability.h']='0'*64
        with self.assertRaises(AssertionError):verify(data)

    def test_altered_input(self):
        data=copy.deepcopy(self.data);data['records'][0]['input_sha256']='0'*64
        with self.assertRaises(AssertionError):verify(data)


if __name__=='__main__':unittest.main()
