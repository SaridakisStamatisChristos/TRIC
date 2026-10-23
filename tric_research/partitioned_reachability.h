// Static exact reachability: SCCs, weak-component partitioning, and the smaller
// of established chain labels / bitset closure. No training or novelty claim.
// C++17. The cap is for TABLE PAYLOAD, not graph input, scratch or total RSS.
#pragma once
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
  enum class Mode { search, chains, bits, compressed };
  struct Row {
    std::size_t offset=0, ids_offset=0;
    std::uint32_t first=0, count=0;
    bool sparse=false;
  };
  struct Partition {
    Mode mode = Mode::search;
    std::size_t offset = 0, stride = 0;
  };
  std::vector<int> component_, group_, local_, chain_;
  std::vector<Partition> partitions_;
  std::vector<std::uint32_t> labels_;
  std::vector<std::uint64_t> bits_;
  std::vector<Row> rows_;
  std::vector<std::uint32_t> word_ids_;
  Graph fallback_dag_;
  std::vector<unsigned> seen_;
  std::vector<int> stack_;
  unsigned epoch_ = 0;
  std::size_t indexed_ = 0, chain_groups_ = 0, bit_groups_ = 0, compressed_groups_ = 0;
  std::uint64_t merged_arcs_ = 0, skipped_arcs_ = 0;
public:
  template<class G>
  explicit PartitionedReachability(const G& graph, std::size_t table_cap_bytes,
                                   std::size_t dense_scratch_cap_bytes=64ULL*1024*1024) {
    if (graph.size() > static_cast<std::size_t>(std::numeric_limits<int>::max()))
      throw std::length_error("graph has too many vertices");
    const int n = static_cast<int>(graph.size());
    Graph reverse(n);
    for (int u=0; u<n; ++u) for (int v: graph[u]) {
      if (v<0 || v>=n) throw std::out_of_range("edge endpoint");
      reverse[v].push_back(u);
    }
    std::vector<unsigned char> visited(n, 0);
    std::vector<int> finish; finish.reserve(n);
    std::vector<std::pair<int,std::size_t>> frames;
    for (int root=0; root<n; ++root) {
      if (visited[root]) continue;
      frames.clear(); frames.emplace_back(root,0); visited[root]=1;
      while (!frames.empty()) {
        auto& frame=frames.back(); const int u=frame.first;
        if (frame.second<graph[u].size()) {
          const int v=graph[u][frame.second++];
          if (!visited[v]) {visited[v]=1; frames.emplace_back(v,0);}
        } else {finish.push_back(u); frames.pop_back();}
      }
    }
    component_.assign(n,-1);
    int count=0;
    std::vector<int> todo;
    for (auto it=finish.rbegin(); it!=finish.rend(); ++it) {
      if (component_[*it]>=0) continue;
      todo.assign(1,*it); component_[*it]=count;
      while (!todo.empty()) {
        const int u=todo.back(); todo.pop_back();
        for (int v:reverse[u]) if (component_[v]<0) {
          component_[v]=count; todo.push_back(v);
        }
      }
      ++count;
    }
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
        // A larger temporary matrix may be compressed into sparse word rows
        // or dense suffixes. This is a distinct, explicit CONSTRUCTION budget.
        if (bb>dense_scratch_cap_bytes ||
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
          // Increasing topological order lets already inherited descendants
          // eliminate redundant row merges without materializing reduction.
          for (int b:dag[a]) {
            if (dst[chain_[b]]<=static_cast<std::uint32_t>(local_[b])) {++skipped_arcs_; continue;}
            ++merged_arcs_;
            const auto* src=labels_.data()+part.offset+std::size_t(local_[b])*chains;
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
    labels_.shrink_to_fit(); bits_.shrink_to_fit();
    rows_.shrink_to_fit(); word_ids_.shrink_to_fit();
    if (needs_search) {
      fallback_dag_=std::move(dag);
      for (int a=0;a<count;++a) if (partitions_[group_[a]].mode!=Mode::search)
        std::vector<int>().swap(fallback_dag_[a]);
      seen_.assign(count,0); stack_.reserve(count);
    }
  }
  // Reflexive semantics: every vertex reaches itself, including an isolate.
  // Fallback reuses mutable scratch: use one instance per querying thread.
  bool reaches(int source,int target) {
    if (source<0 || target<0 || static_cast<std::size_t>(source)>=component_.size()
        || static_cast<std::size_t>(target)>=component_.size()) throw std::out_of_range("query endpoint");
    const int a=component_[source], b=component_[target];
    if (a==b) return true;
    if (a>b || group_[a]!=group_[b]) return false;
    const auto& p=partitions_[group_[a]];
    if (p.mode==Mode::chains)
      return labels_[p.offset+std::size_t(local_[a])*p.stride+chain_[b]]<=static_cast<std::uint32_t>(local_[b]);
    if (p.mode==Mode::bits) {
      const std::size_t bp=static_cast<std::size_t>(local_[b]);
      return (bits_[p.offset+std::size_t(local_[a])*p.stride+(bp>>6)]>>(bp&63))&1U;
    }
    if (p.mode==Mode::compressed) {
      const Row& row=rows_[p.offset+static_cast<std::size_t>(local_[a])];
      const std::uint32_t word=static_cast<std::uint32_t>(local_[b])>>6;
      std::size_t pos=word-row.first;
      if (row.sparse) {
        const auto first=word_ids_.begin()+row.ids_offset,last=first+row.count;
        const auto it=std::lower_bound(first,last,word);
        if (it==last || *it!=word)return false;
        pos=static_cast<std::size_t>(it-first);
      }
      return (bits_[row.offset+pos]>>(local_[b]&63))&1U;
    }
    if (++epoch_==0) {std::fill(seen_.begin(),seen_.end(),0); epoch_=1;}
    stack_.assign(1,a); seen_[a]=epoch_;
    while (!stack_.empty()) {
      const int u=stack_.back(); stack_.pop_back();
      for (int v:fallback_dag_[u]) {
        if (v==b) return true;
        if (v<b && seen_[v]!=epoch_) {seen_[v]=epoch_; stack_.push_back(v);}
      }
    }
    return false;
  }
  std::size_t table_bytes() const {return (labels_.size()+word_ids_.size())*sizeof(std::uint32_t)+bits_.size()*sizeof(std::uint64_t)+rows_.size()*sizeof(Row);}
  std::size_t retained_bytes() const {
    std::size_t total=(component_.capacity()+group_.capacity()+local_.capacity()+chain_.capacity()+stack_.capacity())*sizeof(int)
      +rows_.capacity()*sizeof(Row)+word_ids_.capacity()*sizeof(std::uint32_t)
      +partitions_.capacity()*sizeof(Partition)+labels_.capacity()*sizeof(std::uint32_t)
      +bits_.capacity()*sizeof(std::uint64_t)+seen_.capacity()*sizeof(unsigned)
      +fallback_dag_.capacity()*sizeof(std::vector<int>)+sizeof(*this);
    for (const auto& row:fallback_dag_) total+=row.capacity()*sizeof(int);
    return total;
  }
  std::size_t components() const {return group_.size();}
  std::size_t indexed_components() const {return indexed_;}
  std::size_t chain_partitions() const {return chain_groups_;}
  std::size_t bit_partitions() const {return bit_groups_;}
  std::size_t compressed_partitions() const {return compressed_groups_;}
  std::size_t partitions() const {return partitions_.size();}
  std::uint64_t merged_arcs() const {return merged_arcs_;}
  std::uint64_t skipped_arcs() const {return skipped_arcs_;}
};
