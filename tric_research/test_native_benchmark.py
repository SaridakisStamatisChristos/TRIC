"""Independent compiled differential tests: native certificate+fallback vs native BFS oracle.

These are tests of semantic equivalence, parsing and cost accounting, not
proof that one implementation is faster, nor an external O'Reach comparison.
"""
import random
import shutil
import tempfile
import unittest
from pathlib import Path
from benchmark_native import build_executable, call_native, sample_queries
from tric import graph_family, build_graph


@unittest.skipUnless(shutil.which('g++'), 'g++ C++17 compiler unavailable')
class NativeBenchmarkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.exe,_,_=build_executable(cls.temp.name)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_empty_graph_and_reflexivity(self):
        graph,_=build_graph(4,[])
        q=[(s,t) for s in range(4) for t in range(4)]*3
        out=call_native(self.exe,graph,list(range(4)),{'BFS':[],'Indexed':[2,3,0]},q,3)
        self.assertEqual([x['name'] for x in out['policies']],['BFS','Indexed'])
        self.assertEqual(out['policies'][0]['mean_probes'],0)

    def test_cyclic_and_dag_graphs(self):
        for family in ['dag','chain','blocks','communities']:
            g,_=graph_family(family,65,717)
            q=[(s,t) for s in range(65) for t in range(65)]
            out=call_native(self.exe,g,[0,10,20,30,40,50],
                {'BFS':[],'Ordered':[5,2,0],'Greedy':[4,1,3]},q,3)
            self.assertEqual(out['queries'],65**2)
            self.assertEqual(out['policies'][1]['pivots'],3)

    def test_random_graph_cycles_and_duplicates(self):
        rng=random.Random(1342)
        for n in range(1,10):
            edges=[(rng.randrange(n),rng.randrange(n)) for _ in range(5*n)]
            g,_=build_graph(n,edges)
            q=[(a,b) for a in range(n) for b in range(n)]
            out=call_native(self.exe,g,list(range(n)),{'BFS':[],'Pivots':list(range(n-1,-1,-1))},q,3)
            self.assertEqual(out['queries'],n*n)

    def test_hot_queries_reproducibility(self):
        args=(20,200,391,'hot',[1,2,3],[15,16,17])
        self.assertEqual(sample_queries(*args),sample_queries(*args))


if __name__=='__main__':unittest.main()
