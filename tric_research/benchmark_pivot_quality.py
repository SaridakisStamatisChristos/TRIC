"""Selection quality: interval-stabbing greedy vs exact path optimizer."""
import json, random, statistics
from path_sweep import choose_path_sweep

def greedy_path(n, queries, k, weights):
    covers=[]
    for pivot in range(n):
        mask=0
        for idx,(s,t) in enumerate(queries):
            if min(s,t)<=pivot<=max(s,t):mask|=1<<idx
        covers.append(mask)
    selected=[];covered=0
    for _ in range(k):
        scores=[]
        for p,mask in enumerate(covers):
            if p in selected:continue
            new=mask & ~covered
            score=0
            while new:
                v=new & -new;score+=weights[v.bit_length()-1];new-=v
            scores.append((score,-p,p))
        pivot=max(scores)[2];selected.append(pivot);covered|=covers[pivot]
    missing=sum(w for i,w in enumerate(weights) if not (covered>>i)&1)
    return selected,missing

def run():
    n=50;k=4;q=150;rep=80;runs=[]
    for dist in ('uniform','clusters'):
        for seed in range(rep):
            r=random.Random(seed*137+20261021)
            if dist=='uniform': queries=[(r.randrange(n),r.randrange(n)) for _ in range(q)]
            else:
                centers=[r.randrange(n) for _ in range(6)]
                queries=[(max(0,min(n-1,r.choice(centers)+r.randrange(-4,5))),max(0,min(n-1,r.choice(centers)+r.randrange(-4,5)))) for _ in range(q)]
            weights=[r.randrange(1,7) for _ in queries]
            best, optimal=choose_path_sweep(n,queries,k,weights)
            greed, miss=greedy_path(n,queries,k,weights)
            assert miss>=optimal
            runs.append(dict(seed=seed,distribution=dist,greedy_missed_weight=miss,optimal_missed_weight=optimal,greedy=greed,optimal=best))
    summary=[]
    for dist in ('uniform','clusters'):
        d=[x for x in runs if x['distribution']==dist]
        summary.append(dict(distribution=dist,n=n,k=k,queries=q,seeds=rep,greedy_suboptimal_cases=sum(x['greedy_missed_weight']>x['optimal_missed_weight'] for x in d),average_greedy_missed=round(statistics.mean(x['greedy_missed_weight'] for x in d),2),average_optimal_missed=round(statistics.mean(x['optimal_missed_weight'] for x in d),2),mean_absolute_saved_weight=round(statistics.mean(x['greedy_missed_weight']-x['optimal_missed_weight'] for x in d),2),maximum_saved_weight=max(x['greedy_missed_weight']-x['optimal_missed_weight'] for x in d)))
    out=dict(summary=summary,runs=runs)
    with open('pivot_quality.json','w') as f:json.dump(out,f,indent=2)
    print(json.dumps(summary,indent=2))
if __name__=='__main__':run()
