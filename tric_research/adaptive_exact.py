"""Exact query-hull decomposition for weighted backbone certificate selection.

This implementation uses standard additive decomposition / knapsack convolution
and existing TRIC orientation/frontier/path algorithms. The combination is an
algorithm-engineering experiment; no priority or novelty claim is made.

All pivots lie on integer positions [0,h); select EXACTLY k unique pivots.
For each query, at least one chosen pivot inside any of its <=2 inclusive
intervals certifies it. Return uncovered nonnegative weight and witness.
"""
import math

from backbone import optimize_intervals
from frontier_dp import prepare_events
from path_sweep import choose_path_sweep


def _validate(h, intervals, weights, k):
    if not isinstance(h,int) or isinstance(h,bool) or h<0:
        raise ValueError('h must be a nonnegative integer')
    if not isinstance(k,int) or isinstance(k,bool) or not 0<=k<=h:
        raise ValueError('k must be an integer between 0 and h')
    if len(intervals)!=len(weights):
        raise ValueError('weights/queries length mismatch')
    normalized=[]
    for raw,weight in zip(intervals, weights):
        if not isinstance(weight,(int,float)) or not math.isfinite(weight) or weight<0:
            raise ValueError('finite nonnegative weights required')
        if len(raw)>2: raise ValueError('only one or two intervals per query')
        spans=[]
        for span in raw:
            if len(span)!=2: raise ValueError('interval must be a pair')
            a,b=span
            if not (isinstance(a,int) and isinstance(b,int) and
                    not isinstance(a,bool) and not isinstance(b,bool) and
                    0<=a<=b<h):
                raise ValueError('invalid interval')
            spans.append((a,b))
        spans.sort()
        merged=[]
        for a,b in spans:
            if merged and a<=merged[-1][1]+1:
                merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
            else:
                merged.append((a,b))
        normalized.append((tuple(merged),weight))
    return normalized


def _components(normalized):
    """Group overlapping support hulls; members never span two components."""
    records=sorted((spans[0][0],spans[-1][1],spans,weight)
                   for spans,weight in normalized if spans and weight>0)
    groups=[]
    for lo,hi,spans,weight in records:
        if groups and lo<=groups[-1][1]:
            groups[-1][1]=max(groups[-1][1],hi)
            groups[-1][2].append((spans,weight))
        else:
            groups.append([lo,hi,[(spans,weight)]])
    return groups


def _choose_engine(size,iv,wt,override):
    if override not in ('auto','frontier','orientation','compact'):
        raise ValueError('engine must be auto, frontier, orientation, or compact')
    r=len({tuple(q) for q,w in zip(iv,wt) if len(q)==2 and w>0})
    if r==0: return 'interval',r,0
    w=prepare_events(size,iv,wt)[5]
    if override!='auto':return override,r,w
    # Heuristic for Python implementations, not a theoretical performance bound.
    # Small r favors orientation; a single frontier pass evaluates all budgets.
    if r<=2: return 'orientation',r,w
    # The exact compact engine is advantageous when long components have few
    # distinct interval starts relative to the backbone length. This is a
    # conservative Python dispatch heuristic, not a runtime guarantee.
    distinct_starts=len({a for sig in iv for a,_ in sig})
    if size>=40 and (distinct_starts+1)*4 <= size:
        return 'compact',r,w
    return 'frontier',r,w



def _frontier_profile(h, iv, wt, max_k, *, state_cap=None):
    """Compute all exact budgets 0..max_k in one frontier DP traversal.

    This avoids repeating the same h-position scan for each budget.
    Traceback stores the entire per-layer predecessor relation.
    """
    first,second,single,fixed,_,_,_=prepare_events(h,iv,wt)
    states={(0,-1,0): fixed}
    trace=[]
    for pos in range(h):
        nxt={}; parents={}
        for state,old_loss in states.items():
            used,last,bits=state
            for take in (False,True):
                selected=used+int(take)
                if selected>max_k:continue
                newer_last=pos if take else last
                cost=old_loss
                for a,weight in single[pos]:
                    if newer_last<a:cost+=weight
                newer_bits=bits
                # Phase V's merged branch recycles bit slots when a second
                # interval ends at the same position that another first
                # interval ends. Retire previous live bits BEFORE using slots.
                for slot,a,weight in second[pos]:
                    if not (newer_bits>>slot)&1 and newer_last<a:
                        cost+=weight
                    newer_bits &= ~(1<<slot)
                for slot,a in first[pos]:
                    if newer_last>=a:newer_bits|=1<<slot
                key=(selected,newer_last,newer_bits)
                prior=nxt.get(key)
                if prior is None or cost<prior:
                    nxt[key]=cost
                    parents[key]=(state,take)
        states=nxt;trace.append(parents)
        if state_cap is not None and len(states)>state_cap:
            raise RuntimeError(f'frontier state cap exceeded at position {pos}')
    winners={}
    for key,cost in states.items():
        used=key[0]
        if used not in winners or (cost,key)<(states[winners[used]],winners[used]):
            winners[used]=key
    result=[]
    for budget in range(max_k+1):
        key=winners[budget]
        loss=states[key]
        pivots=[]
        for pos in range(h-1,-1,-1):
            key,take=trace[pos][key]
            if take:pivots.append(pos)
        pivots.reverse()
        result.append((loss,tuple(pivots)))
    return result

def optimize_adaptive(h,intervals,weights,k,*,engine='auto',state_cap=None):
    """Return (pivot_positions, uncovered_weight, diagnostics) for exact-k.

    Components consist of overlapping convex hulls of certificate intervals.
    Each region is solved independently for all relevant budgets; a min-plus
    convolution distributes k across components and uncovered free positions.

    Forced engines are useful for differential testing. The same weighted
    optimum is returned regardless of the engine, barring explicit state_cap.
    """
    normalized=_validate(h,intervals,weights,k)
    if engine not in ('auto','frontier','orientation','compact'):
        raise ValueError('unknown engine')
    empty_loss=sum(w for sig,w in normalized if not sig)
    groups=_components(normalized)
    free_count=h-sum(hi-lo+1 for lo,hi,_ in groups)
    covered=[False]*h
    for lo,hi,_ in groups:
        for p in range(lo,hi+1):covered[p]=True
    free_positions=[i for i in range(h) if not covered[i]]
    dp={0:(empty_loss,())}  # total chosen pivots -> (loss, path of local solutions)
    diag=[]
    for lo,hi,items in groups:
        size=hi-lo+1
        local=[tuple((a-lo,b-lo) for a,b in sig) for sig,_ in items]
        wt=[weight for _,weight in items]
        chosen_engine,r,w=_choose_engine(size,local,wt,engine)
        costs=[]
        if chosen_engine=='compact':
            from frontier_compact import optimize_compact_profile
            profile,_ = optimize_compact_profile(size,local,wt,min(k,size),state_cap=state_cap)
            costs=[(loss,tuple(lo+p for p in positions)) for loss,positions in profile]
        if chosen_engine=='frontier':
            costs=[(loss,tuple(lo+p for p in positions))
                   for loss,positions in _frontier_profile(
                       size,local,wt,min(k,size),state_cap=state_cap)]
        for budget in range(min(k,size)+1) if chosen_engine not in ('frontier','compact') else []:
            if chosen_engine=='interval':
                positions,loss=choose_path_sweep(size,[sig[0] for sig in local],budget,wt)
            else:
                positions,loss,_=optimize_intervals(size,local,wt,budget)
            costs.append((loss,tuple(lo+p for p in positions)))
        updated={}
        for previous_budget,(previous_loss,prior_pivots) in dp.items():
            for local_budget,(local_loss,local_pivots) in enumerate(costs):
                total_budget=previous_budget+local_budget
                if total_budget>k:break
                cand=(previous_loss+local_loss,prior_pivots+local_pivots)
                if total_budget not in updated or cand<updated[total_budget]:
                    updated[total_budget]=cand
        dp=updated
        diag.append({'start':lo,'end':hi,'queries':len(items),'signatures':r,
                     'frontier_width':w,'engine':chosen_engine,'max_budget':min(k,size)})
    options=[]
    for used,(loss,pivots) in dp.items():
        extra=k-used
        if 0<=extra<=free_count:
            full=tuple(sorted(pivots+tuple(free_positions[:extra])))
            options.append((loss,full))
    if not options:
        raise AssertionError('no feasible allocation of pivot budget')
    objective,positions=min(options)
    if len(positions)!=k or len(set(positions))!=k:
        raise AssertionError('invalid reconstruction')
    diagnostics={'components':len(groups),'free_positions':free_count,
                 'component_stats':diag,'allocation_states':len(dp)}
    return list(positions),objective,diagnostics


def optimize_scc_adaptive(adj,backbone,queries,weights,k,*,engine='auto',state_cap=None):
    """Exact weighted selection over original backbone using SCC compression."""
    from backbone_scc import prepare_scc_backbone
    index=prepare_scc_backbone(adj,backbone)
    if not isinstance(k,int) or not 0<=k<=len(index.original_backbone):
        raise ValueError('invalid pivot budget')
    chosen,loss,diag=optimize_adaptive(
        len(index.spine_component),index.intervals(queries),weights,
        min(k,len(index.spine_component)),engine=engine,state_cap=state_cap)
    originals=[index.representatives[x] for x in chosen]
    if len(originals)<k:
        used=set(originals)
        for p in index.original_backbone:
            if p not in used:
                originals.append(p)
                used.add(p)
                if len(originals)==k:break
    return originals,loss,diag
