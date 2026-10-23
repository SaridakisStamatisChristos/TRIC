// Adapter to the PUBLIC API of pinned MIT-licensed O'Reach (unmodified).
// This measures per-query API calls, not the upstream application's CSV loop.
#pragma once
#include "lib/reachability/oreach.h"
#include <memory>
class OReachAdapter {
  graph_access graph_;
  ReachabilityConfig config_;
  std::unique_ptr<oreach> index_;
  bool bidirectional_;
public:
  template<class Graph>
  OReachAdapter(const Graph& g,bool bidirectional,unsigned support)
      :bidirectional_(bidirectional) {
    std::size_t edges=0;for(const auto& row:g)edges+=row.size();
    graph_.start_construction(g.size(),edges);
    for(std::size_t u=0;u<g.size();++u){
      const auto a=graph_.new_node();
      for(int v:g[u])graph_.new_edge(a,static_cast<NodeID>(v));
    }
    graph_.finish_construction();
    config_.seed=20261023;config_.support=support;
    random_functions::setSeed(config_.seed);
    index_=std::make_unique<oreach>(graph_,config_);
    index_->initialize();
    index_->setFallbackMode(bidirectional?FB_PIBFS:FB_PDFS);
  }
  bool reaches(int s,int t){
    Query q(static_cast<NodeID>(s),static_cast<NodeID>(t));
    if(bidirectional_)index_->singleQuery<FB_PIBFS>(q);
    else index_->singleQuery<FB_PDFS>(q);
    if(!q.answered())throw std::runtime_error("O'Reach left an unanswered query");
    return q.isPositive();
  }
};
