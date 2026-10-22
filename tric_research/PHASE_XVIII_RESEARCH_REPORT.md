# Phase XVIII — Incremental Selector-Fit Amortization Audit

## Decision to resolve

Phase XVII verified that an outcome-blind, offline-fitted fallback selector
often saved tens of nanoseconds per query on two small source graphs.
However it required additional milliseconds of selector fitting.
**Question:** Given the actual *paired per-seed* latency observations and
measured fit cost, how many future queries would be needed merely to
break even against the existing bidirectional or topological hybrid?

This phase is a **strict cost-accounting and provenance audit**, *not* an
executed million-query replay or a new search algorithm. We predeclare
scenarios Q = 1,200; 10,000; 100,000; 1,000,000; 10,000,000, and refuse
to imply those volumes were timed on real runners.

## Cost contract (within-TRIC incremental comparison only)

Let F be the selector's **measured additional C++ fitting time in ns**
from the native benchmark (including trying nine rules and choosing one).
Let B be a baseline's observed *median* ns/query and S the selector's
observed *median* ns/query on the **same graph, seed and heldout class**.

The incremental-cost projection is:

    Cost(selector, Q) - Cost(baseline, Q) = F + Q*(S-B).

If B <= S, **there is no positive finite break-even query count**.
If B > S and F >= 0, the smallest integer Q for which the selector's
projected cost is *strictly lower* is floor(F/(B-S))+1.

The indicator at each declared volume Q is merely
`Q*(B-S)-F > 0`. These are projected costs from a fixed query-rate
assumption, not measured throughput at that volume and not a confidence
interval.

The common SCC indexing, pivot training and search-label construction
are identical in the tested TRIC artifact and cancel *between the
existing TRIC selector and its control methods*. They **do not** cancel
against external O'Reach, for which these accounting projections make
**no comparison**. A dedicated topological-only deployment might also
eliminate reverse-graph buffers, so this is not a complete resource
comparison across differently optimized product designs.

### Excluded costs and bias

The selector fit timer in Phase XVII started **after** the training-query
independent BFS correctness oracle was computed; we therefore exclude
that experiment-only oracle cost and ordinary shared TRIC preprocessing.
We must not label the results as absolute deployment start-to-finish costs
or assert the measured F captures all candidate production preparations.

An extrapolation assumes the measured median rate per query holds when
Q is much larger and the graph/query mix stays unchanged; those
assumptions require an actual long-horizon replay or dedicated-machine
measurement to validate. GitHub-hosted nanosecond-scale timing and
train policy instability are major unresolved effects.

## Evidence integrity

The harness now records a cryptographic SHA256 fingerprint of the
actual uniform training pairs used by **both** the original pivot method
and the selector (no evaluation pairs included). The per-stratum JSON
also records the seed. Phase XVIII's summary rejects:

- mixed graph SHA values and duplicate/incomplete seed×stratum matrices;
- absence of 500 train-only queries, mismatched train counts, or a
  different train-pair fingerprint for the **same seed** across heldout classes;
- an incorrect BFS truth checksum, changed pivot probes/rescues/fallback
  totals, or a broken selector-dispatch counter;
- nonpositive/nonfinite query latencies or negative/nonfinite fit cost;
- positive/negative/balanced query labels that disagree with BFS ground truth.

The final output explicitly shows policy IDs chosen across classes for
the *same training data*, to expose timing-based fitting instability
instead of mistakenly attributing different choices to different
training sets.

## Execution and replication

The existing paired O'Reach workflow is run unchanged except for the
new training fingerprints and the independent Phase XVIII summary.
The original O'Reach SHA and all graph/query generation, train/test
seeds, source hashes, query strata, native timing repetitions and
compiler flags are preserved. Python 3.10/3.13 regressions include
`test_phase18_amortization`.

```bash
cd tric_research
python -m unittest -q test_phase18_amortization test_compact_reachability
```

A successful final CI run uploads `phase18_amortization.json` per graph
alongside all raw per-seed `comparison.json` and input provenance.
It reports win counts at each Q, *not* an invented combined result
from pooling unrelated graphs.

**Novelty and deployment judgment:** No novel algorithm claimed,
and Phase XVII's trained selector must remain experimental unless
there is repeatable **end-to-end**, resource-matched benefit at the
actual intended query volume. Even favorable amortized projections
do not establish such a benefit.

## Executed pilot evidence (2026-10-22)

[Python 3.10 and 3.13 unit CI (both successful)](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39778413924).
[Full paired O'Reach research CI (both graph jobs successful)](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39778413930)
at source SHA `f7f65fc5dad7fbdc2ab2cbc2c6aa87c11f70dfb0`.
Raw per-seed graphs, query pairs, verified training fingerprints and
`phase18_amortization.json` reports are included in the
[arXiv artifact](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39778413930/artifacts/12426295064)
and
[Kronecker artifact](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39778413930/artifacts/12425134390).

### Observed *and* modeled evidence

- Both graphs × all four heldout classes × all three seeds passed the
  independent BFS checksum, original pivot-work accounting, exact true/false
  label composition, and uniform **same-seed training input fingerprint**
  checks. None required revising the training samples or query sets.
- **Measured:** the selector fit cost F, per-query native method medians,
  and the selected policy on each seed. This run's fitted policies should
  not be presumed stable across different hosted runners.
- **Derived, not measured:** net cost of Q future queries calculated from
  the equation above using each pair of observed times. Query volumes
  beyond 1200 were **not executed**, and this is not a real time-series
  or empirical scaling measurement.
- **At Q=1200:** selector projected net win against *either baseline*
  in **0/24** graph×seed×class comparisons: extra fit dominates.
- **At Q=1,000,000:** projected selector wins against **original
  bidirectional fallback** by class:

| Graph | Uniform | Positive | Negative | Balanced |
|---|---:|---:|---:|---:|
| arXiv | 3/3 | 2/3 | 3/3 | 2/3 |
| Kronecker | 0/3 | 0/3 | 0/3 | 0/3 |

- Against **topological-only fallback at Q=1,000,000**:
  arXiv uniform 2/3, positive 3/3, negative **0/3**, balanced 3/3;
  Kronecker uniform 3/3, positive 3/3, negative **0/3**,
  balanced 3/3. Be careful: a topology-only implementation might
  save reverse-DAG memory absent in the shared experimental index.

### Key refutation: run-to-run instability on Kronecker negative queries

Phase XVII's earlier benchmark gave the selector ~9% query-only
advantage over bidirectional search on Kronecker negative-only splits.
In the Phase XVIII rerun on the unchanged selection implementation, the
selector had **no per-query advantage in any of the three negative-only
splits**, so no finite incremental break-even exists on those seeds,
irrespective of the future query count. The earlier apparent gain
was **not robust to a new hosted-runner environment**.

This is empirical evidence *against* promoting the selector to the
default path. The regression is not evidence that the underlying
routing idea can never work: dedicated-machine training/evaluation,
broader graph families, and much larger independently sampled query
batches are necessary to distinguish true selection benefit from
training/performance measurement noise.

### Research verdict

- **PASS —** implementation, independent tests, data provenance and
  correctness-conditioned break-even accounting.
- **REJECTED —** claim that the fitted selector is beneficial at 1200
  queries (24/24 comparisons showed a modeled deficit).
- **UNRESOLVED —** general amortized benefit at larger real-life query
  volumes; the table is explicitly conditional extrapolation, not
  a measured million-query benchmark.
- **NO-GO —** new production default, claimed superiority over O'Reach,
  SOTA/novelty, or publication readiness.

**Next high-information experiment:** actual long-volume query replay on
dedicated machines using separately timed warm/cold cache regimes,
independent graphs, and fully accounted index/Python-training/selector
fitting costs. This was **not performed in Phase XVIII**.
