# Phase XXXI evidence

Baseline runtime: PR #30, commit
`ac810f576d9dbc6ef2b9579725e6603d3ad4e049`.

- `experiments.json.gz`: all four prototype source trees, build/dependency
  digests, four initial pilot cohorts, four layout cohorts, four identical-binary
  control cohorts, protocols, rejected empty-seed setup, finite oracle and
  mutation-test receipts. Raw result files are base64-encoded gzip members inside
  this JSON container; no graph case or losing trial is dropped.
- `metrics.json`: deterministic summaries and original acceptance decisions.
- `stability.json.gz`: the complete longer-duration three-arm diagnostic,
  original and amended protocols, and the repeat-bound rejection. Only the
  requested repeat count was clamped to the existing CLI ceiling; earlier
  completed cases were preserved.
- `stability_metrics.json`: every diagnostic case and its gate results.
- `qualification.json.gz`: complete full-compiler qualification, including
  identical controls, both binaries' selected runtime dependencies, generated
  benchmark source, original compiler/linker commands, frozen calibration,
  and the pre-timing include-path build failure.
- `qualification_metrics.json`: every final case and every final gate.
- `sealed_manifest.json`: hashes of this phase's committed artifacts and tools.

All counts are process executions or repeated calls, not independent datasets.
Queries are reflexive exact reachability checks. Native input bytes are verified
against existing frozen graph/query fixtures. Temporary one-case gzip fixture
containers are not retained; their recorded hashes are receipts, while input
verification independently reconstructs the actual native payload. Raw result
gzip bytes are retained and their hashes are checked.

Run from `tric_research`:

```sh
python verify_phase31_evidence.py
python verify_phase31_stability.py
python verify_phase31_qualification.py
python -m unittest -q test_phase31_evidence
python verify_phase31_evidence.py --rebuild-checks
```

The last command rebuilds all five archived runtime alternatives and checks them
with the native oracle suite and UBSan. It also extracts the actual experimental
residual-search bodies and reruns the exhaustive interval and mutation checks.
It does not rerun performance measurements on the CI host. The archived build
commands record local paths that must be mapped to pinned upstream checkouts to
repeat the full external-enabled build; their exact source and header digests
are preserved. No portable cross-compiler speedup is asserted.

Integrity checks establish consistency and completeness of the committed
evidence. They are not a cryptographic attestation of the machine that produced
the timings, and finite tests are not a proof of unbounded correctness.
