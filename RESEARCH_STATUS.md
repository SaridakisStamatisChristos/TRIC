# TRIC research continuation — Phase XXXII

Baseline: PR #31, `09003cb9d7b915516767894f4881542bb8ff4c44`, whose runtime is
identical to PR #30. Phase XXXII releases the interval construction directory
after its final use. This is a retained-memory improvement, not a new reachability
algorithm or latency qualification. Read [the report](tric_research/PHASE_XXXII_RESEARCH_REPORT.md)
and [reproduction instructions](tric_research/evidence/phase32/README.md).

The allocation campaign covers 15 purpose-built cases and 27 preserved fixture
files, including every distinct pair from every original query case. Independent
allocation tracking, BFS, move/destruction checks and a separate full-build smoke
campaign support the change. Admission rules and query source remain unchanged.
Freed directory bytes are not re-spent. Direct closure and forest routes do not
benefit from this change. Generalized SOTA remains unestablished.

Phase XXXI's four rejected candidates remain rejected: branchless residual
search, four-interval scan, Eytzinger residual layout and switch dispatch. The
favorable narrow dispatch diagnostic never superseded failed qualification.
Historical evidence and source snapshots remain intact and independently checked.

Next priorities:

1. Investigate construction work or a different representation using explicit
   correctness and resource contracts.
2. For any speed claim, start with the full comparator-enabled compiler settings,
   preflight replay bounds, freeze acceptance criteria and include an identical
   binary control plus genuine single-pass workloads.
3. Fresh external comparisons must use the exact changed runtime and match total
   memory as well as table allowance; Phase XXX wins cannot be reassigned to a
   later implementation without execution.
4. Broaden real-world topology coverage and reproduce on an independent host.

This checkpoint does not imply background execution.
