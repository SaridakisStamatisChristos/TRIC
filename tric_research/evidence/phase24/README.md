# Phase XXIV preserved evidence

Measured implementation: b5e1a1c3aa4a32cbf4bafedb3a68680722195e00.
The three runtime headers match direct-main PR #24 at 267085808ad53065825c9b1f464a3f15824a450e.

Primary matrix: seven published/original graphs x three seeds x four strata x
both horizons. This contains SIX real graphs and published synthetic Kronecker.
Every primary trial is CI-executed. Ratios >1 favor automatic TRIC. The summary
chooses the faster OReach fallback per graph/seed/stratum separately for query
and lifecycle, then takes the median of the three per-seed paired ratios.

`primary_summary.csv` includes all 56 graph/stratum/horizon medians and seed ranges;
each primary graph's CSV preserves per-seed comparisons against every available
control. Each `.json.gz` preserves ALL raw numeric process trials, answer hashes,
per-answer oracle counts, memory observations, source hashes and environment.
Open them with Python's gzip and json modules. An unavailable bounded closure is
recorded unavailable, never treated as a win.

All nine additional generated stress graph/seed experiments also completed CI,
for 30/30 CI-origin graph/seed records in total. The separate earlier layout
ablation remains a LOCAL exploratory experiment; do not pool its samples with
these CI measurements as independent hardware replication. Raw and SCC-quotient graph identity,
query identity and preprocessing boundaries remain in every experiment.

Primary real-graph CI: https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39899645952
Original/synthetic CI: https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39899645925
Runtime integration CI: https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39899819705

Global SOTA remains NO-GO: GO/YAGO have clear losses, several other lifecycle
regressions remain, memory is not matched to OReach, and other modern indexes and
large-graph regimes are unmeasured. See the report for exact boundaries.
