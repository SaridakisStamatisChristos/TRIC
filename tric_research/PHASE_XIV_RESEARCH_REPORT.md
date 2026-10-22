# Phase XIV — Exact Bidirectional SCC-DAG Fallback Ablation

## Scientific problem and scope
Phase XIII established that an inexpensive topological bound can sharply
improve the existing TRIC pivot+SCC fallback query path on the bundled arXiv
graph and one published Kronecker instance. O'Reach's query times are still
faster, and comparable memory/preprocessing budgets have not been established.

This phase isolates the fallback search choice and explicitly tests a competing
mechanism: **bidirectional breadth-first search on SCC condensation**, expanding
whichever side has fewer queued but unprocessed vertices. This is established
reachability research (not algorithmic novelty); see O'Reach (SEA 2021,
https://doi.org/10.4230/LIPIcs.SEA.2021.13) and the GRAIL bidirectional
variants described by Yildirim et al. (VLDB Journal, 2012).

## Contract, invariants, and resource cost
Given a fixed directed graph G=(V,E), return the same reachability Boolean
for arbitrary vertices s,t, including self pairs, cycles, duplicated edges,
disconnected graphs and full SCCs. First apply the unchanged Phase XIII
certificate and unchanged workload-trained pivot probe order.

If these tests are undecided, use the condensation DAG D=(C,M).
Precompute its reversed adjacency (the existing forward DAG/topological rank
and SCC map remain intact). Maintain two epoch-visited sets and FIFO queues.
Initialize forward queue={SCC(s)}, reverse queue={SCC(t)}.
Repeatedly expand one queued vertex from the side with fewer outstanding
vertices. Forward expansion only admits vertices with topo rank <=rank(t);
reverse expansion only admits vertices with rank >=rank(s).
Return TRUE on intersection of the two visited sets; return FALSE when one
side has exhausted its queue.

**Why the answers are exact.** Every forward visited component is reachable
from s; every reverse visited component can reach t. Their intersection
therefore certifies an s-to-t path. In every SCC-condensation path, topological
rank strictly increases, so pruning a forward vertex ranked after t or a
reverse vertex ranked before s cannot remove a valid path. If one queue
exhausts without intersection then it has explored every permissible vertex
in that direction, so no s-to-t path exists. SCC contraction preserves
reachability between original vertices. This is a human mathematical
correctness argument, not a proof-assistant verification.

**Complexity.** Existing compact index preprocessing costs
O(|V|+|E|+d(C+M)) for fixed d=4; building reverse arcs adds O(M+C) time and
space. Each bidirectional query's worst case is O(C+M), plus O(1) certificate
checks for fixed dimensions, and uses reusable O(C) visited/queue buffers.
No worst-case sublinear query bound is claimed. `extra_storage_bytes`
reports approximate capacity of reverse adjacency and the reusable visited
and queue buffers, excluding allocator overhead and shared forward DAG/RSS.

## Experiment and falsification
Controls: Phase XIII `compact_topo`, `compact_pivots_topo`, and original
plain/guided variants. Treatment: `compact_bidir` (without pivots), and
`compact_pivots_bidir` (same trained pivot probes; only fallback differs).

- All answers must agree with independently evaluated graph traversal.
- Same query checksums; same pivot probes, rescues and fallback-query counts
  for topological versus bidirectional hybrids.
- Exhaustive 3-vertex directed-graph regression, randomized cyclic/dense
  inputs, deep path, giant SCC, duplicate arcs and disconnected DAGs.
- Count both-direction arcs examined, rather than claiming pruning is free.
- Rotate hybrid plain/topo/bidir execution order across **nine** repetitions;
  each position appears three times per method, reducing fixed order bias.
- Same three seeded train/heldout splits per source graph; unmodified SHA-pinned
  O'Reach pDFS and pBiBFS in the existing CI harness.
- Preserve raw per-run timing, graph/query hashes, source SHA and artifacts.
- Report actual nanoseconds/query. The bidirectional candidate must be
  rejected as a *latency improvement* when slower even if it touches fewer arcs.

## Source availability and fairness
Only the actual accessible arXiv example (6,000/66,707) and
`kron_logn12` (4,096/116,952) are default PR datasets. Three other
authors' dataset archives previously returned HTTP 404, so they are not
claimed as completed replications. Further published graph acquisition
must preserve identity/hash without silent substitution.

This remains a **small pilot**, not a matched-budget comparison: O'Reach has
different index structures and build time, and its output adapter still lacks
independent per-query correctness traces. Hosted-runner timing is not
dedicated-machine performance; graph diversity, mixed/positive query
strata, memory/RSS and full amortization remain open.

## Research decision gates
1. Correctness and C++17/Python CI: must pass without weakened tests.
2. Empirical: if median paired topo/bidir latency ratio >1 on either graph,
   record precisely the winning workload and adverse workload, not a
   generalized superiority conclusion.
3. Mechanism attribution: compare visited arc totals and per-query positive
   fractions to explain divergences where observed.
4. Novelty: no claim of an original bidirectional BFS, topological predicate,
   SCC reduction, or interval certificate.
5. Retain this work as an experimental draft PR; do not merge until results
   and regressions are independently reviewed.

## Reproduction
```bash
cd tric_research
python -m unittest -q test_compact_reachability test_closure_index test_oreach_ci
```
See `.github/workflows/research-oreach.yml`; the artifact includes
`phase14_summary.json` plus per-seed raw comparison data.

## Executed pilot results (GitHub Actions, 2026-10-22)

All Python 3.10 and 3.13 regression jobs passed, including the new
bidirectional tests. Both source-specific paired-native experiment jobs passed
on GitHub-hosted Ubuntu 24.04 runners. O'Reach was compiled from its
previously pinned upstream SHA and run against the exact same query files.

Each graph received three seeded held-out splits of 1,200 queries each;
the native hybrid variants each received nine rotated benchmark repetitions.
The following numbers are **native observed nanoseconds per query**, not
predictions, cross-hardware comparisons, or precision-calibrated estimates.

| Graph / seed | Topological hybrid | Bidirectional hybrid | O'Reach pDFS | Topo/Bidir ratio |
|---|---:|---:|---:|---:|
| arXiv / 20261022 | 438.01 | 387.54 | 300.11 | 1.1303 |
| arXiv / 20261023 | 443.78 | 433.23 | 268.56 | 1.0244 |
| arXiv / 20261024 | 389.76 | 319.98 | 267.35 | 1.2181 |
| Kronecker / 20261022 | 871.57 | 96.83 | 72.27 | 9.0009 |
| Kronecker / 20261023 | 813.82 | 94.03 | 62.78 | 8.6552 |
| Kronecker / 20261024 | 307.28 | 65.49 | 63.14 | 4.6920 |

For the **three arXiv seeds**, median of paired topo/bidir ratios = **1.1303×**.
Medians of native per-seed method timings: topo **438.01 ns/q**,
bidir **387.54 ns/q**, and O'Reach pDFS **268.56 ns/q**.

For **three Kronecker seeds**, median paired topo/bidir ratio = **8.6552×**.
Method medians: topo **813.82 ns/q**, bidir **94.03 ns/q**,
and O'Reach pDFS **63.14 ns/q**. The new method remained slower
than O'Reach in all tested seed pairs on both graphs.

The reverse SCC-DAG and bidirectional buffers added **612,168 bytes** on the
arXiv example and **828,072 bytes** on Kronecker by reported vector-capacity
accounting. These are extra logical storage figures, **not full RSS**.
The direct bidirectional fallback examined fewer arcs than Phase XIII's
topological-only fallback on all observed splits. Fewer arcs do not always
equate to proportional CPU savings (e.g., arXiv), and the observed ratios
must not be generalized to all static directed graphs.

### Source artifacts and audit trail

- [Unit-test CI, run 39743725197](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39743725197) — passed.
- [Paired-native research CI, run 39743725356](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39743725356) — both graph jobs passed.
- [Raw arXiv benchmark artifact](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39743725356/artifacts/12409919019).
- [Raw Kronecker benchmark artifact](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39743725356/artifacts/12409759711).

The artifacts include per-seed `comparison.json`, query files,
`phase14_summary.json`, the original O'Reach CSV, and environment provenance.
Only two graph instances are present. A technical conclusion supported here is
that bidirectional fallback reduces query cost **for these workloads**. An
independent algorithmic contribution, dominance over O'Reach, publication
readiness, and statistical generality remain unestablished.

### Adversarial interpretation

**Alternative explanation:** Graph/query structure—particularly the large
number of costly unresolved queries for plain topological forward DFS on the
Kronecker instance—could account for most of the improvement. Bidirectional
search is known to reduce this work. This is a graph/workload phenomenon, not
independent confirmation of algorithmic novelty.

**High-value next experiment:** stratify queries into positive-only,
negative-only and 50:50 positive/negative batches using the published O'Reach
test distributions where accessible; replicate on much larger graphs with
separately measured graph/label memory and build time. If improvements vanish
on a distinct graph class, retain and explain the negative result.
