# Phase XXV evidence

- `fixtures/*.json.gz`: 19 exact native graphs with pinned query pairs, seeds,
  strata and original input SHA256. Ten original graphs retain 3 seeds; nine
  additional GRAIL-author graphs use seed 20261025. Source archive provenance
  for the additions is in `heldout_provenance.json`. Original fixture receipts
  refer to the complete Phase XXIV CI artifact names recorded inside each file.
- `qualification-final/*.json.gz`: all 312 qualified cells with every fresh
  process result, stdout/stderr diagnostics, wall/thread-CPU timers, VmHWM,
  actual call counts, BFS verification counts and cross-arm checksums.
- `qualification-final/manifest.json`: executable and input/result hashes,
  settings, hardware context and the full generated-communities artifact repair.
- `qualification-final/repair_run_manifest.json`: independent complete rerun
  receipt for that graph, using the same executables.
- `build_manifest.json`, `source_hashes.json`: actual compiler/link commands,
  exact runtime and benchmark hashes. Runtime headers match code commit
  `a94c1828abe2212e0239cdc93f09ff9d440d6c4f`.
- `per_seed_summary.csv`, `aggregate_summary.csv`: paired control/candidate
  ratios. Ratios greater than one favor the candidate. Aggregates take a median
  of seed medians, with seed ranges retained. Fastest external = min of BFL,
  OReach-pDFS and OReach-pBiBFS separately per metric and paired trial.
- `verification.json`: all input/result digests and complete case coverage.
- `ablation_layout.json.gz`: rejected split-layout prototype and all pilot rows;
  excluded from the qualified counts. `candidate_ledger.json` records decisions.

Revalidate and regenerate summaries from the repository root:

```bash
python tric_research/summarize_native_changes.py tric_research/evidence/phase25
```

Graphs are original benchmark data from their recorded author/upstream sources,
not newly collected user data. GRAIL source: `zakimjz/grail` at
`c13a7364fbc185841fc6277cd295acf33a7188f0`, original SIGMOD archives. BFL code
retains its original MIT license in `tric_research/third_party/bfl/`.

Frozen-query replays, shared hardware, unmatched total memory, per-query library
adapters and small/medium real graphs limit inference. No novelty, global SOTA,
production-readiness, million-vertex real-graph or formal-verification claim.
