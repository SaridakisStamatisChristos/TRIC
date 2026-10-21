"""Exact Phase VI decomposition: independent oracle and differential tests."""
import itertools
import random
import unittest
from adaptive_exact import optimize_adaptive,optimize_scc_adaptive
from backbone import optimize_intervals
from frontier_dp import optimize_frontier
from tric import build_graph, make_pivot, certify


def brute(h, iv,wt,k):
    ans=[]
    for chosen in itertools.combinations(range(h),k):
        loss=sum(w for regions,w in zip(iv,wt)
                 if not any(a<=p<=b for a,b in regions for p in chosen))
        ans.append(loss)
    return min(ans)

class TestAdaptiveExact(unittest.TestCase):
    def test_empty_and_budget(self):
        for h in range(0,8):
            for k in range(h+1):
                selected,loss,d=optimize_adaptive(h,[(),()],[3,4],k)
                self.assertEqual((len(selected),loss),(k,7))
                self.assertEqual(d['components'],0)
        for k in range(6):
            s,l,d=optimize_adaptive(5,[((0,0),),((2,2),)],[4,9],k)
            self.assertEqual(l,brute(5,[((0,0),),((2,2),)],[4,9],k))

    def test_random_against_brute_and_existing_algorithms(self):
        rng=random.Random(20261021)
        for h in range(1,11):
            for _ in range(65):
                query=[];weight=[]
                for _ in range(rng.randrange(0,12)):
                    pts=sorted(rng.sample(range(h),rng.randint(1,min(h,4))))
                    if rng.random()<.5 and len(pts)>1 and pts[1]>pts[0]+1:
                        query.append(((pts[0],pts[0]),(pts[-1],pts[-1])))
                    else:
                        query.append(((pts[0],pts[-1]),))
                    weight.append(rng.randrange(0,6))
                if rng.random()<.3:query.append(());weight.append(3)
                k=rng.randint(0,min(h,5))
                expected=brute(h,query,weight,k)
                selected,loss,stats=optimize_adaptive(h,query,weight,k)
                self.assertEqual(loss,expected,(h,k,query,weight))
                self.assertEqual(len(set(selected)),k)
                self.assertEqual(sum(w for sig,w in zip(query,weight)
                    if not any(a<=p<=b for a,b in sig for p in selected)),loss)
                if h<=7:
                    self.assertEqual(optimize_frontier(h,query,weight,k)[1],expected)
                    self.assertEqual(optimize_intervals(h,query,weight,k)[1],expected)

    def test_forced_methods(self):
        rng=random.Random(175)
        for _ in range(85):
            h=10
            query=[]
            for _ in range(5):
                a,b=sorted(rng.sample(range(h),2))
                if b-a>=2:query.append(((a,a),(b,b)))
                else:query.append(((a,b),))
            w=[rng.randrange(1,10) for x in query]
            k=rng.randint(0,5)
            results=[optimize_adaptive(h,query,w,k,engine=eng)[1]
                     for eng in ('frontier','orientation','auto')]
            self.assertEqual(results,[brute(h,query,w,k)]*3)

    def test_disconnected_support_and_free_pivots(self):
        q=[((1,1),(3,3)),((8,8),(10,10)),((17,18),),()]
        w=[4,7,2,5]
        for k in range(22):
            out,loss,d=optimize_adaptive(21,q,w,k)
            self.assertEqual(loss,brute(21,q,w,k))
            self.assertEqual(len(out),k)
            self.assertEqual(d['components'],3)
        q=[((0,1),(4,5)),((4,4),(7,8)),((12,12),(16,16))]
        _,_,d=optimize_adaptive(18,q,[1,2,3],2)
        self.assertEqual(d['components'],2)

    def test_cyclic_graph_scc_differential(self):
        rng=random.Random(366)
        for n in range(3,8):
            for _ in range(26):
                backbone=list(range(rng.randint(1,min(5,n))))
                edges=[(backbone[i],backbone[i+1]) for i in range(len(backbone)-1)]
                edges += [(u,v) for u in range(n) for v in range(n)
                          if rng.random()<.17]
                adj,rev=build_graph(n,edges)
                queries=[(rng.randrange(n),rng.randrange(n)) for _ in range(7)]
                weights=[rng.randrange(1,5) for _ in queries]
                for k in range(len(backbone)+1):
                    pivots,loss,_=optimize_scc_adaptive(adj,backbone,queries,weights,k)
                    self.assertEqual(len(pivots),k)
                    self.assertEqual(len(set(pivots)),k)
                    oracle=[]
                    for chosen in itertools.combinations(backbone,k):
                        oracle.append(sum(w for q,w in zip(queries,weights) if not any(
                            certify(make_pivot(adj,rev,p),*q) is not None for p in chosen)))
                    self.assertEqual(loss,min(oracle))

    def test_recycled_bit_slot_event_collision(self):
        # A first interval ends exactly when another second interval ends.
        # The Phase V index recycles that Boolean slot in the same sweep step.
        queries=[((0,0),(3,3)),((3,3),(7,7)),((7,7),(11,11)),
                 ((2,2),(9,9))]
        weights=[5,7,11,13]
        for budget in range(0,6):
            for engine in ('auto','frontier','orientation'):
                pivots,loss,_=optimize_adaptive(12,queries,weights,budget,engine=engine)
                self.assertEqual(len(pivots),budget)
                self.assertEqual(loss,brute(12,queries,weights,budget))

    def test_invalid_values(self):
        bad=[(-1,[],[],0),(2,[],[],3),(2,[((0,2),)],[1],1),
             (2,[((1,0),)],[1],1),(2,[((0,1),)],[float('nan')],1),
             (2,[((0,1),)],[float('inf')],1),(2,[((0,1),)],[-1],1)]
        for a in bad:
            with self.assertRaises(ValueError):optimize_adaptive(*a)
        with self.assertRaises(ValueError): optimize_adaptive(3,[],[],1,engine='unknown')

if __name__=='__main__':unittest.main()
