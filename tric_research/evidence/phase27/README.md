# Phase XXVII evidence

The final runtime is commit 9b51f3a1d54d1bce8b6dcd13adfc556404c7f50b;
its baseline is PR #26 commit 68f32a47802b2133fa5a107a6d2f7ae3f50b2664.
No runtime headers change when this evidence is published.

- `small/`: original 19 graphs / 39 graph-seed pairs; inputs are the exact files
  in `../phase25/fixtures`; seven arms, seven position-balanced trials,
  1,200 pairs and 100 replays.
- `large/`: two author-published SCC-condensed graphs, 693,947 and 1,595,444
  vertices; inputs in `large-fixtures`; four 64-pair strata and 1,000 replays.
- `fresh/`: the same graphs with independent uniform seed 20261029,
  4,096 frozen pairs and one pass; inputs in `fresh-fixtures`. This is not a
  hardware cache-flush experiment. Each trial begins in a fresh process.
- `csr/`: controlled star-of-diamonds, zero table cap, two arms/four trials;
  tests exact general CSR fallback rather than external or SOTA superiority.
- Each run has a sealed `qualification-final/manifest.json`, complete raw
  results, paired CSV summaries and a digest/case completeness receipt.
- `build_manifest.json` and `source_hashes.json`: pinned tools, compiler options,
  source dependencies and binary hashes. Original BFL/OReach and unchanged
  original PLL/PPL code are included in the same comparison source.
- `ablations.json.gz`: complete exploratory trials, rejected prototypes and
  the initial qualification whose partition-first variant regressed direct
  closure. Those measurements are not mixed into final qualification.
- `candidate_ledger.json`: accepted/rejected claims and remaining SOTA gaps.

All results are local measurements on shared hardware. CI independently checks
correctness, sanitizers and preserved result/input integrity; it does not
reproduce performance on dedicated independent hardware. Full methods and all
losses are in `../../PHASE_XXVII_RESEARCH_REPORT.md`.
