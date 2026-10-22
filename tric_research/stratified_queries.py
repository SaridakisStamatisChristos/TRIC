"""Deterministic, oracle-derived reachability-stratified benchmark workloads.

A source is sampled uniformly and a target is selected uniformly among that
source's qualifying destinations (excluding self-pairs). This is NOT uniform
sampling over all reachable/unreachable ordered vertex pairs. The resulting
source-weighted distribution is intentional and documented; do not conflate
it with the source O'Reach query datasets.
"""
from collections import OrderedDict, deque
import random


def _reachable_vertices(adj, source):
    """Full independent FIFO reachability traversal; never consult TRIC labels."""
    n = len(adj)
    seen = bytearray(n)
    seen[source] = 1
    work = deque([source])
    while work:
        u = work.popleft()
        for v in adj[u]:
            if not seen[v]:
                seen[v] = 1
                work.append(v)
    return seen


def generate_stratified_queries(adj, count, seed, stratum):
    if stratum not in ("positive", "negative", "balanced"):
        raise ValueError("stratum must be positive, negative or balanced")
    if count <= 0 or not adj:
        raise ValueError("count and number of vertices must be positive")
    n = len(adj)
    rng = random.Random(seed)
    cache = OrderedDict()

    def reachable(source):
        if source in cache:
            cache.move_to_end(source)
            return cache[source]
        flags = _reachable_vertices(adj, source)
        cache[source] = flags
        if len(cache) > 32:
            cache.popitem(last=False)
        return flags

    def draw(required_true):
        # For both classes, draw uniform sources conditioned on at least
        # one eligible nontrivial target; then uniform eligible targets.
        # Bounds guard against impossible classes (e.g. a fully SCC graph).
        max_attempts = max(2000, 25 * count, 12 * n)
        for _ in range(max_attempts):
            source = rng.randrange(n)
            flags = reachable(source)
            # Enumeration has a predictable O(n) bound and is oracle-only,
            # outside every measured native TRIC/O'Reach query timer.
            eligible = [v for v in range(n)
                        if v != source and bool(flags[v]) == required_true]
            if eligible:
                return source, eligible[rng.randrange(len(eligible))]
        raise ValueError("requested reachability class is unavailable or too rare "
                         "for this graph's source-uniform sampler")

    if stratum == "positive":
        answers = [True] * count
    elif stratum == "negative":
        answers = [False] * count
    else:
        answers = [True] * (count // 2) + [False] * (count - count // 2)
        rng.shuffle(answers)
    return [draw(wanted) for wanted in answers]
