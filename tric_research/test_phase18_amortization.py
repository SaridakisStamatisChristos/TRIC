"""Phase XVIII independent tests: data provenance, arithmetic and evidence gates."""
import copy
import json
import tempfile
from pathlib import Path
import unittest

from phase18_synthetic_graphs import make_graph, metis_bytes, write_dataset
from benchmark_oreach_ci import read_metis
from summarize_phase18 import amortize_training, summarize


def record(stratum,seed,graph_sha="abc",fit=6000000,base_bidir=180,base_topo=220,sel=140):
    n=12
    positive={"uniform":3,"positive":12,"negative":0,"balanced":6}[stratum]
    sha=f"query-{stratum}-{seed}"
    truth=9812
    shared={"pivot_probes":67,"pivot_rescues":11,"fallback_queries":5}
    methods={
        "compact_pivots_selector":{
            "checksum":truth,"training_queries":500,"policy_id":3,
            "topological_fallbacks":2,"bidirectional_fallbacks":3,
            "training_ns":fit,"median_ns_per_query":sel,**shared},
        "compact_pivots_bidir":{
            "checksum":truth,"median_ns_per_query":base_bidir,**shared},
        "compact_pivots_topo":{
            "checksum":truth,"median_ns_per_query":base_topo,**shared},
        "policies":[{"name":"BFS","checksum":truth}],
        "index_build_ms":0.3,"compact_build_ms":0.2
    }
    return{
        "graph_sha256":graph_sha,"graph_origin":"synthetic",
        "query_file_sha256":sha,"query_stratum":stratum,
        "seed":seed,"test_count":n,"heldout_positive_count":positive,
        "training_count":500,"offline_training_seconds_including_pivot_build":0.009,
        "tric":methods
    }


class Phase18Tests(unittest.TestCase):
    def test_break_even_exact_strict_positive_gain(self):
        self.assertEqual(amortize_training(6000000,180,140),150000)
        self.assertEqual(amortize_training(6000000,180,179),6000000)
        self.assertIsNone(amortize_training(6000000,180,180))
        self.assertIsNone(amortize_training(6000000,180,181))
        self.assertEqual(amortize_training(5,7,5),3)
        for values in [(-1,10,9),(10,0,9),(10,10,0)]:
            with self.assertRaises(ValueError):
                amortize_training(*values)

    def test_deterministic_synthetic_graph_and_metis(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            for kind in ("chain","blocks","communities"):
                a=base/(kind+".metis")
                m=base/(kind+".json")
                meta=write_dataset(kind,a,m,n=120,seed=42)
                contents=a.read_bytes()
                self.assertEqual(contents,metis_bytes(make_graph(kind,120,42)))
                self.assertEqual(json.loads(m.read_text()),meta)
                adj,_=read_metis(a)
                self.assertEqual(adj,make_graph(kind,120,42))
                self.assertEqual(meta["origin"].find("synthetic")>=0,True)
                self.assertEqual(meta["vertices"],120)
                self.assertGreater(meta["arcs"],0)
                self.assertEqual(meta["sha256"],__import__("hashlib").sha256(contents).hexdigest())
                self.assertEqual(write_dataset(kind,a,m,120,42),meta)

    def test_synthetic_generator_rejects_invalid_input(self):
        for family,n in [("madeup",120),("chain",25),("chain",100),("blocks",0)]:
            with self.assertRaises(ValueError):
                make_graph(family,n,42)

    def save(self,folder,rows):
        files=[]
        for i,x in enumerate(rows):
            p=Path(folder)/f"case-{i}.json"
            p.write_text(json.dumps(x),encoding="utf8")
            files.append(p)
        return files

    def test_amortization_horizons_do_not_claim_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            data=[record(c,s) for c in ("uniform","positive","negative","balanced")
                  for s in (11,12,13)]
            result=summarize(self.save(folder,data))
        c=result["classes"]["balanced"]
        self.assertEqual(c["median_policy_fit_ns"],6000000)
        self.assertEqual(c["break_even_queries"]["bidir"],[150000]*3)
        self.assertEqual(c["wins_at_horizon"]["bidir"]["1200"],0)
        self.assertEqual(c["wins_at_horizon"]["bidir"]["1000000"],3)
        self.assertEqual(c["wins_at_horizon"]["topo"]["100000"],3)
        self.assertIn("EXTRAPOLATED",result["horizon_type"])
        self.assertEqual(result["stability_same_uniform_train_by_seed"]["11"]["unique_policy_count"],1)

    def test_aggregator_rejects_false_evidence(self):
        original=[record(c,s) for c in ("uniform","positive","negative","balanced")
                  for s in (11,12,13)]
        def reject(mutator):
            rows=copy.deepcopy(original)
            mutator(rows)
            with tempfile.TemporaryDirectory() as folder:
                with self.assertRaises((ValueError,AssertionError)):
                    summarize(self.save(folder,rows))
        reject(lambda r:r[0].update({"graph_sha256":"different"}))
        reject(lambda r:r[0].update({"query_file_sha256":r[1]["query_file_sha256"]}))
        reject(lambda r:r[0].update({"training_count":499}))
        reject(lambda r:r[0].update({"heldout_positive_count":500}))
        reject(lambda r:r[0]["tric"]["compact_pivots_selector"].update({"checksum":2}))
        reject(lambda r:r[0]["tric"]["compact_pivots_selector"].update({"fallback_queries":3}))
        reject(lambda r:r[0]["tric"]["compact_pivots_selector"].update({"training_ns":-1}))
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                summarize(self.save(folder,original[:-1]))


if __name__=="__main__":
    unittest.main()
