# TRIC external benchmark — GitHub Actions pilot

The `TRIC external reachability research` workflow runs a paired experimental
comparison on a hosted Ubuntu 24.04 runner. It uses the **unaltered**, pinned
O'Reach source commit `78b3e326bbb021b7ee225ab605a4cdd074fa1d93`
and compiles both tools from source on the same runner.

**Trigger:** Pull requests touching the harness/workflow run O'Reach's bundled
6,000-vertex arXiv example. Once the workflow is in the default branch, its
manual `workflow_dispatch` offers `arXiv`, `go_sub`, and `kron_logn12` from the
authors' data website. Failing downloads fail the experiment; the workflow
never silently substitutes synthetic data or marks the comparison successful.

**Experimental protocol:**

1. Read the same directed METIS graph (1-indexed neighbor IDs).
2. Choose candidate pivots from graph degree only; train the TRIC order on
   deterministic random queries with seed 20261022.
3. Generate an independent, seeded held-out query file; annotate the true/false
   answers using independent BFS. O'Reach and TRIC receive those same pairs.
4. O'Reach reports both its pruning DFS and pruning bidirectional BFS variants.
   TRIC runs raw BFS, empty-policy control, greedy coverage, and exact
   ordered-cost selection in a shared C++17 executor.
5. Save raw timings, all measured C++ query samples, graph/query SHA256,
   training time, candidate pivots, compiler information and O'Reach commit.
   Run each O'Reach mode in five separate invocations and rotate TRIC's policy
   execution order over seven repetitions.
6. Report training and index-build overhead separately from query latency.

**Scientific restrictions:**

- This is a **cross-system pilot**, not proof of SOTA, nor matched-memory or
  matched-build-budget evaluation. O'Reach indexes the complete graph with
  different data structures; TRIC's pivot count is intentionally bounded.
- TRIC query answers are checked against an independent BFS oracle. O'Reach
  is executed unmodified; this harness does not yet independently capture
  per-query O'Reach answers. A full correctness comparison would require a
  validated output adapter or upstream instrumentation.
- GitHub-hosted shared CPUs are noisy. Repeated CI runs, paired order
  randomization, memory/RSS accounting, confidence intervals, representative
  datasets, and proper ablations are still needed for publication evidence.
- Dataset availability, license/attribution requirements, and the workflow's
  runtime must be checked before adding larger cases; no output is invented.
- The project retains historical experiments and open PRs intact.

Citation: Kathrin Hanauer, Christian Schulz, Jonathan Trummer,
*O'Reach: Even Faster Reachability in Large Graphs*, SEA 2021,
https://doi.org/10.4230/LIPIcs.SEA.2021.13 .
Source: https://github.com/o-reach/O-Reach .
Dataset site: https://oreach.taa.univie.ac.at/ .
