"""Exact frontier-profile DP with canonicalized last-pivot states.

Given weighted query certificate unions (zero, one, or two integer intervals),
solve for ALL cardinalities 0..max_k.  The state stores the predecessor active
interval start rather than the literal last selected vertex.

This is a research prototype. It does not claim a novel general algorithm.
"""
from bisect import bisect_left, bisect_right
from collections import Counter
from frontier_dp import prepare_events


def optimize_compact_profile(h, intervals, weights, max_k, *, state_cap=None):
    """Return ``(profile, diagnostics)`` with optimal uncovered costs and pivots.

    ``profile[b] == (cost, tuple_of_b_distinct_pivots)`` for 0<=b<=max_k.
    The active-start diversity ``d`` counts distinct starts of intervals
    crossing the cut after the currently processed position. Memory also
    includes explicit traceback, which is proportional to total DP states.
    """
    if not isinstance(h, int) or isinstance(h,bool) or h < 0:
        raise ValueError('h must be a nonnegative integer')
    if not isinstance(max_k, int) or isinstance(max_k,bool) or not 0<=max_k<=h:
        raise ValueError('max_k out of range')
    first, second, single, fixed, r, w, _ = prepare_events(h,intervals,weights)

    # Starts of intervals that will end strictly after this position. An
    # interval [a,b] contributes threshold a to the cut at p iff a<=p<b.
    begins=[[] for _ in range(h)]
    finishes=[[] for _ in range(h)]
    for region,weight in zip(intervals,weights):
        if weight==0:continue
        for a,b in region:
            if a<b:
                begins[a].append(a)
                finishes[b].append(a)
    count=Counter()
    starts=[]
    states={(0,-1,0):fixed}
    traceback=[]
    max_states=1
    max_diversity=0
    for pos in range(h):
        for a in begins[pos]:
            if count[a]==0:
                starts.insert(bisect_left(starts,a),a)
            count[a]+=1
        for a in finishes[pos]:
            count[a]-=1
            if count[a]==0:
                del count[a]
                starts.pop(bisect_left(starts,a))
        max_diversity=max(max_diversity,len(starts))

        nxt={}
        parents={}
        for (used,last,bits),prior_cost in states.items():
            for take in (False,True):
                used2=used+int(take)
                if used2>max_k: continue
                real_last=pos if take else last
                cost=prior_cost
                for a,value in single[pos]:
                    if real_last<a: cost+=value
                new_bits=bits
                # Critical: retire bits *before* first events because the
                # Phase V event allocator may reuse bit slots on one position.
                for slot,a,value in second[pos]:
                    if not (new_bits>>slot)&1 and real_last<a:
                        cost+=value
                    new_bits &= ~(1<<slot)
                for slot,a in first[pos]:
                    if real_last>=a:
                        new_bits |= 1<<slot

                # Representatives of the partition induced by pending tests
                # `last >= a` with a in active starts. Earlier literal pivots
                # whose comparisons agree are future-indistinguishable.
                j=bisect_right(starts,real_last)-1
                last2=starts[j] if j>=0 else -1
                key=(used2,last2,new_bits)
                old=nxt.get(key)
                if old is None or cost<old:
                    nxt[key]=cost
                    parents[key]=((used,last,bits),take)
        states=nxt
        traceback.append(parents)
        max_states=max(max_states,len(states))
        if state_cap is not None and len(states)>state_cap:
            raise RuntimeError('compact frontier state cap exceeded')

    choices={}
    for key,cost in states.items():
        used=key[0]
        if used not in choices or (cost,key)<(states[choices[used]],choices[used]):
            choices[used]=key
    profile=[]
    for budget in range(max_k+1):
        key=choices[budget]
        loss=states[key]
        pivots=[]
        for pos in range(h-1,-1,-1):
            key,take=traceback[pos][key]
            if take:pivots.append(pos)
        pivots.reverse()
        profile.append((loss,tuple(pivots)))
    return profile,{'max_states':max_states,'max_active_starts':max_diversity,
                    'two_interval_signatures':r,'frontier_width':w}


def optimize_compact(h, intervals, weights, k, *,state_cap=None):
    profile,diag=optimize_compact_profile(
        h,intervals,weights,k,state_cap=state_cap)
    loss,pivots=profile[k]
    return list(pivots),loss,diag
