"""Auditable Phase XVIII incremental-cost and provenance regression tests."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from summarize_phase18 import amortize, strict_break_even, QUERY_COUNTS


def sample(seed, kind):
    truth={"uniform":20, "positive":1200, "negative":0, "balanced":600}[kind]
    baseline={"checksum":77,"pivot_probes":40,"pivot_rescues":6,
              "fallback_queries":12}
    selector={**baseline,"policy_id":4,"training_queries":500,
              "training_ns":1000000.0,
              "topological_fallbacks":5,"bidirectional_fallbacks":7,
              "median_ns_per_query":100.0}
    return {
        "graph_sha256":"a"*64, "seed":seed, "query_stratum":kind,
        "test_count":1200, "heldout_positive_count":truth,
        "query_file_sha256":hashlib.sha256(f"{seed}-{kind}".encode()).hexdigest(),
        "selector_training_queries_sha256":hashlib.sha256(f"train-{seed}".encode()).hexdigest(),
        "selector_training_count":500,
        "tric":{"policies":[{"name":"BFS","checksum":77}],
                "compact_pivots_selector":selector,
                "compact_pivots_bidir":{**baseline,"median_ns_per_query":140.0},
                "compact_pivots_topo":{**baseline,"median_ns_per_query":90.0}}
    }


class AmortizationTests(unittest.TestCase):
    def populate(self, dirname, corrupt=None):
        paths=[]
        for kind in ("uniform","positive","negative","balanced"):
            for seed in (20261022,20261023,20261024):
                data=sample(seed,kind)
                if corrupt:
                    corrupt(data,kind,seed)
                p=Path(dirname)/f"{kind}-{seed}.json"
                p.write_text(json.dumps(data),encoding="utf8")
                paths.append(p)
        return paths

    def test_break_even_strict_and_nonexistent(self):
        self.assertEqual(strict_break_even(80,140,100),3)
        self.assertEqual(strict_break_even(0,140,100),1)
        self.assertIsNone(strict_break_even(10,100,100))
        self.assertIsNone(strict_break_even(10,90,100))
        with self.assertRaises(ValueError):
            strict_break_even(-1,140,100)
        with self.assertRaises(ValueError):
            strict_break_even(20,float("nan"),100)

    def test_full_matrix_and_amortization(self):
        with tempfile.TemporaryDirectory() as t:
            report=amortize(self.populate(t))
            self.assertEqual(report["query_counts"],list(QUERY_COUNTS))
            for cls,group in report["strata"].items():
                self.assertEqual(len(group["seeds"]),3)
                self.assertEqual(group["baselines"]["bidir"]["per_seed_strict_break_even_queries"],
                                 [25001]*3)
                self.assertEqual(group["baselines"]["bidir"]["modelled_net_wins_by_query_count"]["1200"],0)
                self.assertEqual(group["baselines"]["bidir"]["modelled_net_wins_by_query_count"]["1000000"],3)
                self.assertEqual(group["baselines"]["topo"]["no_finite_break_even_seeds"],3)
                self.assertEqual(group["baselines"]["bidir"]["median_query_saving_ns"],40)
            self.assertEqual(report["selected_policies_by_seed_across_identical_uniform_training"]["20261022"],[4])
            self.assertTrue(report["uniform_train_same_across_all_heldout_classes"])

    def test_identical_training_input_must_match_between_strata(self):
        with tempfile.TemporaryDirectory() as t:
            def corrupt(data,kind,seed):
                if kind=="balanced" and seed==20261023:
                    data["selector_training_queries_sha256"]="f"*64
            with self.assertRaisesRegex(AssertionError,"training data changed"):
                amortize(self.populate(t,corrupt))

    def test_policy_selection_can_be_unstable_on_same_training(self):
        with tempfile.TemporaryDirectory() as t:
            def alter(data,kind,seed):
                if kind=="balanced" and seed==20261022:
                    data["tric"]["compact_pivots_selector"]["policy_id"]=5
            report=amortize(self.populate(t,alter))
            self.assertEqual(report["selected_policies_by_seed_across_identical_uniform_training"]["20261022"],[4,5])

    def test_reject_training_size_incorrect(self):
        with tempfile.TemporaryDirectory() as t:
            def alter(data,kind,seed):
                if kind=="uniform" and seed==20261022:
                    data["selector_training_count"]=499
            with self.assertRaisesRegex(ValueError,"train-only"):
                amortize(self.populate(t,alter))

    def test_reject_checksum_or_pivot_mismatch(self):
        with tempfile.TemporaryDirectory() as t:
            def alter(data,kind,seed):
                if kind=="negative" and seed==20261024:
                    data["tric"]["compact_pivots_selector"]["checksum"]=1
            with self.assertRaisesRegex(AssertionError,"checksum"):
                amortize(self.populate(t,alter))
        with tempfile.TemporaryDirectory() as t:
            def alter(data,kind,seed):
                if kind=="negative" and seed==20261024:
                    data["tric"]["compact_pivots_selector"]["pivot_probes"]=42
            with self.assertRaisesRegex(AssertionError,"pivot"):
                amortize(self.populate(t,alter))

    def test_reject_mixed_graph_and_missing_seed(self):
        with tempfile.TemporaryDirectory() as t:
            def alter(data,kind,seed):
                if kind=="uniform" and seed==20261022:
                    data["graph_sha256"]="b"*64
            with self.assertRaisesRegex(ValueError,"different graph"):
                amortize(self.populate(t,alter))
        with tempfile.TemporaryDirectory() as t:
            paths=self.populate(t)
            with self.assertRaisesRegex(ValueError,"three distinct seeds"):
                amortize(paths[:-1])

    def test_heldout_outcome_label_audit(self):
        with tempfile.TemporaryDirectory() as t:
            def alter(data,kind,seed):
                if kind=="positive" and seed==20261023:
                    data["heldout_positive_count"]=1199
            with self.assertRaisesRegex(AssertionError,"class"):
                amortize(self.populate(t,alter))


if __name__=="__main__":
    unittest.main()
