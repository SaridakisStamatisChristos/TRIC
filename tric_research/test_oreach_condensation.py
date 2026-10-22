"""Verify SCC query mapping against independent reachability oracle."""
import itertools
import tempfile
import unittest
from pathlib import Path
from benchmark_oreach_ci import read_metis, write_queryfile
from oreach_condensation import condensation, prepare, remap_queries, metis_dump
from tric import build_graph, early_reachable

class CondensationTests(unittest.TestCase):
    def test_small_graphs(self):
        for mask in range(512):
            edges=[(u,v) for u in range(3) for v in range(3) if mask & (1 << (u*3+v))]
            adj,_=build_graph(3,edges)
            dag,ids,sizes=condensation(adj)
            with self.subTest(mask=mask):
                self.assertEqual(sum(sizes),3)
                for s,t in itertools.product(range(3),repeat=2):
                    self.assertEqual(early_reachable(adj,s,t)[0],early_reachable(dag,ids[s],ids[t])[0])

    def test_query_rewrite(self):
        adj,_=build_graph(7,[(0,1),(1,0),(1,2),(2,3),(3,2),(4,5),(5,6)])
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            original=d/"graph.metis"
            metis_dump(original,adj)
            graph,ids,meta=prepare(original,d/"condensed")
            self.assertLess(meta["scc_nodes"],7)
            dag,_=read_metis(graph)
            q=d/"heldout.query.m.txt"
            write_queryfile(q,adj,list(itertools.product(range(7),repeat=2)))
            stats=remap_queries(q,d/"mapped.query.m.txt",dag,ids)
            self.assertEqual(stats["query_count"],49)
            self.assertTrue(stats["verified_original_ground_truth_matches_condensed_dag"])

    def test_false_label_is_rejected(self):
        adj,_=build_graph(3,[(0,1)])
        dag,ids,_=condensation(adj)
        with tempfile.TemporaryDirectory() as td:
            q=Path(td)/"sample.txt"
            q.write_text("0 1 0\n")
            with self.assertRaises(AssertionError):
                remap_queries(q,Path(td)/"mapped.txt",dag,ids)

if __name__=="__main__": unittest.main()
