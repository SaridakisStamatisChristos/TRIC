"""Metis and O'Reach output format tests; no O'Reach executable needed."""
import tempfile
import unittest
from pathlib import Path
from benchmark_oreach_ci import read_metis,generate_queries,write_queryfile,parse_oreach_csv

class BenchmarkProtocolTests(unittest.TestCase):
    def test_metis_blank_row_and_one_based(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'tiny.metis'
            path.write_text('% header\n3 2\n\n1\n1\n')
            a,r=read_metis(path)
            self.assertEqual(a,[[],[0],[0]])
            self.assertEqual(r,[[1,2],[],[]])
    def test_heldout_is_deterministic(self):
        g=[[1],[],[]]
        self.assertEqual(generate_queries(g,100,9),generate_queries(g,100,9))
        self.assertNotEqual(generate_queries(g,100,9),generate_queries(g,100,10))
    def test_oracle_queryfile_labels(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'q.m.txt'
            num=write_queryfile(p,[[1],[],[]],[(0,1),(1,0),(2,2)])
            self.assertEqual(num,2)
            self.assertEqual(p.read_text().splitlines(),['0 1 1','1 0 0','2 2 1'])
    def test_oreach_csv_contract(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'r.csv'
            p.write_text('%header\ng,3,2,10,0,mixed,q,oreach-pdfs,12.5,40,4\ng,3,2,10,0,mixed,q,oreach-pbibfs,12.5,30,3\n')
            x=parse_oreach_csv(p,10)
            self.assertEqual(len(x),2)
            self.assertEqual(x[0]['query_us'],4)
            with self.assertRaises(ValueError):parse_oreach_csv(p,9)
            self.assertEqual(len(parse_oreach_csv(p,10,'mixed')),2)
            with self.assertRaisesRegex(ValueError,"query-class metadata"):
                parse_oreach_csv(p,10,'true')
    def test_bad_metis_header_or_edge_count(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.metis'
            p.write_text('2 2\n2\n\n')
            with self.assertRaises(ValueError):read_metis(p)
if __name__=='__main__':unittest.main()
