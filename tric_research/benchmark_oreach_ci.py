"""Paired native TRIC/O'Reach pilot on one directed METIS graph and one query file.

This is an execution-harness comparison, NOT matched-memory SOTA evidence.
O'Reach queries/results are reported by its unmodified upstream executable;
TRIC answers are independently checked against BFS in native_query_bench.cpp.
"""
import argparse
import csv
import hashlib
import json
import platform
import random
import statistics
import subprocess
import sys
import time
from pathlib import Path

from benchmark_native import build_executable, serialize_native
from ordered_probe import greedy_coverage_order, hit_masks_for_pivots, optimize_ordered
from tric import make_pivot, early_reachable


def read_metis(path):
    """Read O'Reach directed METIS (one-based outgoing neighbours, blank rows kept)."""
    with open(path, encoding='utf-8') as stream:
        line = next((x for x in stream if not x.lstrip().startswith('%')), None)
        if line is None:
            raise ValueError('missing graph header')
        header = line.split()
        if len(header) != 2:
            raise ValueError('only unweighted directed METIS supported')
        n, m = map(int, header)
        if n < 1 or m < 0 or n > 150000:
            raise ValueError('invalid/too-large graph')
        adj = []
        for line in stream:
            if line.lstrip().startswith('%'):
                continue
            row = [int(v) - 1 for v in line.split()]
            if any(v < 0 or v >= n for v in row):
                raise ValueError('neighbour index out of bounds')
            adj.append(row)
        if len(adj) != n or sum(map(len, adj)) != m:
            raise ValueError(f'METIS mismatch expected {(n,m)}, got {(len(adj),sum(map(len,adj)))}')
    rev = [[] for _ in range(n)]
    for u, row in enumerate(adj):
        for v in row:
            rev[v].append(u)
    return adj, rev


def generate_queries(adj, size, seed):
    """Seeded held-out pairs. No policy-dependent query selection."""
    rng = random.Random(seed)
    n = len(adj)
    return [(rng.randrange(n), rng.randrange(n)) for _ in range(size)]


def write_queryfile(path, adj, queries):
    # O'Reach reads a third success column; include BFS ground truth.
    positives = 0
    with open(path, 'w', encoding='ascii') as f:
        for s,t in queries:
            ans = bool(early_reachable(adj, s, t)[0])
            positives += ans
            f.write(f'{s} {t} {int(ans)}\n')
    return positives


def parse_oreach_csv(path, expected_q):
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        for fields in csv.reader(f):
            if not fields or fields[0].startswith('%'):
                continue
            if len(fields) < 10:
                raise ValueError('bad O\'Reach CSV row')
            if int(fields[3]) != expected_q:
                raise ValueError('O\'Reach did not use our held-out query count')
            rows.append({'algorithm':fields[7], 'init_ms':float(fields[8]),
                         'query_total_us':float(fields[9]),
                         'query_us':float(fields[9]) / expected_q})
    labels = {v['algorithm'] for v in rows}
    if not {'oreach-pdfs','oreach-pbibfs'} <= labels:
        raise ValueError(f'missing O\'Reach fallback rows: {labels}')
    return rows


def run(args):
    if not 0 <= args.closure_cap_mib <= 1024:
        raise ValueError('closure cap must be in [0,1024] MiB')
    out = Path(args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    graph = Path(args.graph).resolve()
    adj, rev = read_metis(graph)
    n = len(adj)
    if not 0 <= args.budget <= args.candidates <= n or args.candidates > 19:
        raise ValueError('invalid candidate/budget')
    if min(args.train, args.test, args.oreach_repetitions) < 1:
        raise ValueError('nonpositive train/test/repetitions')
    # Degree-based candidates, without looking at held-out query outcomes.
    vertices = sorted(range(n), key=lambda u: (-len(adj[u])-len(rev[u]),u))[:args.candidates]
    training = generate_queries(adj, args.train, args.seed+1)
    heldout = generate_queries(adj, args.test, args.seed+2)
    queryfile = out / 'heldout.query.m.txt'
    positives = write_queryfile(queryfile, adj, heldout)
    q_sha = hashlib.sha256(queryfile.read_bytes()).hexdigest()
    t0 = time.perf_counter()
    pivots = [make_pivot(adj, rev, v) for v in vertices]
    hits = hit_masks_for_pivots(pivots, training)
    fb = [1 + early_reachable(adj, *q)[1] for q in training]
    ordered, _, _ = optimize_ordered(hits, [1.0]*len(hits), fb,
                                     [1.0]*len(vertices), args.budget)
    greedy = greedy_coverage_order(hits, [1.0]*len(hits), len(vertices), args.budget)
    training_seconds = time.perf_counter()-t0
    policies = {'BFS':[], 'Control':[], 'Greedy':greedy, 'Ordered':ordered}
    exe, compile_seconds, command = build_executable(out, args.compiler, args.optimization)
    native_input = out / 'tric_native_input.txt'
    native_input.write_bytes(serialize_native(adj, vertices, policies, heldout))
    native = subprocess.run([str(exe), str(args.tric_repetitions), str(args.closure_cap_mib)],
                            input=native_input.read_bytes(), capture_output=True,
                            check=True, timeout=args.timeout)
    native_results = json.loads(native.stdout)
    closure = native_results['closure']
    compact = native_results['compact']
    bfs_checksum = next(p['checksum'] for p in native_results['policies'] if p['name']=='BFS')
    if compact['checksum'] != bfs_checksum:
        raise AssertionError('compact index disagrees with independent BFS')
    if sum(compact[key] for key in ('certified_yes','certified_no','fallback_queries')) != len(heldout):
        raise AssertionError('compact query accounting incomplete')
    if closure['available'] and closure['checksum'] != next(p['checksum'] for p in native_results['policies'] if p['name']=='BFS'):
        raise AssertionError('closure checksum disagrees with independently checked BFS')
    if closure['index_matrix_bytes'] > args.closure_cap_mib * 1024 * 1024:
        raise AssertionError('closure exceeded matrix memory cap')
    (out/'tric_native.json').write_text(json.dumps(native_results,indent=2)+'\n')
    oreach_samples=[]
    for j in range(args.oreach_repetitions):
        dest = out/f'oreach_{j}.csv'
        cmd = [str(Path(args.oreach_binary).resolve()), str(graph), '--seed',
               str(args.seed), '--queries', str(queryfile), '--pbibfs', '--pdfs',
               '--output', str(dest)]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, timeout=args.timeout)
        (out/f'oreach_{j}.stdout.txt').write_text(proc.stdout)
        (out/f'oreach_{j}.stderr.txt').write_text(proc.stderr)
        if proc.returncode:
            raise RuntimeError(f'O\'Reach failed with code {proc.returncode}; see logs')
        oreach_samples.extend(parse_oreach_csv(dest,len(heldout)))
    methods = {name: [v for v in oreach_samples if v['algorithm']==name]
               for name in ('oreach-pdfs', 'oreach-pbibfs')}
    for name in methods:
        if len(methods[name]) != args.oreach_repetitions:
            raise ValueError('O\'Reach report incomplete')
    stats = {name: {'median_ns_per_query':1000*statistics.median(
                v['query_us'] for v in values),
                'median_init_ms':statistics.median(v['init_ms'] for v in values),
                'samples_ns_per_query':[1000*v['query_us'] for v in values]}
             for name, values in methods.items()}
    result = {'protocol':'TRIC-OReach paired native execution pilot',
              'claim_boundary':'Different indexing methods and memory budgets; compact interval labels are established prior art (GRAIL/PReaCH); closure uses quadratic matrix space; OReach individual answers not independently audited; hosted runner timing is noisy',
              'source_git_sha':args.oreach_git_sha,'graph':str(graph),
              'graph_sha256':hashlib.sha256(graph.read_bytes()).hexdigest(),
              'n':n, 'edges':sum(map(len,adj)),
              'query_file_sha256':q_sha,'test_count':len(heldout),
              'heldout_positive_count':positives,
              'candidate_vertices':vertices,'pivot_budget':args.budget,
              'selected_orders':policies,
              'offline_training_seconds_including_pivot_build':training_seconds,
              'tric_compile_seconds':compile_seconds,'tric_compile_cmd':command,
              'tric':native_results,'oreach':stats,
              'oreach_raw_rows':oreach_samples,
              'environment':{'python':sys.version,'platform':platform.platform()},
              'limitations':['Exact OReach/Tric memory budgets differ',
                             'OReach native query result correctness is not independently checked here',
                             'OReach per-process initialisation differs from TRIC candidate generation and training',
                             'Single shared-hosted runner is noisy; use repeated runners/days for publication']}
    (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'n':n,'edges':result['edges'],'heldout':len(heldout),
            'ordered_ns':next(p['median_ns_per_query'] for p in native_results['policies'] if p['name']=='Ordered'),
            'oreach_pdfs_ns':stats['oreach-pdfs']['median_ns_per_query'],
            'oreach_pbibfs_ns':stats['oreach-pbibfs']['median_ns_per_query'],
            'closure_available':closure['available'],
            'closure_ns':closure.get('median_ns_per_query'),
            'closure_build_ms':closure['build_ms'],
            'closure_matrix_bytes':closure['index_matrix_bytes'],
            'closure_onepass_ns':closure.get('median_onepass_ns_per_query'),
            'compact_ns':compact['median_ns_per_query'],
            'compact_build_ms':compact['build_ms'],
            'compact_label_bytes':compact['labels_bytes'],
            'compact_certificate_fraction':(compact['certified_yes']+compact['certified_no'])/len(heldout)},indent=2))


def parser():
    p=argparse.ArgumentParser()
    p.add_argument('--graph',required=True)
    p.add_argument('--oreach-binary',required=True)
    p.add_argument('--oreach-git-sha',required=True)
    p.add_argument('--output-dir',required=True)
    p.add_argument('--train',type=int,default=500)
    p.add_argument('--test',type=int,default=1200)
    p.add_argument('--seed',type=int,default=20261022)
    p.add_argument('--candidates',type=int,default=11)
    p.add_argument('--budget',type=int,default=5)
    p.add_argument('--oreach-repetitions',type=int,default=5)
    p.add_argument('--tric-repetitions',type=int,default=7)
    p.add_argument('--timeout',type=int,default=240)
    p.add_argument('--closure-cap-mib',type=int,default=64)
    p.add_argument('--compiler',default='g++')
    p.add_argument('--optimization',default='-O3')
    return p

if __name__=='__main__':
    run(parser().parse_args())
