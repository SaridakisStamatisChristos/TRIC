"""Independent full-reachability oracle tests for SCC backbone optimization."""
import itertools
import random
import unittest

from tric import build_graph, make_pivot, certify, early_reachable
from backbone import backbone_intervals, optimize_intervals
from backbone_scc import prepare_scc_backbone, optimize_scc_backbone


class TestSCCBackbone(unittest.TestCase):
    def assert_exact(self, adj, rev, spine):
        idx = prepare_scc_backbone(adj, spine)
        qs = [(s, t) for s in range(len(adj)) for t in range(len(adj))]
        signatures = idx.intervals(qs)
        self.assertEqual(len(signatures), len(qs))
        offspine = len(set(idx.component)) - len(idx.spine_component)
        disjunctive = {sig for sig in signatures if len(sig) == 2}
        self.assertLessEqual(len(disjunctive), offspine * (offspine - 1) // 2)
        # Compare against direct, independent, whole-graph pivot reachability.
        all_pivots = [make_pivot(adj, rev, p) for p in spine]
        for q, signature in zip(qs, signatures):
            for p, oracle in zip(spine, all_pivots):
                self.assertEqual(idx.covered_by(signature, p),
                                 certify(oracle, *q) is not None,
                                 (spine, q, signature, p))
                c = certify(oracle, *q)
                if c is not None:
                    self.assertEqual(c, early_reachable(adj, *q)[0])
        # Recompute a different way (Phase III non-SCC extractor).
        old = backbone_intervals(adj, rev, spine, qs)
        for query, a, b in zip(qs, signatures, old):
            for p in spine:
                j = spine.index(p)
                self.assertEqual(idx.covered_by(a, p), any(x <= j <= y for x, y in b), query)
        return idx

    def test_exhaustive_four_vertex_cyclic_graphs(self):
        n = 4
        fixed = {(0, 1), (1, 2)}
        other = [(u, v) for u in range(n) for v in range(n)
                 if u != v and (u, v) not in fixed]
        for mask in range(1 << len(other)):
            edges = list(fixed) + [arc for bit, arc in enumerate(other) if mask & (1 << bit)]
            adj, rev = build_graph(n, edges)
            self.assert_exact(adj, rev, (0, 1, 2))

    def test_weighted_optimum_and_redundant_backbone_vertices(self):
        rng = random.Random(20261021)
        for n in range(3, 9):
            for _ in range(55):
                h = rng.randrange(2, min(n, 6) + 1)
                spine = tuple(range(h))
                edges = [(i, i + 1) for i in range(h - 1)]
                edges += [(u, v) for u in range(n) for v in range(n)
                          if u != v and rng.random() < 0.2]
                adj, rev = build_graph(n, edges)
                idx = prepare_scc_backbone(adj, spine)
                queries = [(rng.randrange(n), rng.randrange(n)) for _ in range(9)]
                weights = [rng.randrange(0, 9) for _ in queries]
                for k in range(h + 1):
                    chosen, uncovered, r = optimize_scc_backbone(
                        adj, spine, queries, weights, k)
                    self.assertEqual(len(chosen), k)
                    self.assertEqual(len(set(chosen)), k)
                    oracle = min(
                        sum(w for q, w in zip(queries, weights)
                            if not any(certify(make_pivot(adj, rev, p), *q) is not None
                                       for p in subset))
                        for subset in itertools.combinations(spine, k))
                    self.assertEqual(oracle, uncovered)

    def test_backbone_vertex_repetition_in_one_scc(self):
        adj, rev = build_graph(5, [(0, 1), (1, 2), (2, 3), (3, 1), (3, 4)])
        idx = self.assert_exact(adj, rev, (0, 1, 2, 3))
        self.assertEqual(len(idx.representatives), 2)
        selected, uncov, _ = optimize_scc_backbone(
            adj, (0, 1, 2, 3), [(4, 0), (0, 4), (2, 4)], [3, 2, 1], 4)
        self.assertEqual(len(selected), 4)
        self.assertEqual(set(selected), {0, 1, 2, 3})

    def test_invalid_inputs_and_large_depth(self):
        for adj, spine in [([[1], [0]], [0, 1, 0]),
                           ([[2], []], [0, 1]),
                           ([[99], []], [0]),
                           ([[]], [])]:
            with self.assertRaises(ValueError):
                prepare_scc_backbone(adj, spine)
        n = 3500
        adj = [[i + 1] if i + 1 < n else [] for i in range(n)]
        adj[-1].append(0)
        index = prepare_scc_backbone(adj, list(range(n)))
        self.assertEqual(len(index.representatives), 1)
        self.assertEqual(index.intervals([(0, n - 1), (n - 1, 0)]), [((0, 0),), ((0, 0),)])

if __name__ == '__main__':
    unittest.main()
