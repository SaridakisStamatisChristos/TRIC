"""Build the unchanged pinned O'Reach library and our per-answer API adapter.

Needs system CMake, Boost headers and C++17 compiler. Upstream's known missing
cstdint include is supplied as a build flag; no upstream sources are edited.
"""
import argparse
import json
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OREACH_SHA='78b3e326bbb021b7ee225ab605a4cdd074fa1d93'
def build(source, output, compiler='g++'):
    source=Path(source).resolve();output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    sha=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    if sha!=OREACH_SHA:raise ValueError('wrong upstream SHA')
    if subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip():
        raise ValueError('upstream checkout has local changes')
    build_dir=output/'upstream-build'
    commands=[['cmake','-S',str(source),'-B',str(build_dir),'-DCMAKE_BUILD_TYPE=Release',
               '-DCMAKE_CXX_FLAGS=-include cstdint',f'-DCMAKE_CXX_COMPILER={compiler}'],
              ['cmake','--build',str(build_dir),'--parallel','2']]
    for cmd in commands:subprocess.run(cmd,check=True)
    includes=['','app','extern/argtable3-3.0.3','extern/flat_hash_map','lib','extern/KaHIP/lib',
              'extern/KaHIP/lib/io','extern/KaHIP/lib/tools']
    objects=sorted((build_dir/'CMakeFiles/libcommon.dir').rglob('*.o'))
    objects+=sorted((build_dir/'CMakeFiles/libreachability.dir').rglob('*.o'))
    if not objects:raise RuntimeError('no original library objects')
    exe=output/'partitioned_external_bench'
    cmd=[compiler,'-std=c++17','-O3','-DNDEBUG','-include','cstdint','-DTRIC_WITH_OREACH',
         '-fopenmp',*['-I'+str(source/p) for p in includes],str(ROOT/'partitioned_bench.cpp'),
         *map(str,objects),'-o',str(exe)]
    subprocess.run(cmd,check=True);commands.append(cmd)
    (output/'build_manifest.json').write_text(json.dumps({'upstream_sha':sha,'commands':commands},indent=2)+'\n')
    return exe
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();print(build(a.source,a.output))
