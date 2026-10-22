"""Phase XII compact reachability exactness and memory-regime regression tests."""
import itertools
import json
import random
import subprocess
import tempfile
import unittest
from pathlib import Path
from test_closure_index import make_input

ROOT = Path(__file__).resolve().parent


class CompactNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.tmp.name) / "native"
        subprocess.run([
            "g++", "-std=c++17", "-O2", "-DNDEBUG", "-Wall", "-Wextra",
            "-pedantic", "-o", str(cls.binary), str(ROOT / "native_query_bench.cpp")
        ], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def execute(self, adj, queries, closure_cap=0):
        proc = subprocess.run([str(self.binary), "3", str(closure_cap)],
                              input=make_input(adj, queries), capture_output=True,
                              check=True, timeout=50)
        out = json.loads(proc.stdout)
        compact = out["compact"]
        self.assertEqual(compact["checksum"], out["policies"][0]["checksum"])
        self.assertEqual(out["compact_plain"]["checksum"], compact["checksum"])
        self.assertEqual(out["compact_topo"]["checksum"], compact["checksum"])
        self.assertEqual(out["compact_bidir"]["checksum"], compact["checksum"])
        self.assertEqual(out["compact_bidir_intervals"]["checksum"], compact["checksum"])
        self.assertEqual(out["compact_bidir_intervals"]["fallback_queries"],
                         out["compact_bidir"]["fallback_queries"])
        self.assertGreaterEqual(out["compact_bidir_intervals"]["interval_rejections"], 0)
        self.assertEqual(out["compact_bidir"]["fallback_queries"],
                         out["compact_topo"]["fallback_queries"])
        self.assertGreater(out["compact_bidir"]["extra_storage_bytes"], 0)
        self.assertLessEqual(out["compact_topo"]["fallback_edges"],
                             out["compact_plain"]["fallback_edges"])
        self.assertEqual(out["compact_pivots"]["checksum"], compact["checksum"])
        self.assertEqual(out["compact_pivots_topo"]["checksum"], compact["checksum"])
        self.assertEqual(out["compact_pivots_bidir"]["checksum"], compact["checksum"])
        self.assertEqual(out["compact_pivots_bidir_intervals"]["checksum"], compact["checksum"])
        self.assertEqual(out["compact_pivots_selector"]["checksum"], compact["checksum"])
        self.assertEqual(out["compact_pivots_selector"]["training_queries"], 0)
        self.assertEqual(out["compact_pivots_selector"]["policy_id"], 1)
        self.assertEqual(out["compact_pivots_selector"]["fallback_queries"],
                         out["compact_pivots_bidir"]["fallback_queries"])
        self.assertEqual(out["compact_pivots_selector"]["pivot_probes"],
                         out["compact_pivots_bidir"]["pivot_probes"])
        self.assertEqual(out["compact_pivots_selector"]["topological_fallbacks"] +
                         out["compact_pivots_selector"]["bidirectional_fallbacks"],
                         out["compact_pivots_selector"]["fallback_queries"])
        self.assertEqual(out["compact_pivots_bidir_intervals"]["pivot_rescues"],
                         out["compact_pivots_bidir"]["pivot_rescues"])
        self.assertEqual(out["compact_pivots_bidir_intervals"]["pivot_probes"],
                         out["compact_pivots_bidir"]["pivot_probes"])
        self.assertEqual(out["compact_pivots_bidir_intervals"]["fallback_queries"],
                         out["compact_pivots_bidir"]["fallback_queries"])
        self.assertEqual(out["compact_pivots_bidir"]["pivot_probes"],
                         out["compact_pivots_topo"]["pivot_probes"])
        self.assertEqual(out["compact_pivots_bidir"]["pivot_rescues"],
                         out["compact_pivots_topo"]["pivot_rescues"])
        self.assertEqual(out["compact_pivots_bidir"]["fallback_queries"],
                         out["compact_pivots_topo"]["fallback_queries"])
        self.assertEqual(out["compact_pivots_topo"]["pivot_rescues"],
                         out["compact_pivots"]["pivot_rescues"])
        self.assertEqual(out["compact_pivots_topo"]["fallback_queries"],
                         out["compact_pivots"]["fallback_queries"])
        self.assertGreaterEqual(out["compact_pivots"]["pivot_rescues"], 0)
        self.assertEqual(len(out["compact_plain"]["samples_ns_per_query"]), 3)
        self.assertEqual(len(out["compact_topo"]["samples_ns_per_query"]), 3)
        self.assertEqual(len(out["compact_bidir"]["samples_ns_per_query"]), 3)
        self.assertEqual(len(out["compact_bidir_intervals"]["samples_ns_per_query"]), 3)
        self.assertEqual(len(out["compact_pivots_bidir_intervals"]["samples_ns_per_query"]), 3)
        self.assertEqual(len(out["compact_pivots_bidir"]["samples_ns_per_query"]), 3)
        self.assertEqual(len(out["compact_pivots_topo"]["samples_ns_per_query"]), 3)
        self.assertEqual(sum(compact[k] for k in
                             ("certified_yes", "certified_no", "fallback_queries")), len(queries))
        self.assertEqual(compact["dimensions"], 4)
        self.assertEqual(len(compact["samples_ns_per_query"]), 3)
        return out

    def test_exhaustive_three_vertex_graphs(self):
        n = 3
        pairs = [(i, j) for i in range(n) for j in range(n) if i != j]
        queries = list(itertools.product(range(n), repeat=2))
        for mask in range(1 << len(pairs)):
            adj = [[] for _ in range(n)]
            for bit, (s, t) in enumerate(pairs):
                if mask >> bit & 1:
                    adj[s].append(t)
            out = self.execute(adj, queries, 0)
            self.assertFalse(out["closure"]["available"])

    def test_random_cyclic_graphs(self):
        rng = random.Random(20261022)
        for n in (6, 18, 70, 120):
            for p in (0.02, 0.15, 0.75):
                adj = [[v for v in range(n) if u != v and rng.random() < p]
                       for u in range(n)]
                queries = [(rng.randrange(n), rng.randrange(n)) for _ in range(100)]
                self.execute(adj, queries, 0)

    def test_long_chain_no_recursive_stack(self):
        n = 4096
        adj = [[i + 1] if i + 1 < n else [] for i in range(n)]
        queries = [(0, n - 1), (n - 1, 0), (31, 30), (31, 32), (400, 400)]
        data = self.execute(adj, queries, 0)["compact"]
        self.assertGreaterEqual(data["certified_yes"], 3)
        self.assertEqual(data["certified_no"], 2)
        self.assertEqual(data["fallback_queries"], 0)
        self.assertEqual(data["components"], n)

    def test_complex_scc_and_isolated_vertices(self):
        n = 55
        adj = [[(i + 1) % 45] if i < 45 else [] for i in range(n)]
        queries = [(0, 44), (44, 0), (46, 45), (45, 46),
                   (50, 50), (50, 49), (49, 50)]
        out = self.execute(adj, queries, 1)
        self.assertEqual(out["compact"]["components"], 11)
        self.assertEqual(out["closure"]["checksum"], out["compact"]["checksum"])

    def test_bidirectional_interleaved_disconnected_dags(self):
        # Two chains interleave in topological rank but never connect.
        n = 120
        adj = [[] for _ in range(n)]
        for i in range(n - 2):
            adj[i].append(i + 2)
            if i + 4 < n and i % 6 == 0:
                adj[i].append(i + 4)
        queries = [(i, j) for i in range(0, n, 5) for j in range(0, n, 9)]
        out = self.execute(adj, queries, 0)
        self.assertEqual(out["compact_bidir"]["checksum"],
                         out["compact_topo"]["checksum"])

    def test_bidirectional_duplicate_edges_and_cycles(self):
        n = 180
        adj = [[] for _ in range(n)]
        for i in range(n - 1):
            adj[i].extend([i + 1, i + 1])
        for i in range(0, n - 6, 9):
            adj[i + 6].append(i)
        queries = [(s, t) for s in range(0, n, 11) for t in range(0, n, 13)]
        out = self.execute(adj, queries, 0)
        self.assertEqual(out["compact_bidir"]["checksum"],
                         out["compact_plain"]["checksum"])

    def test_two_sided_pruning_branching_nonreachability(self):
        # Most sampled negative pairs share topological order but are
        # disconnected by branch identity. Oracle detects false positives.
        n = 96
        adj = [[] for _ in range(n)]
        for i in range(n - 12):
            for stride in (3,6,9):
                if i+stride < n and i%3 == (i+stride)%3:
                    adj[i].append(i+stride)
        queries = [(u,v) for u in range(0,n,5) for v in range(0,n,7)]
        out = self.execute(adj,queries,0)
        self.assertEqual(out["compact_pivots_bidir_intervals"]["checksum"],
                         out["compact_pivots_bidir"]["checksum"])

    def test_train_only_selector_queries(self):
        # Native executable's optional train-only suffix must not alter the
        # held-out query file or correctness checksum.
        rng = random.Random(171717)
        n=110
        adj=[[i+1] if i+1<n else [] for i in range(n)]
        for i in range(0,n-7,9):
            adj[i].append(i+7)
        for i in range(0,n-3,13):
            adj[i].append(i+3)
        heldout=[(rng.randrange(n),rng.randrange(n)) for _ in range(150)]
        training=[(rng.randrange(n),rng.randrange(n)) for _ in range(200)]
        input_data=make_input(adj,heldout)
        trailer=(str(len(training))+"\n"+
                 "".join(f"{u} {v}\n" for u,v in training)).encode()
        out=json.loads(subprocess.run(
            [str(self.binary),"5","0"],input=input_data+trailer,
            capture_output=True,check=True,timeout=50).stdout)
        selector=out["compact_pivots_selector"]
        self.assertEqual(selector["training_queries"],200)
        self.assertGreaterEqual(selector["policy_id"],0)
        self.assertLessEqual(selector["policy_id"],8)
        self.assertEqual(selector["checksum"],out["policies"][0]["checksum"])
        self.assertEqual(selector["pivot_probes"],
                         out["compact_pivots_bidir"]["pivot_probes"])
        self.assertEqual(selector["topological_fallbacks"]+
                         selector["bidirectional_fallbacks"],
                         selector["fallback_queries"])
        self.assertEqual(len(selector["samples_ns_per_query"]),5)
        self.assertEqual(len(selector["training_policy_medians_ns_per_query"]),9)

    def test_train_only_selector_bad_input(self):
        adj=[[1],[]]
        heldout=[(0,1),(1,0)]
        data=make_input(adj,heldout)+b"1\n2 0\n"
        proc=subprocess.run([str(self.binary),"3","0"],input=data,
                            capture_output=True,timeout=30)
        self.assertNotEqual(proc.returncode,0)
        self.assertIn(b"bad selector training pair",proc.stderr)

    def test_dense_dag_nontrivial_negative_cases(self):
        n = 120
        adj = [[j for j in range(i + 1, n) if (j - i) < 9]
               for i in range(n)]
        queries = [(i, j) for i in range(0, n, 4)
                   for j in (0, min(n-1, i+20), n-1)]
        data = self.execute(adj, queries, 0)["compact"]
        self.assertGreater(data["certified_no"], 0)
        self.assertGreater(data["certified_yes"], 0)


if __name__ == "__main__":
    unittest.main()
