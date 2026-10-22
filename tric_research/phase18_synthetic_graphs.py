"""Phase XVIII deterministic *synthetic* directed graph sources for CI.

Intentionally separate from the two previously verified published O'Reach
source instances. These graph families test structural sensitivity, not
independent real-world graph replication.
"""
import argparse
import hashlib
import json
from pathlib import Path

from tric import graph_family


SUPPORTED = ("chain", "communities", "blocks")


def make_graph(family, n=720, seed=20261022):
    if family not in SUPPORTED:
        raise ValueError("unsupported synthetic graph family")
    if not 80 <= n <= 3000 or n % 40:
        raise ValueError("n must be a multiple of 40, between 80 and 3000")
    adj, _ = graph_family(family, n, seed)
    if len(adj) != n:
        raise AssertionError("generator returned incorrect vertex count")
    for u,row in enumerate(adj):
        for v in row:
            if not 0 <= v < n or u == v:
                raise AssertionError("invalid generated arc")
    return adj


def metis_bytes(adj):
    n=len(adj)
    if n < 1:
        raise ValueError("empty graph")
    m=sum(len(row) for row in adj)
    lines=[f"{n} {m}"]
    for row in adj:
        lines.append(" ".join(str(v+1) for v in row))
    return ("\n".join(lines)+"\n").encode("ascii")


def write_dataset(family, metis_path, manifest_path, n=720, seed=20261022):
    adj=make_graph(family,n,seed)
    payload=metis_bytes(adj)
    metis_path=Path(metis_path)
    manifest_path=Path(manifest_path)
    metis_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    metis_path.write_bytes(payload)
    manifest={
        "origin":"TRIC synthetic test family, NOT original O'Reach graph data",
        "family":family, "vertices":n,
        "arcs":sum(map(len,adj)), "seed":seed,
        "generator":"tric.graph_family, directed graph, one-based unweighted METIS",
        "sha256":hashlib.sha256(payload).hexdigest(),
    }
    manifest_path.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf8")
    return manifest


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--family",choices=SUPPORTED,required=True)
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--manifest",required=True,type=Path)
    parser.add_argument("--vertices",type=int,default=720)
    parser.add_argument("--seed",type=int,default=20261022)
    args=parser.parse_args()
    print(json.dumps(write_dataset(args.family,args.out,args.manifest,
                                  args.vertices,args.seed),sort_keys=True))
