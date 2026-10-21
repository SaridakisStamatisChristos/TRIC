"""Reproducible held-out synthetic GRAPH benchmark for ordered certificate pivots.

Compares candidate-budget-matched coverage greedy, exact ordered cost solver,
and no-index BFS. Records build/search wall time and test inference wall time
separately. Search cost proxy is NOT the same as observed wall-clock latency.
"""
import json,platform,random,statistics,time
from tric import graph_family,make_pivot,certify,early_reachable
from ordered_probe import (hit_masks_for_pivots, optimize_ordered,
                           greedy_coverage_order, ordered_cost)


def generate_queries(n,m,seed,mode,hot_sources=None,hot_targets=None):
    rng=random.Random(seed);qs=[]
    for _ in range(m):
        if mode=='hot' and rng.random()<0.8:
            qs.append((rng.choice(hot_sources),rng.choice(hot_targets)))
        else:
            qs.append((rng.randrange(n),rng.randrange(n)))
    return qs


def evaluate(adj, pivots, test, seq):
    errors=0;hits=0;total_checks=0;edges=0
    t0=time.perf_counter()
    for s,t in test:
        pred=None
        for p in seq:
            total_checks += 1
            pred=certify(pivots[p],s,t)
            if pred is not None:
                hits+=1;break
        if pred is None:
            pred,scans=early_reachable(adj,s,t)
            edges+=scans
        # oracle separated from measured time for factual correctness
    elapsed=time.perf_counter()-t0
    for s,t in test:
        actual,_=early_reachable(adj,s,t)
        predicted=None
        for p in seq:
            predicted=certify(pivots[p],s,t)
            if predicted is not None:break
        if predicted is not None and actual!=predicted:errors+=1
    return {'inference_seconds':elapsed,'errors':errors,'hit_rate':hits/len(test),
            'checks':total_checks,'fallback_edge_scans':edges}


def run(seed=20261021,n=150,train_size=550,test_size=1300,c=11,k=5):
    output={'python':platform.python_version(),'seed':seed,'n':n,
            'train_size':train_size,'test_size':test_size,
            'candidates':c,'budget':k,'proxy':'probe = 1 work unit, fallback = 1 + BFS edge scans',
            'training_and_holdout_independent':True,'results':[]}
    for fam in ('dag','chain','blocks','communities'):
        for trial in range(2):
            graphseed=seed+97*trial+sum(map(ord,fam))
            adj,rev=graph_family(fam,n,graphseed)
            rng=random.Random(graphseed+10)
            hot_s=[rng.randrange(n) for _ in range(8)]
            hot_t=[rng.randrange(n) for _ in range(8)]
            positions=sorted(range(n), key=lambda v:-(len(adj[v])+len(rev[v])))[:c]
            t0=time.perf_counter()
            pivots=[make_pivot(adj,rev,v) for v in positions]
            prebuild=time.perf_counter()-t0
            for train_mode,test_mode in [('uniform','uniform'),('hot','hot'),('hot','uniform')]:
                train=generate_queries(n,train_size,graphseed+200,train_mode,hot_s,hot_t)
                test=generate_queries(n,test_size,graphseed+201,test_mode,hot_s,hot_t)
                t0=time.perf_counter()
                hit_train=hit_masks_for_pivots(pivots,train)
                fb_train=[1+early_reachable(adj,*q)[1] for q in train]
                order,cost,diag=optimize_ordered(hit_train,[1]*train_size,fb_train,[1]*c,k)
                selection_time=time.perf_counter()-t0
                cov=greedy_coverage_order(hit_train,[1]*train_size,c,k)
                hit_test=hit_masks_for_pivots(pivots,test)
                fb_test=[1+early_reachable(adj,*q)[1] for q in test]
                data={'family':fam,'trial':trial,'train':train_mode,'test':test_mode,
                      'graph_edges':sum(map(len,adj)),'pivot_build_seconds':prebuild,
                      'ordered_selection_seconds':selection_time,
                      'ordered_positions':[positions[p] for p in order],
                      'coverage_positions':[positions[p] for p in cov],
                      'predicted_train_opt_cost':cost,'diagnostics':diag}
                for name,seq in [('ordered',order),('coverage',cov),('bfs',[])]:
                    ev=evaluate(adj,pivots,test,seq)
                    ev['test_work_proxy']=ordered_cost(seq,hit_test,[1]*len(test),fb_test,[1]*c)
                    data[name]=ev
                output['results'].append(data)
    return output


if __name__=='__main__':
    result=run()
    from pathlib import Path
    Path('phase8_benchmark.json').write_text(json.dumps(result,indent=2)+'\n')
    for name in ('ordered','coverage','bfs'):
        ratios=[r[name]['test_work_proxy']/r['bfs']['test_work_proxy'] for r in result['results']]
        print(name,'median normalized test work',round(statistics.median(ratios),3),
              'median inference s',round(statistics.median(r[name]['inference_seconds'] for r in result['results']),4))
    print('cases',len(result['results']),'worse-than-greedy',sum(r['ordered']['test_work_proxy']>r['coverage']['test_work_proxy'] for r in result['results']))
