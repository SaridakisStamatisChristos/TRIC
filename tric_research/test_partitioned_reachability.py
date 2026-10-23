"""Independent BFS, exhaustive digraphs, memory refusal and representation tests."""
import json
import random
import subprocess
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent

def serialize(graph, queries):
    edges = [(u,v) for u,row in enumerate(graph) for v in row]
    return '\n'.join([f'{len(graph)} {len(edges)} {len(queries)}',
                      *(f'{u} {v}' for u,v in edges),
                      *(f'{u} {v}' for u,v in queries)])+'\n'

class PartitionedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.exe = Path(cls.tmp.name)/'bench'
        subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Wpedantic',
                        str(ROOT/'partitioned_bench.cpp'),'-o',str(cls.exe)],check=True)
    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()
    def run_graph(self,g,qs,cap=1048576):
        p = subprocess.run([str(self.exe),'partitioned',str(cap),'2'],
                           input=serialize(g,qs),text=True,capture_output=True,check=True,timeout=40)
        result=json.loads(p.stdout)
        self.assertEqual(result['oracle_verified_pairs'],len(qs))
        self.assertLessEqual(result['table_bytes'],cap)
        return result
    def test_exhaustive_including_loops(self):
        p=subprocess.run([str(self.exe),'--self-test'],capture_output=True,text=True,check=True,timeout=40)
        self.assertEqual(json.loads(p.stdout)['exhaustive_checks'],512*4*9)
    def test_random_relabelled_cyclic_and_acyclic(self):
        r=random.Random(20261023)
        for n in (9,40,130):
            for density in (0.01,0.06,0.3):
                for dag in (True,False):
                    perm=list(range(n));r.shuffle(perm)
                    g=[[] for _ in range(n)]
                    for u in range(n):
                        for v in range(n):
                            if (not dag or u<v) and r.random()<density:g[perm[u]].append(perm[v])
                    qs=[(r.randrange(n),r.randrange(n)) for _ in range(150)]
                    for cap in (0,64,1048576):self.run_graph(g,qs,cap)
    def test_long_chain_selects_chain_labels(self):
        n=20000;g=[[i+1] if i+1<n else [] for i in range(n)]
        data=self.run_graph(g,[(0,n-1),(n-1,0),(123,123),(222,223)],4*n)
        self.assertEqual(data['chain_partitions'],1)
        self.assertEqual(data['table_bytes'],4*n)
        self.assertEqual(data['indexed_components'],n)
    def test_wide_connected_graph_selects_bitsets(self):
        n=130;g=[list(range(1,n))]+[[] for _ in range(n-1)]
        qs=[(u,v) for u in range(0,n,3) for v in range(0,n,7)]
        data=self.run_graph(g,qs)
        self.assertEqual(data['bit_partitions'],1)
        self.assertEqual(data['table_bytes'],n*3*8)
    def test_partition_local_budget_and_partial_fallback(self):
        g=[[i+1] if i%10<9 else [] for i in range(100)]
        qs=[(u,v) for u in range(100) for v in range(0,100,7)]
        data=self.run_graph(g,qs,80)
        self.assertEqual(data['partitions'],10)
        self.assertEqual(data['chain_partitions'],2)
        self.assertEqual(data['indexed_components'],20)
        self.assertEqual(data['table_bytes'],80)
    def test_parallel_edges_transitive_arcs_sccs_isolates(self):
        g=[[v for v in range(u+1,80) for _ in range(2)] for u in range(80)]+[[],[]]
        qs=[(u,v) for u in range(82) for v in range(0,82,3)]
        data=self.run_graph(g,qs)
        self.assertGreater(data['skipped_arcs'],data['merged_arcs'])
        g[79]=[0]
        data=self.run_graph(g,qs,0)
        self.assertEqual(data['components'],3)
        self.assertEqual(data['table_bytes'],0)
        self.assertEqual(data['indexed_components'],3)
    def test_compressed_rows_and_refusal(self):
        n=1024;g=[list(range(1,n))]+[[] for _ in range(n-1)]
        qs=[(u,v) for u in range(0,n,17) for v in range(0,n,31)]
        data=self.run_graph(g,qs,65536)
        self.assertEqual(data['compressed_partitions'],1)
        self.assertEqual(data['indexed_components'],n)
        refused=self.run_graph(g,qs,100)
        self.assertEqual(refused['indexed_components'],0)
        self.assertEqual(refused['table_bytes'],0)

    def test_invalid_edges_queries_and_options_rejected(self):
        for raw in ('2 1 1\n0 2\n0 1\n','2 0 1\n-1 0\n'):
            p=subprocess.run([str(self.exe),'partitioned','100','1'],input=raw,text=True,capture_output=True)
            self.assertNotEqual(p.returncode,0)
    def test_empty_and_invalid_public_api(self):
        code = r'''
#include "partitioned_reachability.h"
int main(){
  using G=std::vector<std::vector<int>>;
  PartitionedReachability empty(G{},0);
  if(empty.components()!=0 || empty.table_bytes()!=0)return 1;
  try {empty.reaches(0,0);return 2;}catch(const std::out_of_range&){}
  try {PartitionedReachability bad(G{{-1}},0);return 3;}catch(const std::out_of_range&){}
  PartitionedReachability one(G{{}},0);
  if(!one.reaches(0,0))return 4;
  try {one.reaches(-1,0);return 5;}catch(const std::out_of_range&){}
}'''
        source=Path(self.tmp.name)/'api.cpp';source.write_text(code)
        exe=source.with_suffix('')
        subprocess.run(['g++','-std=c++17','-O2','-I',str(ROOT),str(source),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)

if __name__=='__main__':unittest.main()
