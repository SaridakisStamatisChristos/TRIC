"""Executable upstream root-cause discrimination, never a performance claim."""
import argparse,json,subprocess,time
from pathlib import Path
from benchmark_oreach_ci import read_metis,write_queryfile,parse_oreach_csv
from tric import early_reachable

def diagnose(graph, original, guarded, out, timeout=45):
    graph=Path(graph).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    adj,_=read_metis(graph)
    n=len(adj)
    pairs=[(0,0),(0,n-1),(n-1,0),(n//2,n//2),(0,n//2),(n//2,n-1)]
    pairs += [(i,j) for i,j in ((0,1),(1,0),(n//4,n//4+1),(n//2,n//2+1))]
    pairs=[(i,j) for i,j in pairs if 0<=i<n and 0<=j<n]
    q=out/"smoke.query.m.txt"
    truths=write_queryfile(q,adj,pairs)
    result={"graph":str(graph),"nodes":n,"edges":sum(map(len,adj)),
            "query_count":len(pairs),"positive_count":truths,
            "runners":{}}
    for label,exe,extra in [
        ("original_default",original,[]),
        ("original_support1",original,["--support","1"]),
        ("guarded_default",guarded,[])]:
        csv=out/(label+".csv")
        cmd=[str(Path(exe).resolve()),str(graph),"--seed","20261022",
             "--queries",str(q),"--pbibfs","--pdfs","--output",str(csv),*extra]
        t=time.perf_counter()
        try:
            proc=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
            state={"returncode":proc.returncode,"elapsed_s":time.perf_counter()-t}
            (out/(label+".stdout")).write_text(proc.stdout)
            (out/(label+".stderr")).write_text(proc.stderr)
            state["stdout_tail"]=proc.stdout[-1600:]
            state["stderr_tail"]=proc.stderr[-1600:]
            if proc.returncode==0:
                try:
                    rows=parse_oreach_csv(csv,len(pairs),"mixed")
                    state["valid_algorithm_csv"]={x["algorithm"] for x in rows}=={"oreach-pdfs","oreach-pbibfs"}
                except Exception as exc:
                    state["valid_algorithm_csv"]=False
                    state["parse_error"]=str(exc)
        except subprocess.TimeoutExpired:
            state={"status":"timeout","elapsed_s":time.perf_counter()-t}
        result["runners"][label]=state
        print(json.dumps({"runner":label,**state}),flush=True)
    (out/"diagnosis.json").write_text(json.dumps(result,indent=2)+"\n")
    # A valid diagnostic does not equate successful process exit with
    # independently verified query correctness.
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--graph",required=True)
    p.add_argument("--original",required=True)
    p.add_argument("--guarded",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    diagnose(args.graph,args.original,args.guarded,args.output)
