import itertools, random, unittest
from tric import choose_path_optimal
from path_monge import choose_path_monge, GapCosts

class MongeTest(unittest.TestCase):
    def test_monge(self):
        r=random.Random(2604)
        for n in range(4,12):
            for _ in range(40):
                q=[(r.randrange(n),r.randrange(n)) for __ in range(80)]
                w=[r.randrange(0,10) for __ in q]
                cost=GapCosts(n,q,w)
                for a in range(n):
                    for b in range(a,n):
                        for c in range(b,n):
                            for d in range(c,n):
                                self.assertLessEqual(cost.gap(a,c)+cost.gap(b,d),cost.gap(a,d)+cost.gap(b,c))
    def test_reference_and_bruteforce(self):
        r=random.Random(3801)
        for n in range(1,13):
            for _ in range(35):
                q=[(r.randrange(n),r.randrange(n)) for __ in range(36)]
                w=[r.randrange(0,12) for __ in q]
                for k in range(min(n,5)+1):
                    piv,val=choose_path_monge(n,q,k,w)
                    p2,v2=choose_path_optimal(n,q,k,w)
                    self.assertEqual((piv,val),(p2,v2))
                    if n <= 8:
                        self.assertEqual(val,min(sum(ww for (s,t),ww in zip(q,w) if not any(min(s,t)<=p<=max(s,t) for p in ps)) for ps in itertools.combinations(range(n),k)))
    def test_invalid(self):
        with self.assertRaises(ValueError):choose_path_monge(4,[(0,2)],5)
        with self.assertRaises(ValueError):choose_path_monge(4,[(0,2)],2,[-1])
        with self.assertRaises(ValueError):choose_path_monge(4,[(0,5)],2)

if __name__=='__main__': unittest.main()
