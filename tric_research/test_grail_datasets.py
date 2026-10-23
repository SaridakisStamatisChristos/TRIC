import unittest
from grail_datasets import parse_grail
class GrailParserTests(unittest.TestCase):
    def test_preserves_vertices_arcs_order_duplicates_and_loops(self):
        self.assertEqual(parse_grail(b'graph_for_greach\n3\n2: #\n0: 1 1 0 #\n1: 2 #\n'),[[1,1,0],[2],[]])
    def test_rejects_corrupted_graphs(self):
        cases=[b'x\n1\n0: #\n',b'graph_for_greach\n2\n0: #\n',
               b'graph_for_greach\n1\n0: 1 #\n',b'graph_for_greach\n1\n0: #\n0: #\n',
               b'graph_for_greach\n1\n0: 0\n']
        for raw in cases:
            with self.assertRaises(ValueError):parse_grail(raw)
if __name__=='__main__':unittest.main()
