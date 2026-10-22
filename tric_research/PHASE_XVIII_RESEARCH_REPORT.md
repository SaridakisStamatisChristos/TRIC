# Phase XVIII — Amortization and structural generalization qualification

**Status before CI:** specified/implemented, no claim of experimental success.

## Research decision being tested

Phase XVII's trained selector showed modest (single-digit to ~15%) query
latency savings in some workloads but required an additional 4–13 ms
of offline policy fitting on just two graph instances. Are the gains
economically meaningful at realistic query volume, and do they survive
structural changes in graph topology?

### Cost equation: incremental only

Given selector fit cost F (measured ns), selector native median query
latency S (ns/query) and same-query exact fallback control B,
the incremental cost over Q *future, similarly distributed* queries is:

- trained selector: F + Q × S;
- untrained control: Q × B.

Break-even exists ONLY if B>S, with
`ceil(F / (B-S))` future queries. At exactly break-even they tie;
strict advantage requires `Q×(B-S)>F`. Report `null` if the
selector is slower or equal.

The report separately exposes the existing **common Python pivot training,
native pivot index construction, and native SCC index construction**. These
components were already shared between selector and control in the harness.
Do NOT sum all three and call the result a deployable end-to-end runtime:
the research harness redundantly constructs pivot objects in Python and
C++. These common costs cancel in the *incremental* comparison, which
is the supported research question.

The measured selector fitting time begins after the independent
training-query oracle verification in the native code. Thus reported
fit time EXCLUDES oracle validation and compiler/pivot training; it is
an **optimistic lower bound** on total selector-specific offline cost.

### Horizons

Report 1,200 / 10,000 / 100,000 / 1 million / 10 million
projected requests from same-seed paired medians. Larger horizons are
**extrapolations, not newly executed million-query benchmarks**.
Do not pool graphs. All measured source times and query/graph hashes
remain available in per-seed raw benchmark artifacts.

## Additional independent *synthetic* graph structures

Continue both original source graphs, and explicitly add reproducibly
constructed graphs using existing `tric.graph_family` algorithms:

| Source | Vertices | Graph type | Provenance |
|---|---:|---|---|
| Original bundled arXiv | 6,000 | Directed citation example | Original O'Reach repository |
| `kron_logn12` | 4,096 | Kronecker | Published O'Reach archive |
| `synthetic_chain` | 720 | Forward chain with shortcuts | **Synthetic** TRIC generator |
| `synthetic_blocks` | 720 | Directed disconnected local blocks | **Synthetic** TRIC generator |
| `synthetic_communities` | 720 | Directed modular communities with SCC cycles | **Synthetic** TRIC generator |

The latter three are **not O'Reach authors' original datasets**, and
cannot substitute for independent real-world external validation.
They are deterministic **stress-test structures**, using seed
20261022, one-based directed METIS output and SHA256-provenance
manifest `synthetic_graph_manifest.json`.

The same unmodified O'Reach SHA-pinned executable is run against each
synthetic source graph, with an identical query file for both algorithms.
No SOTA or real-world graph replication claim follows from this.
Potential deterministic dependence between synthetic graph generator
families should not be disguised as independent graph-source evidence.

## Falsification and evidence gates

1. **Exactness and source identity.** On every source graph, all
   native selector and fallback answers must match the independent
   BFS oracle; O'Reach process/row/query-type integrity must pass;
   no silent graph substitutions.
2. **Strict separation.** A policy is trained on uniform training
   pairs only. No heldout results, outcomes, positive fractions, or
   posthoc test times may determine dispatch; test labels are for
   independent evaluation only.
3. **Realistic accounting.** Pay incremental fitting cost. Compare
   selector against **both** original untrained bidirectional and
   topological exact fallback controls, not just its easier rival.
4. **Sensitivity to query mix.** Original `uniform`, `positive`,
   `negative` and `balanced` regimes and three seeds are preserved
   per graph. Record policy-ID instability under equivalent train
   seeds as explicit negative evidence.
5. **Evidence quality.** GitHub-hosted runner timing is noisy,
   indexing/memory budgets differ from O'Reach, and O'Reach per-query
   answers are not separately exported for independent verification.
   Observed query latencies are source-specific, not general rankings.
6. **Reject even plausible conditional superiority** if observed
   net savings do not amortize training at intended query volume.

## Verifiable artifacts and code

- `phase18_synthetic_graphs.py` — original graph-family reuse;
  deterministic METIS and per-graph SHA manifest.
- `summarize_phase18.py` — strict single-graph/3-seed/4-stratum ledger,
  traceable break-even arithmetic and extrapolated volume scenarios.
- `test_phase18_amortization.py` — adversarial checks for arithmetic,
  impossible/mismatched graphs, false strata, invalid query hash,
  broken pivot accounting, and deterministic graph serialization.
- Existing `research-oreach.yml` — **five source-graph jobs**,
  each comparing the pinned original upstream O'Reach and TRIC
  with 12 heldout sets (4 classes × 3 seeds).
- Existing `verify.yml` — Python 3.10 and 3.13 all research tests.

**Default:** retain Phase XIV plain bidirectional and Phase XIII
topological controls; neither trained routing nor two-sided interval
pruning becomes the production default. All prior PRs stay unmerged
pending user authorization. Novelty and SOTA statuses are **NO-GO**.
