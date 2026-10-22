"""Phase XXII audit: fresh-process lifetime, RSS and oracle separation."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from benchmark_native import serialize_native
from benchmark_phase22 import replay_pair,run_fresh
from tric import build_graph

HERE=Path(__file__).resolve().parent

class LifetimeReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.exe=self.root/"phase22_lifetime"
        subprocess.run(["g++","-std=c++17","-O2","-Wall","-Wextra",
                        "-Wpedantic",str(HERE/"lifetime_replay.cpp"),
                        "-o",str(self.exe)],
                        check=True,capture_output=True,text=True)
        adj,_=build_graph(6,[(0,1),(1,2),(2,0),(2,3),(4,5)])
        queries=[(s,t) for s in range(6) for t in range(6)]
        train=[(0,1)]*12+[(4,5)]*8+[(2,0)]*3
        self.raw=serialize_native(adj,[0,2,4],
            {"BFS":[],"Ordered":[0,1,2]},queries,train)

    def test_fresh_index_cache_identical_with_budget(self):
        pair=replay_pair(self.exe,self.raw,1,2,2048,
                         self.root/"one",replications=2)
        self.assertTrue(pair["pivot_index"]["checksum_verified"])
        self.assertTrue(pair["cache_pivot_index"]["checksum_verified"])
        self.assertEqual(pair["pivot_index"]["cache_rows"],0)
        self.assertEqual(pair["cache_pivot_index"]["cache_rows"],2)
        self.assertGreater(pair["cache_pivot_index"]["cache_retained_bytes"],0)
        self.assertEqual(pair["pivot_index"]["actual_query_calls"],36)
        self.assertGreater(pair["pivot_index"]["median_maxrss_kib"],0)
        self.assertTrue(isinstance(pair["cache_wins_full_native_lifecycle"],bool))

    def test_actual_replay_and_complete_oracle(self):
        pair=replay_pair(self.exe,self.raw,9,2,2048,
                         self.root/"nine",replications=1)
        self.assertEqual(pair["pivot_index"]["actual_query_calls"],324)
        self.assertEqual(pair["cache_pivot_index"]["actual_query_calls"],324)
        self.assertGreater(pair["pivot_index"]["median_query_loop_ns"],0)
        rows=json.loads((self.root/"nine"/"rep0_cache_pivot_index"/"result.json").read_text())
        self.assertEqual(rows["independently_verified_queries"],36)
        self.assertEqual(rows["actual_query_calls"],324)

    def test_refusal_and_nonpositive_parameters(self):
        with self.assertRaises(ValueError):
            replay_pair(self.exe,self.raw,1,2,2048,self.root,replications=0)
        with self.assertRaises(ValueError):
            run_fresh(self.exe,self.raw,"made_up",1,2,2048,self.root)
        with self.assertRaises(RuntimeError):
            run_fresh(self.exe,b"bad", "pivot_index",1,2,2048,
                      self.root/"bad")

    def test_zero_order_is_valid_not_missing_policy(self):
        adj,_=build_graph(6,[(0,1),(1,2)])
        queries=[(s,t) for s in range(6) for t in range(6)]
        train=[(0,1)]*5
        raw=serialize_native(adj,[0,1],
            {"BFS":[],"Ordered":[]},queries,train)
        pair=replay_pair(self.exe,raw,2,1,2048,
                         self.root/"zero_order",replications=1)
        self.assertEqual(pair["pivot_index"]["actual_query_calls"],72)
        self.assertTrue(pair["cache_pivot_index"]["checksum_verified"])

    def test_zero_cache_budget(self):
        row=run_fresh(self.exe,self.raw,"cache_pivot_index",1,2,0,
                      self.root/"refusal")
        self.assertEqual(row["cache_rows"],0)
        self.assertEqual(row["cache_hits"],0)

if __name__=="__main__":
    unittest.main()
