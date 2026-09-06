"""Synthetic tests of artifact checks. These do not validate any paper results."""
from pathlib import Path
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'scripts'/'validate_revision_delivery.py'
class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        proof=self.root/'proof.txt';proof.write_text('Synthetic test proof, not research evidence.')
        h=hashlib.sha256(proof.read_bytes()).hexdigest()
        row={'id':'TEST01','title':'Synthetic verification','source_refs':['TEST'],
          'prompt_section':'test','kind':'verification','priority':'blocking',
          'acceptance_checks':['fixture only'],'depends_on':[],
          'minimum_verified_evidence_roles':['source_evidence','verification_report'],
          'empirical':False,'status':'VERIFIED','summary':'Fixture','response_locations':['fixture'],
          'review':{'reviewer':'synthetic self-review','report_path':'proof.txt','independent':False},
          'evidence':[{'role':r,'path':'proof.txt','sha256':h} for r in ['source_evidence','verification_report']]}
        self.seed={'requirements':[copy.deepcopy(row)]}
        self.status={'requirements':[copy.deepcopy(row)]}
    def tearDown(self):
        self.tmp.cleanup()
    def run_check(self):
        (self.root/'seed.json').write_text(json.dumps(self.seed))
        (self.root/'status.json').write_text(json.dumps(self.status))
        return subprocess.run([sys.executable,str(SCRIPT),'--seed',str(self.root/'seed.json'),
          '--status',str(self.root/'status.json'),'--root',str(self.root)],capture_output=True,text=True)
    def test_valid_fixture(self):self.assertEqual(self.run_check().returncode,0)
    def test_omission(self):
        self.status['requirements']=[];self.assertEqual(self.run_check().returncode,1)
    def test_changed_requirement(self):
        self.status['requirements'][0]['acceptance_checks']=['weakened'];self.assertEqual(self.run_check().returncode,1)
    def test_missing_evidence(self):
        self.status['requirements'][0]['evidence']=[];self.assertEqual(self.run_check().returncode,1)
    def test_tampered_artifact(self):
        (self.root/'proof.txt').write_text('tampered');self.assertEqual(self.run_check().returncode,1)
    def test_incomplete_is_not_success(self):
        self.status['requirements'][0]['status']='RUN_UNVALIDATED';self.assertEqual(self.run_check().returncode,2)
    def test_cached_build_is_not_empirical_run(self):
        receipt={'command':'fixture command','start_utc':'2026-01-01T00:00:00Z',
          'end_utc':'2026-01-01T00:00:01Z','exit_code':0,'mode':'aggregate_rebuild',
          'code_hash':'fixture','spec_id':'fixture'}
        f=self.root/'receipt.json';f.write_text(json.dumps(receipt))
        for doc in [self.seed,self.status]:
            doc['requirements'][0]['empirical']=True
            doc['requirements'][0]['minimum_verified_evidence_roles'].append('run_receipt')
        self.status['requirements'][0]['evidence'].append({'role':'run_receipt','path':'receipt.json',
          'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
        self.assertEqual(self.run_check().returncode,1)
if __name__=='__main__':unittest.main()
