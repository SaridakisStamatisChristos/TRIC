# Phase XXVIII evidence

Frozen runtime: 3505d6390e24f30515d78f90c0fed43e7a6e4bb8.
Baseline: PR #27 / 49eafb9b8cc06ff15b9f71058e2eb8770fc50961.

- `native/`: matched PR #26 / PR #27 / candidate, six balanced trials, 3,000 replays.
- `small/`: seven arms including original BFL, OReach, PLL/PPL; seven balanced trials, 100 replays.
- Both use exact `../phase25/fixtures` (19 graphs, 39 graph-seed pairs, 156 cells).
- `forest-warm/`: two arms/four trials, 1,000 replays; `../phase27/large-fixtures`.
- `forest-fresh/`: two arms/four trials, single pass; `../phase27/fresh-fixtures`.
- Every accepted root has sealed raw results, summaries and complete digest/case receipts.
- `baseline-sources/`: the complete repository-shaped set of source files hashed
  by Phase XXVII; its validator uses these immutable bytes for historical checks.
- `query_profile.json`: decision-path counts from a separately instrumented
  partitioned backend. Counts are not a cycle profile.
- `experiments.json.gz`: matched/rejected pilots, invalid initial builds and
  interrupted long-replay run, all labelled with their scope and exclusions.
- `build_manifest.json`, `reference26_build_manifest.json`, `source_hashes.json`
  and `provenance_verification.json`: exact build/source/selected-dependency receipts.

No global SOTA or independent dedicated-hardware replication is claimed.
Full methods, every regression and claim limits are in
`../../PHASE_XXVIII_RESEARCH_REPORT.md`.
