"""Traced CPython allocation peaks; not whole-process RSS or C++ memory."""
import json,random,tracemalloc,platform,sys
from path_monge import choose_path_monge
from path_sweep import choose_path_sweep

def run():
    n=1200;k=8;q=2000;r=random.Random(555)
    queries=[(r.randrange(n),r.randrange(n)) for _ in range(q)]
    weights=[r.randint(1,8) for _ in range(q)]
    ans={}
    for fn in (choose_path_monge,choose_path_sweep):
        tracemalloc.start()
        result=fn(n,queries,k,weights)
        _,peak=tracemalloc.get_traced_memory()
        tracemalloc.stop()
        ans[fn.__name__]=dict(peak_traced_bytes=peak,objective=result[1],pivots=result[0])
    if ans['choose_path_monge']['objective']!=ans['choose_path_sweep']['objective'] or ans['choose_path_monge']['pivots']!=ans['choose_path_sweep']['pivots']:raise AssertionError('mismatch')
    out=dict(n=n,k=k,q=q,seed=555,python=sys.version,platform=platform.platform(),results=ans)
    with open('memory_results.json','w') as f:json.dump(out,f,indent=2)
    print({name:round(v['peak_traced_bytes']/1024/1024,3) for name,v in ans.items()})
if __name__=='__main__':run()
