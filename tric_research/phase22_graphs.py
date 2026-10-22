"""Deterministic, provenance-labeled Phase XXII fallback graph families.

NOT original published O'Reach instances. This replaces unavailable
published go_sub, pubmed_sub and Delaunay URLs, which currently return 404.
Graph identity stays constant across all three query/training seeds.
"""
import argparse
import hashlib
import json
from pathlib import Path
from tric import graph_family
from benchmark_oreach_ci import read_metis

FAMILIES={"generated_dag":"dag",
          "generated_blocks":"blocks",
          "generated_communities":"communities"}
GENERATOR_SEED=20261001
N=2000

def generate(family, output, n=N, seed=GENERATOR_SEED):
    if family not in FAMILIES:
        raise ValueError("unsupported synthetic graph label")
    if n<80 or n>5000:
        raise ValueError("bounded synthetic size must be in [80,5000]")
    adj,_=graph_family(FAMILIES[family],n,seed)
    path=Path(output)
    path.parent.mkdir(parents=True,exist_ok=True)
    m=sum(map(len,adj))
    with path.open("w",encoding="ascii",newline="\n") as f:
        f.write(f"{n} {m}\n")
        for row in adj:
            f.write(" ".join(str(v+1) for v in row)+"\n")
    parsed,_=read_metis(path)
    if parsed!=adj:
        raise AssertionError("METIS roundtrip lost graph structure")
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    info={"source":"TRIC synthetic graph_family deterministic generator; NOT original OReach instance",
          "label":family,"graph_family":FAMILIES[family],
          "generator_seed":seed,"vertices":n,"edges":m,
          "graph_sha256":sha}
    (path.parent/"generated_graph_provenance.json").write_text(
        json.dumps(info,indent=2)+"\n")
    return info

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--family",choices=sorted(FAMILIES),required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    print(json.dumps(generate(args.family,args.output),indent=2))

if __name__=="__main__":
    main()
