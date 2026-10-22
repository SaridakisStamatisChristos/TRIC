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

## Pilot findings

To be populated from the exact final-commit CI run. No cost model
results are claimed prior to successful verification.
