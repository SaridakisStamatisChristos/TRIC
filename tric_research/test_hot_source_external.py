"""Phase XX source-skew protocol and cross-native correctness regression."""
import json
import math
import random
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmark_hot_source_external import (
    workload_sets, sample_pairs, fingerprint_pairs, check_times,
    compile_cache_binary,
)
from benchmark_hot_source_cache import native_input
from benchmark_native import build_executable, serialize_native
from ordered_probe import greedy_coverage_order, hit_masks_for_pivots, optimize_ordered
from tric import graph_family, make_pivot, early_reachable

class PhaseXXContractTests(unittest.TestCase):
    def test_sampling_no_leakage_or_shift_overlap(self):
        adj,_=graph_family("dag",160,79)
        training,groups,hot,shifted=workload_sets(adj,20261022,500,2400,8)
        self.assertEqual(len(hot),8)
        self.assertFalse(set(hot)&set(shifted))
        self.assertEqual(len(set(hot)),8)
        self.assertTrue(all(len(v)==2400 for v in groups.values()))
        matched=sum(s in hot for s,_ in groups["matched_hot"])
        shifted_hits=sum(s in hot for s,_ in groups["shifted_hot"])
        self.assertGreater(matched,1800)
        self.assertLess(shifted_hits,300)
        self.assertEqual(len(training),500)
        self.assertEqual(workload_sets(adj,20261022,500,2400,8),
                         (training,groups,hot,shifted))
        self.assertNotEqual(fingerprint_pairs(training),
                            fingerprint_pairs(groups["matched_hot"]))
        self.assertNotEqual(fingerprint_pairs(groups["matched_hot"]),
                            fingerprint_pairs(groups["shifted_hot"]))

    def test_invalid_and_nonfinite_inputs(self):
        with self.assertRaises(ValueError):
            sample_pairs(10,0,1)
        with self.assertRaises(ValueError):
            sample_pairs(10,4,1,(10,))
        with self.assertRaises(ValueError):
            workload_sets([[],[],[]],1,10,10,2)
        for v in (-1,0,math.inf,math.nan):
            with self.assertRaises(ValueError):
                check_times("corrupted",v)
        self.assertEqual(check_times("valid",20),20)

    def test_compiled_cache_and_tric_same_pairs(self):
        adj,rev=graph_family("dag",46,23)
        training,groups,_,_=workload_sets(adj,103,120,90,3)
        qs=groups["matched_hot"]
        import json
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname)
            cache_exe,_=compile_cache_binary(root,"g++","-O2")
            cache_out=subprocess.run([str(cache_exe)],
                input=native_input(adj,training,qs,3,1024*1024),
                capture_output=True,check=True,timeout=40)
            cached=json.loads(cache_out.stdout)
            self.assertEqual(cached["heldout"],90)
            self.assertEqual(len(cached["cache_samples"]),14)
            self.assertLessEqual(cached["retained_bytes"],1024*1024)
            ids=sorted(range(len(adj)),key=lambda v:(-len(adj[v])-len(rev[v]),v))[:7]
            pivots=[make_pivot(adj,rev,v) for v in ids]
            hits=hit_masks_for_pivots(pivots,training)
            fb=[1+early_reachable(adj,*q)[1] for q in training]
            optimal,_,_=optimize_ordered(hits,[1.0]*len(training),fb,
                                        [1.0]*len(ids),3)
            greedy=greedy_coverage_order(hits,[1.0]*len(training),len(ids),3)
            policies={"BFS":[],"Control":[],"Greedy":greedy,"Ordered":optimal}
            exe,_,_=build_executable(root,"g++","-O2")
            native_out=subprocess.run([str(exe),"15","0"],
                input=serialize_native(adj,ids,policies,qs,training),
                capture_output=True,check=True,timeout=40)
            native=json.loads(native_out.stdout)
            bfs=next(p["checksum"] for p in native["policies"] if p["name"]=="BFS")
            self.assertEqual(native["compact_pivots_bidir"]["checksum"],bfs)
            self.assertEqual(native["compact_pivots_selector"]["checksum"],bfs)
            self.assertEqual(native["queries"],90)

if __name__=="__main__":
    unittest.main()
