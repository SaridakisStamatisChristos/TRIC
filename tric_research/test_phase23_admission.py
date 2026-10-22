"""Adversarial Phase XXIII source-only admission and exact output regression."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from benchmark_native import serialize_native
from phase23_admission import run_one,compare
from tric import build_graph

ROOT=Path(__file__).resolve().parent

class AdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.binary=Path(cls.tmp.name)/"phase23_lifetime"
        subprocess.run(["g++","-std=c++17","-O2","-Wall","-Wextra",
                        "-Wpedantic",str(ROOT/"lifetime_replay.cpp"),
                        "-o",str(cls.binary)],
                       check=True,text=True,capture_output=True)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def payload(self,distribution,training=None):
        adj,_=build_graph(16,[(i,i+1) for i in range(15)])
        train=training or [(0,4)]*140+[(1,9)]*12+[(2,3)]*2
        if distribution=="matched":
            queries=[(0,i%16) for i in range(300)]
        elif distribution=="shifted":
            queries=[(14,i%16) for i in range(300)]
        else:
            queries=[(i%16,(i*7)%16) for i in range(300)]
        return serialize_native(adj,[3,6],
            {"BFS":[],"Ordered":[0,1]},queries,train)

    def test_admission_and_refusal_by_source_distribution(self):
        with tempfile.TemporaryDirectory() as td:
            for cls,expected in (("matched",True),("uniform",False),
                                 ("shifted",False)):
                raw=self.payload(cls)
                base=run_one(self.binary,raw,"pivot_index",200,2,2048,
                             Path(td)/cls/"base")
                cached=run_one(self.binary,raw,"cache_pivot_index",200,2,2048,
                               Path(td)/cls/"eager")
                adaptive=run_one(self.binary,raw,
                    "adaptive_cache_pivot_index",200,2,2048,
                    Path(td)/cls/"adaptive")
                self.assertEqual(len({base["checksum"],cached["checksum"],
                                      adaptive["checksum"]}),1)
                self.assertEqual(adaptive["adaptive_admitted"],expected)
                self.assertEqual(adaptive["admission_prefix_queries"],256)
                self.assertEqual(adaptive["actual_query_calls"],60000)
                self.assertEqual(adaptive["independently_verified_queries"],300)
                if expected:
                    self.assertGreater(adaptive["cache_rows"],0)
                else:
                    self.assertEqual(adaptive["retained_cache_bytes"],0)

    def test_short_horizon_is_cache_free_even_if_hot(self):
        with tempfile.TemporaryDirectory() as td:
            row=run_one(self.binary,self.payload("matched"),
                        "adaptive_cache_pivot_index",1,2,2048,td)
            self.assertFalse(row["adaptive_admitted"])
            self.assertEqual(row["cache_rows"],0)
            self.assertEqual(row["actual_query_calls"],300)

    def test_zero_cap_cannot_allocate(self):
        with tempfile.TemporaryDirectory() as td:
            row=run_one(self.binary,self.payload("matched"),
                        "adaptive_cache_pivot_index",200,2,0,td)
            self.assertFalse(row["adaptive_admitted"])
            self.assertEqual(row["retained_cache_bytes"],0)

    def test_two_horizons_three_modes_agree(self):
        with tempfile.TemporaryDirectory() as td:
            report=compare(self.binary,self.payload("matched"),2,2048,
                           td,replications=1)
            self.assertEqual(set(report),{"1","50"})
            self.assertTrue(all(
                v["all_answers_independently_verified"]
                for factor in report.values() for v in factor.values()))
            self.assertFalse(report["1"]["adaptive_cache_pivot_index"]["admitted"])

if __name__=="__main__":unittest.main()
