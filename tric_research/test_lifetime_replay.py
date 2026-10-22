"""Independent exactness and corrupted-evidence tests for measured batches."""
import copy
import itertools
import json
import random
import subprocess
import tempfile
import unittest
from pathlib import Path

from benchmark_lifetime import summarize
from benchmark_native import build_executable, serialize_native
from stratified_queries import _reachable_vertices


class LifetimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.exe, _, _ = build_executable(cls.tmp.name, optimization='-O2')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_case(self, adj, queries, train=None, reps=3):
        train = queries[:15] if train is None else train
        vertices = list(range(min(len(adj), 3)))
        data = serialize_native(adj, vertices, {'Ordered': list(range(len(vertices)))}, queries, train)
        proc = subprocess.run([str(self.exe), str(reps), '0', '--lifetime'],
                              input=data, capture_output=True, timeout=60)
        return proc

    def verify(self, adj, queries):
        proc = self.run_case(adj, queries)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        raw = json.loads(proc.stdout)
        flags = [_reachable_vertices(adj, s) for s in range(len(adj))]
        self.assertEqual(raw['oracle_positive_count'], sum(flags[s][t] for s, t in queries))
        self.assertEqual(raw['verified_answers_per_method'], len(queries))
        summarize(raw)
        return raw

    def test_all_three_vertex_graphs_and_pairs(self):
        edges = [(u, v) for u in range(3) for v in range(3) if u != v]
        for bits in range(1 << len(edges)):
            adj = [[] for _ in range(3)]
            for i, (u, v) in enumerate(edges):
                if bits >> i & 1:
                    adj[u].append(v)
            self.verify(adj, list(itertools.product(range(3), repeat=2)))

    def test_batches_cycles_duplicates_disconnected_and_self_pairs(self):
        rng = random.Random(1919)
        adj = [[v for v in range(70) if rng.random() < .02] for _ in range(70)]
        queries = [(rng.randrange(70), rng.randrange(70)) for _ in range(1201)]
        raw = self.verify(adj, queries)
        self.assertEqual([r['queries'] for r in summarize(raw)], [1200, 1201])

    def test_corrupt_evidence_rejected(self):
        raw = self.verify([[1], [2], [], []], [(0, 2), (2, 0), (3, 3)] * 6)
        mutations = [
            lambda r: r['batches'].pop(),
            lambda r: r['batches'].append(copy.deepcopy(r['batches'][0])),
            lambda r: r.update(training_ns=float('nan')),
            lambda r: r.update(verified_answers_per_method=0),
            lambda r: r['batches'][0].update(first_mode='selector'),
            lambda r: r['batches'][0]['selector'].update(checksum=-1),
            lambda r: r['batches'][0]['selector'].update(probes=999),
            lambda r: r['batches'][0]['selector'].update(total_ns=0),
            lambda r: r['batches'][0].update(queries=1000000),
        ]
        for mutate in mutations:
            changed = copy.deepcopy(raw)
            mutate(changed)
            with self.assertRaises(ValueError):
                summarize(changed)

    def test_measured_savings_and_ties(self):
        raw = self.verify([[1], []], [(0, 1), (1, 0)])
        raw['training_ns'] = 100
        for r in raw['batches']:
            r['selector']['total_ns'] = 200
            r['topo']['total_ns'] = 300  # equality is not a net win
            r['bidir']['total_ns'] = 301
        out = summarize(raw)[0]
        self.assertEqual(out['topo']['paired_net_wins_after_fit'], 0)
        self.assertEqual(out['topo']['median_paired_net_savings_after_fit_ns'], 0)
        self.assertEqual(out['bidir']['paired_net_wins_after_fit'], 3)
        self.assertEqual(out['bidir']['median_paired_net_savings_after_fit_ns'], 1)

    def test_requires_training_and_balanced_repetitions(self):
        self.assertNotEqual(self.run_case([[1], []], [(0, 1)], train=[]).returncode, 0)
        self.assertNotEqual(self.run_case([[1], []], [(0, 1)], reps=4).returncode, 0)


if __name__ == '__main__':
    unittest.main()
