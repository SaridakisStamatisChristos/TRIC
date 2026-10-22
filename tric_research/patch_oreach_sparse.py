"""Diagnostic patch for O-Reach at pinned original commit.

The original code uses nth_element with begin+8 even when eligible
candidate count is fewer than 8 on disconnected graphs. This optional
pruning index can be omitted safely: support masks initialize to zero.
An explicitly separate patched comparator is used for diagnostics.
"""
import argparse
import hashlib
import json
from pathlib import Path

PINNED_SHA="78b3e326bbb021b7ee225ab605a4cdd074fa1d93"
ANCHOR="""    auto it = candidates.begin();
    std::advance(it, NUM_SUPPORTS);
    std::nth_element(candidates.begin(), it, candidates.end(), comp1);
"""
REPLACEMENT="""    // TRIC diagnostic sparse-component compatibility guard.
    // The original assumes >= NUM_SUPPORTS eligible candidates. When
    // no large component exists, candidates is empty; begin()+8 is UB.
    // Zero-initialized support masks simply disable optional pruning.
    if (candidates.size() < NUM_SUPPORTS) {
        std::cerr << "OREACH_SPARSE_GUARD candidate_count="
                  << candidates.size() << " threshold=" << NUM_SUPPORTS
                  << std::endl;
        return;
    }
    auto it = candidates.begin();
    std::advance(it, NUM_SUPPORTS - 1);
    std::nth_element(candidates.begin(), it, candidates.end(), comp1);
"""

def apply(path):
    path=Path(path)
    src=path.read_text()
    a=src.index("void oreach::sampleSupportsFromLevels(")
    b=src.index("void oreach::sampleSupportsFromLevels2(",a)
    section=src[a:b]
    if section.count(ANCHOR)!=1 or src.count(ANCHOR)!=1:
        raise ValueError("unexpected upstream source — refusing unverified patch")
    if "OREACH_SPARSE_GUARD" in src:
        raise ValueError("patch was already applied")
    patched=src[:a]+section.replace(ANCHOR,REPLACEMENT)+src[b:]
    path.write_text(patched)
    return {"path":str(path),"upstream_commit":PINNED_SHA,
            "patch":"candidate-count guard in sampleSupportsFromLevels only",
            "original_sha256":hashlib.sha256(src.encode()).hexdigest(),
            "patched_sha256":hashlib.sha256(patched.encode()).hexdigest()}

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("source",type=Path)
    ap.add_argument("--report",type=Path)
    args=ap.parse_args()
    data=apply(args.source)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(data,indent=2)+"\n")
    print(json.dumps(data))
