"""Check all defaults, inputs, trials and failures of the expanded comparison."""
import statistics
from pathlib import Path
from verify_phase33_evidence import E, ROOT, read, sha, fixtures, positive
from benchmark_native_changes import payload


def validate_record(rec,queries,target):
    assert rec['status'] in ('ok','timeout','process_failure','wrong_answer','disqualified','not_attempted_after_resource_failure')
    if rec['status']!='ok':return None
    assert rec['returncode']==0 and not rec['stderr']
    row=rec['row'];assert read_json(rec['stdout'])==row
    assert row['queries']==row['verified']==queries
    assert type(row['repeats']) is int and 1<=row['repeats']<=1000000
    assert row['calls']==row['repeats']*queries
    assert row['query_cpu_ns']>=target
    for k in ('query_cpu_ns','query_ns','build_cpu_ns','build_ns'):positive(row[k])
    assert row['peak_rss_kib']>0 and row['reported_bytes']>=0
    return row


def read_json(text):
    import json
    return json.loads(text)


def verify():
    D=E/'external-results';p=read(E/'external_protocol.json');m=read(D/'manifest.json')
    assert m['complete'] is True and m['protocol_sha256']==sha((E/'external_protocol.json').read_bytes())
    prior=read(E/'external-interrupted-manifest.json')
    assert m['continuation']['prior_manifest_sha256']==sha((E/'external-interrupted-manifest.json').read_bytes())
    assert len(prior['files'])==m['continuation']['completed_cases']==72 and not prior['complete']
    assert m['files'][:72]==prior['files']
    stop=read(E/'external-resource-stop.json');stopped=read(E/'external-resource-stop-manifest.json')
    assert stop['protocol_deviation'] is True and stop['skipped_attempts']==24
    assert sha((E/'external-resource-stop.json').read_bytes())==m['resource_stop_sha256']
    assert sha((E/'external-resource-stop-manifest.json').read_bytes())==stop['prior_manifest_sha256']
    assert len(stopped['files'])==73 and m['files'][:73]==stopped['files']
    uniform=read(D/'kron_logn12-uniform.json.gz')
    assert sum(r['status']=='timeout' for r in uniform['rows']['tflabel'])==4
    choice=read(E/'external_runtime.json');assert m['executable_sha256']==choice['executable_sha256']
    assert choice['runtime']=='PR32 baseline unchanged' and choice['promotion_decision']=='RETAIN_BASELINE'
    for name,digest in choice['runtime_headers'].items():assert sha((ROOT/name).read_bytes())==digest
    build=read(E/'external_baseline_build.json')
    assert build['executable_sha256']==m['executable_sha256']
    assert build['source_sha256']==sha((E/'campaign-sources/external.cpp').read_bytes())
    assert build['checks']=={'exhaustive_checks':32256}
    assert p['arms']==['tric','feline','grail','preach','ferrari','tflabel','tol','identical']
    assert p['trials']==8 and p['query_target_cpu_ns']==100000000 and p['cpu']==1
    assert p['upstream_commit']=='0c84ca38de2d384c561690f4782f93e19fc76816'
    up=read(E/'external-upstream-manifest.json');assert up['commit']==p['upstream_commit']
    for name,digest in up['files'].items():assert sha((E/'external-upstream'/name).read_bytes())==digest
    pre=read(D/'preflight.json');assert sha((D/'preflight.json').read_bytes())==m['preflight_sha256']
    names={x['file'] for x in read(E/'fixture_manifest.json')}
    expected={f['dataset']:f for name,(_,f) in fixtures().items() if name in names and f['graph']['vertices']<=40000}
    assert len(pre)==len(expected);seen=set();disqualified=set();failures=[];checks=0
    for c in pre:
        assert c['dataset'] not in seen;seen.add(c['dataset']);f=expected[c['dataset']]
        assert c['input_sha256']==f['cases'][0]['native_input_sha256']
        assert set(c['rows'])==set(p['arms'][:-1]);answers=set()
        for arm,rec in c['rows'].items():
            row=validate_record(rec,len(f['cases'][0]['queries']),1)
            if row:answers.add(row['answer_hash']);checks+=row['verified']
            else:failures.append({'stage':'preflight','dataset':c['dataset'],'arm':arm,'status':rec['status']})
            if rec['status']=='wrong_answer':disqualified.add(arm)
        assert len(answers)<=1
    assert seen==set(expected)
    specs={(s['dataset'],s['seed'],s['stratum']):s for s in p['cases']};assert len(specs)==76
    seen=set();names=set();cells=[];processes=0
    for entry in m['files']:
        assert entry['file'] not in names;names.add(entry['file'])
        path=D/entry['file'];assert sha(path.read_bytes())==entry['sha256']
        c=read(path);s=c['spec'];key=(s['dataset'],s['seed'],s['stratum'])
        assert key not in seen;seen.add(key);assert s==specs[key]
        f=read(ROOT/'evidence/phase25/fixtures'/Path(s['fixture']).name)
        case=next(c for c in f['cases'] if c['seed']==s['seed'] and c['stratum']==s['stratum'])
        assert sha(payload(f,case))==s['input_sha256']
        rows=c['rows'];assert set(rows)==set(p['arms']);answers=set()
        for arm,records in rows.items():
            assert len(records)==8 and [r['trial'] for r in records]==list(range(8))
            for rec in records:
                row=validate_record(rec,len(case['queries']),100000000)
                if rec['status'] not in ('disqualified','not_attempted_after_resource_failure'):processes+=1
                if rec['status']=='not_attempted_after_resource_failure':assert arm=='tflabel' and s['dataset']=='kron_logn12' and s['stratum'] in stop['skip_strata']
                if row:answers.add(row['answer_hash']);checks+=row['verified']
                else:failures.append({'stage':'timing','dataset':s['dataset'],'stratum':s['stratum'],'arm':arm,'status':rec['status']})
                if rec['status']=='wrong_answer':disqualified.add(arm)
        assert len(answers)<=1
        def complete(arm):return all(r['status']=='ok' for r in rows[arm])
        def cost(rec):return rec['row']['query_cpu_ns']/rec['row']['calls']
        null=statistics.median(cost(a)/cost(b) for a,b in zip(rows['tric'],rows['identical'])) if complete('tric') and complete('identical') else None
        cell={'dataset':s['dataset'],'stratum':s['stratum'],'identical_ratio':null,'control_pass':null is not None and .9<=null<=1/.9,'ratios':{}}
        for arm in p['arms'][1:-1]:
            if complete('tric') and complete(arm):
                cell['ratios'][arm]=statistics.median(cost(b)/cost(a) for a,b in zip(rows['tric'],rows[arm]))
        cell['measurements']={arm:{key:statistics.median(r['row'][key] for r in records if r['status']=='ok') for key in ('build_cpu_ns','reported_bytes','peak_rss_kib')} for arm,records in rows.items() if complete(arm)}
        cells.append(cell)
    assert sum(f['status']=='not_attempted_after_resource_failure' for f in failures)==24
    assert seen==set(specs) and sorted(disqualified)==m['disqualified']
    results={}
    for arm in p['arms'][1:-1]:
        all_ratios=[c['ratios'][arm] for c in cells if arm in c['ratios']]
        qualified=[c['ratios'][arm] for c in cells if arm in c['ratios'] and c['control_pass'] and arm not in disqualified]
        results[arm]={'complete_cases':len(all_ratios),'qualified_cases':len(qualified),'all_median':statistics.median(all_ratios) if all_ratios else None,'qualified_median':statistics.median(qualified) if qualified else None,'qualified_tric_faster':sum(r>1 for r in qualified),'qualified_comparator_faster':sum(r<1 for r in qualified)}
    strata={}
    for stratum in sorted({c['stratum'] for c in cells}):
        strata[stratum]={}
        for arm in p['arms'][1:-1]:
            ratios=[c['ratios'][arm] for c in cells if c['stratum']==stratum and c['control_pass'] and arm in c['ratios'] and arm not in disqualified]
            strata[stratum][arm]={'qualified_cases':len(ratios),'median':statistics.median(ratios) if ratios else None}
    return {'strata':strata,'cases':76,'timing_processes':processes,'oracle_checks':checks,'protocol_deviation':stop,'control_failures':[c for c in cells if not c['control_pass']],'failures':failures,'disqualified':sorted(disqualified),'methods':results,'cells':cells,'scope':'Repeated warm queries, specific default implementations, no total-memory matching or global SOTA claim.'}


if __name__=='__main__':
    import json
    print(json.dumps(verify(),indent=2))
