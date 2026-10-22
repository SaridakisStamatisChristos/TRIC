# Phase XV — Outcome-Stratified Reachability Qualification

**Research artifact:** stacked, unmerged draft, targeting
`research/phase-xiv-bidirectional-fallback`.

## Problem and testable hypothesis

The previous TRIC Phase XIV showed meaningful in-repository improvements from
an exact bidirectional SCC-DAG fallback, especially on one small Kronecker
instance. But almost all benchmarks used *uniformly random query pairs*.
This is not sufficient to determine whether the query strategy generalizes.

The original O'Reach study (Hanauer, Schulz & Trummer, SEA 2021,
[DOI 10.4230/LIPIcs.SEA.2021.13](https://doi.org/10.4230/LIPIcs.SEA.2021.13))
reports that performance depends strongly on the true reachability result and
provides random/true/false/mixed query collections. Current reachability
indexing surveys, e.g. Zhang, Bonifati & Özsu (ACM CSUR 2025,
[DOI 10.1145/3776737](https://doi.org/10.1145/3776737)), show that
bidirectional pruning and SCC/landmark indexing are established techniques.

**Main question:** Does Phase XIV's bidirectional hybrid remain faster than
Phase XIII's topological-only hybrid on each of the positive, negative,
balanced and uniform-query distributions? How does this compare with the
same unmodified pinned O'Reach algorithm?

No proposed mechanism is claimed novel in this phase.

## Four reproducible regimes

| Regime | Query labels | Meaning |
|---|---|---|
| `uniform` | Not controlled | Independent uniform `s,t` from earlier phases, self allowed |
| `positive` | 100% true | Uniform eligible source, random distinct reachable target |
| `negative` | 100% false | Uniform eligible source, random distinct unreachable target |
| `balanced` | 50% true, 50% false | Half of each class (floor for odd sizes), shuffled |

Positive and negative classes use **independent oracle BFS**, not
`CompactReachability` certificates, pivots or O'Reach labels.
The *sampling process* draws uniform source vertices conditioned on at least
one eligible non-self target, then uniform targets within that source's
qualifying destinations. Thus **source-uniform conditional strata are not
uniform over all ordered reachable/unreachable vertex pairs**. This is a
different distribution from O'Reach's published query files and must never be
called a reproduction of its original query set.

**Self pairs are removed from the stratified classes** to prevent an easy
`s==t` path from inflating positive outcomes. Uniform pairs retain
self-pairs for exact backward compatibility. This changes more than just the
outcome ratio, so only like-for-like methods *within* a stratum can be
compared causally.

All query source/target labels are written to the O'Reach-compatible query
file and independently checked again by the existing `early_reachable` oracle
and C++ graph traversal. A graph with no nontrivial positive or negative
pairs raises an explicit error instead of silently changing the target class.

## Controlled paired experimental protocol

- Reuse the published O'Reach arXiv example and `kron_logn12` sources with
  graph SHA256 preserved.
- Per graph and regime, generate **three** independent seeded train/test
  splits (seeds 20261022, 20261023, 20261024). Held-out evaluation is 1,200
  queries per split. Training is always **500 uniform pairs** with the same
  seed, degree-based pivot candidates and budget across all four regimes;
  labeled held-out outcomes do not influence pivot training.
- Run original pinned O'Reach commit
  `78b3e326bbb021b7ee225ab605a4cdd074fa1d93`
  (pDFS and pBiBFS) against the **identical held-out query file**,
  with five independent native repetitions per split.
- Run exact TRIC native C++ hybrid topo and hybrid bidirectional, with
  nine three-way position-rotated timing repetitions per split.
- Report median times in *nanoseconds per query*, median paired ratios,
  3/3 win counts, pivot probes/rescues/fallbacks, positive fractions,
  per-method checksum, and BFS oracle validation.
- Never pool graph identities or reinterpret query splits as graph replications.
- Retain raw `comparison.json`, O'Reach CSV, query files, source hashes,
  toolchain manifests, `phase15_summary.json`.
- Expand Python 3.10 and Python 3.13 unit CI to include earlier Phases X–XIV
  C++ regressions plus new query-generation tests.

## Refutation and acceptance gates

1. **Correctness:** all benchmark truth checksums equal the independent BFS
   oracle, and the exact target positive fraction is attained for each stratum.
2. **Reproducibility:** deterministic query seeds; no hidden dataset
   substitution; source SHA/checksums; actual working CI runs.
3. **Answer-class robustness:** explicitly identify any negative outcome
   class or graph where Phase XIV loses to Phase XIII, and quantify the loss.
4. **Baseline fairness:** only compare on exactly identical pairs, workload
   size, hardware job and reporting metric. Label differences in memory,
   index preparation and sampler assumptions separately.
5. **Research novelty:** none claimed: SCC condensation, bidirectional
   traversal, interval filtering and topological rank checks are known.

## Non-goals and limitations

These are two small graphs on GitHub-hosted machines. Graph-specific
variability, positivity class sampling bias, 1,200-pair batch timer effects,
unmatched preprocessing and index RSS versus O'Reach, missing per-query O'Reach
answer export, and source-code execution of upstream O'Reach all prevent a
broad SOTA superiority conclusion.

If a class suffers large losses, the result is valuable evidence against
overgeneralizing Phase XIV and motivates an independently evaluated
cost-based dispatch policy; no adaptive dispatch method is preauthorized by
this phase.

## Rerun

```bash
cd tric_research
python -m unittest -q test_stratified_queries test_oreach_ci test_compact_reachability
```

See `.github/workflows/research-oreach.yml` for pinned upstream build,
all four strata and three seeded splits; reports are emitted as raw artifacts.

## Executed results — 2026-10-22, Phase XV code SHA `db129fd4e7b7f19b`

Both Python 3.10 and Python 3.13 expanded research regressions passed
([unit CI run 39746729519](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39746729519)).
The two native external graph jobs independently passed with source checksum,
query count, true/false composition, per-method answer checksums, identical
pivot probe accounting, and O'Reach on each exact query file:
[external CI run 39746729504](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39746729504).

**All values below are observed query-only nanoseconds per query.** Each cell
uses the median across three independently seeded held-out query sets (1200
pairs per seed); "ratio" is the median of the three *paired per-seed
topological/bidirectional ratios*, not the ratio of reported medians.

| Graph | Stratum | Phase XIII topo hybrid | Phase XIV bidir hybrid | O'Reach pDFS | Paired topo/bidir median | Bidirectional wins |
|---|---|---:|---:|---:|---:|---:|
| arXiv | uniform | 445.25 | 396.91 | 283.06 | 1.1355x | 3/3 |
| arXiv | positive | 960.01 | 551.16 | 609.80 | 1.6653x | 3/3 |
| arXiv | negative | 291.24 | 344.39 | 135.86 | **0.8517x** | **0/3** |
| arXiv | balanced | 692.20 | 532.44 | 433.97 | 1.2699x | 3/3 |
| Kronecker | uniform | 757.87 | 78.33 | 54.40 | 9.6675x | 3/3 |
| Kronecker | positive | 2781.56 | 239.18 | 142.69 | 11.6295x | 3/3 |
| Kronecker | negative | 27.22 | 27.30 | 9.74 | **0.9968x** | **1/3** |
| Kronecker | balanced | 1509.91 | 138.40 | 79.93 | 10.6920x | 3/3 |

**Strong falsification result:** the bidirectional fallback is not uniformly
faster than forward topological fallback. On the arXiv negative-only regime,
the bidirectional method is slower in **all three** splits (paired ratio
0.8517x); on Kronecker negative-only the two are essentially tied, while
O'Reach pDFS stays markedly faster. This supports workload sensitivity,
not universal dominance.

**Narrow positive-only observation:** arXiv's bidirectional method was
faster than O'Reach pDFS in all three source-uniform positive splits:
TRIC 542.76/551.16/576.49 ns/query versus O'Reach
574.42/621.31/609.80 ns/query. Median paired TRIC/O'Reach ratio:
**0.9449** (~5.8% lower observed latency). This is a small, specific regime
and not a general superiority result; differences in index memory and
preprocessing, noisy runners, and no independent per-query O'Reach answer
export remain major blockers.

### Exact query provenance and class composition

Each positive and negative set consists of 1,200 **non-self** ordered vertex
pairs independently classified by BFS. Balanced consists of exactly 600
positive and 600 negative non-self pairs. The historic uniform classes
include self-pairs, and their positive counts on arXiv were
192, 156, 197 out of 1200; on Kronecker 334, 325, 324.
The source-conditioned sampling differs from the O'Reach authors' query
distribution; this is not a reproduction of their published performance
figures. Repeated runs with the same graph and seed are dependent evidence.

### Raw evidence

- [arXiv CI artifact, all 12 seed/stratum combinations](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39746729504/artifacts/12412290061).
- [Kronecker CI artifact, all 12 combinations](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39746729504/artifacts/12411348241).
- Each artifact retains `phase15_summary.json`, per-seed
  `comparison.json`, the oracle-labeled query files, raw O'Reach CSV,
  graph hashes, compiler provenance and C++ results.

### Independent code/research auditor decision

**PASS:** correctness regression and paired external experiment execution
for the stated two graphs and four query regimes.

**NO-GO:** blanket "bidirectional is always faster", blanket SOTA superiority,
original algorithmic novelty, paper readiness or system-wide efficiency
claims. The evidence points to a selective fallback strategy as a
*testable design hypothesis* but the query's true label cannot legitimately
be used as a runtime selector: it is unknown before executing reachability.
Any dispatch policy must be based on inexpensive query-visible features,
trained on separate data and compared honestly against both unconditionally
selected methods.

Future gates: compare memory/preprocessing budgets, obtain diverse graphs,
independent O'Reach per-query outcome export, and test a preregistered
feature-only selector on held-out workloads before generalizing.
