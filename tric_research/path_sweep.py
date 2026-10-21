"""Exact weighted path-pivot optimizer using a segment-tree interval sweep.

Time O(k*(n+q)*log n), memory O(n+q+k*n), for q workload entries.
Preprocessing query events O(n+q); each DP row is an online range-add min-query
sweep. This is a specialization of standard range-add/range-min machinery.
"""
class RangeAddMin:
    def __init__(self, vals):
        n=len(vals);self.n=n
        self.val=[float('inf')]*(4*max(1,n));self.arg=[0]*(4*max(1,n));self.lazy=[0]*(4*max(1,n))
        if n:self.build(1,0,n-1,vals)
    def build(self,x,l,r,v):
        if l==r:self.val[x]=v[l];self.arg[x]=l;return
        m=(l+r)//2;self.build(2*x,l,m,v);self.build(2*x+1,m+1,r,v);self.pull(x)
    def pull(self,x):
        a=2*x;b=a+1
        if (self.val[a],self.arg[a]) <= (self.val[b],self.arg[b]):self.val[x]=self.val[a];self.arg[x]=self.arg[a]
        else:self.val[x]=self.val[b];self.arg[x]=self.arg[b]
    def apply(self,x,w):
        self.val[x]+=w;self.lazy[x]+=w
    def push(self,x):
        if self.lazy[x]:
            self.apply(x*2,self.lazy[x]);self.apply(x*2+1,self.lazy[x]);self.lazy[x]=0
    def add(self,L,R,w,x=1,l=0,r=None):
        if r is None:r=self.n-1
        if L>R or l>R or r<L or w==0:return
        if L<=l and r<=R:self.apply(x,w);return
        self.push(x);m=(l+r)//2
        self.add(L,R,w,x*2,l,m);self.add(L,R,w,x*2+1,m+1,r);self.pull(x)
    def prefix_min(self,R,x=1,l=0,r=None):
        if r is None:r=self.n-1
        if R<l:return (float('inf'),-1)
        if r<=R:return self.val[x],self.arg[x]
        self.push(x);m=(l+r)//2
        a=self.prefix_min(R,x*2,l,m)
        if R<=m:return a
        b=self.prefix_min(R,x*2+1,m+1,r)
        return min(a,b,key=lambda z:(z[0],z[1]))


def choose_path_sweep(n,queries,k,weights=None):
    if k<0 or k>n:raise ValueError('invalid pivot budget')
    if n<0:raise ValueError('invalid n')
    if n==0:
        if queries:raise ValueError('invalid empty domain')
        return [],0
    if weights is None:weights=[1]*len(queries)
    if len(weights)!=len(queries) or any(w<0 for w in weights):raise ValueError('invalid weights')
    # At step j the gap ends at j-1; process all intervals with right endpoint j-1.
    events=[[] for _ in range(n+1)]
    totals=[0]*(n+1)
    for (s,t),w in zip(queries,weights):
        if not (0<=s<n and 0<=t<n):raise ValueError('out-of-bounds query')
        lo=min(s,t);hi=max(s,t)
        events[hi+1].append((lo,w))
        totals[hi+1]+=w
    if k==0:return [],sum(weights)
    # Leftmost gap for first pivot j consists of vertices 0..j-1.
    dp_prev=[0]*n
    cur=0
    for j in range(n):
        cur+=totals[j]
        dp_prev[j]=cur
    parents=[[-1]*n for _ in range(k+1)]
    for r in range(2,k+1):
        tree=RangeAddMin(dp_prev)
        dp_cur=[float('inf')]*n
        for j in range(n):
            for lo,w in events[j]:
                if lo>0:tree.add(0,lo-1,w)
            if j>=r-1:
                dp_cur[j],parents[r][j]=tree.prefix_min(j-1)
        dp_prev=dp_cur
    # The final gap j+1..n-1 contains any query with both endpoints strictly > j.
    # Sweep from right to left: when the low endpoint equals j+1, this query joins.
    tail=[0]*(n+1)
    lo_totals=[0]*n
    for (s,t),w in zip(queries,weights):lo_totals[min(s,t)]+=w
    cur=0
    for j in range(n-1,-1,-1):
        cur+=lo_totals[j+1] if j+1<n else 0
        tail[j]=cur
    last=min(range(k-1,n),key=lambda j:(dp_prev[j]+tail[j],j))
    val=dp_prev[last]+tail[last]
    selected=[]
    for r in range(k,0,-1):
        selected.append(last);last=parents[r][last]
    selected.reverse()
    return selected,val
