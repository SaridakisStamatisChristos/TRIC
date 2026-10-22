// Phase XIX opt-in warm-index batch timing. Included after native benchmark
// helpers. Does not change default algorithms or the Phase XVII fit procedure.
#pragma once
#include <array>

struct ReplayResult {
  uint64_t ns=0, checksum=0, probes=0, rescues=0, fallbacks=0;
};

static ReplayResult replay_batch(CompactReachability& compact,
    const std::vector<Pivot>& pivots,const Policy& policy,
    const std::vector<std::pair<int,int>>& queries,const std::vector<int>& order,
    int mode,int selected,std::vector<uint8_t>* answers=nullptr){
  ReplayResult out;
  const auto start=Clock::now();
  for(int id:order){
    const int source=queries[id].first,target=queries[id].second;
    int decision=compact.certificate(source,target);
    if(decision==-1)for(int p:policy.order){
      ++out.probes;
      const int cert=certify(pivots.at(p),source,target);
      if(cert!=-1){decision=cert;++out.rescues;break;}
    }
    if(decision==-1){
      ++out.fallbacks;
      const bool topo=mode==2?compact.select_topological(source,target,selected):mode==0;
      decision=topo?compact.reaches(source,target,nullptr,false,true)
                   :compact.reaches_bidirectional(source,target);
    }
    if(answers)(*answers)[id]=static_cast<uint8_t>(decision);
    out.checksum=(out.checksum*0x100000001b3ULL)
        ^(static_cast<uint64_t>(id)*4ULL+static_cast<unsigned>(decision));
  }
  out.ns=static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
      Clock::now()-start).count());
  return out;
}

static void emit_lifetime_replay(CompactReachability& compact,
    const std::vector<Pivot>& pivots,const Policy& policy,
    const std::vector<std::pair<int,int>>& queries,const std::vector<uint8_t>& truth,
    int reps,int selected,double fit_ns,std::size_t train_count,
    double pivot_build_ms,double compact_build_ms){
  const int count=static_cast<int>(queries.size());
  std::vector<int> full_order(count);std::iota(full_order.begin(),full_order.end(),0);
  // Exact, per-answer comparison of all three arms outside reported timers.
  for(int mode=0;mode<3;++mode){
    std::vector<uint8_t> answers(count,2);
    (void)replay_batch(compact,pivots,policy,queries,full_order,mode,selected,&answers);
    if(answers!=truth)throw std::runtime_error("lifetime per-answer oracle mismatch");
  }
  std::vector<int> horizons;
  for(int q:{1200,10000,100000,count})if(q<=count)horizons.push_back(q);
  std::sort(horizons.begin(),horizons.end());
  horizons.erase(std::unique(horizons.begin(),horizons.end()),horizons.end());
  const char* names[]={"topo","bidir","selector"};
  std::cout<<std::setprecision(17)
      <<"{\"schema\":\"tric-phase19-warm-batches-v1\",\"queries\":"<<count
      <<",\"training_queries\":"<<train_count<<",\"training_ns\":"<<fit_ns
      <<",\"policy_id\":"<<selected<<",\"repetitions\":"<<reps
      <<",\"oracle_positive_count\":"<<std::count(truth.begin(),truth.end(),uint8_t(1))
      <<",\"pivot_build_ms\":"<<pivot_build_ms<<",\"compact_build_ms\":"<<compact_build_ms
      <<",\"verified_answers_per_method\":"<<count<<",\"batches\":[";
  bool first=true;
  for(int q:horizons){
    std::vector<int> order(q);std::iota(order.begin(),order.end(),0);
    for(int rep=0;rep<reps;++rep){
      std::mt19937_64 rng(0x1920261022ULL+static_cast<uint64_t>(rep));
      std::shuffle(order.begin(),order.end(),rng);
      uint64_t expected=0;
      for(int id:order)expected=(expected*0x100000001b3ULL)
          ^(static_cast<uint64_t>(id)*4ULL+truth[id]);
      // Equal full-batch warmup for each method immediately before timing;
      // warm-index result only. No cold-cache or independent-process claim.
      std::array<ReplayResult,3> result;
      for(int offset=0;offset<3;++offset){
        int mode=(rep+offset)%3;
        (void)replay_batch(compact,pivots,policy,queries,order,mode,selected);
        result[mode]=replay_batch(compact,pivots,policy,queries,order,mode,selected);
      }
      for(int mode=0;mode<3;++mode){
        const auto& r=result[mode];
        if(r.checksum!=expected || r.probes!=result[0].probes ||
           r.rescues!=result[0].rescues || r.fallbacks!=result[0].fallbacks)
          throw std::runtime_error("lifetime checksum/pivot accounting mismatch");
      }
      if(!first)std::cout<<',';
      first=false;
      std::cout<<"{\"queries\":"<<q<<",\"rep\":"<<rep
          <<",\"first_mode\":\""<<names[rep%3]<<"\",\"expected_checksum\":"<<expected;
      for(int mode=0;mode<3;++mode){
        const auto& r=result[mode];
        std::cout<<",\""<<names[mode]<<"\":{\"total_ns\":"<<r.ns
            <<",\"checksum\":"<<r.checksum<<",\"probes\":"<<r.probes
            <<",\"rescues\":"<<r.rescues<<",\"fallbacks\":"<<r.fallbacks<<'}';
      }
      std::cout<<'}';
    }
  }
  std::cout<<"]}\n";
}
