"""Recover original real graphs from GRAIL author's immutable GitHub archive.

No renamed generated replacements, sampled subgraphs, deduplication or changed
edge directions. Only convert original GRAIL text to directed METIS, losslessly.
"""
import argparse
import hashlib
import io
import json
import tarfile
import urllib.request
from pathlib import Path
from benchmark_oreach_ci import read_metis

SHA='c13a7364fbc185841fc6277cd295acf33a7188f0'
ARCHIVES={
    'sigmod08.tar.gz':('87530101a5bd050841c92fee3f9ee33e93233160',582001),
    'sigmod09.tar.gz':('08aaf9b00a2bc7f52ee63988d02a381b0714b896',412956),
}
FILES={
    'grail_go':('sigmod09.tar.gz','sigmod09/go_sub_6793.gra'),
    'grail_pubmed':('sigmod09.tar.gz','sigmod09/pubmed_sub_9000-1.gra'),
    'grail_citeseer':('sigmod09.tar.gz','sigmod09/citeseer_sub_10720.gra'),
    'grail_yago':('sigmod09.tar.gz','sigmod09/yago_sub_6642.gra'),
    'grail_kegg':('sigmod08.tar.gz','sigmod08/kegg_dag_uniq.gra'),
}

def parse_grail(raw):
    lines=raw.decode('ascii').splitlines()
    if len(lines)<2 or lines[0].strip()!='graph_for_greach':raise ValueError('wrong GRAIL header')
    n=int(lines[1])
    if n<1 or n>150000:raise ValueError('unsupported graph size')
    rows=[None]*n
    for line in lines[2:]:
        if not line.strip():continue
        if line.count(':')!=1 or not line.rstrip().endswith('#'):raise ValueError('malformed GRAIL row')
        key,values=line.split(':');u=int(key)
        if not 0<=u<n or rows[u] is not None:raise ValueError('duplicate/invalid vertex')
        row=list(map(int,values.rstrip().removesuffix('#').split()))
        if any(not 0<=v<n for v in row):raise ValueError('invalid edge endpoint')
        rows[u]=row
    if any(row is None for row in rows):raise ValueError('missing graph rows')
    return rows

def acquire(dataset,output,cache=None):
    if dataset not in FILES:raise ValueError('unknown dataset')
    archive,member=FILES[dataset];blob,expected_size=ARCHIVES[archive]
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    cache=Path(cache) if cache else output.parent
    cache.mkdir(parents=True,exist_ok=True);path=cache/archive
    url=f'https://raw.githubusercontent.com/zakimjz/grail/{SHA}/Downloads/{archive}'
    if not path.exists():
        with urllib.request.urlopen(url,timeout=90) as response:data=response.read(expected_size+1)
        path.write_bytes(data)
    data=path.read_bytes()
    git_blob=hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()
    if len(data)!=expected_size or git_blob!=blob:raise ValueError('archive differs from pinned author repository blob')
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive_file:
        raw=archive_file.extractfile(member).read()
    graph=parse_grail(raw)
    with output.open('w',encoding='ascii',newline='\n') as stream:
        stream.write(f'{len(graph)} {sum(map(len,graph))}\n')
        for row in graph:stream.write(' '.join(str(v+1) for v in row)+'\n')
    if read_metis(output)[0]!=graph:raise AssertionError('lossless conversion failed')
    info={'dataset':dataset,'source':'Original GRAIL author repository; real benchmark graph',
          'repository':'https://github.com/zakimjz/grail','commit':SHA,'archive_url':url,
          'archive_git_blob':blob,'archive_sha256':hashlib.sha256(data).hexdigest(),
          'member':member,'member_sha256':hashlib.sha256(raw).hexdigest(),
          'vertices':len(graph),'arcs':sum(map(len,graph)),
          'metis_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
          'conversion':'Only text encoding: all vertices, directed arcs, order and duplicates preserved'}
    output.with_suffix('.provenance.json').write_text(json.dumps(info,indent=2)+'\n')
    return info
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',choices=sorted(FILES),required=True)
    p.add_argument('--output',required=True);p.add_argument('--cache');a=p.parse_args()
    print(json.dumps(acquire(a.dataset,a.output,a.cache),indent=2))
