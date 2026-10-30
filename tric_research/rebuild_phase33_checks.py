"""Rebuild archived construction variants and independent oracle checks."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path
from verify_phase33_evidence import ROOT, E, sha, read


def run(output,external=False):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    assert not any(output.iterdir()),'output must be empty'
    result={}
    for arm in ('previous','csr','closure','buffers','csr_v2'):
        d=output/arm;d.mkdir()
        for p in (E/'prototypes'/arm).glob('*.h'):shutil.copyfile(p,d/p.name)
        src=d/'native_runtime_check.cpp';shutil.copyfile(ROOT/src.name,src)
        cmd=['g++','-std=c++17','-O2','-fsanitize=undefined',str(src),'-o',str(d/'native-check')]
        subprocess.run(cmd,capture_output=True,check=True)
        proc=subprocess.run([str(d/'native-check'),'--self-test'],capture_output=True,check=True,timeout=300)
        assert not proc.stderr;result[arm]=json.loads(proc.stdout)
        expected=read(E/'v2_builds.json')['native_checks'] if arm=='csr_v2' else read(E/'checks.json')[arm]
        # Early campaign records include command metadata around native counts.
        if 'result' in expected:expected=expected['result']
        assert result[arm]==expected
    src=output/'identity.cpp';shutil.copyfile(E/'campaign-sources/csr_v2_identity.cpp',src)
    cmd=['g++','-std=c++17','-O2','-fsanitize=undefined',str(src),'-o',str(output/'identity-check')]
    subprocess.run(cmd,capture_output=True,check=True)
    p=subprocess.run([str(output/'identity-check')],capture_output=True,check=True,timeout=300);assert not p.stderr
    result['identity']=json.loads(p.stdout);assert result['identity']==read(E/'v2_builds.json')['identity']
    from verify_interval_storage import purpose_cases
    from test_native_runtime import serialize
    for arm in ('previous','csr_v2','buffers'):
        d=output/arm;source=d/'interval_storage_check.cpp'
        shutil.copyfile(ROOT/source.name,source)
        subprocess.run(['g++','-std=c++17','-O2','-fsanitize=undefined',str(source),'-o',str(d/'allocation-check')],capture_output=True,check=True)
    resources=[]
    for spec in purpose_cases():
        raw=serialize(spec['graph'],spec['queries']).encode();rows={}
        for arm in ('previous','csr_v2','buffers'):
            proc=subprocess.run([str(output/arm/'allocation-check'),spec['mode'],str(spec['cap']),str(spec['scratch'])],input=raw,capture_output=True,check=True,timeout=300)
            assert not proc.stderr;rows[arm]=json.loads(proc.stdout)
        for arm in ('csr_v2','buffers'):
            for key,value in rows['previous'].items():
                if key=='construction_peak_heap_bytes':assert rows[arm][key]<=value
                else:assert rows[arm][key]==value
        resources.append({'name':spec['name'],'rows':rows})
    result['resource_cases']=len(resources);assert len(resources)==15
    (output/'resources.json').write_text(json.dumps(resources,indent=2)+'\n')
    if external:
        up=E/'external-upstream';source=output/'external.cpp';shutil.copyfile(E/'campaign-sources/external.cpp',source)
        names=('csr_graph','scc','levels','minpost','feline','grail','preach','ferrari','tflabel','tol','two_hop')
        cmd=['g++','-std=c++17','-O1','-fsanitize=undefined','-I'+str(output/'csr_v2'),'-I'+str(up/'src/cpp/include'),str(source),*[str(up/'src/cpp'/(n+'.cpp')) for n in names],'-o',str(output/'external-check')]
        subprocess.run(cmd,capture_output=True,check=True)
        p=subprocess.run([str(output/'external-check'),'--self-test'],capture_output=True,check=True,timeout=300);assert not p.stderr
        result['external']=json.loads(p.stdout);assert result['external']=={'exhaustive_checks':32256}
    (output/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output');p.add_argument('--external',action='store_true');a=p.parse_args()
    print(json.dumps(run(a.output,a.external),indent=2))
