"""Independent Phase XXIII parity across small graph/cycle and DFS boundaries."""
import random
import subprocess
import tempfile
import unittest
from pathlib import Path
from phase23_training import (
    compile_native,native_fit,legacy_fit,assert_parity,serialize_training)
from tric import build_graph, graph_family

class NativeTrainingParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.exe=compile_native(cls.tmp.name,optimization="-O2")
    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def check(self,adj,rev,pivots,queries,k):
        native=native_fit(adj,pivots,queries,k,self.exe,timeout=40)
        legacy=legacy_fit(adj,rev,pivots,queries,k)
        self.assertTrue(assert_parity(native,legacy))
        self.assertEqual(native["native_metrics"]["train"],len(queries))
        self.assertGreater(native["fit_ns"],0)
        return native

    def test_cyclic_sparse_dense_and_isolated(self):
        rng=random.Random(20261022)
        for n in (1,2,3,6,11,20,65):
            for prob in (0,0.08,0.3,0.8):
                edges=[(u,v) for u in range(n) for v in range(n)
                       if rng.random()<prob]
                adj,rev=build_graph(n,edges)
                verts=list(range(min(n,6)))
                train=[(rng.randrange(n),rng.randrange(n)) for _ in range(60)]
                for budget in (0,len(verts)//2,len(verts)):
                    with self.subTest(n=n,prob=prob,budget=budget):
                        self.check(adj,rev,verts,train,budget)

    def test_large_scc_and_repeated_sources(self):
        for family in ("dag","blocks","communities"):
            adj,rev=graph_family(family,240,20261001)
            ids=list(range(7))
            train=[(j%5,(j*17+3)%240) for j in range(200)]
            with self.subTest(family=family):
                self.check(adj,rev,ids,train,5)

    def test_training_only_no_heldout_access_and_invalid_input(self):
        adj,rev=build_graph(4,[(0,1),(1,2)])
        native=self.check(adj,rev,[1,0],[(0,1),(0,3),(2,2)],2)
        for bad in ([(-1,0)],[(0,4)],[]):
            with self.assertRaises(ValueError):
                serialize_training(adj,[1,0],bad)
        with self.assertRaises(ValueError):
            serialize_training(adj,[0,0],[(0,1)])
        with self.assertRaises(ValueError):
            serialize_training([[4],[],[],[]],[0],[(0,1)])
        self.assertEqual(len(native["hit_masks"]),3)

    def test_exact_fallback_off_by_one(self):
        adj,rev=build_graph(3,[(0,1),(1,2)])
        x=self.check(adj,rev,[1],[(0,0),(0,1),(0,2),(2,0)],1)
        self.assertEqual(x["fallback_costs"],[1,2,3,1])

if __name__=="__main__":
    unittest.main()
