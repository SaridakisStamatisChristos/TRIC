# Phase XXXI: scope of the SOTA claim

Literature check: 26–27 October 2026. Execution and literature coverage are
separate obligations. A faster internal implementation does not by itself
establish superiority over the current research field.

## Executed comparison boundary

Phase XXX compared the production candidate against original BFL, OReach PDFS,
OReach PBiBFS, PLL and PPL on 19 graphs and 76 graph/stratum aggregates. It won
46 aggregates; its worst remaining query-time deficit was 1.333×. These are
historical local measurements at the Phase XXX source snapshot, not new
Phase XXXI external results. Phase XXXI prototypes must not inherit those exact
counts merely because their internal median improves.

Total-memory Pareto matching, new real-world graph families, and dedicated-host
replication are still missing. A 2 MiB table-payload cap is not a total memory
cap. Repeated timings and BFS checks are not independent datasets. Prespecified
gates can reject a proposed improvement even when its median is favorable.

## Current primary-source leads

| Work | Verified source | Execution state and remaining obligation |
|---|---|---|
| MLRQ / MLRQ-O (2025) | [Publisher article](https://link.springer.com/article/10.1007/s44443-025-00310-0) | NOT_EXECUTED. The publisher describes topological filters, partial two-hop labels and spanning-tree intervals. Its Data Availability section links datasets, not a verified author implementation. A bounded search did not establish an authoritative code release. This is not proof that none exists. |
| Lightweight 2-Hop Labels for Reachability Queries on Large-Scale Graphs (ICDE 2026) | [Author publication page](https://faculty.neu.edu.cn/wangyishu/en/lwcg/398729/content/38298.htm), [conference program](https://icde2026.github.io/program_details.html) | NOT_EXECUTED. Publication is confirmed; an authoritative implementation has not been verified. No performance numbers are inferred from its title. |
| Reachability-state Encoding / RE-toy | [Publisher article](https://journal.hep.com.cn/fcs/EN/10.1007/s11704-025-50122-8) | NOT_EXECUTED. The publisher describes adjustable space/query tradeoffs and a prototype. Code access and resource-matched comparisons remain unresolved. The page has inconsistent online/issue dating; use the DOI and article identity rather than guessing a priority date. |
| Graph Reachability Queries: A Unified Multi-Metric Framework with Dynamic Evaluation and Practical Guidelines (2026) | [Authors' lab page](https://raids-lab.com/publications/he2026graph/?r=tp) | NOT_EXECUTED. The authors describe 1,400 graphs and more than 38,000 query configurations. The inspected page's venue link leads to the journal homepage, not a verified benchmark download. Treat it as a lead requiring artifact verification. |
| Indexing Techniques for Graph Reachability Queries | [ACM record](https://doi.org/10.1145/3776737) | Literature context, not an executed competitor. It emphasizes graph-structure-dependent tradeoffs. |

These statements concern only the inspected sources. No emails or other messages
were sent to authors, and no external paid services were used. Implementing a
method from a paper would need to be labeled an independent reproduction until
validated against authoritative outputs; it must not silently replace author code.

## Next admissible claim

First establish exact behavior, actual memory accounting, timing stability and
paired improvement against the pinned production implementation. Then rerun the
external competitors on the accepted source, add available current methods, and
report the complete loss surface across graph structure, query mix, memory and
construction cost. A defensible narrow best-known result must name that regime.
No global SOTA or historical novelty claim is established by this campaign.
