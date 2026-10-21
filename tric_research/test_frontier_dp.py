"""Adversarial and differential verification of the Phase V exact frontier DP."""
import itertools
import random
import unittest
from frontier_dp import optimize_frontier, optimize_scc_frontier, prepare_events
from backbone import optimize_intervals
from backbone_hardness import make_vertex_cover_instance
from tric import build_graph, make_pivot, certify


def brute(h, intervals, weights, k):
    def covered(chosen, sig):
        return any(a <= p <= b for p in chosen for a,b in sig)
    values = [(sum(weight for sig,weight in zip(intervals,weights)
                   if not covered(chosen,sig)), chosen)
              for chosen in itertools.combinations(range(h),k)]
    return min(values)[0]


class TestFrontierDP(unittest.TestCase):
    def test_all_small_signatures(self):
        for h in range(1,5):
            ivs = [((a,b),) for a in range(h) for b in range(a,h)]
            ivs += [((a,b),(c,d)) for a in range(h) for b in range(a,h)
                    for c in range(b+2,h) for d in range(c,h)]
            ivs += [()]
            for k in range(h+1):
                for sig in ivs:
                    for sig2 in ivs:
                        workload = [sig,sig2]
                        weights = [2,5]
                        pivots, objective,_ = optimize_frontier(h,workload,weights,k)
                        self.assertEqual(objective,brute(h,workload,weights,k), (h,k,workload))
                        self.assertEqual(len(pivots),k)

    def test_random_equivalence_existing_optimizer(self):
        rng = random.Random(20261021)
        for _ in range(240):
            h = rng.randint(1,13)
            queries = []
            weights = []
            for _ in range(rng.randint(0,12)):
                a,b=sorted(rng.sample(range(h),k=2)) if h>1 else (0,0)
                if rng.random() < 0.55 and b-a>=2:
                    cut = rng.randint(a,b-2)
                    c = rng.randint(cut+2,b)
                    queries.append(((a,cut),(c,b)))
                else:
                    queries.append(((a,b),))
                weights.append(rng.randint(0,9))
            k=rng.randint(0,min(5,h))
            ours=optimize_frontier(h,queries,weights,k)
            old=optimize_intervals(h,queries,weights,k)
            self.assertEqual(ours[1],old[1], (h,k,queries,weights))
            self.assertEqual(ours[1],brute(h,queries,weights,k))

    def test_matching_hardness_graph_wide_r_narrow_w(self):
        edges = [(3*i,3*i+2) for i in range(10)]
        adj,rev,backbone,queries = make_vertex_cover_instance(30, edges)
        weight=[1]*len(queries)
        expected=5
        pivots,loss,diag=optimize_scc_frontier(adj,backbone,queries,weight,expected)
        self.assertEqual(len(pivots),expected)
        self.assertEqual(loss,5)
        self.assertEqual(diag['two_interval_signatures'],10)
        self.assertEqual(diag['frontier_width'],1)
        for source,target in queries:
            for p in pivots:
                pred=make_pivot(adj,rev,p)
                if certify(pred,source,target) is not None:
                    break

    def test_random_cyclic_graphs_against_bruteforce(self):
        rng=random.Random(746)
        for n in range(3,8):
            for _ in range(45):
                backbone=list(range(rng.randint(1,min(5,n))))
                edges=[(backbone[i],backbone[i+1]) for i in range(len(backbone)-1)]
                edges.extend((u,v) for u in range(n) for v in range(n)
                             if rng.random()<0.22)
                adj,rev=build_graph(n,edges)
                q=[(rng.randrange(n),rng.randrange(n)) for _ in range(8)]
                w=[rng.randint(0,3) for _ in q]
                for k in range(len(backbone)+1):
                    pivots,loss,_=optimize_scc_frontier(adj,backbone,q,w,k)
                    self.assertEqual(len(pivots),k)
                    self.assertEqual(len(set(pivots)),k)
                    actual=sum(weight for (s,t),weight in zip(q,w)
                               if not any(certify(make_pivot(adj,rev,p),s,t) is not None
                                          for p in pivots))
                    self.assertEqual(loss,actual)
                    all_losses=[]
                    for chosen in itertools.combinations(backbone,k):
                        all_losses.append(sum(weight for (s,t),weight in zip(q,w)
                              if not any(certify(make_pivot(adj,rev,p),s,t) is not None
                                         for p in chosen)))
                    self.assertEqual(loss,min(all_losses))

    def test_width_and_invalid_inputs(self):
        starts,ends,_,_,r,w,_ = prepare_events(8,[((0,1),(4,5)),((2,3),(6,7))],[3,4])
        self.assertEqual(w,2)
        self.assertEqual(max(slot for events in starts for slot,_ in events),1)
        # State slots are recycled, never proportional to the number r of
        # non-overlapping disjunctive signatures.
        r=1500
        many=[((4*i,4*i),(4*i+2,4*i+2)) for i in range(r)]
        starts,ends,_,_,count,width,_=prepare_events(4*r,many,[1]*r)
        self.assertEqual((count,width),(r,1))
        self.assertEqual({slot for events in starts for slot,_ in events},{0})
        for args in [(4,[((0,4),)],[1],1), (4,[((0,2),)],[1],5),
                     (4,[((0,1),)],[-1],1),(4,[((0,1),)],[float('nan')],1)]:
            with self.assertRaises(ValueError):optimize_frontier(*args)
        with self.assertRaises(RuntimeError):
            optimize_frontier(8,[((0,1),(4,5)),((2,3),(6,7))],[3,4],2,state_cap=1)

if __name__ == '__main__':unittest.main()
