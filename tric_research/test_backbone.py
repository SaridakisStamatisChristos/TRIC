import unittest, itertools, random
from tric import build_graph, certify, make_pivot
from backbone import backbone_intervals, optimize_intervals, optimize_backbone, greedy_backbone, verify_intervals
from backbone_hardness import make_max2sat_instance,assignment_score

class TestBackbone(unittest.TestCase):
    def test_backbone_characterization_random(self):
        rng=random.Random(20261021)
        count=0;has_two=False
        for length in range(2,8):
            for trial in range(38):
                n=length+rng.randrange(0,5)
                edges=[(i,i+1) for i in range(length-1)]
                # Add off-spine sources/sinks and forward DAG arcs using
                # interleaved topological coordinates to guarantee acyclicity.
                topo=list(range(length))
                for j in range(length,n):
                    topo.insert(rng.randrange(0,len(topo)+1),j)
                for i,u in enumerate(topo):
                    for v in topo[i+1:]:
                        if rng.random()<0.20:edges.append((u,v))
                adj,rev=build_graph(n,edges)
                qs=[(s,t) for s in range(n) for t in range(n)]
                regions=backbone_intervals(adj,rev,list(range(length)),qs)
                count+=verify_intervals(adj,rev,list(range(length)),qs)
                if any(len(z)==2 for z in regions):has_two=True
        self.assertGreater(count,2000)
        self.assertTrue(has_two)

    def test_optimizer_vs_bruteforce(self):
        rng=random.Random(50123)
        for n in range(2,9):
            for rep in range(80):
                intervals=[];weights=[]
                for _ in range(8):
                    raw=[]
                    for _ in range(rng.randrange(3)):
                        a,b=sorted((rng.randrange(n),rng.randrange(n)))
                        raw.append((a,b))
                    raw.sort()
                    merged=[]
                    for a,b in raw:
                        if merged and a<=merged[-1][1]+1:
                            merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
                        else:merged.append((a,b))
                    intervals.append(tuple(merged));weights.append(rng.randrange(0,8))
                for k in range(min(3,n)+1):
                    positions,uncovered,r=optimize_intervals(n,intervals,weights,k)
                    oracle=min(sum(w for seg,w in zip(intervals,weights)
                                    if not any(a<=p<=b for a,b in seg for p in subset))
                               for subset in itertools.combinations(range(n),k))
                    self.assertEqual(uncovered,oracle)
                    self.assertEqual(len(positions),k)

    def test_reduction_assignment_correspondence(self):
        rng=random.Random(8401)
        for nvars in range(1,5):
            for rep in range(40):
                cls=[];ws=[]
                for _ in range(1+rep%6):
                    cl=((rng.randrange(nvars),bool(rng.randrange(2))),
                        (rng.randrange(nvars),bool(rng.randrange(2))))
                    cls.append(cl);ws.append(rng.randrange(1,5))
                adj,rev,backbone,qs,weights,M=make_max2sat_instance(nvars,cls,ws)
                regs=backbone_intervals(adj,rev,backbone,qs)
                for cl,reg in zip(cls,regs[nvars:]):
                    pts=sorted({2*v+int(pos) for v,pos in cl})
                    self.assertEqual([p for p in backbone if any(a<=p<=b for a,b in reg)],pts)
                for assignment in itertools.product((False,True),repeat=nvars):
                    pivots={2*i+int(truth) for i,truth in enumerate(assignment)}
                    coverage=sum(w for reg,w in zip(regs,weights)
                                 if any(a<=p<=b for a,b in reg for p in pivots))
                    self.assertEqual(coverage,nvars*M+assignment_score(assignment,cls,ws))
                if nvars<=3 and len(cls)<=6:
                    best=max(assignment_score(bits,cls,ws) for bits in itertools.product((False,True),repeat=nvars))
                    oracle=max(sum(w for reg,w in zip(regs,weights)
                                    if any(a<=p<=b for a,b in reg for p in subset))
                               for subset in itertools.combinations(range(2*nvars),nvars))
                    self.assertEqual(oracle,nvars*M+best)

    def test_graph_optimizer_bruteforce(self):
        rng=random.Random(101)
        for nvars in range(2,4):
            for rep in range(8):
                clauses=[((rng.randrange(nvars),bool(rng.randrange(2))),
                          (rng.randrange(nvars),bool(rng.randrange(2)))) for _ in range(4)]
                adj,rev,bb,qs,ws,M=make_max2sat_instance(nvars,clauses)
                chosen,uncov,r=optimize_backbone(adj,rev,bb,qs,ws,nvars)
                all_regions=backbone_intervals(adj,rev,bb,qs)
                oracle=min(sum(w for reg,w in zip(all_regions,ws)
                               if not any(a<=p<=b for a,b in reg for p in subset))
                           for subset in itertools.combinations(range(len(bb)),nvars))
                self.assertEqual(uncov,oracle)
                self.assertEqual(len(chosen),nvars)


class TestVertexCoverReduction(unittest.TestCase):
    def test_all_five_vertex_graphs(self):
        from backbone_hardness import make_vertex_cover_instance
        from tric import early_reachable
        for nv in range(1,6):
            potential=list(itertools.combinations(range(nv),2))
            for bit in range(1<<len(potential)):
                edges=[e for i,e in enumerate(potential) if (bit>>i)&1]
                adj,rev,bb,qs=make_vertex_cover_instance(nv,edges)
                intervals=backbone_intervals(adj,rev,bb,qs)
                for (u,v),region,q in zip(edges,intervals,qs):
                    self.assertEqual([p for p in bb if any(a<=p<=b for a,b in region)], [u,v])
                    self.assertFalse(early_reachable(adj,*q)[0])
                for k in range(nv+1):
                    oracle_cover=any(all(u in S or v in S for u,v in edges)
                                     for S in itertools.combinations(range(nv),k))
                    certificate_cover=any(all(any(a<=p<=b for a,b in region for p in S)
                                              for region in intervals)
                                          for S in itertools.combinations(range(nv),k))
                    self.assertEqual(oracle_cover,certificate_cover)

class TestLinearExtraction(unittest.TestCase):
    def test_fast_vs_reference_and_offbackbone_invariant(self):
        from backbone import backbone_intervals_fast
        rng=random.Random(99111)
        count=0
        for h in range(1,11):
            for _ in range(80):
                n=h+rng.randrange(0,7)
                backbone=list(range(h))
                topo=backbone[:]
                for x in range(h,n):topo.insert(rng.randrange(len(topo)+1),x)
                edges=[(i,i+1) for i in range(h-1)]
                edges.extend((u,v) for i,u in enumerate(topo) for v in topo[i+1:] if rng.random()<0.16)
                adj,rev=build_graph(n,edges)
                qs=[(s,t) for s in range(n) for t in range(n)]
                truth=backbone_intervals(adj,rev,backbone,qs)
                fast=backbone_intervals_fast(adj,rev,backbone,qs)
                self.assertEqual(fast,truth)
                for (s,t),region in zip(qs,fast):
                    if s in backbone or t in backbone:
                        self.assertLessEqual(len(region),1)
                count+=len(qs)
        self.assertGreater(count,20000)

if __name__=='__main__':unittest.main()
