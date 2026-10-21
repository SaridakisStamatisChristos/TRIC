"""Independent exhaustive oracle and adversarial differential tests for Phase VII."""
import itertools
import random
import unittest
from frontier_compact import optimize_compact,optimize_compact_profile
from adaptive_exact import optimize_adaptive


def brute(h,iv,wt,k):
    return min(sum(w for intervals,w in zip(iv,wt)
                   if not any(a<=p<=b for a,b in intervals for p in subset))
               for subset in itertools.combinations(range(h),k))


class TestCompact(unittest.TestCase):
    def test_exhaustive_small_signatures(self):
        for h in range(1,5):
            ivs=[()] + [((a,b),) for a in range(h) for b in range(a,h)]
            ivs += [((a,b),(c,d)) for a in range(h) for b in range(a,h)
                    for c in range(b+2,h) for d in range(c,h)]
            for first,second in itertools.product(ivs,repeat=2):
                Q=[first,second]
                profile,_=optimize_compact_profile(h,Q,[2,3],h)
                for k in range(h+1):
                    self.assertEqual(profile[k][0],brute(h,Q,[2,3],k),(h,Q,k))
                    self.assertEqual(len(profile[k][1]),k)
    def test_random_multi_budget(self):
        rng=random.Random(20261021)
        for h in range(1,12):
            for _ in range(100):
                iv=[]; wt=[]
                for _ in range(rng.randrange(0,16)):
                    pts=sorted(rng.sample(range(h),rng.randint(1,min(4,h))))
                    if len(pts)>1 and pts[1]>pts[0]+1 and rng.random()<.6:
                        iv.append(((pts[0],pts[0]),(pts[-1],pts[-1])))
                    else:iv.append(((pts[0],pts[-1]),))
                    wt.append(rng.randint(0,8))
                if rng.random()<.4:iv.append(());wt.append(3)
                for k in range(min(h,5)+1):
                    selected,loss,_=optimize_compact(h,iv,wt,k)
                    expected=brute(h,iv,wt,k)
                    self.assertEqual(loss,expected,(h,k,iv,wt))
                    self.assertEqual(len(selected),k)
                    self.assertEqual(len(set(selected)),k)
                    self.assertEqual(loss,sum(w for reg,w in zip(iv,wt) if not any(a<=p<=b for a,b in reg for p in selected)))
    def test_many_concurrent_starts(self):
        for h in [10,20]:
            iv=[((i,h-1),) for i in range(h-1)]
            w=list(range(1,h))
            for k in [0,1,2,3]:
                got=optimize_compact(h,iv,w,k)[1]
                self.assertEqual(got,optimize_adaptive(h,iv,w,k)[1])
    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):optimize_compact(3,[],[],4)
        with self.assertRaises(ValueError):optimize_compact(-1,[],[],0)

if __name__=='__main__':unittest.main()

class TestAdaptiveIntegration(unittest.TestCase):
    def test_dispatch_on_long_two_interval_hulls(self):
        for h in (60,80):
            iv=[((1,i+3),(h-20+i,h-1)) for i in range(6)]
            wt=[i+1 for i in range(6)]
            for k in (0,1,2,5):
                auto=optimize_adaptive(h,iv,wt,k)
                compact=optimize_adaptive(h,iv,wt,k,engine='compact')
                frontier=optimize_adaptive(h,iv,wt,k,engine='frontier')
                self.assertEqual(auto[1],compact[1])
                self.assertEqual(compact[1],frontier[1])
                self.assertEqual(auto[2]['component_stats'][0]['engine'],'compact')
    def test_compact_scc_cyclic(self):
        from adaptive_exact import optimize_scc_adaptive
        from tric import build_graph,make_pivot,certify
        adj,rev=build_graph(8,[(0,1),(1,2),(2,0),(2,3),(3,4),
                                 (4,5),(5,4),(5,6),(6,7)])
        bb=[0,1,2,3,4,5,6,7]
        queries=[(u,v) for u in range(8) for v in range(8) if u!=v]
        weights=[(u*3+v)%9 for u,v in queries]
        for k in range(0,9):
            s,cost,_=optimize_scc_adaptive(adj,bb,queries,weights,k,engine='compact')
            self.assertEqual(len(s),k)
            oracle=min(sum(w for (u,v),w in zip(queries,weights) if not any(
                certify(make_pivot(adj,rev,p),u,v) is not None for p in chosen))
                for chosen in itertools.combinations(bb,k))
            self.assertEqual(cost,oracle)
