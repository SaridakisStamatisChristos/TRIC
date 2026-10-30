# Phase XXXIII evidence

The runtime remains PR #32. CSR v2 failed its fixed replication rule; favorable
pooled results do not override that decision. See
[the report](../../PHASE_XXXIII_RESEARCH_REPORT.md).

From `tric_research/`:

```bash
python verify_phase33_evidence.py
python verify_phase33_external.py
python -m unittest -q test_phase33_evidence
python materialize_phase33_fixtures.py /tmp/tric-phase33-fixtures
python rebuild_phase33_checks.py /tmp/tric-phase33-checks --external
python verify_interval_storage.py --source-root evidence/phase33/baseline-sources
```

The rebuild output directory must be empty. It compiles all five archived
variants with UBSan, repeats the independent native oracle tests and exact SCC-ID
comparison, checks 15 allocation cases for baseline/CSR-v2/buffers, and checks
all 512 three-vertex directed graphs across the seven external implementations.
The external C++ sources are vendored at a fixed commit under their MIT license;
these checks require no network access.

## What is preserved

- `protocol.json`: original 31-graph pilot gates and source hashes.
- `prototypes/`: baseline, CSR v1, closure, buffers and CSR v2 source bytes.
- `qualification_protocol.json`: superseded CSR-v1 protocol; no timing occurred.
- `qualification_v2_protocol.json`: 37-graph, nine-trial qualification.
- `replication_protocol.json`: the one fixed 27-trial replication and pooled gate.
- `pilot/`, `qualification-{warm,cold}/`, `replication-{warm,cold}/`: all raw rows,
  manifests, process counters, timings, BFS checks and answer checksums.
- `replication-warm-part{1,2}/` and `replication_continuation.json`: the preserved
  interrupted run and continuation. The combined manifest references both parts.
- `resources.json`: 52 independently tracked allocation cases; the original
  empty-graph failure is in `empty-resource-counterexample.json`.
- `builds.json`, `standard_builds.json`, `v2_builds.json`: exact compiler commands,
  selected runtime dependencies and executable hashes. The single-build baseline
  reproduces the PR #32 executable hash.
- `new-fixtures/`: only the 12 new graphs. Historical graph fixtures are
  reconstructed from their already-preserved sources by retaining the first case;
  the verifier checks both source and reconstructed hashes. The original Unix
  gzip OS byte is normalized explicitly for Python-version portability.
- `external-upstream/`: pinned C++ source subset, license and upstream fidelity
  notes. `external-upstream-manifest.json` records every source digest.
- `external-resource-stop.json`: explicit deviation after four TF-Label build
  timeouts on `kron_logn12`. Its remaining 24 builds on that graph were not
  attempted and cannot support a speed comparison; the original protocol remains.
- `external-results/`: all preflight/timing results, including failures and
  identical-control results. `external_runtime.json` binds the unchanged runtime
  and actual comparison executable to the run.
- `campaign-sources/`: historical launch, fixture-generation, adapter and timing
  sources. Original absolute paths are provenance, not portable install paths.
  Rebase those paths and provide the pinned O'Reach build objects to repeat the
  full original construction compiler configuration on a new host. Fresh runs
  must use separate output directories and must not replace archived evidence.
- `baseline-sources/`: sparse repository-shaped snapshot supporting historical
  Phase XXXII checks after the evidence workflow/documentation changes.
- `sealed_manifest.json`: content hashes covering evidence, validators, reports,
  workflow and production headers. It detects accidental edits; it is not a
  cryptographic timestamp or an independently signed attestation.

## Interpretation

Ratios are paired per-trial ratios followed by a per-graph median, then equal
weight across graphs. Warm construction divides CPU by the actual build count;
single construction uses one build in each fresh process. Pooled qualification
uses every paired ratio from all 36 trials, not a median of the two campaign
medians. All original failed controls remain in the archive.

The external comparison uses per-call thread CPU after an equal one-pass warmup.
Its implementation-specific ratios are qualified only on cells whose identical
control is within [0.90, 1/0.90], with all eight successful trials and no observed
wrong-answer disqualification for the method. Reported payload estimates are
not matched total-memory usage. Global SOTA remains unestablished.
