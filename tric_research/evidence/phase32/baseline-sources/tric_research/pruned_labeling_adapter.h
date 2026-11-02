// Benchmark-only adapter for the unchanged original Yano et al. implementation.
// MIT, pinned in third_party/pruned_labeling/PROVENANCE.json.
#pragma once
// Include the original translation unit so the same -O3 benchmark compilation
// may inline the authors' query API, just as it may inline TRIC's headers.
#include "third_party/pruned_labeling/src/PrunedLabeling.cpp"

template<class OriginalIndex>
class PrunedLabelingAdapter {
  OriginalIndex index_;
public:
  explicit PrunedLabelingAdapter(const std::vector<std::vector<int>>& graph)
    :index_(graph){}
  // The upstream graph is zero-based; its public query API subtracts one.
  bool reaches(int source,int target){return index_.query(source+1,target+1);}
  long long upstream_reported_label_bytes(){return index_.indexSize();}
};
using PllAdapter=PrunedLabelingAdapter<RQPrunedLandmarkLabeling>;
using PplAdapter=PrunedLabelingAdapter<RQPrunedPathLabeling>;
