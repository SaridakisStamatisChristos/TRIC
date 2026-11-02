"""Recompute descriptive Phase XXX metrics from sealed paired trial records."""
import csv
import gzip
import json
import statistics
from collections import defaultdict
from pathlib import Path


def describe(values):
    return {'median': statistics.median(values), 'wins': sum(v > 1 for v in values),
            'cells': len(values), 'min': min(values), 'max': max(values)}


def summarize():
    root = Path(__file__).resolve().parent / 'evidence/phase30'
    protocol = json.loads((root / 'qualification_protocol.json').read_text())
    result = {'campaigns': {}, 'native_routes': {}, 'counts': {}}
    processes = checks = calls = 0
    replication = json.loads((root / 'forest_replication_protocol.json').read_text())
    specs = protocol['runs'] + [dict(replication, tag='forest-replication')]
    warm_replication = json.loads((root / 'forest_warm_replication_protocol.json').read_text())
    specs.append(dict(warm_replication, tag='forest-warm-replication'))
    for spec in specs:
        if spec['tag'] == 'forest-replication':
            result['primary_counts'] = {'processes': processes, 'BFS_pair_checks': checks, 'actual_query_calls': calls}
        folder = root / spec['tag']; output = folder / 'qualification-final'
        manifest = json.loads((output / 'manifest.json').read_text())
        assert manifest['complete']
        aggregate = list(csv.DictReader((folder / 'aggregate_summary.csv').open()))
        result['campaigns'][spec['tag']] = {}
        for horizon in spec['horizons']:
            rows = [r for r in aggregate if int(r['repeats']) == horizon]
            fields = [k for k in rows[0] if k.startswith(('previous_over_candidate_', 'external_over_candidate_'))]
            result['campaigns'][spec['tag']][str(horizon)] = {
                field: describe([float(r[field]) for r in rows]) for field in fields}
        if spec['tag'] == 'external':
            worst = min(aggregate, key=lambda r: float(r['external_over_candidate_query_ns']))
            result['external_worst'] = {k: worst[k] for k in ('dataset', 'stratum', 'external_over_candidate_query_ns')}
        if spec['tag'] == 'native':
            result['native_regressions'] = [{k: r[k] for k in ('dataset', 'stratum', 'previous_over_candidate_query_ns', 'previous_over_candidate_lifecycle_ns')}
                                            for r in aggregate if float(r['previous_over_candidate_query_ns']) < 1]
            result['ecoo_negative'] = float(next(r for r in aggregate if r['dataset'] == 'heldout_ecoo' and r['stratum'] == 'negative')['previous_over_candidate_query_ns'])
        routes = {'general': [], 'direct': []}
        baseline_external = defaultdict(list)
        for entry in manifest['files']:
            for cell in json.loads(gzip.decompress((output / entry['file']).read_bytes())):
                if spec['tag'] == 'external':
                    names = ('bfl', 'oreach-pdfs', 'oreach-pbibfs', 'pll', 'ppl')
                    baseline_external[(cell['dataset'], cell['stratum'])].append(
                        statistics.median(min(cell['rows'][name][i]['query_ns'] for name in names) / row['query_ns']
                                          for i, row in enumerate(cell['rows']['previous'])))
                if spec['tag'] == 'native':
                    route = 'direct' if cell['rows']['candidate'][0]['uses_direct_closure'] else 'general'
                    routes[route].append(statistics.median(a['query_ns'] / b['query_ns'] for a, b in zip(cell['rows']['previous'], cell['rows']['candidate'])))
                for rows in cell['rows'].values():
                    processes += len(rows)
                    checks += sum(r['oracle_verified_pairs'] for r in rows)
                    calls += sum(r['actual_calls'] for r in rows)
        if spec['tag'] == 'native':
            result['native_routes'] = {k: describe(v) for k, v in routes.items()}
        if spec['tag'] == 'external':
            paired = {k: statistics.median(v) for k, v in baseline_external.items()}
            result['external_vs_previous_in_same_campaign'] = describe(list(paired.values()))
            worst = min(paired, key=paired.get)
            result['previous_external_worst_in_same_campaign'] = {
                'dataset': worst[0], 'stratum': worst[1], 'external_over_previous_query_ns': paired[worst]}
    result['counts'] = {'processes': processes, 'BFS_pair_checks': checks, 'actual_query_calls': calls}
    native = result['campaigns']['native']['2000']
    result['numeric_acceptance'] = {
        'native_general_at_least_1_05': result['native_routes']['general']['median'] >= 1.05,
        'ecoo_negative_at_least_1_10': result['ecoo_negative'] >= 1.10,
        'native_aggregate_query_at_least_parity': native['previous_over_candidate_query_ns']['median'] >= 1,
        'native_aggregate_lifecycle_at_least_0_97': native['previous_over_candidate_lifecycle_ns']['median'] >= .97,
        'native_no_aggregate_query_regression_over_10_percent': native['previous_over_candidate_query_ns']['min'] >= .9}
    (root / 'result_metrics.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    print(json.dumps(summarize(), indent=2))
