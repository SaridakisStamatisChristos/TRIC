"""Independent checks for optional SCC transitive closure on C++ query plane."""
import json
import random
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def make_input(adj, queries):
    edges = [(u,v) for u, row in enumerate(adj) for v in row]
    chunks = [f'{len(adj)} {len(edges)} 0 {len(queries)}']
    chunks += [f'{u} {v}' for u,v in edges]
    chunks += ['', '1', 'BFS 0']
    chunks += [f'{s} {t}' for s,t in queries]
    return ('\n'.join(chunks) + '\n').encode()


class TestClosureIndex(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.exe = Path(cls.tmp.name)/'test_native'
        subprocess.run(['g++', '-std=c++17','-O2','-DNDEBUG','-Wall','-Wextra','-pedantic',
                        '-o', str(cls.exe), str(ROOT/'native_query_bench.cpp')],check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_native(self, adj, queries, cap):
        proc = subprocess.run([str(self.exe), '3', str(cap)],
                              input=make_input(adj, queries), capture_output=True, check=True, timeout=30)
        return json.loads(proc.stdout)

    def test_random_digraphs_bfs_oracle(self):
        rng = random.Random(26716)
        for n in (2, 5, 30, 90):
            for density in (0, 0.03, 0.25, 0.85):
                adj = [[v for v in range(n) if v!=u and rng.random()<density] for u in range(n)]
                q = [(rng.randrange(n), rng.randrange(n)) for _ in range(48)]
                o = self.run_native(adj, q, 1)
                c = o['closure']
                self.assertTrue(c['available'])
                self.assertEqual(c['timed_query_repeats'], 128)
                self.assertEqual(c['checksum'], o['policies'][0]['checksum'])
                self.assertLessEqual(c['index_matrix_bytes'], 1024*1024)

    def test_disabled_falls_back_without_crashing(self):
        adj = [[i+1] if i < 39 else [] for i in range(40)]
        q=[(0,39), (39,0), (13,13), (17,19)]
        o=self.run_native(adj,q,0)
        self.assertFalse(o['closure']['available'])
        self.assertEqual(o['closure']['index_matrix_bytes'],0)

    def test_budget_rejects_large_matrix(self):
        # Path components are all distinct; a 4,096 vertex path needs 2 MiB.
        n=4096
        adj=[[i+1] if i < n-1 else [] for i in range(n)]
        q=[(0,n-1),(n-1,0)]
        self.assertFalse(self.run_native(adj,q,1)['closure']['available'])
        o=self.run_native(adj,q,4)
        self.assertTrue(o['closure']['available'])
        self.assertEqual(o['closure']['components'],n)
        self.assertEqual(o['closure']['checksum'],o['policies'][0]['checksum'])

    def test_giant_scc_and_isolates(self):
        n=50
        adj=[[((u+1)%45)] if u<45 else [] for u in range(n)]
        queries=[(0,44),(44,0),(48,0),(0,48),(48,48),(46,47)]
        o=self.run_native(adj,queries,1)
        self.assertEqual(o['closure']['components'],6)
        self.assertEqual(o['closure']['checksum'],o['policies'][0]['checksum'])

if __name__ == '__main__':
    unittest.main()
