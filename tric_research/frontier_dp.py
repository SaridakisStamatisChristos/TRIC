"""Exact weighted 1/2-interval pivot selection with frontier-state DP.

A query is certified when at least one chosen pivot lies in any of its
inclusive intervals. Distinct two-interval signatures maintain one Boolean
state only between the end of the first interval and the end of the second.

Let h be the domain length, q the number of query entries, k the pivot budget,
and w the maximum number of live two-interval signatures after any position.
The straightforward implementation takes O((h+q) * h * (k+1) * 2^w) time
and O(h*h*(k+1)*2^w + q) memory including all traceback records.
Its objective-only DP uses O(h*(k+1)*2^w + q) memory. This is an
FPT algorithm in frontier width w, independent of total number of
separated signatures r in the exponent. This is not a novelty claim.
"""
from collections import defaultdict


def prepare_events(h, intervals, weights):
    if not isinstance(h, int) or h < 0 or len(intervals) != len(weights):
        raise ValueError('invalid domain or mismatched lengths')
    group = defaultdict(int)
    fixed_loss = 0
    for raw, weight in zip(intervals, weights):
        if not isinstance(weight, (int, float)) or not (0 <= weight < float('inf')):
            raise ValueError('weights must be finite and nonnegative')
        if len(raw) > 2:
            raise ValueError('at most two intervals per query')
        sorted_ivs = []
        for pair in raw:
            if len(pair) != 2:
                raise ValueError('invalid interval')
            a,b = pair
            if not isinstance(a,int) or not isinstance(b,int) or not(0 <= a <= b < h):
                raise ValueError('interval outside domain')
            sorted_ivs.append((a,b))
        sorted_ivs.sort()
        if len(sorted_ivs) == 2 and sorted_ivs[1][0] <= sorted_ivs[0][1] + 1:
            sorted_ivs = [(sorted_ivs[0][0], max(sorted_ivs[0][1],sorted_ivs[1][1]))]
        if not weight:
            continue
        if not sorted_ivs:
            fixed_loss += weight
        else:
            group[tuple(sorted_ivs)] += weight
    first = [[] for _ in range(h)]
    second = [[] for _ in range(h)]
    single = [[] for _ in range(h)]
    doubles = [(sig, weight) for sig, weight in group.items() if len(sig) == 2]
    for sig, weight in group.items():
        if len(sig) == 1:
            a,b = sig[0]
            single[b].append((a,weight))
    starts = [[] for _ in range(h)]
    ends = [[] for _ in range(h)]
    for ident,(sig,weight) in enumerate(doubles):
        (a,b),(c,d) = sig
        starts[b].append((ident,a))
        ends[d].append((ident,c,weight))
    # Recycle Boolean slots in active-frontier order. A signature's slot is
    # freed at its second end d; signatures starting at the same position can
    # reuse it. Thus all state masks contain <= w bits, not r global bits.
    free_slots = []
    live = {}
    next_slot = 0
    pending = []
    max_active = 0
    for pos in range(h):
        for ident,a,weight in ends[pos]:
            slot = live.pop(ident)
            second[pos].append((slot,a,weight))
            free_slots.append(slot)
        for ident,a in starts[pos]:
            if free_slots:
                slot = free_slots.pop()
            else:
                slot = next_slot
                next_slot += 1
            live[ident] = slot
            first[pos].append((slot,a))
        pending.append(len(live))
        max_active = max(max_active, len(live))
    assert not live and next_slot == max_active
    return (first, second, single, fixed_loss, len(doubles), max_active, pending)


def optimize_frontier(h, intervals, weights, k, *, state_cap=None):
    """Return (selected_pivots, uncovered_weight, diagnostics).

    All selected pivots are different and exactly k are returned. The
    diagnostics include width, unique double-signature count, and max states.
    state_cap, if set, raises RuntimeError instead of silently approximating.
    """
    if not isinstance(k,int) or k < 0 or k > h:
        raise ValueError('invalid pivot budget')
    first, second, single, fixed, r, w, occupancy = prepare_events(h, intervals, weights)
    # State (number_selected, last_selected_position, first-covered-bitset).
    states = {(0,-1,0): fixed}
    traceback = []
    maxstates = 1
    for pos in range(h):
        next_states = {}
        parents = {}
        for state, old_loss in states.items():
            used,last,bits = state
            for take in (False,True):
                if take and used >= k:
                    continue
                chosen = used + int(take)
                remaining = h - pos - 1
                if chosen > k or chosen + remaining < k:
                    continue
                newlast = pos if take else last
                cost = old_loss
                for a,weight in single[pos]:
                    if newlast < a:
                        cost += weight
                newbits = bits
                for slot,a,weight in second[pos]:
                    if not (newbits >> slot)&1 and newlast < a:
                        cost += weight
                    newbits &= ~(1 << slot)
                for slot,a in first[pos]:
                    if newlast >= a:
                        newbits |= 1 << slot
                newstate = (chosen,newlast,newbits)
                prev = next_states.get(newstate)
                if prev is None or cost < prev:
                    next_states[newstate] = cost
                    parents[newstate] = (state, take)
        states = next_states
        traceback.append(parents)
        maxstates = max(maxstates,len(states))
        if state_cap is not None and len(states) > state_cap:
            raise RuntimeError(f'frontier state cap exceeded at position {pos}: {len(states)}')
    if not states:
        raise AssertionError('no feasible exact-k assignment')
    winner = min(states, key=lambda key:(states[key],key))
    objective = states[winner]
    out = []
    for pos in range(h-1,-1,-1):
        winner,take = traceback[pos][winner]
        if take:
            out.append(pos)
    out.reverse()
    if len(out)!=k:
        raise AssertionError('invalid pivot reconstruction')
    return out,objective,{'frontier_width':w,'two_interval_signatures':r,
                          'max_states':maxstates,'frontier_occupancy':occupancy}


def optimize_scc_frontier(adj, backbone, queries, weights, k, *, state_cap=None):
    """Run frontier exact selection using Phase IV SCC boundaries."""
    from backbone_scc import prepare_scc_backbone
    index = prepare_scc_backbone(adj, backbone)
    if not 0 <= k <= len(index.original_backbone):
        raise ValueError('invalid pivot budget')
    intervals = index.intervals(queries)
    chosen, loss, diag = optimize_frontier(
        len(index.spine_component), intervals, weights,
        min(k,len(index.spine_component)),state_cap=state_cap)
    pivots = [index.representatives[x] for x in chosen]
    if len(pivots) < k:
        selected = set(pivots)
        for p in index.original_backbone:
            if p not in selected:
                pivots.append(p)
                selected.add(p)
                if len(pivots) == k:
                    break
    return pivots,loss,diag
