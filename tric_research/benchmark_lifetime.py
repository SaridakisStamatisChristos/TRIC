"""Phase XIX: executed warm-index uniform batches, not cost extrapolations.

Same existing TRIC index/pivots and Phase XVII native selector fit. Fit once
per seed, then freeze across batch sizes. Uniform pairs are sampled with
replacement from a fresh PRNG stream; natural duplicates/overlap are reported.
No external O'Reach timing or end-to-end deployment claim.
"""
import argparse
import hashlib
import json
import math
import platform
import statistics
import subprocess
import time
from pathlib import Path

from benchmark_native import build_executable, serialize_native
from benchmark_oreach_ci import generate_queries, read_metis
from ordered_probe import hit_masks_for_pivots, optimize_ordered
from tric import early_reachable, make_pivot

ROOT = Path(__file__).resolve().parent


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, separators=(',', ':')).encode('ascii')).hexdigest()


def summarize(raw):
    """Fail closed on incomplete timing/answer/accounting evidence."""
    qmax, reps = raw['queries'], raw['repetitions']
    fit = raw['training_ns']
    if not isinstance(qmax, int) or qmax <= 0 or not 3 <= reps <= 24 or reps % 3:
        raise ValueError('invalid query/repetition contract')
    if raw['schema'] != 'tric-phase19-warm-batches-v1':
        raise ValueError('unknown replay schema')
    if not math.isfinite(fit) or fit < 0 or raw['training_queries'] <= 0:
        raise ValueError('invalid fit cost or missing training')
    if raw['verified_answers_per_method'] != qmax or not 0 <= raw['oracle_positive_count'] <= qmax:
        raise ValueError('incomplete exact-answer validation')
    if raw['policy_id'] not in range(9):
        raise ValueError('invalid frozen policy')
    horizons = sorted(set(q for q in (1200, 10000, 100000, qmax) if q <= qmax))
    seen, groups = set(), {q: [] for q in horizons}
    for row in raw['batches']:
        q, rep = row['queries'], row['rep']
        if q not in groups or rep not in range(reps) or (q, rep) in seen:
            raise ValueError('invalid/duplicate batch')
        seen.add((q, rep))
        if row['first_mode'] != ('topo', 'bidir', 'selector')[rep % 3]:
            raise ValueError('unbalanced method order')
        for name in ('topo', 'bidir', 'selector'):
            value = row[name]
            if not isinstance(value['total_ns'], int) or value['total_ns'] <= 0:
                raise ValueError('invalid measured batch duration')
            if value['checksum'] != row['expected_checksum']:
                raise ValueError('oracle checksum mismatch')
            for key in ('probes', 'rescues', 'fallbacks'):
                if value[key] < 0 or value[key] != row['topo'][key]:
                    raise ValueError('changed pivot work')
            if value['rescues'] + value['fallbacks'] > q:
                raise ValueError('impossible query accounting')
        groups[q].append(row)
    if len(seen) != len(horizons) * reps:
        raise ValueError('missing batch measurements')
    result = []
    for q, rows in groups.items():
        item = {'queries': q, 'measured_repetitions': reps}
        for baseline in ('topo', 'bidir'):
            savings = [r[baseline]['total_ns'] - r['selector']['total_ns'] for r in rows]
            item[baseline] = {
                'median_baseline_batch_ns': statistics.median(r[baseline]['total_ns'] for r in rows),
                'median_selector_batch_ns': statistics.median(r['selector']['total_ns'] for r in rows),
                'median_paired_query_savings_ns': statistics.median(savings),
                'median_paired_net_savings_after_fit_ns': statistics.median(savings) - fit,
                'paired_net_wins_after_fit': sum(s > fit for s in savings),
            }
        result.append(item)
    return result


def execute(args):
    if not 1 <= args.queries <= 1000000 or not 1 <= args.train <= 100000:
        raise ValueError('invalid query/train size')
    if not 3 <= args.repetitions <= 24 or args.repetitions % 3:
        raise ValueError('repetitions must be a multiple of three in [3,24]')
    if not args.seeds or len(set(args.seeds)) != len(args.seeds):
        raise ValueError('seeds must be distinct')
    out = Path(args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    graph = Path(args.graph).resolve()
    adj, rev = read_metis(graph)
    n = len(adj)
    if not 0 <= args.budget <= args.candidates <= min(n, 19):
        raise ValueError('invalid pivot configuration')
    vertices = sorted(range(n), key=lambda u: (-len(adj[u])-len(rev[u]), u))[:args.candidates]
    exe, compile_s, command = build_executable(out, args.compiler, '-O3')
    env = {
        'platform': platform.platform(), 'python': platform.python_version(),
        'compiler': subprocess.check_output([args.compiler, '--version'], text=True).splitlines()[0],
        'compile_command': command, 'compile_seconds': compile_s,
        'cpu': next((s.split(':', 1)[1].strip() for s in Path('/proc/cpuinfo').read_text().splitlines()
                     if s.startswith('model name')), 'unknown'),
        'source_sha256': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                         for name in ('native_query_bench.cpp', 'lifetime_replay.h',
                                      'compact_reachability.h', 'closure_index.h',
                                      'benchmark_lifetime.py', 'benchmark_native.py',
                                      'benchmark_oreach_ci.py', 'ordered_probe.py', 'tric.py')},
    }
    cases = []
    for seed in args.seeds:
        case_dir = out / str(seed)
        case_dir.mkdir(exist_ok=True)
        train = generate_queries(adj, args.train, seed+1)
        heldout = generate_queries(adj, args.queries, seed+2)
        t0 = time.perf_counter()
        pivots = [make_pivot(adj, rev, v) for v in vertices]
        hits = hit_masks_for_pivots(pivots, train)
        costs = [1 + early_reachable(adj, *q)[1] for q in train]
        order, _, _ = optimize_ordered(hits, [1.0]*len(hits), costs,
                                       [1.0]*len(vertices), args.budget)
        python_preparation_s = time.perf_counter()-t0
        data = serialize_native(adj, vertices, {'Ordered': order}, heldout, train)
        (case_dir/'input.txt').write_bytes(data)
        started = time.perf_counter()
        run = subprocess.run([str(exe), str(args.repetitions), '0', '--lifetime'],
                             input=data, capture_output=True, check=True, timeout=args.timeout)
        native_wall_s = time.perf_counter()-started
        raw = json.loads(run.stdout)
        if raw['queries'] != args.queries or raw['training_queries'] != args.train:
            raise ValueError('native input counts disagree')
        summary = summarize(raw)
        train_set = set(train)
        case = {
            'seed': seed, 'candidate_vertices': vertices, 'ordered_pivots': order,
            'training_pairs_sha256': fingerprint(train), 'heldout_pairs_sha256': fingerprint(heldout),
            'input_sha256': hashlib.sha256(data).hexdigest(),
            'unique_heldout_pairs': len({s*n+t for s, t in heldout}),
            'heldout_occurrences_also_in_training': sum(q in train_set for q in heldout),
            'python_pivot_preparation_seconds': python_preparation_s,
            'native_process_wall_seconds': native_wall_s,
            'raw': raw, 'summary': summary,
        }
        (case_dir/'result.json').write_text(json.dumps(case, indent=2)+'\n')
        cases.append(case)
        print(json.dumps({'seed': seed, 'policy': raw['policy_id'],
                          'fit_ms': raw['training_ns']/1e6, 'largest_batch': summary[-1]}), flush=True)
    result = {
        'protocol': 'Phase XIX executed warm-index uniform batches; within-TRIC only',
        'graph_sha256': hashlib.sha256(graph.read_bytes()).hexdigest(),
        'vertices': n, 'edges': sum(map(len, adj)), 'environment': env,
        'sampling': 'uniform pairs with replacement; independent PRNG streams, natural overlap allowed',
        'cache_regime': 'full per-method batch warmup; no cache flushing or dedicated hardware guarantee',
        'cost_scope': 'measured selector fit + measured query batch; excludes shared preparations, oracle, I/O and warmup',
        'config': vars(args), 'cases': cases,
    }
    (out/'results.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--graph', required=True)
    p.add_argument('--output-dir', required=True)
    p.add_argument('--queries', type=int, default=1000000)
    p.add_argument('--train', type=int, default=500)
    p.add_argument('--candidates', type=int, default=11)
    p.add_argument('--budget', type=int, default=5)
    p.add_argument('--seeds', nargs='+', type=int, default=[20261022, 20261023, 20261024])
    p.add_argument('--repetitions', type=int, default=9)
    p.add_argument('--compiler', default='g++')
    p.add_argument('--timeout', type=int, default=1200)
    return p


if __name__ == '__main__':
    execute(parser().parse_args())
