"""Paired fresh-process comparisons on pinned native input bytes.

Each available arm BFS-verifies every query after its timed region. Repeats
execute frozen query pairs; they are not independent new requests. Includes
parsing/build/query costs, excludes process startup, verification and teardown.
"""
import argparse
import gzip
import hashlib
import json
import math
import os
import platform
import statistics
import subprocess
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def payload(fixture,case):
    graph=fixture['graph']
    return ('\n'.join([f"{graph['vertices']} {len(graph['arcs'])} {len(case['queries'])}",
        *(f'{u} {v}' for u,v in graph['arcs']),
        *(f'{u} {v}' for u,v in case['queries'])])+'\n').encode('ascii')


def atomic_write(path,data):
    """Publish complete bytes before a manifest can reference their digest."""
    temporary=path.with_name(path.name+'.tmp')
    with temporary.open('wb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())
    temporary.replace(path)
    directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(directory)
    finally:os.close(directory)


def run(args):
    if args.cpu is not None:
        os.sched_setaffinity(0,{args.cpu})
    arms=[{'name':name,'executable':str(Path(exe).resolve()),'mode':mode,
           'executable_sha256':digest(Path(exe).read_bytes())} for name,exe,mode in args.arm]
    if len({arm['name'] for arm in arms})!=len(arms) or args.trials%len(arms):
        raise ValueError('unique arm names and a multiple of arm count trials required')
    if args.trials<1 or any(x<1 for x in args.horizons):
        raise ValueError('positive trials/horizons required')
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    if any(output.iterdir()):
        raise ValueError('output directory must be empty')
    # Exclusive creation prevents two fresh invocations sharing an empty folder.
    lock=os.open(output/'manifest.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
    os.close(lock)
    manifest={'schema':1,'arms':arms,'cap_bytes':args.cap,'trials':args.trials,'horizons':args.horizons,
              'environment':{'platform':platform.platform(),'python':platform.python_version(),
                             'cpu_affinity':sorted(os.sched_getaffinity(0)),
                             'cpu_model':next((line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                                               if line.startswith('model name')),'unknown')},
              'timing_scope':__doc__,'files':[]}
    atomic_write(output/'manifest.json',(json.dumps(manifest,indent=2)+'\n').encode())
    for path in sorted(Path(args.fixtures).glob('*.json.gz')):
        fixture=json.loads(gzip.decompress(path.read_bytes()))
        if args.datasets and fixture['dataset'] not in args.datasets:
            continue
        results=[]
        for case in fixture['cases']:
            if args.seeds and case['seed'] not in args.seeds:
                continue
            raw=payload(fixture,case)
            if digest(raw)!=case['native_input_sha256']:
                raise AssertionError('fixture differs from pinned input bytes')
            for repeats in args.horizons:
                rows={arm['name']:[] for arm in arms}
                for trial in range(args.trials):
                    shift=trial%len(arms)
                    for arm in arms[shift:]+arms[:shift]:
                        mode=arm['mode']
                        if fixture['dataset'].startswith('generated_') and mode.startswith('oreach-'):
                            mode+='0'  # Same SCC quotient for every arm, upstream support=0.
                        command=[arm['executable'],mode,str(args.cap),str(repeats)]
                        proc=subprocess.run(command,input=raw,capture_output=True,timeout=args.timeout)
                        if proc.returncode:
                            (output/'failure.json').write_text(json.dumps({'command':command,'dataset':fixture['dataset'],
                                'case':case,'returncode':proc.returncode,'stderr':proc.stderr.decode(errors='replace')},indent=2)+'\n')
                            raise RuntimeError(f"{arm['name']} failed on {fixture['dataset']}")
                        lines=proc.stdout.decode().splitlines()
                        row=json.loads(lines[-1])
                        count=len(case['queries'])
                        if not row['available'] or row['actual_calls']!=count*repeats or row['oracle_verified_pairs']!=count:
                            raise AssertionError('missing calls or independent oracle checks')
                        if row['mode']!=mode or row['queries']!=count or row['repeats']!=repeats:
                            raise AssertionError('wrong mode or query shape')
                        if 'table_bytes' in row and row['table_bytes']>args.cap:
                            raise AssertionError('table payload cap exceeded')
                        if any(not isinstance(row[k],(int,float)) or not math.isfinite(row[k]) or row[k]<=0
                               for k in ('parse_ns','build_ns','query_ns','lifecycle_ns','timed_peak_rss_kib')):
                            raise AssertionError('invalid timing or memory measurement')
                        if abs(row['lifecycle_ns']-sum(row[k] for k in ('parse_ns','build_ns','query_ns')))>2:
                            raise AssertionError('lifecycle accounting mismatch')
                        row['trial']=trial
                        # Preserve upstream diagnostics, not just its final timer JSON.
                        row['stdout_prefix']='\n'.join(lines[:-1])
                        row['stderr']=proc.stderr.decode(errors='replace')
                        rows[arm['name']].append(row)
                if len({r['checksum'] for values in rows.values() for r in values})!=1:
                    raise AssertionError('cross-arm answer mismatch')
                summary={name:{'query_ns_per_call':statistics.median(r['query_ns']/r['actual_calls'] for r in values),
                               'query_thread_cpu_ns_per_call':statistics.median(r['query_thread_cpu_ns']/r['actual_calls'] for r in values) if 'query_thread_cpu_ns' in values[0] else None,
                               'build_ns':statistics.median(r['build_ns'] for r in values),
                               'lifecycle_ns':statistics.median(r['lifecycle_ns'] for r in values),
                               'peak_rss_kib':statistics.median(r['timed_peak_rss_kib'] for r in values)}
                         for name,values in rows.items()}
                result={'dataset':fixture['dataset'],'seed':case['seed'],'stratum':case['stratum'],
                        'repeats':repeats,'input_sha256':digest(raw),'rows':rows,'summary':summary}
                results.append(result)
                print(json.dumps({'dataset':fixture['dataset'],'seed':case['seed'],'stratum':case['stratum'],
                                  'repeats':repeats,'summary':summary}),flush=True)
                dest=output/(fixture['dataset']+'.json.gz')
                atomic_write(dest,gzip.compress(json.dumps(results,separators=(',',':')).encode(),mtime=0))
        if results:
            manifest['files'].append({'fixture_sha256':digest(path.read_bytes()),'file':dest.name,'sha256':digest(dest.read_bytes()),'cells':len(results)})
            atomic_write(output/'manifest.json',(json.dumps(manifest,indent=2)+'\n').encode())

    if not manifest['files']:
        raise ValueError('no matching fixture cases')
    for entry in manifest['files']:
        data=(output/entry['file']).read_bytes()
        if digest(data)!=entry['sha256'] or len(json.loads(gzip.decompress(data)))!=entry['cells']:
            raise AssertionError('final artifact integrity mismatch')
    manifest['complete']=True
    atomic_write(output/'manifest.json',(json.dumps(manifest,indent=2)+'\n').encode())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--arm',nargs=3,action='append',required=True,metavar=('NAME','EXECUTABLE','MODE'))
    parser.add_argument('--cap',type=int,default=2*1024*1024)
    parser.add_argument('--trials',type=int,default=5)
    parser.add_argument('--horizons',type=int,nargs='+',default=[1,100])
    parser.add_argument('--datasets',nargs='+')
    parser.add_argument('--seeds',nargs='+',type=int)
    parser.add_argument('--cpu',type=int)
    parser.add_argument('--timeout',type=int,default=180)
    run(parser.parse_args())
