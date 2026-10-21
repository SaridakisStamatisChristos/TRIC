# Phase IV — Cyclic Graph Extension

The new `backbone_scc.py` computes backbone-certificate intervals on **any directed graph** with a designated directed backbone. It condenses strongly connected components, groups backbone pivots that provide identical certificates, and calls Phase III's exact interval selector. This is **research code**; no novel reachability-certificate primitive is claimed.

```bash
cd tric_research
python -m unittest -q test_tric test_path_monge test_path_sweep test_backbone test_backbone_scc
python benchmark_backbone_scc.py > phase4_benchmark.json
```

Start with `prepare_scc_backbone(adj, backbone)` to build a reusable index. Use `.intervals(queries)` to retrieve exact certificate signatures in compressed-backbone coordinates; `.representatives` maps compressed indices back to original graph vertices. Use `optimize_scc_backbone(adj,backbone,queries,weights,k)` to select exactly `k` original backbone pivots for nonnegative weighted queries. Optimization still has an exponential `2^r` factor in distinct disjunctive signatures; the preprocessing is linear in the graph size.

See [`PHASE_IV_RESEARCH_REPORT.md`](PHASE_IV_RESEARCH_REPORT.md) for mathematical justification, prior art, benchmarks, and limitations.
