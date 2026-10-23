"""Reject incomplete answers, wrong horizons, invalid timings and cap violations."""
import copy
import unittest
from benchmark_partitioned import validate,assert_parity
class BenchmarkTests(unittest.TestCase):
    def row(self):
        return dict(mode='partitioned',queries=10,repeats=100,available=True,
                    actual_calls=1000,oracle_verified_pairs=10,checksum=123,
                    parse_ns=100,build_ns=200,query_ns=300,lifecycle_ns=600,
                    timed_peak_rss_kib=12,table_bytes=64)
    def test_valid(self):validate(self.row(),'partitioned',10,100,100)
    def test_invalid_observations(self):
        for key,value in [('mode','other'),('queries',9),('repeats',99),
                          ('actual_calls',10),('oracle_verified_pairs',9),
                          ('query_ns',float('nan')),('build_ns',-1),('table_bytes',101),
                          ('lifecycle_ns',6010),('available',False)]:
            row=self.row();row[key]=value
            with self.assertRaises(AssertionError,msg=key):validate(row,'partitioned',10,100,100)
    def test_unavailable_is_not_a_win(self):
        row=self.row();row.update(mode='bounded',available=False,actual_calls=0,oracle_verified_pairs=0)
        validate(row,'bounded',10,100,100)
        good=self.row();assert_parity([row,good])
        with self.assertRaises(AssertionError):assert_parity([row])
    def test_mismatched_checksum_is_rejected(self):
        a=self.row();b=copy.deepcopy(a);b['checksum']+=1
        with self.assertRaises(AssertionError):assert_parity([a,b])
if __name__=='__main__':unittest.main()
