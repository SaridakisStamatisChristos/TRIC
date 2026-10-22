# Phase XIX — Measured warm-index query batches

## Decision and continuity

Phase XVIII PR #16 projected selector cost at large query volumes from
1,200-query medians. This phase replaces that extrapolation with executed
batches. It is stacked on `785875a22557ce44f249184ef83cecd87264c49d`,
without merging or replacing either Phase XVIII branch (#15/#16).
Both Phase XVIII final-head research and test workflows were successful
when inspected on 2026-10-22; PR #15's earlier pending-status prose is stale.

Question: on separately sampled **uniform pairs**, does the existing trained
selector save enough measured batch time to recover its additional fit cost
against the existing topological or bidirectional hybrid?

## What changed

- `native_query_bench.cpp` has an opt-in `--lifetime` mode. The existing
  default query implementations, fit procedure and benchmark mode remain.
- `lifetime_replay.h` measures three full hybrid arms (topological,
  bidirectional, trained selector), retaining certificate/pivot counters.
- `benchmark_lifetime.py` constructs reproducible train and evaluation
  inputs, fits pivots on training only, records provenance and checks
  complete paired measurements. The native selector is fitted **once per
  seed**, then frozen across every query horizon and repetition.
- `test_lifetime_replay.py` checks all 64 three-vertex directed graphs,
  independent Python FIFO truth counts, cyclic/disconnected/self/duplicate
  pairs, strict equality accounting and deliberately corrupted evidence.
- A separate CI workflow retains raw measurements and exact input files.
  It uses O'Reach's graph sources but **does not run its algorithm**; the
  older paired external benchmark workflow remains separate.

This is experimental evaluation infrastructure, not a newly invented
reachability mechanism or a change to the production/default selector.

## Protocol

- Graphs: pinned O'Reach arXiv example (6,000 vertices / 66,707 arcs) and
  published Kronecker logn12 (4,096 vertices / 116,952 arcs).
- Seeds: 20261022, 20261023, 20261024; 500 uniform training pairs using
  `seed+1`; one million evaluation draws using `seed+2`.
- Training and evaluation use independent PRNG streams, **not disjoint
  pair sets**. Sampling is with replacement. Each result records unique
  evaluation pairs and natural overlap with training; neither duplicate
  draws nor timing repetitions are called independent evidence.
- The first 1,200 / 10,000 / 100,000 / 1,000,000 draws form nested batches.
  Each batch is actually executed nine times in three-position balanced
  method order; query order is shuffled identically for all arms in a pair.
  Horizons run in increasing order and are not independent replications.
- Before timing, original-graph traversal computes exact reachability once
  per source, storing only one reachability bit row at a time. Every answer
  from each of the three arms is compared individually with that oracle.
  Each timed batch also checks an order-sensitive checksum against oracle
  truth and equal pivot probes, rescues and fallback counts.
- Each method receives a full identical-batch warmup immediately before
  its timed batch. This is a **warm-index** protocol. No cache flushing,
  cold-start workload, separate-process timing, CPU isolation, frequency
  locking, or dedicated-machine guarantee is asserted.
- Compiler: recorded in raw evidence, C++17 `-O3 -DNDEBUG`; native selector
  fitting uses the unchanged Phase XVII nine-policy/nine-rotation procedure.
  Its timer includes per-answer training checks; timed evaluation uses
  checksums/counters. This pre-existing fitting/evaluation instrumentation
  mismatch is a potential selection-quality limitation, not hidden overhead.

## Cost meaning

For each paired repetition and horizon, compute

    observed_incremental_saving = measured_baseline_batch_ns
                                - measured_selector_batch_ns
                                - measured_selector_fit_ns.

Report the median of these paired differences and the count strictly above
zero. **Do not subtract separate method medians**: that is a different
statistic under noise. Equality is not a win. A single observed fit cost is
charged once to each hypothetical deployment of that measured query batch;
the fit itself was not rerun for each timing repetition.

All horizons are measured query workloads; the incremental total is an
accounting sum of observed components, not an extrapolated rate. It is
still **not start-to-finish deployment time**: shared Python/native pivot
preparation, SCC construction, training-oracle generation, I/O, validation
and warmups are excluded from the incremental comparison. Python pivot
preparation and native index construction are separately recorded, and
must not be naively summed into an optimized production build estimate.
The two baseline arms share the same index; a specialized topo-only
deployment could remove reverse-DAG memory. No matched-memory O'Reach
comparison is made here.

## Sources and reconstruction

arXiv: `examples/arXiv.metis` from
`https://github.com/o-reach/O-Reach` commit
`78b3e326bbb021b7ee225ab605a4cdd074fa1d93`.
Graph SHA256: `12a89444586f2eaca16dc17951a999efca2b879f87f566b8c3f67714bc2b3ab2`.

Kronecker archive:
`https://oreach.taa.univie.ac.at/assets/data/instances/kron_logn12.tar.xz`.
Archive SHA256: `fce81156429ea01c218f837cdc94c9879a890ee38320e6a829b3240c5769a2ae`.
Member: `kron_g500-simple-logn12.metis/kron_g500-simple-logn12.metis`.
Graph SHA256: `f81f2b31f90f6873360b89f6af1963e165f6912cf407fd5f45bebcf9ed55fa22`.
The CI workflow checks these hashes before execution.

Run from `tric_research` (once for each graph):

```sh
python benchmark_lifetime.py --graph /path/to/graph.metis \
  --output-dir /path/to/results --queries 1000000 --train 500 \
  --candidates 11 --budget 5 --seeds 20261022 20261023 20261024 --repetitions 9
```

Source-code hashes, input/pair hashes, compiler/CPU details, per-seed raw
batch durations/checksums/counters and derived summaries are retained in
`evidence/phase19/`. Raw timing observations are not fabricated from a model.
Exact input files can be regenerated from these pinned sources/configuration;
the CI artifact also retains them directly. Timings are not expected to
reproduce bit-for-bit.

## Validation and scope

Local research suite: **86 tests passed**, including legacy native/compact
tests and six new lifetime tests. Three-vertex exhaustive subcases are
within one test method; they are not counted as 64 separate suite tests.
Workflow YAML parses, and `git diff --check` passes.

Local environment: AMD EPYC 9V74, GCC 13.3.0, Python 3.12.14; shared
execution environment. Graph runs were sequential, with the test suite
finished before timing. This does not exclude unrelated host activity.

No fresh novelty search was conducted because no novelty claim is made.
This phase cannot certify general SOTA, external-baseline superiority,
publication readiness, cold-cache performance, or broad graph coverage.
The frozen policy and long batches close specific experimental gaps;
they do not close the matched-resource and dedicated-hardware gaps.

## Executed local results — 2026-10-22

One million uniform draws per graph/seed; values below are median paired
net savings **after fit**, in milliseconds. Positive favors the selector.

| Graph | Seed | Frozen policy | Fit ms | Net vs topo ms | Net vs bidir ms | Net wins vs bidir |
|---|---:|---:|---:|---:|---:|---:|
| arxiv | 20261022 | 5 | 9.513 | -19.764 | -12.292 | 0/9 |
| arxiv | 20261023 | 4 | 12.247 | -11.445 | -16.059 | 2/9 |
| arxiv | 20261024 | 4 | 7.303 | -12.571 | -5.272 | 4/9 |
| kron | 20261022 | 4 | 10.992 | +630.225 | -22.149 | 2/9 |
| kron | 20261023 | 4 | 11.720 | +716.902 | +4.026 | 5/9 |
| kron | 20261024 | 4 | 6.147 | +249.365 | -7.977 | 3/9 |

**Finding:** arXiv loses after fit on all three seeds against both controls.
Kronecker beats the slower topological control on all three seeds, but beats
bidirectional on only one of three seed medians (5/9 paired repetitions for
that seed). Thus the fitted selector does not show a consistent net benefit
over the stronger bidirectional baseline, even at one million uniform
queries. Do not choose a favorable seed or the weaker baseline to declare
success.

These observations challenge favorable Phase XVIII rate projections under
this larger sampled workload and environment; they do not invalidate its
algebra or prove that a routing policy can never pay off. The seeds and
timing repetitions share graph instances and a host, so they are not
independent graph or hardware replications.

Across both graphs, six million query draws were validated per arm (three
arms = 18 million answer comparisons). Nine repetitions at the four
horizons give 180,014,400 **timed** query executions across all arms and
cases; warmup and validation executions are excluded from that number.
The independent evidence remains two graph instances, not 180 million
independent tests of generalization.

**Disposition:** preserve this draft as negative/conditional evidence.
Do not promote the selector to default. A subsequent controlled experiment
should first align fitting and evaluation instrumentation and assess
policy stability on isolated hardware before adding further heuristics.
Larger independent graphs, outcome-conditioned million-query batches,
matched-resource external baselines and cold-start/end-to-end costs remain
unresolved. No SOTA or novelty claim.
