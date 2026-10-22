"""Adversarial checks of Phase XV held-out reachability query construction."""
import unittest

from stratified_queries import generate_stratified_queries
from tric import early_reachable


class StratifiedQueryTests(unittest.TestCase):
    def setUp(self):
        self.adj = [[1, 2], [3], [3], [], [5], [], []]

    def check_class(self, stratum, count):
        queries = generate_stratified_queries(self.adj, count, 811, stratum)
        self.assertEqual(len(queries), count)
        self.assertEqual(queries, generate_stratified_queries(
            self.adj, count, 811, stratum))
        self.assertNotEqual(queries, generate_stratified_queries(
            self.adj, count, 812, stratum))
        self.assertTrue(all(u != v for u, v in queries))
        positives = sum(bool(early_reachable(self.adj, u, v)[0]) for u, v in queries)
        if stratum == "positive":
            self.assertEqual(positives, count)
        elif stratum == "negative":
            self.assertEqual(positives, 0)
        else:
            self.assertEqual(positives, count // 2)

    def test_positive(self):
        self.check_class("positive", 101)

    def test_negative(self):
        self.check_class("negative", 101)

    def test_balanced_odd(self):
        self.check_class("balanced", 101)

    def test_disjoint_components_and_cycles(self):
        adj = [[1], [0, 2], [3], [2], [5], [4]]
        for stratum in ("positive", "negative", "balanced"):
            pairs = generate_stratified_queries(adj, 35, 59, stratum)
            actual = sum(bool(early_reachable(adj, s, t)[0]) for s, t in pairs)
            self.assertEqual(actual, {"positive": 35, "negative": 0, "balanced": 17}[stratum])

    def test_impossible_negative_fully_strongly_connected(self):
        with self.assertRaisesRegex(ValueError, "unavailable"):
            generate_stratified_queries([[1], [2], [0]], 10, 9, "negative")

    def test_impossible_positive_without_nontrivial_edges(self):
        with self.assertRaisesRegex(ValueError, "unavailable"):
            generate_stratified_queries([[], [], []], 10, 9, "positive")

    def test_single_vertex_self_query_excluded(self):
        for stratum in ("positive", "negative", "balanced"):
            with self.assertRaises(ValueError):
                generate_stratified_queries([[]], 2, 7, stratum)

    def test_argument_validation(self):
        with self.assertRaises(ValueError):
            generate_stratified_queries([[0]], 0, 7, "positive")
        with self.assertRaises(ValueError):
            generate_stratified_queries([[0]], 3, 7, "unknown")


if __name__ == "__main__":
    unittest.main()
