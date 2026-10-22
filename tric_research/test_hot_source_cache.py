"""Independent C++ tests for optional Phase XIX hot-source exact cache."""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CPP=r"""
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <stdexcept>
#include <utility>
#include <vector>
#include "hot_source_cache.h"
using G=std::vector<std::vector<int>>;
using Pair=std::pair<int,int>;
bool reference(const G& g,int a,int b){
  std::vector<unsigned char> seen(g.size(),0);
  std::vector<int> stack{a};seen[a]=1;
  while(!stack.empty()){
    int u=stack.back();stack.pop_back();
    for(int v:g[u])if(!seen[v]){seen[v]=1;stack.push_back(v);}
  }
  return seen[b];
}
int main(){
  // All 512 directed 3-vertex graphs including loops and cycles.
  for(unsigned mask=0;mask<(1U<<9);++mask){
    G graph(3);
    for(int a=0;a<3;++a)for(int b=0;b<3;++b)
      if(mask&(1U<<(a*3+b)))graph[a].push_back(b);
    std::vector<Pair> training;
    for(int s=0;s<3;++s)
      for(int j=0;j<3;++j)training.emplace_back(s,j);
    HotSourceCache cache(graph,training,3,1024,2);
    assert(cache.rows()==3);
    assert(cache.retained_bytes()<=1024);
    for(int s=0;s<3;++s)for(int t=0;t<3;++t){
      bool answer=false;
      assert(cache.lookup(s,t,answer));
      assert(answer==reference(graph,s,t));
    }
  }
  G graph(65);
  graph[0].push_back(64);graph[64].push_back(0);graph[0].push_back(1);
  // The first row has 16 data bytes, 65*4 direct-index bytes and 4
  // source-id bytes. Exact one-row budget, no room for second row.
  std::vector<Pair> training{{64,0},{64,1},{64,2},{0,64},{0,1}};
  HotSourceCache one(graph,training,2,280,2);
  assert(one.rows()==1);
  assert(one.sources()[0]==64);
  assert(one.retained_bytes()<=280);
  bool answer=false;
  assert(one.lookup(64,1,answer) && answer);
  assert(!one.lookup(0,1,answer));
  HotSourceCache zero(graph,training,2,0,2);
  assert(zero.rows()==0 && zero.retained_bytes()==0);
  assert(!zero.lookup(64,1,answer));
  // No heldout truth labels can influence source selection.
  HotSourceCache tie(graph,{{1,2},{0,2},{1,4},{0,4}},1,1024,2);
  assert(tie.sources()[0]==0);
  try{one.lookup(65,0,answer);assert(false);}catch(const std::out_of_range&){}
  try{HotSourceCache invalid(graph,{{65,0}},1,1024);assert(false);}
    catch(const std::invalid_argument&){}
  G bad(2);bad[0].push_back(5);
  try{HotSourceCache invalid(bad,{{0,0},{0,0}},1,1024);assert(false);}
    catch(const std::invalid_argument&){}
  return 0;
}
"""

class HotSourceIndexTests(unittest.TestCase):
    def test_exhaustive_and_budget(self):
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'verify.cpp'
            binary=Path(td)/'verify'
            source.write_text(CPP)
            subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra',
                            '-Wpedantic','-I',str(ROOT),str(source),'-o',str(binary)],
                           check=True,capture_output=True,text=True)
            subprocess.run([str(binary)],check=True,capture_output=True,text=True)

    def test_paired_benchmark_smoke(self):
        with tempfile.TemporaryDirectory() as td:
            dest=Path(td)/'out.json'
            subprocess.run(['python',str(ROOT/'benchmark_hot_source_cache.py'),
                            '--n','40','--training','120','--heldout','90',
                            '--sources','3','--seeds','1','--output',str(dest)],
                           check=True,capture_output=True,text=True)
            import json
            data=json.loads(dest.read_text())
            self.assertEqual(set(data['results'][0]['classes']),
                             {'matched_hot','uniform','shifted_hot'})
            for row in data['results'][0]['classes'].values():
                self.assertLessEqual(row['retained_bytes'],row['cap_bytes'])
                self.assertEqual(len(row['baseline_samples']),14)
                self.assertEqual(len(row['cache_samples']),14)

if __name__=='__main__':
    unittest.main()
