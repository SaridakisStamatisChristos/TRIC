"""Independent correctness proof by exhaustive tiny-graph reachability enumeration.

The upstream C++ binary is separately run under the full CI matrix.
These tests establish that SCC reduction + query remapping preserve the
same answers for arbitrary cycles, self-loops, isolated and disjoint nodes.
"""
import itertools
import json
import tempfile
import unittest
from pathlib import Path

from oreach_compatible_input import (
    prepare_comparator, remap_queryfile, scc_quotient, digest, write_graph)
from benchmark_oreach_ci import read_metis, write_queryfile
from tric import build_graph, early_reachable, graph_family

class SCCComparatorExactness(unittest.TestCase):
    def test_all_three_vertex_graphs_and_all_query_pairs(self):
        n=3
        for mask in range(512):
            edges=[(u,v) for u in range(n) for v in range(n)
                   if mask & (1<<(u*n+v))]
            adj,_=build_graph(n,edges)
            quotient,mapping,sizes=scc_quotient(adj)
            self.assertEqual(sum(sizes),n)
            self.assertTrue(all(0<=c<len(quotient) for c in mapping))
            self.assertFalse(any(u in row for u,row in enumerate(quotient)))
            for s,t in itertools.product(range(n),repeat=2):
                self.assertEqual(bool(early_reachable(adj,s,t)[0]),
                                 bool(early_reachable(quotient,mapping[s],mapping[t])[0]),
                                 (mask,s,t))

    def test_query_file_mapping_and_original_truth(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            adj,_=build_graph(6,[(0,1),(1,2),(2,0),(2,3),(4,5)])
            graph=root/"original.metis"
            write_graph(graph,adj)
            out,q,map_,meta=prepare_comparator(
                adj,graph,"generated_communities",root/"compatible")
            queries=list(itertools.product(range(6),repeat=2))
            raw=root/"original.query.m.txt"
            positive=write_queryfile(raw,adj,queries)
            mapped=root/"compatible.query.m.txt"
            info=remap_queryfile(raw,mapped,adj,q,map_)
            self.assertEqual(info["equivalence_verified_pairs"],len(queries))
            self.assertEqual(info["positive_count"],positive)
            self.assertEqual(meta["original_nodes"],6)
            self.assertEqual(meta["comparator_scc_nodes"],4)
            self.assertEqual(meta["upstream_support_parameter"],0)
            self.assertEqual(digest(out),meta["comparator_graph_sha256"])
            parsed,_=read_metis(out)
            self.assertEqual(parsed,q)
            self.assertEqual(len(mapped.read_text().splitlines()),len(queries))
            self.assertEqual(json.loads(
                (out.parent/"vertex_to_scc.json").read_text()),map_)
            with self.assertRaisesRegex(ValueError,"generated"):
                prepare_comparator(adj,graph,"example",root/"wrong")
            with self.assertRaisesRegex(ValueError,"preserve"):
                remap_queryfile(raw,raw,adj,q,map_)
            with self.assertRaises(AssertionError):
                corrupt=root/"corrupt.query.m.txt"
                corrupt.write_text("0 3 1\n")
                remap_queryfile(corrupt,mapped,adj,q,map_)

    def test_fixed_seed_generated_family_support(self):
        for family in ("dag","blocks","communities"):
            adj,_=graph_family(family,120,20261001)
            quotient,mapping,sizes=scc_quotient(adj)
            self.assertGreater(len(quotient),0)
            self.assertTrue(all(q!=i for i,row in enumerate(quotient) for q in row))
            for s in range(0,120,11):
                for t in range(0,120,13):
                    self.assertEqual(bool(early_reachable(adj,s,t)[0]),
                                     bool(early_reachable(quotient,mapping[s],mapping[t])[0]))

if __name__=="__main__":
    unittest.main()
