# Phase XXIX evidence

Baseline: PR #28, `4baa1a8b9a19d86bff33e304849e76ed77a7d511`.
Runtime commit: `e5a63e8f429b089439d294362f2629145f349d85`.

`qualification_protocol.json` freezes the selected candidate, budgets, arm sets,
launch balancing, replay horizons and input directories before qualification.
The full comparison source is unchanged. `build_manifest.json` records compiler
commands, selected header dependencies, upstream revisions and binary digests.
The previous binary reproduces the PR #28 candidate digest exactly.

`experiments.json.gz` contains every exploratory pilot, not just the selected
arm: baseline, widest interval, last interval, early-exit binary membership,
widest-before-Bloom, widest-without-Bloom, high-degree DFS order and low-degree
DFS order. Raw gzip results are base64 encoded with their original manifests;
compiled prototype headers and executed generation scripts are retained. Scripts
contain the original scratch paths as execution provenance, not portable paths.
Each prototype used the same eight baseline headers, changing only the recorded
partitioned header (five headers are actually selected in the native-only pilots). No pilot is counted as fresh qualification.

`baseline-sources/` freezes every source attested by Phase XXVIII. The historical
validator is explicitly pointed to this snapshot; old evidence is not rebound
to new source bytes. Current sources and artifacts are checked separately by
`verify_phase29_evidence.py` and `source_hashes.json`.

Five separate runs occupy `native`, `external`, `fresh`, `forest-warm` and
`forest-fresh`. Each contains sealed raw results, paired seed/aggregate CSVs and
a completeness receipt. Repeat counts are actual calls on repeated frozen
pairs, not new requests or independent experiments. Native and external horizons
must not be combined as if measured in the same run. Historical `heldout_*`
filenames denote exposed campaign inputs. Fresh fixtures are synthetic and
frozen after candidate selection; they are not independent real-world or
hardware replication.

All timing processes run sequentially pinned to CPU 1, with position-balanced
launch order. Tests, sanitizer compilation and fixture generation finish before
timing. Repository inspection, documentation and tool orchestration may continue;
there is no claim of exclusive host ownership. Wall time is primary; thread CPU
is secondary. Each process BFS-checks every input pair after timing. Budget is
2 MiB table payload and 64 MiB requested index scratch, not total RSS. This
change preserves exact table payload and retained capacities on matched trials.

The initial fresh cross-chain graph exposed a pre-existing false-negative bug
in chain merge skipping. `superseded.json.gz` preserves the initial complete
native/external results and aborted fresh run; none contributes to final results.
The initial protocol remains in `qualification_protocol_initial.json`. The
amended protocol restarts all comparisons on the repaired runtime. Native and
fresh use the chain-corrected control; native includes original PR #28 as a
third arm. External and forest comparisons use original PR #28 only on inputs
where each process passes the BFS oracle. `control_build_manifest.json` and
`corrected-control/` preserve the exact ablation. Fresh graphs were exposed for
correctness repair, with no performance retuning. `chain_counterexample.txt`
is a 160-vertex reproducer; its JSON contains the old failure and repaired pass.
