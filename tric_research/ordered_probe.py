"""Exact budgeted *ordered* certificate-pivot optimization.

A query q carries a bitset of pivots that can certify it, a nonnegative
frequency weight and a fallback work estimate. Each examined pivot incurs
its own nonnegative probe cost; certification stops at the first match.

The algorithm jointly chooses <= budget distinct pivots and their order,
minimizing total weighted probe plus fallback work. It is an exhaustive
subset DP with subset-zeta preprocessing: O(c * 2**c + c * m) time,
O(2**c + m) memory, with c the candidate count, m the workload size.
It is not a claim of algorithmic novelty or real wall-clock optimization.
"""
from math import isfinite, inf
from numbers import Real, Integral


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value) or value < 0:
        raise ValueError(f'{name} must be a finite nonnegative real number')
    return float(value)


def ordered_cost(order, hit_masks, weights, fallback_costs, probe_costs):
    """Independent direct evaluator (reference oracle for a concrete order)."""
    cost = 0.0
    for mask, w, fb in zip(hit_masks, weights, fallback_costs):
        for p in order:
            cost += w * probe_costs[p]
            if mask & (1 << p):
                break
        else:
            cost += w * fb
    return cost


def greedy_coverage_order(hit_masks, weights, candidate_count, budget):
    """Common selection baseline: weighted new hits, ignoring actual probe cost."""
    remain = set(range(candidate_count)); chosen = []; covered = 0
    for _ in range(min(budget, candidate_count)):
        best = max(remain, key=lambda p:(
            sum(w for mask, w in zip(hit_masks,weights)
                if (mask & (1 << p)) and not (mask & covered)), -p))
        chosen.append(best);covered |= 1 << best;remain.remove(best)
    return chosen


def optimize_ordered(hit_masks, weights, fallback_costs, probe_costs,
                     budget, *, max_candidates=19):
    """Return (ordered pivots, optimum expected-work sum, diagnostics).

    The budget is an upper bound, not an obligation to probe useless pivots.
    Every eligible set and every permutation is represented via subset DP.
    """
    c = len(probe_costs)
    if (isinstance(budget, bool) or not isinstance(budget, Integral)
            or not 0 <= budget <= c):
        raise ValueError('budget must be an integer between 0 and c')
    if c > max_candidates or max_candidates < 0:
        raise ValueError('candidate count exceeds exact solver cap')
    if not (len(hit_masks) == len(weights) == len(fallback_costs)):
        raise ValueError('query input lengths differ')
    costs = [_number(v, 'probe cost') for v in probe_costs]
    n = 1 << c; full=n-1
    weight_by_hit = [0.0]*n
    fb_by_hit = [0.0]*n
    for h, w, f in zip(hit_masks, weights, fallback_costs):
        if isinstance(h, bool) or not isinstance(h, Integral) or not 0<=h<=full:
            raise ValueError('query hit mask out of range')
        w = _number(w,'query weight'); f = _number(f,'fallback cost')
        weight_by_hit[h] += w
        fb_by_hit[h] += w*f
    # Subset zeta: for X, sums weights of queries whose hit-mask is subset of X.
    # For chosen S, uncovered iff hit-mask subset of complement(S).
    for i in range(c):
        bit=1<<i
        for mask in range(n):
            if mask & bit:
                weight_by_hit[mask] += weight_by_hit[mask^bit]
                fb_by_hit[mask] += fb_by_hit[mask^bit]
    dp = [inf]*n; parent = [None]*n
    dp[0]=0.0
    visited=0
    for mask in range(n):
        if dp[mask] == inf or mask.bit_count() >= budget:continue
        visited += 1
        survivors=weight_by_hit[full^mask]
        not_selected = full ^ mask
        while not_selected:
            bit=not_selected & -not_selected
            p=bit.bit_length()-1
            nxt=mask | bit
            cand=dp[mask] + costs[p]*survivors
            if cand < dp[nxt]:
                dp[nxt]=cand; parent[nxt]=(mask,p)
            not_selected-=bit
    best_mask = min(
        (mask for mask in range(n) if mask.bit_count()<=budget),
        key=lambda mask:(dp[mask] + fb_by_hit[full^mask],mask.bit_count(),mask))
    answer = dp[best_mask] + fb_by_hit[full^best_mask]
    order=[];mask=best_mask
    while mask:
        prev,p=parent[mask]
        order.append(p);mask=prev
    order.reverse()
    return order,answer,{'candidates':c,'queries':len(hit_masks),
                         'budget':budget,'selected':len(order),
                         'states':n,'relaxed_states':visited,
                         'uncovered_weight':weight_by_hit[full^best_mask],
                         'uncovered_fallback':fb_by_hit[full^best_mask]}


def hit_masks_for_pivots(pivots, queries):
    """Build exact per-query certifier bitsets from existing TRIC pivots."""
    from tric import certify
    result=[]
    for s,t in queries:
        mask=0
        for i,p in enumerate(pivots):
            if certify(p,s,t) is not None: mask |= 1<<i
        result.append(mask)
    return result
