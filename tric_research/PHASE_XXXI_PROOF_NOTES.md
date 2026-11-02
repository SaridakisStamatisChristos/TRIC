# Phase XXXI: residual interval lookup obligations

These are correctness propositions for established search techniques, not claims
of mathematical novelty or performance superiority. No formal proof assistant
was used. The statements below have human-checkable proofs; executable checks
provide separate, finite evidence.

## Contract

A closure row is a finite nonempty collection of disjoint half-open integer
intervals `[a_i,b_i)`, with `0 <= a_i < b_i <= INT_MAX`. Construction initially
sorts intervals by their lower endpoints. One interval is moved to a cached
slot, leaving the residual list sorted. The residual routine is called only
when this list is nonempty. The query coordinate is an unsigned 32-bit integer.
Membership in the cached interval OR membership in the residual union is the
answer. SCC preorder is unique across components, so this union represents the
same exact reachability relation before and after a permutation of its storage.

## P31.1: shrinking-window predecessor search

Let `R[0..n)` be the sorted residual intervals, with `n >= 1`. Start with
`p=0, c=n`. While `c>1`, put `h=floor(c/2)`, advance `p` by `h` iff
`R[p+h].first <= t`, and replace `c` by `c-h`. Return
`R[p].first <= t && t < R[p].end`.

If some lower endpoint is at most `t`, let `k` be the greatest such index. The
invariant is `p <= k < p+c`. If the pivot endpoint is at most `t`, then
`k >= p+h`, and the new window is exactly the old suffix. Otherwise `k < p+h`;
the new prefix has length `ceil(c/2) >= h`, so it still contains `k`. In both
cases it stays within the old window and its length strictly decreases.
Termination therefore gives `p=k`. If no lower endpoint is at most `t`, every
comparison is false, `p` remains zero, and the final lower-bound check rejects.
Disjointness makes membership equivalent to containment by the predecessor.
The procedure uses `O(log n)` comparisons and `O(1)` auxiliary space.

## P31.2: short-list unsigned membership

For an interval `[a,b)` in the stated domain, unsigned subtraction satisfies
`t-a < b-a` iff `a <= t < b`. If `t<a`, wraparound gives
`2^32+t-a >= 2^32-a`, which is greater than `b-a` since `b<2^32`.
For `t>=a`, subtraction does not wrap and the equivalence is immediate.
Taking the OR over every residual interval therefore gives exact membership.
Scanning at most four intervals takes constant work; using binary search for
longer rows retains `O(log n)` worst-case lookup. The finite test additionally
exercises unsigned coordinates near `UINT32_MAX`.

## P31.3: implicit binary-search-tree layout

For `n` residual intervals, consider the implicit complete binary tree with
array nodes `0..n-1`, left child `2p+1` and right child `2p+2`. Assign the sorted
intervals during an inorder traversal. Induction on subtrees shows that all
left endpoints in a left subtree are smaller than the root's and all endpoints
in the right subtree are larger. Standard predecessor traversal is therefore
valid: record the current node and go right when its lower endpoint is at most
`t`; otherwise go left. If a predecessor exists, the last recorded node is it.
If none exists, a final lower-endpoint check rejects the initial root sentinel.
The tree has height `O(log n)`, and traversal uses constant auxiliary space.

The cached interval is untouched. Reordering the residual intervals after all
closure unions have finished changes neither the represented set nor retained
table bytes. Reordering before union completion would violate the construction
merge invariant and is explicitly outside this proposition. The experimental
builder uses a temporary row copy and a logarithmic recursive traversal stack;
there is no claim that preprocessing time or peak memory is unchanged.

## P31.4: dispatch equivalence

For a non-valueless variant whose alternatives are closure, partitioned index,
and forest index in that order, branching on `index()` and selecting the matching
alternative dispatches exactly the same query as the existing `get_if` chain.
The class exposes no alternative-changing mutation after construction. Both
versions fall through to `get<2>` for any unexpected state and consequently
retain the same exception behavior. This proposition says nothing about machine
code layout or elapsed time.

## Practical consequence and fidelity boundary

All four candidate mechanisms can preserve exact answers, yet that does not
imply faster queries. Performance acceptance is a separate executed gate.
The branchless and short-list bodies are extracted from the actual prototype
headers for bit-set-oracle tests; boundary mutations must be detected. The layout
prototype also runs the native exhaustive, adversarial, interval, cross-chain,
forest and packed-coordinate suites. Every timed process independently checks
all its query pairs against BFS outside the measured region.

Proof status: **PROVED (human-checkable, conditional on the explicit contracts)**.
Formal-checker status: **NOT_EXECUTED**. Novelty: **not claimed**.
