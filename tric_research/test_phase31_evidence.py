"""Adversarial integrity tests: coordinated metadata/raw tampering must fail."""
import base64
import copy
import gzip
import hashlib
import json
import unittest
from verify_phase31_evidence import EVIDENCE, load_archive, verify
from verify_phase31_qualification import verify_qualification
from verify_phase31_stability import verify_stability


class EvidenceTampering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = load_archive()

    def setUp(self):
        self.archive = copy.deepcopy(self.original)

    def corrupt_raw(self, change):
        run = self.archive['runs']['pilot']
        entry = run['manifest']['files'][0]
        cells = json.loads(gzip.decompress(base64.b64decode(run['raw_gzip_base64'][entry['file']])))
        change(cells)
        raw = gzip.compress(json.dumps(cells).encode(), mtime=0)
        entry['sha256'] = hashlib.sha256(raw).hexdigest()
        entry['cells'] = len(cells)
        run['raw_gzip_base64'][entry['file']] = base64.b64encode(raw).decode()

    def rejected(self):
        with self.assertRaises(AssertionError):
            verify(self.archive)

    def test_missing_cell_even_with_recomputed_hash(self):
        self.corrupt_raw(lambda cells: cells.pop())
        self.rejected()

    def test_duplicate_cell(self):
        self.corrupt_raw(lambda cells: cells.append(cells[0]))
        self.rejected()

    def test_missing_trial(self):
        self.corrupt_raw(lambda cells: cells[0]['rows']['dispatch'].pop())
        self.rejected()

    def test_changed_answer(self):
        def change(cells):
            row = cells[0]['rows']['dispatch'][0]
            row['checksum'] += 1
        self.corrupt_raw(change)
        self.rejected()

    def test_silent_memory_growth(self):
        def change(cells):
            cells[0]['rows']['dispatch'][0]['retained_capacity_bytes'] += 8
        self.corrupt_raw(change)
        self.rejected()

    def test_false_independent_oracle_claim(self):
        def change(cells):
            cells[0]['rows']['dispatch'][0]['oracle_verified_pairs'] -= 1
        self.corrupt_raw(change)
        self.rejected()

    def test_nonidentical_negative_control(self):
        self.archive['runs']['null']['manifest']['arms'][1]['executable_sha256'] = '0'*64
        self.rejected()

    def test_dropped_case_and_rewritten_protocol(self):
        self.archive['specs']['pilot']['datasets'].remove('example')
        self.rejected()

    def test_changed_source(self):
        self.archive['headers']['dispatch']['tric_reachability.h'] += '\n// changed\n'
        self.rejected()

    def test_nonfinite_timing(self):
        def change(cells):
            cells[0]['rows']['dispatch'][0]['query_ns'] = float('nan')
        self.corrupt_raw(change)
        self.rejected()


class QualificationTampering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = load_archive()
        cls.qualification = json.loads(gzip.decompress((EVIDENCE/'qualification.json.gz').read_bytes()))
        cls.stability = json.loads(gzip.decompress((EVIDENCE/'stability.json.gz').read_bytes()))

    def reject_qualification(self, change):
        data = copy.deepcopy(self.qualification)
        change(data)
        with self.assertRaises(AssertionError):
            verify_qualification(data, self.original)

    def test_missing_full_qualification_case(self):
        self.reject_qualification(lambda d: d['runs'].pop('0'))

    def test_unattested_benchmark_source(self):
        def change(data):
            data['build']['source'] += '\n// changed\n'
        self.reject_qualification(change)

    def test_posthoc_recalibration(self):
        def change(data):
            data['protocol']['specs'][0]['horizon'] += 1
        self.reject_qualification(change)

    def test_wrong_qualification_control_binary(self):
        def change(data):
            data['runs']['0']['manifest']['arms'][2]['executable_sha256'] = '0'*64
        self.reject_qualification(change)

    def test_lowered_duration_gate(self):
        data = copy.deepcopy(self.stability)
        data['protocol']['gates']['minimum_observed_query_cpu_ns'] = 1
        with self.assertRaises(AssertionError):
            verify_stability(data, self.original)


if __name__ == '__main__':
    unittest.main()
