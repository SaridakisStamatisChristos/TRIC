"""Regression: original upstream SIGSEGV cannot become a fake comparison win.

Runs the exact C++ TRIC + cold-start replay with a deliberately exiting
fake external executable to reproduce an upstream crash deterministically.
Never modifies the original pinned O'Reach source or TRIC query semantics.
"""
import json
import tempfile
import unittest
from pathlib import Path

import benchmark_hot_source_external as benchmark
import benchmark_phase22
from phase22_graphs import generate
from verify_phase22_artifact import verify

class OriginalComparatorSegfault(unittest.TestCase):
    def make_args(self,root,exit_code=139):
        root=Path(root)
        source=root/"graph.metis"
        generate("generated_blocks",source,n=80,seed=100)
        upstream=root/"fake-upstream.sh"
        upstream.write_text("#!/bin/sh\nexit "+str(exit_code)+"\n")
        upstream.chmod(0o755)
        args=benchmark.parser().parse_args([
            "--graph",str(source),"--oreach-binary",str(upstream),
            "--oreach-git-sha","upstream-test-double-unavailable",
            "--output-dir",str(root/"output"),"--train","32","--test","24",
            "--candidates","4","--pivot-budget","2","--hot-sources","2",
            "--seed","100","--oreach-repetitions","1",
            "--tric-repetitions","15","--closure-cap-mib","0",
            "--allow-upstream-segfault",
        ])
        args.dataset="generated_blocks"
        args.replay_factors=[1,50]
        args.lifetime_repetitions=1
        return args

    def test_native_lifetime_kept_and_original_crash_not_falsely_counted(self):
        with tempfile.TemporaryDirectory() as d:
            args=self.make_args(d)
            result=benchmark_phase22.run(args)
            self.assertFalse(result["upstream_comparisons_complete"])
            self.assertEqual(verify(Path(args.output_dir)/"phase22_lifetime_summary.json",
                                    "generated_blocks",100),
                             ["matched_hot","uniform","shifted_hot"])
            for i,cls in enumerate(benchmark.CLASSES):
                state=result["upstream_comparator_per_class"][cls]
                self.assertEqual(state["valid_comparisons"],0)
                self.assertEqual(state["status"],
                    "unavailable_upstream_segfault" if i==0 else
                    "unavailable_after_upstream_segfault")
                record=json.loads(
                    (Path(args.output_dir)/cls/"comparison.json").read_text())
                self.assertNotIn("oreach-pdfs",record["times"])
                self.assertNotIn("oreach-pbibfs",record["times"])
                self.assertEqual(record["oreach_status"]["valid_comparisons"],0)
                self.assertTrue((Path(args.output_dir)/cls/"oreach_unavailable.json").is_file())
                for horizon in ("1","50"):
                    measured=result["classes"][cls][horizon]
                    self.assertTrue(measured["pivot_index"]["checksum_verified"])
                    self.assertTrue(measured["cache_pivot_index"]["checksum_verified"])
                    external=measured["original_oreach_pdfs_fresh_process"]
                    self.assertEqual(external["actual_calls"],0)
                    self.assertEqual(external["valid_comparisons"],0)
            self.assertTrue(
                (Path(args.output_dir)/"matched_hot"/"oreach_0.stderr.txt").is_file())

    def test_opt_in_refused_on_original_graph(self):
        with tempfile.TemporaryDirectory() as d:
            args=self.make_args(d)
            args.dataset="example"
            with self.assertRaisesRegex(ValueError,"generated"):
                benchmark.run(args)

    def test_false_success_requires_only_sigsegv(self):
        # This negative case must still FAIL even when synthetic opt-in is set.
        # Exit 42 is not the tracked upstream signal, not a valid comparator.
        with tempfile.TemporaryDirectory() as d:
            args=self.make_args(d,exit_code=42)
            with self.assertRaisesRegex(RuntimeError,"failed matched_hot/0: 42"):
                benchmark.run(args)

if __name__=="__main__":
    unittest.main()
