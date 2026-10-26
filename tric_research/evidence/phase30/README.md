# Phase XXX evidence

Baseline: PR #29, `c719c1973b47ad881a9a0cc25d5a5391c6335bdc`.
The local runtime revision is recorded in `campaign.json`; publication may use
a different Git commit ID while preserving the exact source tree.

The candidate separates residual interval search and noninterval handling from
the common query function. It preserves the moved bodies, preprocessing,
representation sizes, route choices and public semantics.

- `qualification_protocol.json`: candidate and five campaigns frozen before qualification.
- `forest_replication_protocol.json`: separately frozen supplemental check after observing a cold forest regression; no runtime changes.
- `forest_warm_replication_protocol.json`: one additional fixed eight-trial check of all warm forest cells after identifying the warm CiteSeer positive-query regression.
- `build_manifest.json`: matched compiler, dependencies, pinned upstream objects and binary hashes. PR29 is reproduced exactly.
- `baseline-sources/`: all source files attested by Phase XXIX, preserving historical verification.
- `native/`, `external/`, `fresh/`, `forest-warm/`, `forest-fresh/`, `forest-replication/`, `forest-warm-replication/`: sealed manifests, raw trials, paired summaries and complete-case verification receipts.
- `fresh-fixtures/`: new seeds/topologies and 2048 pairs per stratum from four synthetic families derived from Phase XXIX. These are not new real-world graph families.
- `experiments.json.gz`: all five pilots, 16 arms including control, raw compressed results, prototype source, generators, commands and selected compiler dependency hashes.
- `diagnostics.json`, `compiler_diagnostics.json`: rejection/row counts and compiler call-site evidence used to distinguish hypotheses.
- `source_hashes.json`: current source and artifact integrity manifest.
- `result_metrics.json`: descriptive metrics recomputed by `summarize_phase30.py`.
- `campaign.json`: accepted/rejected paths, scope, claim provenance and unresolved gaps.
- `tests.log`, `sanitizer.log`: local checks. Local LeakSanitizer alone was disabled for the traced environment; CI retains the full command.

Read `../../PHASE_XXX_RESEARCH_REPORT.md` for every native and external aggregate,
the cold forest regression, evidence limitations and remaining SOTA gaps.
Repeated requests, seeds and related synthetic families are dependent evidence.
The table cap does not bound total memory, and the competitors are not compared
at matched total-memory Pareto points.

From `tric_research/`:

```bash
python verify_phase29_evidence.py --source-root evidence/phase30/baseline-sources
python verify_phase30_evidence.py
python summarize_phase30.py
```

For new timing runs, use a separate checkout/output tree and the unchanged
recorded build flags/upstream objects. The five main campaigns are executed by
`run_phase30_qualification.py --build BUILD_DIRECTORY`. The supplemental run was:

```bash
python benchmark_native_changes.py \
  --fixtures evidence/phase27/fresh-fixtures \
  --output evidence/phase30/forest-replication/qualification-final \
  --trials 12 --horizons 1 --cpu 1 \
  --arm previous BUILD_DIRECTORY/previous auto \
  --arm candidate BUILD_DIRECTORY/candidate auto
```

The original four-trial forest result remains intact; replication does not
replace it. No claim of uniform workload improvement or global SOTA is made.
The warm replication uses the same command with fixtures
`evidence/phase27/large-fixtures`, output
`evidence/phase30/forest-warm-replication/qualification-final`, eight trials and
1000 replays.
