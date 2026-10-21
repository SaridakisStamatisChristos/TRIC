import random,itertools,unittest
from tric import build_graph, reach_mask, early_reachable, make_pivot, certify, choose_path_optimal

class TestTRIC(unittest.TestCase):
    def test_random_graphs(self):
        rng=random.Random(1124)
        for n in range(1,9):
            for trial in range(100):
                edges=[(u,v) for u in range(n) for v in range(n) if u!=v and rng.random()<rng.random()]
                adj,rev=build_graph(n,edges)
                for p in range(n):
                    pivot=make_pivot(adj,rev,p)
                    for s in range(n):
                        for t in range(n):
                            pred=certify(pivot,s,t)
                            truth,_=early_reachable(adj,s,t)
                            if pred is not None:self.assertEqual(pred,truth)
    def test_dp_exact_by_bruteforce(self):
        rng=random.Random(37)
        for n in range(1,9):
            for trial in range(30):
                queries=[(rng.randrange(n),rng.randrange(n)) for _ in range(25)]
                weights=[rng.randrange(1,10) for _ in queries]
                for k in range(min(3,n)+1):
                    chosen,value=choose_path_optimal(n,queries,k,weights)
                    optimal=float('inf')
                    for subset in itertools.combinations(range(n),k):
                        no_pivot=sum(w for (s,t),w in zip(queries,weights) if not any(min(s,t)<=p<=max(s,t) for p in subset))
                        optimal=min(optimal,no_pivot)
                    self.assertEqual(value,optimal)
                    self.assertEqual(len(chosen),k)
    def test_invalid_budget(self):
        with self.assertRaises(ValueError):choose_path_optimal(5,[],6)

if __name__=='__main__':unittest.main()
