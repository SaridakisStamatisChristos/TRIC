"""Exact Monge-accelerated optimizer for TRIC pivot selection on directed paths.

The existing TRIC `choose_path_optimal` is the O(k*n*n) reference solver.
This version exploits the Monge property of pair-contained-in-interval cost.
The speed and use of classical Monge DP optimization are not claims of novelty.
"""
from dataclasses import dataclass

@dataclass
class GapCosts:
    n: int
    queries: list
    weights: list | None = None

    def __post_init__(self):
        n = self.n
        weights = self.weights if self.weights is not None else [1] * len(self.queries)
        if len(weights) != len(self.queries) or any(w < 0 for w in weights):
            raise ValueError('weights must be nonnegative and align with queries')
        if any(not (0 <= s < n and 0 <= t < n) for s,t in self.queries):
            raise ValueError('queries out of bounds')
        self.prefix = [[0] * (n + 1) for _ in range(n + 1)]
        for (s, t), w in zip(self.queries, weights):
            self.prefix[s+1][t+1] += w
        for i in range(1, n+1):
            row = self.prefix[i]
            prev = self.prefix[i-1]
            accum = 0
            for j in range(1, n+1):
                accum += row[j]
                row[j] = accum + prev[j]

    def gap(self, l, r):
        if l > r: return 0
        p = self.prefix
        a = r + 1
        return p[a][a] - p[l][a] - p[a][l] + p[l][l]


def choose_path_monge(n, queries, k, weights=None):
    """Optimal exactly k pivots, O(n^2+|Q|+k*n*log n) time, O(n^2+k*n) memory.

    D&C optimization of monotone row-minima; ties select the earliest predecessor.
    """
    if k < 0 or k > n: raise ValueError('invalid pivot budget')
    if n <= 0:
        if k or queries: raise ValueError('invalid empty domain')
        return [], 0
    c = GapCosts(n, queries, weights)
    if k == 0: return [], c.gap(0, n-1)
    inf = float('inf')
    dp_prev = [c.gap(0,j-1) for j in range(n)]
    parents = [[-1]*n for _ in range(k+1)]
    for r in range(2, k+1):
        dp_cur = [inf]*n
        def solve(jlo, jhi, ilo, ihi):
            if jlo > jhi: return
            j=(jlo+jhi)//2
            upper=min(ihi,j-1)
            bestv=inf
            besti=-1
            for i in range(ilo,upper+1):
                cost=dp_prev[i]+c.gap(i+1,j-1)
                if cost < bestv or (cost == bestv and (besti < 0 or i < besti)):
                    bestv=cost;besti=i
            if besti < 0: raise AssertionError('missing feasible predecessor')
            dp_cur[j]=bestv;parents[r][j]=besti
            solve(jlo,j-1,ilo,besti)
            solve(j+1,jhi,besti,ihi)
        solve(r-1,n-1,r-2,n-2)
        dp_prev=dp_cur
    last=min(range(k-1,n),key=lambda j:(dp_prev[j]+c.gap(j+1,n-1),j))
    val=dp_prev[last]+c.gap(last+1,n-1)
    positions=[]
    for r in range(k,0,-1):
        positions.append(last)
        last=parents[r][last]
    positions.reverse()
    return positions,val
