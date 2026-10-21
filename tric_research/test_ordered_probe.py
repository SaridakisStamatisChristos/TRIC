"""Independent brute-force ordering and direct graph-certificate oracles."""
import itertools,random,unittest
from ordered_probe import (optimize_ordered,ordered_cost,
                           hit_masks_for_pivots,greedy_coverage_order)
from tric import build_graph,make_pivot,certify,early_reachable


class TestOrderedProbe(unittest.TestCase):
    def test_exhaustive_small_binary_query_masks(self):
        for c in range(1,5):
            m=3
            for masks in itertools.product(range(1<<c),repeat=m):
                weights=[1,2,3]; fb=[4,1,7]; probes=[1,2,1,3][:c]
                for k in range(c+1):
                    order,val,_=optimize_ordered(masks,weights,fb,probes,k)
                    oracle=min(
                        ordered_cost(order2,masks,weights,fb,probes)
                        for b in range(k+1)
                        for order2 in itertools.permutations(range(c),b))
                    self.assertAlmostEqual(val,oracle)
                    self.assertAlmostEqual(val,ordered_cost(order,masks,weights,fb,probes))

    def test_randomized_float_costs_and_lengths(self):
        rng=random.Random(8821)
        for _ in range(180):
            c=rng.randrange(0,8);m=rng.randrange(0,13);k=rng.randrange(c+1)
            masks=[rng.randrange(1<<c) for _ in range(m)]
            weights=[rng.random()*4 for _ in range(m)]
            fb=[rng.random()*12 for _ in range(m)]
            pc=[rng.random()*3 for _ in range(c)]
            order,val,_=optimize_ordered(masks,weights,fb,pc,k)
            oracle=min(ordered_cost(seq,masks,weights,fb,pc)
                       for b in range(k+1) for seq in itertools.permutations(range(c),b))
            self.assertAlmostEqual(val,oracle,places=8)
            self.assertAlmostEqual(val,ordered_cost(order,masks,weights,fb,pc),places=8)

    def test_graph_integration_and_negative_certificates(self):
        rng=random.Random(9705)
        for n in range(2,8):
            for _ in range(20):
                adj,rev=build_graph(n,[(u,v) for u in range(n)
                                           for v in range(n) if u!=v and rng.random()<0.23])
                pivots=[make_pivot(adj,rev,p) for p in range(min(n,5))]
                qs=[(s,t) for s in range(n) for t in range(n)]
                masks=hit_masks_for_pivots(pivots,qs)
                for (s,t),h in zip(qs,masks):
                    truth,_=early_reachable(adj,s,t)
                    for i,p in enumerate(pivots):
                        ans=certify(p,s,t)
                        self.assertEqual(ans is not None,bool(h & (1<<i)))
                        if ans is not None:self.assertEqual(ans,truth)
                fb=[2+early_reachable(adj,*q)[1] for q in qs]
                seq,v,_=optimize_ordered(masks,[1]*len(qs),fb,[1]*len(pivots),2)
                self.assertAlmostEqual(v,ordered_cost(seq,masks,[1]*len(qs),fb,[1]*len(pivots)))

    def test_different_objectives(self):
        # Coverage demands both pivots but fallback may be cheaper than probes.
        h=[1,2,2,0];w=[2,3,4,1]; f=[.01,.01,.01,.01];pc=[4,4]
        ordered,cost,info=optimize_ordered(h,w,f,pc,2)
        self.assertEqual(ordered,[])
        self.assertEqual(info['selected'],0)
        self.assertEqual(len(greedy_coverage_order(h,w,2,2)),2)
        self.assertAlmostEqual(cost,0.1)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):optimize_ordered([4],[1],[1],[1,1],1)
        with self.assertRaises(ValueError):optimize_ordered([0],[float('nan')],[1],[1],1)
        with self.assertRaises(ValueError):optimize_ordered([0],[1],[1],[-1],1)
        with self.assertRaises(ValueError):optimize_ordered([0],[1],[1],[1],2)
        with self.assertRaises(ValueError):optimize_ordered([0],[1],[],[1],1)
        with self.assertRaises(ValueError):optimize_ordered([0],[1],[1],[1]*20,1)

if __name__=='__main__':unittest.main()
