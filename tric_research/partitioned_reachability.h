// Static exact reachability: SCCs, weak partitions, chains, bitsets and bounded
// unions of DFS intervals. All techniques are established; no query training.
// C++17. The cap is for TABLE PAYLOAD, not graph input, scratch or total RSS.
#pragma once
#include "scc_decomposition.h"
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <utility>
#include <vector>

class PartitionedReachability {
  using Graph = std::vector<std::vector<int>>;
  enum class Mode { search, chains, bits, compressed, intervals };
  struct Interval { std::uint32_t first, end; };
  struct IntervalRow { std::uint32_t offset=0, count=0; };
  struct Row {
    std::size_t offset=0, ids_offset=0;
    std::uint32_t first=0, count=0;
    bool sparse=false;
  };
  struct Partition {
    Mode mode = Mode::search;
    std::size_t offset = 0, stride = 0;
  };
  struct alignas(32) Label {
    // Interval labels tag group as -group_id-1; auxiliary=count, route=offset,
    // local=cached range begin, tree_end=cached range end, tree_begin=self preorder.
    // Other modes pack forward/backward depths in auxiliary; route is a chain
    // ID or SCC ID, and tree_begin/tree_end retain the DFS subtree.
    std::uint32_t auxiliary=0;
    int group=0, local=0;
    std::uint32_t route=0;
    int tree_begin=0, tree_end=0;
    std::uint64_t signature=0;
  };
  static_assert(sizeof(Label)==32,"vertex labels must remain 32 bytes");
  std::vector<Label> vertex_labels_;
  std::size_t component_count_=0;
  std::vector<Partition> partitions_;
  std::vector<std::uint32_t> labels_;
  std::vector<std::uint64_t> bits_;
  std::vector<Row> rows_;
  std::vector<IntervalRow> interval_rows_;
  std::vector<Interval> intervals_;
  std::vector<std::uint32_t> word_ids_;
  std::vector<std::size_t> fallback_offsets_;
  std::vector<int> fallback_edges_;
  std::vector<unsigned> seen_;
  std::vector<int> stack_;
  unsigned epoch_ = 0;
  std::size_t indexed_ = 0, chain_groups_ = 0, bit_groups_ = 0, compressed_groups_ = 0, interval_groups_ = 0;
  std::uint64_t merged_arcs_ = 0, skipped_arcs_ = 0;
  bool try_interval_partition(std::size_t g,const std::vector<int>& nodes,
                              const Graph& dag,const std::vector<int>& local_,
                              const std::vector<int>& tree_begin,
                              std::size_t& remaining,std::size_t index_scratch_cap_bytes) {
    // Exact unions of DFS intervals avoid a quadratic dense intermediate.
    // Every child row is complete before its parent (reverse DAG order).
    const std::size_t size=nodes.size();
    const std::uint64_t row_bytes=std::uint64_t(size)*sizeof(IntervalRow);
    if (row_bytes+std::uint64_t(size)*sizeof(Interval)<=remaining) {
      const auto old_rows=interval_rows_.size(), old_intervals=intervals_.size();
      const std::size_t limit=std::min((remaining-static_cast<std::size_t>(row_bytes))/sizeof(Interval),
                                      index_scratch_cap_bytes/(2*sizeof(Interval)));
      bool fits=limit>0;
      if(fits) {
        interval_rows_.resize(old_rows+size);
        std::vector<Interval> current,next;
        current.reserve(limit);next.reserve(limit);
        for(auto it=nodes.rbegin();it!=nodes.rend() && fits;++it) {
          const int a=*it;
          current.assign(1,Interval{static_cast<std::uint32_t>(tree_begin[a]),
                                    static_cast<std::uint32_t>(tree_begin[a]+1)});
          for(int b:dag[a]) {
            const auto row=interval_rows_[old_rows+static_cast<std::size_t>(local_[b])];
            const auto* child=intervals_.data()+row.offset;
            // Start from self only, then union COMPLETE child closures.
            // A covered child entry therefore implies its full closure is
            // already inherited; skip the transitive arc without row copying.
            const auto target=static_cast<std::uint32_t>(tree_begin[b]);
            const auto covered=std::upper_bound(current.begin(),current.end(),target,
              [](std::uint32_t value,const Interval& range){return value<range.first;});
            if(covered!=current.begin() && target<(covered-1)->end){++skipped_arcs_;continue;}
            ++merged_arcs_;
            next.clear();std::size_t i=0,j=0;
            while(i<current.size() || j<row.count) {
              const Interval value=(j==row.count || (i<current.size() && current[i].first<=child[j].first))
                ?current[i++]:child[j++];
              if(!next.empty() && value.first<=next.back().end)
                next.back().end=std::max(next.back().end,value.end);
              else {
                if(next.size()==limit){fits=false;break;}
                next.push_back(value);
              }
            }
            if(!fits)break;
            current.swap(next);
          }
          const auto added=intervals_.size()-old_intervals;
          if(!fits || current.size()>(remaining-static_cast<std::size_t>(row_bytes))/sizeof(Interval)-added ||
              current.size()>std::numeric_limits<std::uint32_t>::max()-intervals_.size()) {fits=false;break;}
          interval_rows_[old_rows+static_cast<std::size_t>(local_[a])]=IntervalRow{
            static_cast<std::uint32_t>(intervals_.size()),static_cast<std::uint32_t>(current.size())};
          intervals_.insert(intervals_.end(),current.begin(),current.end());
        }
      }
      if(fits) {
        auto& part=partitions_[g];part.mode=Mode::intervals;part.offset=old_rows;
        remaining-=static_cast<std::size_t>(row_bytes)+(intervals_.size()-old_intervals)*sizeof(Interval);
        indexed_+=size;++interval_groups_;return true;
      }
      interval_rows_.resize(old_rows);intervals_.resize(old_intervals);
    }
    return false;
  }
public:
  template<class G>
  explicit PartitionedReachability(const G& graph, std::size_t table_cap_bytes,
                                   std::size_t index_scratch_cap_bytes=64ULL*1024*1024)
    : PartitionedReachability(graph,table_cap_bytes,index_scratch_cap_bytes,
                              tric_detail::SccDecomposition(graph)) {}
private:
  friend class TricReachability;
  // Internal construction route: consume already validated SCCs exactly once.
  template<class G>
  PartitionedReachability(const G& graph, std::size_t table_cap_bytes,
                          std::size_t index_scratch_cap_bytes, tric_detail::SccDecomposition scc) {
    const int n=static_cast<int>(graph.size());
    auto component_=std::move(scc.component);
    const int count=scc.count;
    std::vector<int> group_, local_, chain_;
    // Kosaraju numbers the condensation in topological order.
    Graph dag(count), incoming(count);
    std::vector<int> parent(count), weight(count,1); std::iota(parent.begin(),parent.end(),0);
    auto root = [&parent](int a) {
      while (parent[a]!=a) {parent[a]=parent[parent[a]]; a=parent[a];}
      return a;
    };
    for (int u=0; u<n; ++u) for (int v:graph[u]) {
      const int a=component_[u], b=component_[v];
      if (a!=b) dag[a].push_back(b);
    }
    for (int a=0; a<count; ++a) {
      auto& row=dag[a]; std::sort(row.begin(),row.end());
      row.erase(std::unique(row.begin(),row.end()),row.end());
      for (int b:row) {
        if (a>=b) throw std::logic_error("SCC order is not topological");
        incoming[b].push_back(a);
        int ra=root(a), rb=root(b);
        if (ra!=rb) {
          if (weight[ra]<weight[rb])std::swap(ra,rb);
          parent[rb]=ra;weight[ra]+=weight[rb];
        }
      }
    }
    group_.resize(count); local_.resize(count); chain_.resize(count);
    std::vector<int> root_group(count,-1);
    Graph members;
    for (int a=0; a<count; ++a) {
      const int r=root(a);
      if (root_group[r]<0) {root_group[r]=static_cast<int>(members.size()); members.emplace_back();}
      const int g=root_group[r]; group_[a]=g;
      local_[a]=static_cast<int>(members[g].size()); members[g].push_back(a);
    }
    // DFS tree subtrees are exact positive certificates, including when the
    // original DAG has cross edges. Absence from the subtree proves nothing.
    std::vector<int> tree_begin(count,-1),tree_end(count,0);
    std::vector<std::pair<int,std::size_t>> frames;int clock=0;
    for(int root=0;root<count;++root) {
      if(tree_begin[root]>=0)continue;
      tree_begin[root]=clock++;frames.emplace_back(root,0);
      while(!frames.empty()) {
        auto& f=frames.back();const int a=f.first;
        if(f.second<dag[a].size()) {
          const int b=dag[a][f.second++];
          if(tree_begin[b]<0){tree_begin[b]=clock++;frames.emplace_back(b,0);}
        } else {tree_end[a]=clock;frames.pop_back();}
      }
    }
    // Descendant and ancestor signatures each use 32 bits. Reachability a->b
    // requires D(b) subset D(a) and A(a) subset A(b). Complementing the ancestor
    // half combines both necessary conditions in one 64-bit subset check.
    // Hash collisions only weaken rejection; matching never proves an answer.
    std::vector<std::uint64_t> signature(count,0),ancestors(count,0);
    for(int a=count-1;a>=0;--a) {
      const auto hash=(std::uint64_t(a)+1)*0x9e3779b97f4a7c15ULL;
      signature[a]=std::uint64_t(1)<<(hash>>59);
      for(int b:dag[a])signature[a]|=signature[b];
    }
    for(int a=0;a<count;++a) {
      const auto hash=(std::uint64_t(a)+1)*0x9e3779b97f4a7c15ULL;
      ancestors[a]|=std::uint64_t(1)<<(hash>>59);
      for(int b:dag[a])ancestors[b]|=ancestors[a];
    }
    for(int a=0;a<count;++a)
      signature[a]=(signature[a]<<32) | ((~ancestors[a])&0xffffffffULL);
    partitions_.resize(members.size());
    std::vector<int> tail, lengths;
    std::size_t remaining=table_cap_bytes;
    bool needs_search=false;
    for (std::size_t g=0; g<members.size(); ++g) {
      const auto& nodes=members[g]; const std::size_t size=nodes.size();
      // A singleton SCC is answered by equality/cross-component tests alone.
      if (size==1) {++indexed_; continue;}
      tail.clear(); lengths.clear();
      for (int a:nodes) {
        int best=-1;
        for (int p:incoming[a]) {
          const int c=chain_[p];
          if (tail[c]==p && (best<0 || lengths[c]>lengths[best])) best=c;
        }
        if (best<0) {best=static_cast<int>(tail.size()); tail.push_back(a); lengths.push_back(0);}
        chain_[a]=best; tail[best]=a; ++lengths[best];
      }
      const std::size_t chains=tail.size(), words=(size+63)/64;
      // Both products fit uint64_t for int-indexed graphs. Compare before
      // allocating; never truncate a product through a smaller size_t.
      const std::uint64_t cb=std::uint64_t(size)*chains*sizeof(std::uint32_t);
      const std::uint64_t bb=std::uint64_t(size)*words*sizeof(std::uint64_t);
      const bool use_chains=cb<bb;
      const std::uint64_t bytes=use_chains?cb:bb;
      if (bytes>remaining) {
        if(try_interval_partition(g,nodes,dag,local_,tree_begin,
                                  remaining,index_scratch_cap_bytes))continue;
        // A larger temporary matrix may be compressed into sparse word rows
        // or dense suffixes. This is a distinct, explicit CONSTRUCTION budget.
        if (bb>index_scratch_cap_bytes ||
            std::uint64_t(size)*(sizeof(Row)+sizeof(std::uint64_t))>remaining) {
          needs_search=true; continue;
        }
        std::vector<std::uint64_t> temp(size*words,0);
        for (auto it=nodes.rbegin();it!=nodes.rend();++it) {
          const int a=*it; const std::size_t pos=static_cast<std::size_t>(local_[a]);
          auto* dst=temp.data()+pos*words; dst[pos>>6]|=std::uint64_t(1)<<(pos&63);
          for (int b:dag[a]) {
            const std::size_t bp=static_cast<std::size_t>(local_[b]);
            if ((dst[bp>>6]>>(bp&63))&1U) {++skipped_arcs_;continue;}
            ++merged_arcs_;
            const auto* src=temp.data()+bp*words;
            for (std::size_t w=bp>>6;w<words;++w)dst[w]|=src[w];
          }
        }
        std::uint64_t compressed_bytes=std::uint64_t(size)*sizeof(Row);
        for (std::size_t i=0;i<size;++i) {
          std::size_t nonzero=0;
          for (std::size_t w=i>>6;w<words;++w)nonzero+=temp[i*words+w]!=0;
          compressed_bytes+=std::min(std::uint64_t(nonzero)*12,std::uint64_t(words-(i>>6))*8);
        }
        if (compressed_bytes>remaining) {needs_search=true;continue;}
        auto& part=partitions_[g];part.mode=Mode::compressed;part.offset=rows_.size();
        remaining-=static_cast<std::size_t>(compressed_bytes);indexed_+=size;++compressed_groups_;
        for (std::size_t i=0;i<size;++i) {
          std::size_t nonzero=0;
          for (std::size_t w=i>>6;w<words;++w)nonzero+=temp[i*words+w]!=0;
          Row row;row.offset=bits_.size();row.ids_offset=word_ids_.size();
          row.first=static_cast<std::uint32_t>(i>>6);
          row.sparse=nonzero*12<(words-(i>>6))*8;
          if (row.sparse) {
            row.count=static_cast<std::uint32_t>(nonzero);
            for (std::size_t w=i>>6;w<words;++w)if(temp[i*words+w]) {
              word_ids_.push_back(static_cast<std::uint32_t>(w));bits_.push_back(temp[i*words+w]);
            }
          } else {
            row.count=static_cast<std::uint32_t>(words-(i>>6));
            bits_.insert(bits_.end(),temp.begin()+i*words+(i>>6),temp.begin()+(i+1)*words);
          }
          rows_.push_back(row);
        }
        continue;
      }
      remaining-=static_cast<std::size_t>(bytes); indexed_+=size;
      auto& part=partitions_[g]; part.stride=use_chains?chains:words;
      if (use_chains) {
        part.mode=Mode::chains; part.offset=labels_.size(); ++chain_groups_;
        labels_.resize(labels_.size()+size*chains,std::numeric_limits<std::uint32_t>::max());
        for (auto it=nodes.rbegin(); it!=nodes.rend(); ++it) {
          const int a=*it;
          auto* dst=labels_.data()+part.offset+std::size_t(local_[a])*chains;
          dst[chain_[a]]=static_cast<std::uint32_t>(local_[a]);
          // The self-chain threshold proves membership of later chain nodes,
          // but does NOT mean their off-chain descendants were inherited.
          // Track only coverage obtained from complete child rows for this
          // chain. Other chain thresholds already come from complete rows.
          auto inherited_self_chain=std::numeric_limits<std::uint32_t>::max();
          // Increasing topological order lets already inherited descendants
          // eliminate redundant row merges without materializing reduction.
          for (int b:dag[a]) {
            const auto covered=chain_[b]==chain_[a]?inherited_self_chain:dst[chain_[b]];
            if (covered<=static_cast<std::uint32_t>(local_[b])) {++skipped_arcs_; continue;}
            ++merged_arcs_;
            const auto* src=labels_.data()+part.offset+std::size_t(local_[b])*chains;
            inherited_self_chain=std::min(inherited_self_chain,src[chain_[a]]);
            for (std::size_t c=0;c<chains;++c) dst[c]=std::min(dst[c],src[c]);
          }
        }
      } else {
        part.mode=Mode::bits; part.offset=bits_.size(); ++bit_groups_;
        bits_.resize(bits_.size()+size*words,0);
        for (auto it=nodes.rbegin();it!=nodes.rend();++it) {
          const int a=*it; const std::size_t pos=static_cast<std::size_t>(local_[a]);
          auto* dst=bits_.data()+part.offset+pos*words;
          dst[pos>>6]|=std::uint64_t(1)<<(pos&63);
          for (int b:dag[a]) {
            const std::size_t bp=static_cast<std::size_t>(local_[b]);
            if ((dst[bp>>6]>>(bp&63))&1U) {++skipped_arcs_; continue;}
            ++merged_arcs_;
            const auto* src=bits_.data()+part.offset+bp*words;
            // No descendant precedes b in the topological order.
            for (std::size_t w=bp>>6;w<words;++w) dst[w]|=src[w];
          }
        }
      }
    }
    // Closure union must see sorted complete rows. Only after ALL partitions
    // are built, move the widest exact interval to the cache slot at row[0].
    // Stable rotation keeps row[1..count) sorted for residual binary search.
    // Rows are disjoint in storage; SCC aliases later share the same row.
    // Strict comparison retains the first interval on ties. No query samples,
    // allocations, table growth or change to the represented set is involved.
    for(const auto& row:interval_rows_) {
      auto first=intervals_.begin()+row.offset, last=first+row.count;
      if(first==last)continue;
      const auto chosen=std::max_element(first,last,[](const Interval& a,const Interval& b){
        return a.end-a.first<b.end-b.first;
      });
      std::rotate(first,chosen,chosen+1);
    }
    labels_.shrink_to_fit(); bits_.shrink_to_fit();
    rows_.shrink_to_fit(); word_ids_.shrink_to_fit();
    interval_rows_.shrink_to_fit();intervals_.shrink_to_fit();
    std::vector<int> forward(count,0),backward(count,0);
    for(int a=0;a<count;++a)for(int b:dag[a])forward[b]=std::max(forward[b],forward[a]+1);
    for(int a=count-1;a>=0;--a)for(int b:dag[a])backward[a]=std::max(backward[a],backward[b]+1);
    vertex_labels_.resize(n);component_count_=static_cast<std::size_t>(count);
    for(int u=0;u<n;++u){
      const int a=component_[u];
      const auto& part=partitions_[group_[a]];
      const auto row=part.mode==Mode::intervals
        ?interval_rows_[part.offset+static_cast<std::size_t>(local_[a])]:IntervalRow{};
      const auto auxiliary=part.mode==Mode::intervals?row.count:
        (static_cast<std::uint32_t>(std::min(forward[a],65535)) |
         (static_cast<std::uint32_t>(std::min(backward[a],65535))<<16));
      const auto route=part.mode==Mode::intervals?row.offset:
        static_cast<std::uint32_t>(part.mode==Mode::search?a:chain_[a]);
      // Cache the selected widest range in fields unused by membership.
      // Retain the Bloom signature and original SCC preorder for all labels.
      const bool interval=part.mode==Mode::intervals;
      const auto first=interval?intervals_[row.offset]:Interval{};
      vertex_labels_[u]=Label{auxiliary,interval?-group_[a]-1:group_[a],
        interval?static_cast<int>(first.first):local_[a],route,
        tree_begin[a],interval?static_cast<int>(first.end):tree_end[a],signature[a]};
    }
    if (needs_search) {
      // Free reverse adjacency before allocating compact forward CSR.
      Graph().swap(incoming);
      std::size_t arcs=0;
      for(int a=0;a<count;++a)if(partitions_[group_[a]].mode==Mode::search)arcs+=dag[a].size();
      fallback_offsets_.reserve(static_cast<std::size_t>(count)+1);
      fallback_edges_.reserve(arcs);fallback_offsets_.push_back(0);
      for(int a=0;a<count;++a) {
        if(partitions_[group_[a]].mode==Mode::search)
          fallback_edges_.insert(fallback_edges_.end(),dag[a].begin(),dag[a].end());
        fallback_offsets_.push_back(fallback_edges_.size());
      }
      seen_.assign(count,0); stack_.reserve(count);
    }
  }
public:
  // Reflexive semantics: every vertex reaches itself, including an isolate.
  // Fallback reuses mutable scratch: use one instance per querying thread.
  bool reaches(int source,int target) {
    if (static_cast<std::size_t>(source)>=vertex_labels_.size()
        || static_cast<std::size_t>(target)>=vertex_labels_.size()) throw std::out_of_range("query endpoint");
    const auto& from=vertex_labels_[source];const auto& to=vertex_labels_[target];
    if ((from.signature & to.signature)!=to.signature)return false;
    if(from.group<0) {
      // All DFS preorder coordinates are globally unique across SCCs. A full
      // closure interval contains only reachable SCCs, even across DFS trees;
      // no partition/equality/topological certificate is needed on this route.
      const auto target=static_cast<std::uint32_t>(to.tree_begin);
      if(target-static_cast<std::uint32_t>(from.local)<
         static_cast<std::uint32_t>(from.tree_end-from.local))return true;
      if(from.auxiliary==1)return false;
      const auto first=intervals_.begin()+from.route+1,last=first+from.auxiliary-1;
      const auto it=std::upper_bound(first,last,target,[](std::uint32_t value,const Interval& range){return value<range.first;});
      return it!=first && target<(it-1)->end;
    }
    if (from.tree_begin==to.tree_begin) return true;
    if (from.group!=to.group || from.local>to.local) return false;
    if(from.tree_begin<=to.tree_begin && to.tree_begin<from.tree_end)return true;
    const auto& p=partitions_[from.group];
    if (p.mode==Mode::chains)
      return labels_[p.offset+std::size_t(from.local)*p.stride+to.route]<=static_cast<std::uint32_t>(to.local);
    if (p.mode==Mode::bits) {
      const std::size_t bp=static_cast<std::size_t>(to.local);
      return (bits_[p.offset+std::size_t(from.local)*p.stride+(bp>>6)]>>(bp&63))&1U;
    }
    if (p.mode==Mode::compressed) {
      const Row& row=rows_[p.offset+static_cast<std::size_t>(from.local)];
      const std::uint32_t word=static_cast<std::uint32_t>(to.local)>>6;
      std::size_t pos=word-row.first;
      if (row.sparse) {
        const auto first=word_ids_.begin()+row.ids_offset,last=first+row.count;
        const auto it=std::lower_bound(first,last,word);
        if (it==last || *it!=word)return false;
        pos=static_cast<std::size_t>(it-first);
      }
      return (bits_[row.offset+pos]>>(to.local&63))&1U;
    }
    // Keep both depth bounds for the potentially expensive search route.
    // 65535 means saturated: equal saturated values provide no rejection.
    const auto from_forward=from.auxiliary&65535U,to_forward=to.auxiliary&65535U;
    const auto from_backward=from.auxiliary>>16,to_backward=to.auxiliary>>16;
    if((from_forward>=to_forward && to_forward!=65535) ||
       (from_backward<=to_backward && from_backward!=65535))return false;
    const int a=static_cast<int>(from.route),b=static_cast<int>(to.route);
    if (++epoch_==0) {std::fill(seen_.begin(),seen_.end(),0); epoch_=1;}
    stack_.assign(1,a); seen_[a]=epoch_;
    while (!stack_.empty()) {
      const int u=stack_.back(); stack_.pop_back();
      for(std::size_t edge=fallback_offsets_[u];edge<fallback_offsets_[u+1];++edge) {
        const int v=fallback_edges_[edge];
        if (v==b) return true;
        if (v<b && seen_[v]!=epoch_) {seen_[v]=epoch_; stack_.push_back(v);}
      }
    }
    return false;
  }
  std::size_t table_bytes() const {return interval_rows_.size()*sizeof(IntervalRow)+intervals_.size()*sizeof(Interval)+(labels_.size()+word_ids_.size())*sizeof(std::uint32_t)+bits_.size()*sizeof(std::uint64_t)+rows_.size()*sizeof(Row);}
  std::size_t retained_bytes() const {
    std::size_t total=interval_rows_.capacity()*sizeof(IntervalRow)+intervals_.capacity()*sizeof(Interval)+vertex_labels_.capacity()*sizeof(Label)+stack_.capacity()*sizeof(int)
      +rows_.capacity()*sizeof(Row)+word_ids_.capacity()*sizeof(std::uint32_t)
      +partitions_.capacity()*sizeof(Partition)+labels_.capacity()*sizeof(std::uint32_t)
      +bits_.capacity()*sizeof(std::uint64_t)+seen_.capacity()*sizeof(unsigned)
      +fallback_offsets_.capacity()*sizeof(std::size_t)+fallback_edges_.capacity()*sizeof(int)+sizeof(*this);
    return total;
  }
  std::size_t components() const {return component_count_;}
  std::size_t indexed_components() const {return indexed_;}
  std::size_t chain_partitions() const {return chain_groups_;}
  std::size_t bit_partitions() const {return bit_groups_;}
  std::size_t compressed_partitions() const {return compressed_groups_;}
  std::size_t interval_partitions() const {return interval_groups_;}
  std::size_t partitions() const {return partitions_.size();}
  std::uint64_t merged_arcs() const {return merged_arcs_;}
  std::uint64_t skipped_arcs() const {return skipped_arcs_;}
};
