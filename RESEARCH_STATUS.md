# TRIC research continuation

Current accepted runtime: PR #30, commit
`ac810f576d9dbc6ef2b9579725e6603d3ad4e049`.

Phase XXXI is a completed falsification and measurement campaign, not a promoted
runtime optimization. Read [its report](tric_research/PHASE_XXXI_RESEARCH_REPORT.md),
[proof obligations](tric_research/PHASE_XXXI_PROOF_NOTES.md), and
[current comparator gaps](tric_research/PHASE_XXXI_SOTA_SCOPE.md).

Do not resurrect branchless residual search, the four-interval scan, Eytzinger
residual layout, or switch dispatch as accepted changes. Their source trees,
all losses, negative controls, diagnostics and full qualification are archived.
The favorable narrow dispatch diagnostic did not supersede its failed broader
qualification. No global SOTA claim is established.

Before another optimization campaign:

1. Verify all Phase XXXI evidence and run its evidence-tampering tests.
2. Use the full comparator-enabled compiler configuration from the start.
3. Preflight repeat bounds against the minimum timed-duration requirement.
4. Include an identical-binary control, actual memory accounting, original
   cohorts, new query/topology inputs and genuine single-pass tests.
5. Freeze candidate code and acceptance criteria before qualification. Retain
   failed trials and protocols; do not tune on qualification results.
6. Only promote an implementation after correctness, resource and performance
   gates pass. External superiority requires fresh comparator measurements on
   that exact accepted source and a clearly named workload/resource regime.

The next runtime experiment should test a structurally different hypothesis.
The current priority is representation or construction efficiency with a
complete correctness argument, rather than another unqualified code-layout
micro-optimization. No background execution is implied by this checkpoint.
