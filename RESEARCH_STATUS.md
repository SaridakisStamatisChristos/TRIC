# TRIC research continuation — Phase XXXIII

Current accepted runtime: PR #32,
`02a91849193e12266785ecfd1d49cd8d87b458f2`. Phase XXXIII leaves every production
header unchanged. Read [the report](tric_research/PHASE_XXXIII_RESEARCH_REPORT.md)
and [reproduction instructions](tric_research/evidence/phase33/README.md).

Three construction experiments were tested. Closure pruning and smaller merge
buffers failed the pilot. Stable CSR transpose storage passed the pilot but failed
qualification controls. After its empty-graph allocation regression was fixed,
a single preregistered replication still failed the fresh-process construction
floor on a dense graph and one identical-binary control. Both the replication and
pooled data had to pass; favorable pooled medians do not authorize promotion.
All 8,767 construction timing processes and failures are preserved.

Phase XXXIII also expands comparison coverage to six pinned C++ implementations
of FELINE, GRAIL, PReaCH, FERRARI, TF-Label and TOL. These are warm repeated-query,
implementation-specific comparisons with independently checked answers. They are
not memory-matched, do not replace original-author baselines, and do not establish
generalized SOTA. The report records qualified cells and control failures.

Phase XXXI's four rejected query candidates also remain rejected. The Phase XXXII
interval-directory release remains the latest accepted runtime improvement.
Historical results, gates and source snapshots stay independently verifiable.

Next work should address the dense-graph single-build regression with a new
construction strategy and genuinely new held-out inputs, then repeat the fixed
correctness, resource and speed gates. External superiority still needs comparable
total-memory budgets, more recent/original-author implementations, broader large
graph families and independent-host reproduction. Do not repeat the same campaign
until it happens to pass or transfer old wins to a changed runtime.

This checkpoint does not imply background execution.
