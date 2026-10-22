"""Phase XXI independent exact cache/index portfolio regression.

Exhaustively differential-tests ALL three-vertex directed multicyclic shapes
(512 simple digraphs, including self loops) against original Python BFS.
"""
import itertools
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from benchmark_native import serialize_native
from tric import build_graph, early_reachable

ROOT=Path(__file__).resolve().parent

def compile_portfolio(folder):
    exe=Path(folder)/"cache_indexed_test"
    subprocess.run(["g++","-std=c++17","-O2","-Wall","-Wextra",
                    "-Wpedantic",str(ROOT/"cache_indexed_bench.cpp"),
                    "-o",str(exe)],check=True,capture_output=True,text=True)
    return exe

def run_case(exe,adj,ids,train,queries,hot=2,cap=1024*1024):
    methods={"BFS":[],"Ordered":list(range(len(ids)))}
    raw=serialize_native(adj,ids,methods,queries,train)
    p=subprocess.run([str(exe),"16",str(hot),str(cap)],
                     input=raw,capture_output=True,text=True,timeout=20)
    if p.returncode:
        raise AssertionError(f"compiled phase-XXI failed: {p.stderr}")
    data=json.loads(p.stdout)
    if data["queries"]!=len(queries):
        raise AssertionError("missing queries")
    if data["training"]!=len(train):
        raise AssertionError("training count changed")
    if data["cache_retained_bytes"]>cap:
        raise AssertionError("cache cap violated")
    if data["oracle_positive_count"]!=sum(
            bool(early_reachable(adj,s,t)[0]) for s,t in queries):
        raise AssertionError("BFS truth count differs")
    modes=data["modes"]
    if set(modes)!={"index_only","cache_index","pivot_index","cache_pivot_index"}:
        raise AssertionError("incorrect portfolio arms")
    if len({v["checksum"] for v in modes.values()})!=1:
        raise AssertionError("unequal exact-answer checksums")
    for v in modes.values():
        if len(v["samples_ns_per_query"])!=16:
            raise AssertionError("incomplete position rotation")
    return data

class PortfolioRegression(unittest.TestCase):
    def test_all_three_vertex_directed_graphs(self):
        with tempfile.TemporaryDirectory() as td:
            exe=compile_portfolio(td)
            queries=list(itertools.product(range(3),repeat=2))
            training=queries*3
            ids=[0,1,2]
            for mask in range(512):
                edges=[(u,v) for u in range(3) for v in range(3)
                       if mask&(1<<(u*3+v))]
                adj,_=build_graph(3,edges)
                with self.subTest(mask=mask):
                    out=run_case(exe,adj,ids,training,queries,hot=2,cap=1024)
                    self.assertEqual(out["cache_rows"],2)
                    self.assertEqual(out["cache_hits"],6)

    def test_64_bit_boundary_and_budget_refusal(self):
        with tempfile.TemporaryDirectory() as td:
            exe=compile_portfolio(td)
            edges=[(0,64),(64,0),(1,2),(2,3),(3,2)]
            adj,_=build_graph(65,edges)
            queries=[(s,t) for s in (0,1,2,64) for t in (0,2,3,64)]
            training=[(0,64)]*9+[(64,0)]*6
            large=run_case(exe,adj,[0,64],training,queries,hot=2,cap=4096)
            tiny=run_case(exe,adj,[0,64],training,queries,hot=2,cap=0)
            self.assertGreater(large["cache_hits"],0)
            self.assertEqual(tiny["cache_rows"],0)
            self.assertEqual(tiny["cache_hits"],0)

if __name__=="__main__":
    unittest.main()
