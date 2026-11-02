# Phase XXXI: falsify query optimizations and qualify timing stability

Date: 27 October 2026. Baseline: PR #30, `ac810f576d9dbc6ef2b9579725e6603d3ad4e049`.

## Outcome

**Preserve the existing runtime.** Four candidate families were implemented and tested; none earns promotion under the frozen campaign gates. Production runtime headers and the original benchmark remain unchanged. No new external win count, global SOTA result, or novel algorithm is claimed.

The most promising pilot, switch-based dispatch, measured 1.048× in a longer narrow diagnostic, but the complete full-build qualification measured 1.033× across 180 warm seed/stratum cases. Its worst case over all 182 cases was 0.833×. The broad qualification, not the favorable pilot, governs the decision.

This outcome is evidence of insufficient generalization across the tested builds/workloads. Compiler options, linked comparator code, the benchmark repeat guard, and cohort coverage differ between exploratory and full-build campaigns; the experiment does not isolate one of these as the unique cause.

## Experiments and frozen decisions

Ratios are paired baseline/candidate elapsed times, reduced by median within each case. Values above one favor the candidate. Pilot cases comprise eight original graphs (32 cells), cross-chain queries (four), warm forests (eight), and single-pass forests (two). All are exposed inputs, not independent holdouts.

| Candidate family | Median query ratio, 46 cells | Worst cell | Original gate |
|---|---:|---:|---|
| branchless | 0.989× | 0.646× | Rejected |
| linear4 | 0.986× | 0.813× | Rejected |
| dispatch | 1.050× | 0.839× | Rejected |
| eytzinger | 0.997× | 0.735× | Rejected |

The alternatives were shrinking-window branchless predecessor search, a direct scan for at most four residual intervals, switch-based variant dispatch, and Eytzinger storage for residual intervals. Cached intervals and exact semantics were preserved. The first three used the original fixed criterion: median greater than 1.03× and every cell at least 0.90×. The fourth additionally required lifecycle median at least 0.97×. Criteria were not lowered after failures.

## Negative control and longer diagnostic

The initial identical-binary control used exactly the same executable SHA under two arm names. One warm UniProt-negative cell measured **0.773×**, even though the implementations were identical. This demonstrates timing/environment variation in that measurement; it does not prove that every candidate loss is noise. CPU-time ratios also varied, so wall-clock scheduling alone is not established as the cause.

A separate six-trial, three-arm diagnostic froze longer replay counts from baseline-only timings, targeting 200 ms per query region. It measured 1.048× candidate median and 0.966× worst case, with all identical-control medians inside [0.90, 1/0.90]. Nevertheless, its shortest region was 33.2 ms, below the fixed 50 ms gate. It therefore remained **NOT_QUALIFIED**.

The old benchmark rejects more than one million repeats before timing. This stopped the diagnostic at case 36; the remaining requested counts were clamped to that existing bound, preserving completed results and the original protocol. The clamp was disclosed and did not waive the duration gate. “Cold” inputs replayed in this diagnostic became warm repeated-query workloads; these measurements do not establish single-pass improvement.

## Full qualification

A generated copy of the unchanged benchmark raises only the repeat bound to one billion. The timed loop, clocks, input handling, BFS oracle, checksum, compiler safety settings, graph caps and query API are unchanged. Both arms use the same generated source, compiler flags and pinned external objects, with selected runtime dependency hashes checked. Invalid repeat counts above the new bound were rejected for both executables. This harness is an experimental artifact; the repository benchmark CLI remains unchanged.

All 19 original graphs and 39 seeds are included, plus the four existing fresh synthetic families, two warm large forests, and two true single-pass forest cases. Warm durations are frozen from Phase XXX baseline-only CPU measurements. Warm cases use six cyclic trials across baseline/candidate/identical; genuine single-pass cases use 24 trials without replay expansion. Every process BFS-checks every query pair outside timing.

| Cohort | Seed/stratum cases | Median query ratio | Worst ratio | Wins |
|---|---:|---:|---:|---:|
| native | 156 | 1.028× | 0.833× | 89/156 |
| fresh | 16 | 1.049× | 1.008× | 16/16 |
| forest | 8 | 1.036× | 1.014× | 8/8 |
| cold | 2 | 1.029× | 1.013× | 2/2 |

Warm lifecycle median: **1.029×**. Minimum observed warm query CPU duration: **123.9 ms**. Identical-control cells outside the fixed band: **1**.

The candidate floor failure is generated-community balanced queries (0.833×).
The final negative-control exception is GRAIL GO uniform queries, seed 20261022
(0.882×). These are different cases; the control exception does not explain away
the candidate's worst regression.

| Predeclared gate | Result |
|---|---|
| duration | PASS |
| null_control | FAIL |
| median | PASS |
| floor | FAIL |
| lifecycle | PASS |

Exact table payload, retained capacity and route selection match in every paired trial. Lifecycle includes parsing, construction and querying; process startup, BFS verification and teardown are excluded. Results are descriptive paired medians, not confidence intervals. One shared host, related graph families, repeated inputs and compiler lineage limit independence.

After timing completed, rebuilding the original full Phase XXX command reproduced
its candidate binary exactly: SHA-256
`12cbc59121898bdfb985f8ec88df304d2d2a3a88cc7a92cb7328bd542a5580e7`.
The receipt is in the final build manifest, alongside the two qualification
binaries. This check did not overlap timing.

## Correctness and evidence integrity

The extracted branchless and short-scan bodies passed **5,502,440** bit-set-oracle comparisons, including integer boundaries and long rows near binary-search size transitions. Deliberate endpoint mutations caused 693,077 and 578,728 disagreements respectively. These are finite executable checks, separate from the conditional human-checkable correctness proofs in [the proof notes](PHASE_XXXI_PROOF_NOTES.md). No proof assistant was used and no novelty is claimed.

All five archived runtime alternatives were rebuilt and passed the native suite under UBSan: 18,432 exhaustive, 1,440 adversarial, 589,824 interval, 153,600 cross-chain, 207,360 forest and 1,296 packed-coordinate checks per alternative. Fifteen adversarial evidence tests reject removed/duplicated cases, missing trials, altered answers, concealed memory growth, missing oracle checks, a nonidentical control, changed selection, changed sources, nonfinite timings, missing qualification cases, altered benchmark source, post-hoc recalibration, wrong qualification control binaries and lowered duration gates.

Timing totals: **6,052 processes**, **7,765,632 BFS pair executions**, and **288,585,979,008 repeated query calls**. These are execution counts, not unique examples or independent replications.

All raw trials and rejected source variants are sealed in [the evidence directory](evidence/phase31/README.md). The initial empty-seed selection failure, missing-include build failure, and repeat-bound rejection are retained; none produced accepted timing data. Verifiers reconstruct exact native input payloads and recompute all reported decisions. Temporary derived gzip fixture containers are not retained; their original compression hashes are receipts, not independently reconstructed cross-version evidence.

## RFP checkpoint

- Exactness propositions: human-checkable proofs under explicit contracts; finite tests executed locally. Formal-checker verification: NOT_EXECUTED.
- Four original performance candidates: failed their pilot gates; their failures remain in the ledger.
- Longer dispatch diagnostic: numeric ratios improved, but minimum-duration gate failed; not a promotion.
- Full-build dispatch qualification: completed; at least one fixed gate fails. Retain PR #30 runtime.
- Global SOTA: UNRESOLVED. Current literature and missing execution obligations are recorded in [the scope audit](PHASE_XXXI_SOTA_SCOPE.md).

Next campaign should begin with the full external-enabled compiler configuration, a duration feasibility preflight, and an identical-binary control. Use a structurally different runtime hypothesis rather than retrying these rejected implementations unchanged. Broader comparator execution and total-memory tradeoff matching remain necessary before a new SOTA claim.
