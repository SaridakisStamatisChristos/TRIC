# Phase XXXII evidence

Baseline: PR #31, commit `09003cb9d7b915516767894f4881542bb8ff4c44` (PR #30 runtime).
`baseline-sources/` preserves source versions required by the historical seals.

- `protocol.json`: frozen memory objective and acceptance gates.
- `results.json`: complete 42-case paired allocation records and build provenance.
- `build_manifest.json`: full comparator-enabled builds and baseline reproduction.
- `full-build-smoke.json`: 27 fixture files, 54 executions, one query case per file.
  Raw clock fields are diagnostic output, not qualified comparative timing.
- `metrics.json`: mechanically derived memory results and scope limitations.
- `unit-tests.log`, `evidence-tests.log`, `sanitizer*.log`: local receipts,
  including the initial LeakSanitizer environment failure.
- `sealed_manifest.json`: source, snapshot, report and data SHA-256 digests.

From `tric_research/`:

```bash
python verify_interval_storage.py
python -m unittest -q test_interval_storage_evidence
python verify_interval_storage.py --quick --run /tmp/tric-storage-quick
python verify_interval_storage.py --run /tmp/tric-storage-full
python verify_phase30_evidence.py --source-root evidence/phase32/baseline-sources
python verify_phase31_evidence.py --source-root evidence/phase32/baseline-sources
```

Output folders must be empty. Full runs cover all distinct pairs from all original
cases. Probes need C++17 and UBSan. Rebuild the full binaries with
`build_native_comparison.py`, the pinned upstream sources/objects and include paths
recorded in the manifest, then use
`run_interval_storage_smoke.py --build BUILD --output NEW_FILE.json`.

The source check permits exactly the directory-release insertion relative to the
baseline header; other runtime headers must match. Old seals check original files
without changing old measurements. The Phase XXXI verifier supports a sparse
historical source overlay while still requiring every original digest.

Memory here means requested live C++ allocation payload plus the index object;
allocator metadata, graph storage and RSS are excluded. Correctness combines
executable evidence with a conditional argument, not machine-checked proof.
No latency improvement, external ranking or global SOTA is established.
