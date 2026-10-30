from pathlib import Path
import json,shutil,hashlib,subprocess,shlex
ROOT=Path('/workspace/scratch/750cc954fdb8/TRIC/tric_research');OUT=Path(__file__).resolve().parent
for arm in ('previous','csr','closure','buffers'):
 d=OUT/arm;d.mkdir(exist_ok=True)
 for p in ROOT.glob('*.h'):shutil.copyfile(p,d/p.name)
p=OUT/'csr/scc_decomposition.h';s=p.read_text();start=s.index('    std::vector<std::vector<int>> reverse(n);');end=s.index('    // Nonrecursive DFS',start)
s=s[:start]+'''    // Stable CSR transpose: preserve the predecessor order of push_back.
    std::vector<std::size_t> reverse_offsets(static_cast<std::size_t>(n)+1,0);
    for(int u=0;u<n;++u)for(int v:graph[u]) {
      if(v<0 || v>=n)throw std::out_of_range("edge endpoint");
      ++reverse_offsets[static_cast<std::size_t>(v)+1];
    }
    for(int v=0;v<n;++v) {
      if(reverse_offsets[v+1]>std::numeric_limits<std::size_t>::max()-reverse_offsets[v])
        throw std::length_error("too many graph edges");
      reverse_offsets[v+1]+=reverse_offsets[v];
    }
    std::vector<int> reverse_edges(reverse_offsets.back());
    {
      auto cursor=reverse_offsets;
      for(int u=0;u<n;++u)for(int v:graph[u])reverse_edges[cursor[v]++]=u;
    }
'''+s[end:]
s=s.replace('for(int v:reverse[u])if(component[v]<0){component[v]=count;stack.push_back(v);}', '''for(std::size_t edge=reverse_offsets[u];edge<reverse_offsets[u+1];++edge) {
          const int v=reverse_edges[edge];
          if(component[v]<0){component[v]=count;stack.push_back(v);}
        }''');p.write_text(s)
p=OUT/'closure/closure_index.h';s=p.read_text().replace('#include <queue>\n','').replace('    std::vector<int> indegree(components_,0);\n','');s=s.replace('if(a!=b){dag[a].push_back(b);++indegree[b];}', '''if(a!=b){
        if(a>=b)throw std::logic_error("SCC order is not topological");
        dag[a].push_back(b);
      }''');start=s.index('    std::queue<int> ready;');end=s.index('    bits_.assign',start)
s=s[:start]+'''    for(auto& row:dag) {
      std::sort(row.begin(),row.end());
      row.erase(std::unique(row.begin(),row.end()),row.end());
    }
'''+s[end:];s=s.replace('    for(auto it=topo.rbegin();it!=topo.rend();++it){\n      int a=*it;','    for(int a=components_-1;a>=0;--a){');s=s.replace('      for(int b:dag[a]){\n        const auto *src=', '''      for(int b:dag[a]){
        // Membership obtained from complete child rows proves the child's
        // entire closure is already present. Self cannot cover a distinct b.
        if((dst[b>>6]>>(b&63))&1U)continue;
        const auto *src=''');s=s.replace('for(std::size_t w=0;w<words_;++w)dst[w]|=src[w];','for(std::size_t w=static_cast<std::size_t>(b)>>6;w<words_;++w)dst[w]|=src[w];');p.write_text(s)
p=OUT/'buffers/partitioned_reachability.h';s=p.read_text();old='''const std::size_t limit=std::min((remaining-static_cast<std::size_t>(row_bytes))/sizeof(Interval),
                                      index_scratch_cap_bytes/(2*sizeof(Interval)));''';new='''// A union over this partition contains at most one interval per SCC.
      // Cap reserve requests by that semantic bound, without changing admission.
      const std::size_t limit=std::min({size,
          (remaining-static_cast<std::size_t>(row_bytes))/sizeof(Interval),
          index_scratch_cap_bytes/(2*sizeof(Interval))});''';assert old in s;s=s.replace(old,new);p.write_text(s)
# Generated harness: repeated destruction/construction on one already parsed graph.
s=(ROOT/'native_compare_bench.cpp').read_text();s=s.replace('    if(mode=="auto")automatic=std::make_unique<TricReachability>(g,cap);','''    std::uint64_t build_count=0;volatile std::uint64_t build_witness=0;
    if(mode=="auto") {
      do {
        automatic.reset();
        automatic=std::make_unique<TricReachability>(g,cap);
        build_witness=build_witness+automatic->table_bytes()+automatic->retained_bytes();
        ++build_count;
        if(build_count==1000000)throw std::runtime_error("construction batch limit");
      } while(build_count<2 || thread_cpu_ns()-cpu_parsed<200000000ULL);
    }''');s=s.replace('      <<",\\\"build_ns\\\":"<<ns(parsed,built)', '      <<",\\\"build_count\\\":"<<build_count<<",\\\"build_witness\\\":"<<build_witness\n      <<",\\\"build_ns\\\":"<<ns(parsed,built)');assert '<<build_count' in s;(OUT/'native_compare_bench.cpp').write_text(s)
protocol={'baseline_commit':'02a91849193e12266785ecfd1d49cd8d87b458f2','arms':['previous','csr','closure','buffers','identical'],'trials':5,'cpu':1,'target_build_cpu_ns':200000000,'cap':2097152,'gates':{'median_build_cpu_ratio_min':1.05,'minimum_build_cpu_ratio':.90,'null_control_band':[.9,1/.9],'retained_and_table_equal':True,'BFS_and_sanitizers':True},'scope':'Pilot: repeated destruction/construction of frozen parsed graphs; no cold-start/query speed/SOTA claim. Each graph equally weighted; all failures retained. No tuning after output. Successful pilot requires separate qualification.'}
protocol['headers']={a:{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (OUT/a).glob('*.h')} for a in protocol['arms'] if a!='identical'}
protocol['harness_sha256']=hashlib.sha256(s.encode()).hexdigest();(OUT/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
old=json.loads((ROOT/'evidence/phase32/build_manifest.json').read_text());template=next(c['command'] for c in old['commands'] if c['name']=='candidate');builds={}
for arm in ('previous','csr','closure','buffers'):
 d=OUT/arm;cmd=template.copy();cmd[cmd.index('-MF')+1]=str(d/'deps.d');cmd[cmd.index('-o')+1]=str(d/'bench');cmd=[str(OUT/'native_compare_bench.cpp') if x.endswith('/native_compare_bench.cpp') else '-I'+str(d) if x=='-I'+str(ROOT) else x for x in cmd];cmd.append('-I'+str(ROOT))
 result=subprocess.run(cmd,text=True,capture_output=True);(d/'compile.log').write_text(result.stderr);result.check_returncode()
 deps=shlex.split((d/'deps.d').read_text().replace('\\\n','').split(':',1)[1]);selected={Path(x).name:Path(x) for x in deps if Path(x).name in protocol['headers'][arm]};assert len(selected)==8 and all(x.parent==d for x in selected.values())
 builds[arm]={'command':cmd,'binary_sha256':hashlib.sha256((d/'bench').read_bytes()).hexdigest(),'selected':{n:hashlib.sha256(x.read_bytes()).hexdigest() for n,x in selected.items()}}
 print('Built',arm,flush=True)
(OUT/'builds.json').write_text(json.dumps(builds,indent=2)+'\n')
