"""Constructive MAX-2SAT to exact backbone pivot coverage reduction.

For m Boolean variables, the backbone has 2m vertices, one pair for each
variable. Choose k=m pivots. Each variable's positive chain query has weight
M = 1 + sum(clause weights), enforcing one pivot per variable at the optimum.
Each clause becomes an unreachable query whose two certificate regions are the
singleton positions of its literals. Weighted satisfaction is exactly coverage.
"""
from tric import build_graph, make_pivot, certify
from backbone import backbone_intervals


def make_max2sat_instance(nvars,clauses,clause_weights=None):
    """clause=((var0,truth0),(var1,truth1)); variable 0..nvars-1.
    positive literal (i,True) is true at pivot 2i+1, negative at 2i.
    """
    if not nvars or any(len(cl)!=2 for cl in clauses):raise ValueError('invalid formula')
    if clause_weights is None:clause_weights=[1]*len(clauses)
    if len(clause_weights)!=len(clauses) or any(w<0 for w in clause_weights):
        raise ValueError('bad clause weights')
    h=2*nvars
    next_id=h
    edges=[(i,i+1) for i in range(h-1)]
    queries=[];weights=[]
    M=sum(clause_weights)+1
    for i in range(nvars):
        queries.append((2*i,2*i+1));weights.append(M)
    for clause,w in zip(clauses,clause_weights):
        loc=[]
        for variable,positive in clause:
            if not 0<=variable<nvars: raise ValueError('bad variable')
            loc.append(2*variable+int(bool(positive)))
        i,j=sorted(loc)
        if i==j: # duplicated literal -> can realize as a single positive query at i
            queries.append((i,i));weights.append(w)
            continue
        # Intended left certificate {i}: (L[t],L[s]]=(i-1,i]
        # Intended right certificate {j}: [R[t],R[s])=[j,j+1)
        # Reserve one fresh source and target per nonduplicate clause.
        s=next_id
        t=s+1
        next_id+=2
        if i>=0: edges.append((i,s))
        if j+1<h: edges.append((s,j+1))
        if i-1>=0: edges.append((i-1,t))
        if j<h: edges.append((t,j))
        # If a source with no incoming/outgoing has no edges, it still counts in n.
        # Nodes always have at least one edge for i<j with h>=2.
        queries.append((s,t));weights.append(w)
    adj,rev=build_graph(next_id,edges)
    return adj,rev,list(range(h)),queries,weights,M


def assignment_score(bits,clauses,weights):
    return sum(w for cl,w in zip(clauses,weights)
               if any(bits[var] == bool(pos) for var,pos in cl))


def make_vertex_cover_instance(nvertices,undirected_edges):
    """Linear-size reduction from Vertex Cover to certificate pivot selection.

    A graph H=(U,E) with |U|=nvertices maps to a DAG containing a directed
    path on |U| backbone pivots. Each edge (i,j) corresponds to an UNREACHABLE
    directed query with exactly two certifying backbone pivots {i,j}.

    Thus selecting <=k pivots to certify ALL query pairs is equivalent to
    selecting a vertex cover of size <=k in H.
    """
    if nvertices<0:raise ValueError('bad vertex count')
    edges=[(i,i+1) for i in range(nvertices-1)]
    queries=[]
    nxt=nvertices
    for e in undirected_edges:
        if len(e)!=2:raise ValueError('edge must have two endpoints')
        i,j=sorted(e)
        if not(0<=i<j<nvertices):raise ValueError('loop or invalid vertex')
        s=nxt;t=nxt+1;nxt+=2
        edges.append((i,s))
        if j+1<nvertices:edges.append((s,j+1))
        if i-1>=0:edges.append((i-1,t))
        edges.append((t,j))
        queries.append((s,t))
    adj,rev=build_graph(nxt,edges)
    return adj,rev,list(range(nvertices)),queries
