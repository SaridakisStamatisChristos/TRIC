"""Local Python exploratory benchmark: SCC extraction against internal BFS oracle.

Output JSON is emitted to stdout; using redirection prevents mutations of archived
Phase I--III evidence. Timings are NOT compared against O'Reach or compiled code.
"""
import json
import platform
import random
import statistics
import sys
import time

from tric import build_graph
from backbone import backbone_intervals
from backbone_scc import prepare_scc_backbone


def median_seconds(f, repeats=5):
    times = []
    result = None
    for _ in range(repeats):
        start = time.perf_counter()
        result = f()
        times.append(time.perf_counter() - start)
    return statistics.median(times), result, times


def case(h, shape, seed):
    rng = random.Random(seed)
    n = h + max(2, h // 4)
    edges = [(i, i + 1) for i in range(h - 1)]
    # Random off-spine attachments and cycles (without altering the backbone).
    for x in range(h, n):
        p = rng.randrange(h)
        if rng.random() < .65:
            edges.append((p, x))
        if shape != 'forward' and rng.random() < .65:
            edges.append((x, rng.randrange(h)))
    if shape == 'cycle_blocks':
        for i in range(0, h - 5, 6):
            edges.append((i + 5, i))
    elif shape == 'one_giant_scc':
        edges.append((h - 1, 0))
    elif shape != 'forward':
        raise ValueError(shape)
    adj, rev = build_graph(n, edges)
    workload = [(rng.randrange(n), rng.randrange(n)) for _ in range(400)]
    return adj, rev, tuple(range(h)), workload


def run():
    rows = []
    for shape in ('forward', 'cycle_blocks', 'one_giant_scc'):
        for h in (40, 80, 160, 320):
            adj, rev, spine, workload = case(h, shape, 8103 + h)
            def fast():
                idx = prepare_scc_backbone(adj, spine)
                return idx, idx.intervals(workload)
            fast_t, (idx, intervals), ft = median_seconds(fast)
            old_t, oracle, ot = median_seconds(
                lambda: backbone_intervals(adj, rev, spine, workload))
            # Compare membership, not compressed indices.
            for j, p in enumerate(spine):
                for i, old_regions in enumerate(oracle):
                    old_hit = any(a <= j <= b for a, b in old_regions)
                    new_hit = idx.covered_by(intervals[i], p)
                    if old_hit != new_hit:
                        raise AssertionError((shape, h, j, i))
            rows.append({
                'shape': shape, 'vertices': len(adj), 'backbone': h,
                'distinct_backbone_scc': len(idx.representatives),
                'edges': sum(map(len, adj)), 'queries': len(workload),
                'scc_preprocess_query_median_s': fast_t,
                'repeated_search_median_s': old_t,
                'reference_over_scc': old_t / fast_t,
                'scc_runs_s': ft, 'reference_runs_s': ot})
    return {'environment': {'python': sys.version, 'platform': platform.platform()},
            'seed': '8103 + backbone length', 'repetitions': 5, 'results': rows}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
