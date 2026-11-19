import json,sys,tempfile,unittest,sqlite3,types
from unittest.mock import patch
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P));import finite_pipeline_v2 as f;import publish_physical_v3 as p
sys.modules['finite_pipeline']=f
sys.path.insert(0,str(P.parent/'control'))
from test_finite_pipeline import FiniteTest
class JsonlTest(unittest.TestCase):
 def test_unicode_separators_are_data(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'synthetic.jsonl';value=[{'text':'alpha\u2028beta\u0085gamma\u2029end'},{'text':'second'}]
   path.write_bytes(b''.join(json.dumps(x,ensure_ascii=False).encode()+b'\n' for x in value))
   self.assertEqual([json.loads(x) for x in f.jsonl_lines(path)],value)
   self.assertEqual(p.lines(path),value)
 def test_malformed_not_repaired_or_dropped(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'synthetic.jsonl';path.write_bytes(b'{"a":\n')
   with self.assertRaises(json.JSONDecodeError):p.lines(path)
   with self.assertRaises(json.JSONDecodeError):[json.loads(x) for x in f.jsonl_lines(path)]
 def test_no_final_newline(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'synthetic.jsonl';path.write_bytes(b'{"a":1}')
   self.assertEqual(p.lines(path),[{'a':1}])
 def test_policy_and_budget_not_changed(self):
  self.assertEqual(f.MAX_PHYSICAL,10000);self.assertEqual(f.MAX_WALL,172800)
  self.assertEqual(f.PILOT_CAP_NANO,150_000_000_000)

 def test_no_call_requires_real_size_bound_and_no_claim(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   with sqlite3.connect(root/'ADMISSION_PRIVATE.sqlite3') as db:db.execute('create table claims(leg text,context text)')
   item={'case':'1','row':{'context_sha256':'synthetic','record_id':'synthetic-id'}}
   row={'case':'1','context_sha256':'synthetic','record_id':'synthetic-id','leg':'Luna','payload':None,'field_validation':None}
   manifest={'manifest_path':str(root/'manifest'),'manifest_sha256':'synthetic'}
   obj=f.Supervisor.__new__(f.Supervisor);obj.root=root
   common=types.SimpleNamespace(load_bundle=lambda *a:({},[item],{},{}),encoded=lambda x:x,model_payload=lambda *a:b'X'*11,MAX_REQUEST_BYTES=10)
   with patch.dict(sys.modules,{'pilot_common':common}):
    self.assertTrue(obj.verified_size_no_call(manifest,row))
    common.MAX_REQUEST_BYTES=11
    with self.assertRaisesRegex(f.StopPipeline,'size_bound_not_reproduced'):obj.verified_size_no_call(manifest,row)
    common.MAX_REQUEST_BYTES=10
    with sqlite3.connect(root/'ADMISSION_PRIVATE.sqlite3') as db:db.execute("insert into claims values ('Luna','synthetic')")
    with self.assertRaisesRegex(f.StopPipeline,'existing_claim'):obj.verified_size_no_call(manifest,row)
 def test_no_call_cannot_be_label_or_wrong_input(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);item={'case':'1','row':{'context_sha256':'synthetic','record_id':'synthetic-id'}}
   row={'case':'1','context_sha256':'synthetic','record_id':'synthetic-id','leg':'Luna','payload':{'not':'allowed'},'field_validation':None}
   obj=f.Supervisor.__new__(f.Supervisor);obj.root=root
   common=types.SimpleNamespace(load_bundle=lambda *a:({},[item],{},{}))
   with patch.dict(sys.modules,{'pilot_common':common}):
    with self.assertRaisesRegex(f.StopPipeline,'semantic_result'):obj.verified_size_no_call({'manifest_path':'x','manifest_sha256':'x'},row)
    row['case']='wrong'
    with self.assertRaisesRegex(f.StopPipeline,'identity_mismatch'):obj.verified_size_no_call({'manifest_path':'x','manifest_sha256':'x'},row)

if __name__=='__main__':unittest.main()
