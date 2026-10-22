"""Phase XXII provenance audit for unavailable published instance links."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from benchmark_oreach_ci import read_metis
from phase22_graphs import FAMILIES,generate

class GeneratedGraphProvenance(unittest.TestCase):
    def test_deterministic_across_query_seeds(self):
        with tempfile.TemporaryDirectory() as td:
            a=Path(td)/"seed_a"/"graph.metis"
            b=Path(td)/"seed_b"/"graph.metis"
            for name in FAMILIES:
                pa=generate(name,a,n=120)
                pb=generate(name,b,n=120)
                self.assertEqual(pa["graph_sha256"],pb["graph_sha256"])
                self.assertEqual(pa["label"],name)
                self.assertIn("NOT original OReach",pa["source"])
                adj,_=read_metis(a)
                self.assertEqual(len(adj),120)
                self.assertEqual(sum(map(len,adj)),pa["edges"])
                self.assertTrue((a.parent/"generated_graph_provenance.json").is_file())

    def test_refuses_fake_original_labels(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                generate("go_sub",Path(td)/"fake_original.metis")
            with self.assertRaises(ValueError):
                generate("generated_dag",Path(td)/"bad.metis",n=0)

if __name__=="__main__":
    unittest.main()
