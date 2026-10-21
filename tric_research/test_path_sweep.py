import random, itertools, unittest
from tric import choose_path_optimal
from path_monge import choose_path_monge
from path_sweep import choose_path_sweep,RangeAddMin

class TestPathSweep(unittest.TestCase):
    def test_tree(self):
        r=random.Random(13)
        for n in (1,2,3,5,17,100):
            a=[r.randrange(30) for _ in range(n)]
            t=RangeAddMin(a)
            for i in range(150):
                if r.random()<0.6:
                    lo=r.randrange(n);hi=r.randrange(lo,n);delta=r.randint(0,9)
                    t.add(lo,hi,delta)
                    for j in range(lo,hi+1):a[j]+=delta
                else:
                    end=r.randrange(n)
                    self.assertEqual(t.prefix_min(end),min(((v,j) for j,v in enumerate(a[:end+1]))))
    def test_equivalence(self):
        rng=random.Random(12345)
        for n in range(1,18):
            for _ in range(28):
                q=[(rng.randrange(n),rng.randrange(n)) for __ in range(55)]
                w=[rng.randrange(0,13) for __ in q]
                for k in range(min(n,7)+1):
                    a=choose_path_sweep(n,q,k,w)
                    b=choose_path_monge(n,q,k,w)
                    c=choose_path_optimal(n,q,k,w)
                    self.assertEqual(a,b)
                    self.assertEqual(a,c)
                    if n<=7:
                        self.assertEqual(a[1],min(sum(ww for (s,t),ww in zip(q,w) if not any(min(s,t)<=p<=max(s,t) for p in ps)) for ps in itertools.combinations(range(n),k)))
    def test_invalid(self):
        for args in [(3,[(1,3)],1,None),(3,[(1,2)],4,None),(3,[(1,2)],1,[-2])]:
            with self.assertRaises(ValueError):choose_path_sweep(*args)

if __name__=='__main__':unittest.main()
