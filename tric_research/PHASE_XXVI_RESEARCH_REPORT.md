# Phase XXVI: inline interval rows and bidirectional signatures

## Problem and implementation

PR #25's exact interval route loads its row directory before the interval
payload. Its 64-bit negative filter tracks only descendants. This change reuses
existing label fields for interval row offset/count and splits the signature
into 32-bit descendants plus complemented 32-bit ancestors. Both negative
conditions execute as one 64-bit subset check. It uses no query training or
workload-dependent runtime route.

The label remains 32 bytes. Other representations retain their chain/SCC ID
and packed saturating forward/backward levels. The original interval directory
is still retained and charged to the table payload; the change neither raises
its capacity nor disguises memory in another budget. The additional ancestor
construction vector costs 8 bytes per SCC temporarily and one DAG propagation
pass. Default budgets remain 2 MiB table payload and 64 MiB for the existing
index-union buffers or dense temporary matrix, neither of which bounds total
constructor memory or RSS.

## Correctness argument

For a nontrivial reachable pair a -> b, the descendant set of b is a subset
of that of a, and the ancestor set of a is a subset of that of b. Mapping set
members to bits preserves these inclusions. Define S(a) as the concatenation
of D(a) and the 32-bit complement of A(a). Then reachability implies
S(a) & S(b) == S(b). Failure proves a negative answer. Passing proves nothing;
the existing exact certificates, index or DFS still answer. Hash collisions
only weaken rejection. Reverse and forward topological passes build D and A,
respectively, on the same exact SCC condensation.

For an interval partition, every original vertex in an SCC copies the completed
SCC row's offset and count into its label. Queries read those same values
without the intermediate directory load. For every other partition, the fields
retain their prior meaning. A partition's mode is fixed at construction;
queries check mode before interpreting these fields. Search still extracts
both saturated 16-bit levels; equal saturated values cannot reject. Nothing
changes reflexivity, invalid-endpoint exceptions, snapshot ownership, or the
one-instance-per-query-thread requirement.

The changes add O(S + M) construction work and O(S) temporary space for S SCCs
and M condensation arcs. They preserve the previous worst-case query and index
construction bounds. This is an engineering optimization using established
ancestor/descendant filtering and metadata reuse, without a novelty claim or
proof-assistant verification.

## Verification and candidate selection

The local suite passes 32 methods, including the original Python research
checks. Native self-tests compare both automatic and partitioned indexes with
independent BFS on 18,432 exhaustive three-vertex cases, 1,440 adversarial cases,
and 589,824 lifted DAG-family cases. Existing tests cover interval refusal,
rollback, compressed words, 100,000-vertex indexing, 140,000-vertex depth
saturation and deep cross-subtree diamonds. A new relabelled SCC-alias test
forces interval routing with several original vertices sharing a row; zero
budget exercises exact fallback on the same graph.

Local address/undefined-behavior checks pass. Only the local sanitizer command
sets ASAN_OPTIONS=detect_leaks=0 because this traced environment cannot support
LeakSanitizer's thread inspection. CI retains full leak checking. The frozen
runtime passes both Python 3.10 and 3.13 jobs, including full sanitizers, in
[run 39952604712](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39952604712).
Final evidence-head CI is linked separately in PR #26.

Three complete exploratory comparisons are preserved in ablations.json.gz:

- A certified-complete-subtree fast path lost on most of its 32 pilot cells and
  was rejected. The extra query branch did not pay for itself.
- A 76-cell, 19-graph ablation separates inline row fields, split signatures,
  and their combination. Median thread-CPU cell speedups against PR #25 were
  1.062x, 1.023x and 1.073x, respectively. These are exploratory, not independent
  qualification results; direct-closure controls also show timing noise.
- A 36-cell follow-up compared a 48/16 descendant/ancestor split and a 32/32
  split with identical inline rows. Against inline rows alone, their median
  thread-CPU speedups were 1.022x and 1.044x. The 32/32 candidate was frozen.

All pilots use position-balanced fresh processes, one pinned CPU, 1,200 frozen
pairs replayed 1,000 times, and post-timing BFS checks. Their graph/seed pairs
were used in candidate selection; they are not held-out evidence. A separate
initial signature pilot failed final artifact integrity on one graph, and is
excluded from selection statistics and qualification. Complete graphs were
rerun in the preserved ablations. The runner now publishes each completed
graph once, rather than repeatedly replacing intermediate graph checkpoints;
its final digest/readback checks and refusal of nonempty output remain intact.

## Qualification protocol

Runtime code: 7c72dbb73fbd3cb2b6cf8b75fbdd2121c1287e58.
Baseline: PR #25, f6e6b37bc25e797a1c893f96ad06ae6651442e29.
The same original BFL and OReach revisions, adapters, compiler options, 19 input
graphs, 39 graph/seed pairs, source-weighted query strata, and horizons of 1 and
100 are reused from Phase XXV. The exact fixture files remain in
`evidence/phase25/fixtures`; their digests are checked by the new manifest.
Six real plus one published synthetic and three generated graphs have three
seeds; the nine other real graphs retain their original one seed. All 19 graph
shapes have now been exposed during tuning. The two other seeds on the first
ten graphs are repeated-pair checks, not new held-out graph qualification.

Five arms and five cyclic launch positions balance process order. Every arm
parses identical native bytes, executes actual calls, and checks each input
pair against BFS after timing. Warm horizon means 120,000 calls from 1,200
frozen pairs. Parse/build/query wall-clock lifetime is primary; thread CPU time
is secondary. Native VmHWM is sampled before oracle verification. Compilation,
process startup, oracle checking and teardown are excluded. Shared hardware
and unmatched total retained/peak memory limit comparisons.

The final result manifest, all raw trials, compiler/source/binary hashes,
paired CSV summaries, and completeness receipt are in `evidence/phase26`.
Refer to Phase XXV's report for original archive/graph provenance and exact
stratum construction. No external literature timing is treated as a measured
head-to-head result.

## Results

The final sealed run covers **39 graph/seed experiments on 19 graphs**, all
312 stratum/horizon cells, 7,800 fresh processes, 9,360,000 independent
post-timing BFS pair checks and 472,680,000 actual query calls. The latter are
replays, not distinct requests. All input/result digests and expected cases pass.

Across 76 warm graph/stratum aggregates, the median paired query speedup over
PR #25 is **1.110x**, with **58/76** faster cells. Thread-CPU results agree:
1.109x and 58/76. The 13 graphs that use the modified partitioned route account
for 52 cells: median 1.140x, with 45/52 faster. The six direct-closure graphs
retain unchanged runtime source; their measured gains/losses are controls and
are not attributed to these algorithm changes.

Construction median is 0.993x (about 0.7% slower), and parse/build/query lifecycle
median is 0.999x, effectively flat on this shared machine. They win only 34/76
and 37/76 cells, respectively. At horizon 1, lifecycle median is 1.000x.
This supports a query-path improvement, not a claim of broad lifecycle or
construction acceleration. The additional constructor pass and host variability
must both be considered.

Retained capacity and table payload are identical to PR #25 in every aggregate
cell. Modified-route native peak RSS has a median candidate/previous ratio of
1.016, reflecting extra temporary construction memory and measurement variation.

Uniform strata at 120,000 calls follow. Values above 1 favor Phase XXVI. The
external column uses the fastest of original BFL and both OReach variants for
each paired trial. Ratios are medians of paired trials, then medians across
seeds; they are not ratios of independently rounded timing medians.

| Graph | Query vs PR #25 | Build vs PR #25 | Lifecycle vs PR #25 | Query vs fastest external |
|---|---:|---:|---:|---:|
| example | 1.303x | 0.987x | 0.991x | 12.510x |
| generated_blocks | 1.001x | 1.085x | 0.991x | 0.916x |
| generated_communities | 1.071x | 0.997x | 0.999x | 1.791x |
| generated_dag | 0.955x | 0.947x | 1.007x | 68.979x |
| grail_citeseer | 1.215x | 0.998x | 0.980x | 1.047x |
| grail_go | 1.150x | 0.957x | 1.002x | 1.044x |
| grail_kegg | 0.949x | 1.020x | 1.002x | 0.828x |
| grail_pubmed | 1.287x | 0.961x | 0.983x | 1.248x |
| grail_yago | 1.049x | 1.003x | 1.005x | 0.903x |
| heldout_agrocyc | 0.943x | 0.903x | 1.038x | 0.499x |
| heldout_amaze | 1.352x | 1.114x | 1.084x | 0.657x |
| heldout_anthra | 1.137x | 1.075x | 1.146x | 0.517x |
| heldout_ecoo | 1.162x | 0.962x | 1.029x | 0.564x |
| heldout_human | 1.001x | 0.976x | 0.998x | 0.508x |
| heldout_mtbrv | 0.900x | 1.033x | 0.956x | 0.516x |
| heldout_nasa | 1.130x | 1.012x | 1.007x | 1.068x |
| heldout_vchocyc | 1.104x | 1.013x | 0.994x | 0.578x |
| heldout_xmark | 1.106x | 0.993x | 1.057x | 1.296x |
| kron_logn12 | 1.014x | 0.901x | 0.974x | 10.098x |

All warm query regressions on the modified partitioned route are listed here;
the CSV also retains losses in unchanged direct-closure controls and all cold
cells. A ratio of 0.900x means approximately 11.1% longer query time, not 10%.

| Graph | Stratum | Query speedup vs PR #25 |
|---|---|---:|
| grail_yago | negative | 0.910x |
| heldout_agrocyc | uniform | 0.943x |
| heldout_ecoo | negative | 0.930x |
| heldout_human | negative | 0.927x |
| heldout_mtbrv | negative | 0.993x |
| heldout_mtbrv | uniform | 0.900x |
| heldout_nasa | positive | 0.971x |

A separate position-balanced arXiv confirmation checks all three seeds and all
four strata, using the same benchmark source, compiler, external revisions and
flags across PR #24, PR #25 and this frozen runtime. At 1,000 replays, uniform
query speedups are **1.139x versus PR #24** and **1.336x versus PR #25**. Positive,
negative and balanced strata also improve against both. This directly resolves
the previously observed arXiv regression in this confirmation workload; it is
not inferred by multiplying speedups from different runs. Its manifest, raw
trials and Phase XXIV build provenance are preserved in arxiv_legacy.json.gz,
and are additional to the 7,800-process qualification totals above.

Against the fastest measured external baseline, the new runtime wins **40/76**
warm query cells and **45/76** lifecycle cells. Uniform biological workloads
still lose: approximately 1.7-2.0x the fastest external query time on several
sparse graphs, and YAGO remains about 1.11x slower. PLL/MLRQ-O, much larger
authentic graphs, genuinely held-out graph families, matched total memory and
independent dedicated-hardware measurements remain unqualified. This is not
global SOTA, novelty, or production-readiness evidence.


## Reproduction

From the repository root, with a clean checkout of the baseline and the pinned
OReach checkout/objects described in Phase XXV:

```sh
python tric_research/build_native_comparison.py \
  --before-headers /path/to/phase25/tric_research --output /tmp/phase26-build \
  --oreach-source /path/to/upstream-oreach --oreach-build /path/to/upstream-build \
  --extra-include /path/to/boost/include
python tric_research/benchmark_native_changes.py \
  --fixtures tric_research/evidence/phase25/fixtures --output /tmp/phase26-results \
  --arm previous /tmp/phase26-build/previous auto \
  --arm candidate /tmp/phase26-build/candidate auto \
  --arm bfl /tmp/phase26-build/candidate bfl \
  --arm oreach-pdfs /tmp/phase26-build/candidate oreach-pdfs \
  --arm oreach-pbibfs /tmp/phase26-build/candidate oreach-pbibfs \
  --trials 5 --horizons 1 100 --cpu 1
python tric_research/summarize_native_changes.py \
  tric_research/evidence/phase26 --fixtures tric_research/evidence/phase25/fixtures
```

Use a new empty output directory. To summarize a new run, place its directory
at `<result-root>/qualification-final` and pass `<result-root>` to the summary
command with the pinned fixture directory. The summary validates every input,
result digest, arm, trial, checksum, BFS count and expected cell before reporting.
