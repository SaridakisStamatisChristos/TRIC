"""Corruption tests for construction evidence and external replay accounting."""
import copy
import unittest
from unittest.mock import patch

import verify_phase33_evidence as v
from verify_phase33_external import validate_record


class ConstructionEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.name='phase33_many_weak_parts.json.gz'
        cls.path=v.E/'pilot'/cls.name
        cls.cell=v.read(cls.path)
        cls.manifest=v.read(v.E/'pilot/manifest.json')
        cls.manifest['files']=[f for f in cls.manifest['files'] if f['file']==cls.name]
        raw=(v.E/'new-fixtures'/cls.name).read_bytes()
        cls.fixture=(raw,v.read(v.E/'new-fixtures'/cls.name))

    def run_case(self,change=None):
        data=copy.deepcopy(self.cell)
        if change:change(data[0])
        original=v.read
        def reader(path):
            if path==self.path:return data
            if path==v.E/'pilot/manifest.json':return copy.deepcopy(self.manifest)
            return original(path)
        with patch.object(v,'read',side_effect=reader),patch.object(v,'fixtures',return_value={self.name:self.fixture}):
            return v.construction('pilot',['csr','closure','buffers','identical'],5,'warm',[self.name])

    def test_valid_case(self):
        self.assertEqual(self.run_case()[1],25)

    def reject(self,change):
        with self.assertRaises(AssertionError):self.run_case(change)

    def test_missing_trial(self):self.reject(lambda c:c['rows']['csr'].pop())
    def test_repeated_trial_id(self):self.reject(lambda c:c['rows']['csr'][1].update(trial=0))
    def test_missing_oracle(self):self.reject(lambda c:c['rows']['csr'][0].update(oracle_verified_pairs=0))
    def test_wrong_answers(self):self.reject(lambda c:c['rows']['csr'][0].update(checksum=0))
    def test_changed_retained_storage(self):self.reject(lambda c:c['rows']['csr'][0].update(retained_capacity_bytes=0))
    def test_replay_count_zero(self):self.reject(lambda c:c['rows']['csr'][0].update(build_count=0))
    def test_inadequate_duration(self):self.reject(lambda c:c['rows']['csr'][0].update(build_thread_cpu_ns=199999999))
    def test_nan_duration(self):self.reject(lambda c:c['rows']['csr'][0].update(build_thread_cpu_ns=float('nan')))
    def test_wrong_input(self):self.reject(lambda c:c.update(input_sha256='0'*64))
    def test_wrong_runtime_mode(self):self.reject(lambda c:c['rows']['csr'][0].update(mode='closure'))


class ExternalAccountingTests(unittest.TestCase):
    def row(self):
        import json
        row={'queries':3,'verified':3,'repeats':4,'calls':12,'query_cpu_ns':100000001,'query_ns':100000002,'build_cpu_ns':12,'build_ns':13,'reported_bytes':128,'peak_rss_kib':1024,'answer_hash':7,'checksum':9}
        return {'status':'ok','returncode':0,'stderr':'','stdout':json.dumps(row),'row':row}

    def test_valid_accounting(self):self.assertEqual(validate_record(self.row(),3,100000000)['calls'],12)
    def test_missing_checks(self):
        rec=self.row();rec['row']['verified']=2
        with self.assertRaises(AssertionError):validate_record(rec,3,100000000)
    def test_invented_parsed_timing(self):
        rec=self.row();rec['row']['query_cpu_ns']=1
        with self.assertRaises(AssertionError):validate_record(rec,3,100000000)
    def test_failure_never_yields_timing(self):
        self.assertIsNone(validate_record({'status':'timeout'},3,100000000))


if __name__=='__main__':unittest.main()
