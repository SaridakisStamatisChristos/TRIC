"""Exact SCC-condensed backbone certificates for arbitrary directed graphs.

This extension combines established SCC condensation with the Phase III TRIC
backbone interval characterisation. SCC condensation and O'Reach certificate
rules are prior art; neither is claimed here as a new primitive.

Only the selected backbone may contain pivot vertices. Each SCC containing one
or more backbone vertices contributes exactly one distinct certificate pivot.
"""
from collections import deque
from dataclasses import dataclass

from backbone import optimize_intervals


@dataclass(frozen=True)
class SCCBackboneIndex:
    """Precomputed certificate boundaries in *compressed spine* coordinates.

    `representatives[i]` is an original-graph vertex in the i-th spine SCC.
    `spine_component[i]` is its SCC ID. An original pivot p certifies precisely
    the same queries as the representative of its SCC.
    """
    component: tuple[int, ...]
    spine_component: tuple[int, ...]
    representatives: tuple[int, ...]
    left: tuple[int, ...]
    right: tuple[int, ...]
    original_backbone: tuple[int, ...]
    pivot_rank: tuple[int, ...]

    def intervals(self, queries):
        """Return per-query 0, 1, or 2 inclusive certificate intervals.

        O(|queries|) with constant work per query after the index is built.
        """
        n = len(self.component)
        h = len(self.representatives)
        out = []
        for s, t in queries:
            if not (0 <= s < n and 0 <= t < n):
                raise ValueError('bad query endpoints')
            cs, ct = self.component[s], self.component[t]
            Ls, Lt = self.left[cs], self.left[ct]
            Rs, Rt = self.right[cs], self.right[ct]
            raw = ((Rs, Lt), (Lt + 1, Ls), (Rt, Rs - 1))
            valid = sorted((max(0, a), min(h - 1, b)) for a, b in raw
                           if max(0, a) <= min(h - 1, b))
            merged = []
            for a, b in valid:
                if merged and a <= merged[-1][1] + 1:
                    merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
                else:
                    merged.append((a, b))
            if len(merged) > 2:
                raise AssertionError('unexpected more than two intervals')
            out.append(tuple(merged))
        return out

    def covered_by(self, query_intervals, pivot):
        """Whether a backbone vertex certifies a query, in O(1) time."""
        if not (isinstance(pivot, int) and 0 <= pivot < len(self.pivot_rank)):
            return False
        i = self.pivot_rank[pivot]
        return i >= 0 and any(lo <= i <= hi for lo, hi in query_intervals)


def prepare_scc_backbone(adj, backbone):
    """Build SCC-compressed backbone and certificate endpoints in O(V+E+h).

    Requirements: vertices are 0..len(adj)-1; `backbone` is a nonempty
    simple path whose successive directed edges exist. Self loops/cycles and
    duplicate adjacency edges are supported; invalid vertex IDs are rejected.
    """
    n = len(adj)
    spine = tuple(backbone)
    if not spine or len(set(spine)) != len(spine):
        raise ValueError('backbone must be nonempty and simple')
    if any(not isinstance(p, int) or not 0 <= p < n for p in spine):
        raise ValueError('invalid backbone vertex')
    rev = [[] for _ in range(n)]
    for u, successors in enumerate(adj):
        for v in successors:
            if not isinstance(v, int) or not 0 <= v < n:
                raise ValueError('edge endpoint out of bounds')
            rev[v].append(u)
    if any(spine[i + 1] not in adj[spine[i]] for i in range(len(spine) - 1)):
        raise ValueError('backbone must follow directed edges')

    # First-pass DFS is iterative to avoid recursion limits on long paths.
    seen = [False] * n
    finish = []
    for src in range(n):
        if seen[src]:
            continue
        seen[src] = True
        stack = [(src, iter(adj[src]))]
        while stack:
            u, successors = stack[-1]
            try:
                v = next(successors)
            except StopIteration:
                finish.append(u)
                stack.pop()
                continue
            if not seen[v]:
                seen[v] = True
                stack.append((v, iter(adj[v])))

    component = [-1] * n
    nc = 0
    for src in reversed(finish):
        if component[src] >= 0:
            continue
        component[src] = nc
        todo = [src]
        while todo:
            u = todo.pop()
            for v in rev[u]:
                if component[v] < 0:
                    component[v] = nc
                    todo.append(v)
        nc += 1

    # Consecutive backbone positions in the same SCC are equivalent; by
    # reachability along the path, an SCC cannot reappear nonconsecutively.
    compressed = []
    representatives = []
    for p in spine:
        c = component[p]
        if not compressed or c != compressed[-1]:
            compressed.append(c)
            representatives.append(p)
    if len(set(compressed)) != len(compressed):
        raise AssertionError('backbone SCCs must be contiguous')

    dag = [set() for _ in range(nc)]
    indeg = [0] * nc
    for u, successors in enumerate(adj):
        cu = component[u]
        for v in successors:
            cv = component[v]
            if cu != cv and cv not in dag[cu]:
                dag[cu].add(cv)
                indeg[cv] += 1

    ready = deque(u for u in range(nc) if indeg[u] == 0)
    topo = []
    while ready:
        u = ready.popleft()
        topo.append(u)
        for v in dag[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                ready.append(v)
    if len(topo) != nc:
        raise AssertionError('condensation must be a DAG')

    h = len(compressed)
    left = [-1] * nc
    right = [h] * nc
    for i, c in enumerate(compressed):
        left[c] = i
        right[c] = i
    for u in topo:
        for v in dag[u]:
            if left[u] > left[v]:
                left[v] = left[u]
    for u in reversed(topo):
        for v in dag[u]:
            if right[v] < right[u]:
                right[u] = right[v]

    rank = [-1] * n
    spine_component_rank = {c: i for i, c in enumerate(compressed)}
    for p in spine:
        rank[p] = spine_component_rank[component[p]]
    return SCCBackboneIndex(tuple(component), tuple(compressed),
                            tuple(representatives), tuple(left), tuple(right),
                            spine, tuple(rank))


def optimize_scc_backbone(adj, backbone, queries, weights, k):
    """Optimize exactly k original backbone pivots; return (pivots, loss, r).

    If backbone has fewer than k different SCCs, redundant original pivots
    are included to maintain the exact-k contract without changing coverage.
    Uses the Phase III exact orientation enumeration; exponential in the
    number r of distinct two-interval query signatures.
    """
    index = prepare_scc_backbone(adj, backbone)
    if not (0 <= k <= len(index.original_backbone)):
        raise ValueError('invalid pivot budget')
    if len(weights) != len(queries):
        raise ValueError('mismatched query weights')
    intervals = index.intervals(queries)
    selected, uncovered, r = optimize_intervals(
        len(index.spine_component), intervals, weights,
        min(k, len(index.spine_component)))
    pivots = [index.representatives[i] for i in selected]
    if len(pivots) < k:
        chosen = set(pivots)
        for p in index.original_backbone:
            if p not in chosen:
                pivots.append(p)
                chosen.add(p)
                if len(pivots) == k:
                    break
    return pivots, uncovered, r
