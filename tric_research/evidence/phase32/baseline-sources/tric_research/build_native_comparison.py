"""Build previous/current TRIC and original BFL/PLL/PPL with one benchmark source.

Optional O'Reach support links an already built, unchanged pinned upstream tree.
No upstream code is patched; the required cstdint include is a compiler flag.
"""
import argparse
import hashlib
import json
import shlex
import shutil
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OREACH_SHA='78b3e326bbb021b7ee225ab605a4cdd074fa1d93'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(args):
    output=Path(args.output).resolve();output.mkdir(parents=True,exist_ok=True)
    before=Path(args.before_headers).resolve()
    source=output/'native_compare_bench.cpp'
    shutil.copyfile(ROOT/'native_compare_bench.cpp',source)
    common=[args.compiler,'-std=c++17','-O3','-DNDEBUG','-DTRIC_WITH_BFL','-DTRIC_WITH_PRUNED_LABELING']
    common.extend('-I'+str(Path(path).resolve()) for path in args.extra_include)
    objects=[]
    if bool(args.oreach_source)!=bool(args.oreach_build):
        raise ValueError('provide both OReach source and build directories')
    if args.oreach_source:
        upstream=Path(args.oreach_source).resolve();compiled=Path(args.oreach_build).resolve()
        revision=subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD'],text=True).strip()
        if revision!=OREACH_SHA:
            raise ValueError('OReach checkout is not the pinned baseline')
        subprocess.run(['git','-C',str(upstream),'diff','--exit-code','HEAD'],check=True,capture_output=True)
        common+=['-DTRIC_WITH_OREACH','-include','cstdint','-fopenmp']
        common.extend('-I'+str(upstream/path) for path in (
            '.', 'app','extern/argtable3-3.0.3','extern/flat_hash_map','lib',
            'extern/KaHIP/lib','extern/KaHIP/lib/io','extern/KaHIP/lib/tools'))
        for library in ('libcommon','libreachability'):
            entries=sorted((compiled/'CMakeFiles'/(library+'.dir')).rglob('*.o'))
            if not entries:
                raise ValueError('missing compiled OReach library objects')
            objects.extend(map(str,entries))
    commands=[]
    for name,headers in [('previous',before),('candidate',ROOT)]:
        dependency_file=output/(name+'.d')
        command=common+['-MMD','-MF',str(dependency_file),'-I'+str(headers),'-I'+str(ROOT),str(source),*objects,'-o',str(output/name)]
        result=subprocess.run(command,capture_output=True,text=True)
        (output/(name+'-compile.stderr')).write_text(result.stderr)
        result.check_returncode()
        dependencies=shlex.split(dependency_file.read_text().replace('\\\n','').split(':',1)[1])
        runtime_names={p.name for p in headers.glob('*.h')}
        selected={Path(p).name:Path(p).resolve() for p in dependencies if Path(p).name in runtime_names}
        if not {'tric_reachability.h','partitioned_reachability.h','closure_index.h','scc_decomposition.h'}<=selected.keys():
            raise ValueError('missing compiled runtime dependencies')
        if any(path!=headers/key for key,path in selected.items()):
            raise ValueError('compiler selected a different runtime header directory')
        commands.append({'name':name,'command':command,'executable_sha256':digest(output/name),
                         'runtime_source_hashes':{p.name:digest(p) for p in headers.glob('*.h')},
                         'selected_runtime_dependencies':{str(path):digest(path) for path in selected.values()}})
    manifest={'compiler':subprocess.check_output([args.compiler,'--version'],text=True).splitlines()[0],
              'source_sha256':digest(source),'oreach_sha':OREACH_SHA if args.oreach_source else None,
              'bfl_commit':'0c837927a3f2fa3fc633abeedd56cea6e75d3a9a',
              'bfl_main_sha256':digest(ROOT/'third_party/bfl/main.cpp'),
              'pruned_labeling_commit':'65b4cadc8d70cd267cff80c4522b381e4a0b9e30',
              'pruned_labeling_sources':{str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT/'third_party/pruned_labeling').rglob('*')) if p.is_file()},
              'commands':commands}
    (output/'build_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before-headers',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--compiler',default='g++')
    p.add_argument('--oreach-source')
    p.add_argument('--oreach-build')
    p.add_argument('--extra-include',action='append',default=[])
    build(p.parse_args())
