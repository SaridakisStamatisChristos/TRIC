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
                        str(ROOT/'native_runtime_check.cpp'),'-o',str(cls.exe)],check=True)
    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()
    def run_graph(self,g,qs,cap=1048576,mode="partitioned"):
        p = subprocess.run([str(self.exe),mode,str(cap),'2'],
                           input=serialize(g,qs),text=True,capture_output=True,check=True,timeout=40)
        result=json.loads(p.stdout)
        self.assertEqual(result['oracle_verified_pairs'],len(qs))
        self.assertLessEqual(result['table_bytes'],cap)
        return result
    def test_exhaustive_including_loops(self):
        p=subprocess.run([str(self.exe),'--self-test'],capture_output=True,text=True,check=True,timeout=40)
        data=json.loads(p.stdout)
        self.assertEqual(data['exhaustive_checks'],512*4*9)
        self.assertEqual(data['interval_checks'],4096*3*6*8)
        self.assertGreater(data['interval_indexes'],4096)
        self.assertEqual(data['forest_checks'],720*2*12*12)
        self.assertEqual(data['packed_checks'],6**4)
        self.assertEqual(data['cross_chain_checks'],2*3*160*160)
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
        self.assertEqual(data['interval_partitions'],1)
        self.assertEqual(data['indexed_components'],n)
        refused=self.run_graph(g,qs,100)
        self.assertEqual(refused['indexed_components'],0)
        self.assertEqual(refused['table_bytes'],0)

    def test_fragmented_intervals_fall_back_to_compressed_words(self):
        r=random.Random(20261023)
        n=1024
        g=[sorted(r.sample(range(512,n),32)) for _ in range(512)]+[[] for _ in range(512)]
        qs=[(r.randrange(n),r.randrange(n)) for _ in range(700)]
        data=self.run_graph(g,qs,98304)
        self.assertEqual(data['compressed_partitions'],1)
        self.assertEqual(data['interval_partitions'],0)
        self.assertEqual(data['indexed_components'],n)

    def test_interval_row_labels_with_relabelled_scc_aliases(self):
        # Different original vertices share one SCC row; cross-tree positive
        # pairs exercise the inline interval metadata after all certificates.
        n=512;r=random.Random(20261026);perm=list(range(n));r.shuffle(perm)
        original=[[] for _ in range(n)]
        original[0]=list(range(1,n));original[1]=[2];original[2]=[0]
        for u in range(3,128):original[u]=[128+(u*17)%384,128+(u*53+7)%384]
        g=[[] for _ in range(n)]
        for u,row in enumerate(original):g[perm[u]]=[perm[v] for v in row]
        qs=[(perm[u],perm[v]) for u in range(128) for v in range(0,n,7)]
        for mode in ('partitioned','auto'):
            data=self.run_graph(g,qs,16000,mode)
            if mode=='partitioned':self.assertEqual(data['interval_partitions'],1)
        self.run_graph(g,qs,0)

    def test_large_interval_index_without_dense_matrix(self):
        n=100000
        g=[list(range(1,n))]+[[] for _ in range(n-1)]
        data=self.run_graph(g,[(0,n-1),(n-1,0),(123,124),(1,1)],2*1024*1024)
        self.assertEqual(data['interval_partitions'],1)
        self.assertEqual(data['indexed_components'],n)
        # One interval per SCC remains; its construction directory is released.
        self.assertEqual(data['table_bytes'],8*n)
        self.assertLess(data['retained_capacity_bytes'],40*n+1024)

    def test_cached_interval_residuals_all_pairs(self):
        # Unequal reachable sink blocks, with gaps on both sides, exercise
        # cached ranges that need not be the first or last sorted interval.
        # Permutations and SCC aliases prevent dependence on original IDs.
        n=512
        original=[[] for _ in range(n)]
        original[0]=list(range(1,n))
        for u in range(1,64):
            for start,width in ((128+u%17,1),(192+u%23,3),
                                (288+u%19,11),(416+u%13,5)):
                original[u].extend(range(start,start+width))
        original[64]=[65];original[65]=[64,128,193,300,420]
        r=random.Random(29017);perm=list(range(n));r.shuffle(perm)
        g=[[] for _ in range(n)]
        for u,row in enumerate(original):g[perm[u]]=[perm[v] for v in row]
        queries=[(u,v) for u in range(n) for v in range(n)]
        data=self.run_graph(g,queries,16000)
        self.assertEqual(data['interval_partitions'],1)
        self.assertEqual(data['indexed_components'],n-1)

    def test_interval_failure_rolls_back_between_partitions(self):
        r=random.Random(20261023)
        star=[list(range(1,1024))]+[[] for _ in range(1023)]
        fragmented=[sorted(r.sample(range(512,1024),32)) for _ in range(512)]+[[] for _ in range(512)]
        g=[]
        for part in (star,fragmented,star):
            offset=len(g)
            g.extend([[v+offset for v in row] for row in part])
        qs=[(r.randrange(len(g)),r.randrange(len(g))) for _ in range(700)]
        qs.extend([(0,1023),(2048,3071),(1024,fragmented[0][0]+1024)])
        data=self.run_graph(g,qs,65536)
        self.assertEqual(data['interval_partitions'],2)
        self.assertEqual(data['indexed_components'],2048)

    def test_saturated_depths_preserve_long_path_reachability(self):
        n=140000
        g=[[u+1] if u+1<n else [] for u in range(n)]
        qs=[(66000,70000),(70000,66000),(0,n-1),(n-1,n-1)]
        for cap in (0,4*n):
            self.run_graph(g,qs,cap)
            self.run_graph(g,qs,cap,mode='auto')
        # A deep diamond makes one branch reach a previously finished subtree.
        # Both level fields saturate, so a positive query must survive search
        # pruning instead of being answered by the DFS positive certificate.
        prefix=66000;target=prefix+3;n=target+66001
        g=[[u+1] if u+1<n else [] for u in range(n)]
        g[prefix]=[prefix+1,prefix+2]
        g[prefix+1]=[target];g[prefix+2]=[target]
        qs=[(u,v) for u in (prefix+1,prefix+2) for v in (target,target+100)]
        for mode in ('partitioned','auto'):
            self.run_graph(g,qs,0,mode=mode)

    def test_auto_routes_only_on_graph_and_cap(self):
        g=[list(range(1,130))]+[[] for _ in range(129)]
        qs=[(0,129),(128,129),(1,1),(1,0)]
        direct=self.run_graph(g,qs,1048576,mode='auto')
        self.assertTrue(direct['uses_direct_closure'])
        n=1024;g=[list(range(1,n))]+[[] for _ in range(n-1)]
        compressed=self.run_graph(g,qs,65536,mode='auto')
        self.assertFalse(compressed['uses_direct_closure'])
        self.assertTrue(compressed['uses_forest_index'])
        self.assertEqual(compressed['table_bytes'],0)

    def test_invalid_edges_queries_and_options_rejected(self):
        for raw in ('2 1 1\n0 2\n0 1\n','2 0 1\n-1 0\n'):
            p=subprocess.run([str(self.exe),'partitioned','100','1'],input=raw,text=True,capture_output=True)
            self.assertNotEqual(p.returncode,0)
    def test_original_bfl_adapter_and_source_provenance(self):
        import hashlib
        raw=(ROOT/'third_party/bfl/main.cpp').read_bytes()
        self.assertEqual(hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest(),
                         'f1a75eecbb74bdc5370282328283bbd4c250814e')
        exe=Path(self.tmp.name)/'bfl'
        subprocess.run(['g++','-std=c++17','-O2','-DTRIC_WITH_BFL',
                        str(ROOT/'native_compare_bench.cpp'),'-o',str(exe)],check=True,capture_output=True)
        r=random.Random(20261023)
        for n in (3,40,160):
            for cyclic in (False,True):
                g=[[v for v in range(n) if (cyclic or u<v) and r.random()<0.08] for u in range(n)]
                qs=[(u,v) for u in range(n) for v in range(n)]
                result=subprocess.run([str(exe),'bfl','0','1'],input=serialize(g,qs),text=True,
                                      capture_output=True,check=True,timeout=40)
                data=json.loads(result.stdout.splitlines()[-1])
                self.assertEqual(data['oracle_verified_pairs'],n*n)

    def test_forward_and_reverse_forests_with_scc_aliases_and_cross_roots(self):
        r=random.Random(20261028)
        for reverse in (False,True):
            n=400;g=[[] for _ in range(2*n)];perm=list(range(2*n));r.shuffle(perm)
            for u in range(n):
                g[perm[2*u]].append(perm[2*u+1]);g[perm[2*u+1]].append(perm[2*u])
                if u and u%17:
                    p=r.randrange(u);a,b=(u,p) if reverse else (p,u)
                    g[perm[2*a]].extend([perm[2*b],perm[2*b]])
            qs=[(u,v) for u in range(2*n) for v in range(0,2*n,11)]
            data=self.run_graph(g,qs,0,mode='auto')
            self.assertTrue(data['uses_forest_index'])
            self.assertEqual(data['table_bytes'],0)
            self.assertLess(data['retained_capacity_bytes'],8*len(g)+1024)
        # Both degree conditions fail: exact general fallback is mandatory.
        g=[[1,2],[3],[3],[]]
        data=self.run_graph(g,[(a,b) for a in range(4) for b in range(4)],0,mode='auto')
        self.assertFalse(data['uses_forest_index'])

    def test_original_pruned_labeling_adapters_and_provenance(self):
        import hashlib
        provenance=json.loads((ROOT/'third_party/pruned_labeling/PROVENANCE.json').read_text())
        for name,expected in provenance['files'].items():
            raw=(ROOT/'third_party/pruned_labeling'/name).read_bytes()
            self.assertEqual(hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest(),expected)
        exe=Path(self.tmp.name)/'pruned'
        subprocess.run(['g++','-std=c++17','-O2','-DTRIC_WITH_PRUNED_LABELING',
                        str(ROOT/'native_compare_bench.cpp'),'-o',str(exe)],check=True,capture_output=True)
        r=random.Random(20261028)
        for n in (1,3,40,160):
            for cyclic in (False,True):
                g=[[v for v in range(n) if (cyclic or u<v) and r.random()<0.08] for u in range(n)]
                qs=[(u,v) for u in range(n) for v in range(n)]
                for mode in ('pll','ppl'):
                    result=subprocess.run([str(exe),mode,'0','1'],input=serialize(g,qs),text=True,
                                          capture_output=True,check=True,timeout=40)
                    data=json.loads(result.stdout.splitlines()[-1])
                    self.assertEqual(data['oracle_verified_pairs'],n*n)
                    self.assertGreater(data['upstream_reported_label_bytes'],0)

    def test_comparison_runner_verifies_inputs_and_all_arms(self):
        import gzip
        import hashlib
        raw=serialize([[1],[],[]],[(0,1),(1,0),(2,2)])
        fixture={'dataset':'smoke','graph':{'vertices':3,'arcs':[[0,1]]},
                 'cases':[{'seed':1,'stratum':'uniform','queries':[[0,1],[1,0],[2,2]],
                           'native_input_sha256':hashlib.sha256(raw.encode()).hexdigest()}]}
        other=serialize([[1],[],[]],[(0,2),(2,0)])
        fixture['cases'].append({'seed':2,'stratum':'negative','queries':[[0,2],[2,0]],
                                 'native_input_sha256':hashlib.sha256(other.encode()).hexdigest()})
        folder=Path(self.tmp.name)/'fixtures';folder.mkdir(exist_ok=True)
        path=folder/'smoke.json.gz';path.write_bytes(gzip.compress(json.dumps(fixture).encode()))
        output=Path(self.tmp.name)/'comparison'
        command=['python',str(ROOT/'benchmark_native_changes.py'),'--fixtures',str(folder),'--output',str(output),
                 '--arm','auto',str(self.exe),'auto','--arm','partitioned',str(self.exe),'partitioned',
                 '--trials','2','--horizons','1']
        subprocess.run(command,capture_output=True,text=True,check=True,timeout=40)
        result=json.loads(gzip.decompress((output/'smoke.json.gz').read_bytes()))
        self.assertEqual(len(result),2)
        manifest=json.loads((output/'manifest.json').read_text())
        self.assertTrue(manifest['complete'])
        self.assertEqual(manifest['files'][0]['cells'],2)
        self.assertEqual(manifest['files'][0]['sha256'],hashlib.sha256((output/'smoke.json.gz').read_bytes()).hexdigest())
        for cell,count in zip(result,(3,2)):
            for rows in cell['rows'].values():
                self.assertEqual(len(rows),2)
                self.assertTrue(all(row['oracle_verified_pairs']==count for row in rows))
        duplicate=subprocess.run(command,capture_output=True,text=True,timeout=40)
        self.assertNotEqual(duplicate.returncode,0)
        self.assertIn('output directory must be empty',duplicate.stderr)
        command[command.index('--output')+1]=str(output.with_name('comparison-corrupt'))
        fixture['cases'][0]['native_input_sha256']='0'*64
        path.write_bytes(gzip.compress(json.dumps(fixture).encode()))
        result=subprocess.run(command,capture_output=True,text=True,timeout=40)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('fixture differs',result.stderr)

    def test_empty_and_invalid_public_api(self):
        code = r'''
#include "partitioned_reachability.h"
#include "tric_reachability.h"
int main(){
  using G=std::vector<std::vector<int>>;
  PartitionedReachability empty(G{},0);
  if(empty.components()!=0 || empty.table_bytes()!=0)return 1;
  try {empty.reaches(0,0);return 2;}catch(const std::out_of_range&){}
  try {PartitionedReachability bad(G{{-1}},0);return 3;}catch(const std::out_of_range&){}
  PartitionedReachability one(G{{}},0);
  if(!one.reaches(0,0))return 4;
  try {one.reaches(-1,0);return 5;}catch(const std::out_of_range&){}
  TricReachability auto_empty(G{},0);
  try {auto_empty.reaches(0,0);return 7;}catch(const std::out_of_range&){}
  TricReachability no_scratch(G{{1},{}},0,0);
  if(no_scratch.uses_forest_index() || !no_scratch.reaches(0,1))return 12;
  TricReachability forest_tiny_scratch(G{{1},{}},0,39);
  if(forest_tiny_scratch.uses_forest_index() || !forest_tiny_scratch.reaches(0,1))return 13;
  TricReachability exact_scratch(G{{1},{}},0,40);
  if(!exact_scratch.uses_forest_index() || !exact_scratch.reaches(0,1))return 14;
  TricReachability auto_one(G{{}},8);
  if(!auto_one.uses_direct_closure() || !auto_one.reaches(0,0))return 8;
  try {auto_one.reaches(-1,0);return 9;}catch(const std::out_of_range&){}
  try {TricReachability bad(G{{1}},8);return 10;}catch(const std::out_of_range&){}
  G wide(1024);for(int i=1;i<1024;++i)wide[0].push_back(i);
  PartitionedReachability tiny_scratch(wide,65536,16);
  if(tiny_scratch.interval_partitions()!=1 || tiny_scratch.indexed_components()!=1024 || !tiny_scratch.reaches(0,1023))return 11;
  PartitionedReachability refused(wide,65536,0);
  if(refused.indexed_components()!=0 || refused.table_bytes()!=0 || !refused.reaches(0,1023))return 6;
}'''
        source=Path(self.tmp.name)/'api.cpp';source.write_text(code)
        exe=source.with_suffix('')
        subprocess.run(['g++','-std=c++17','-O2','-I',str(ROOT),str(source),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)

if __name__=='__main__':unittest.main()
