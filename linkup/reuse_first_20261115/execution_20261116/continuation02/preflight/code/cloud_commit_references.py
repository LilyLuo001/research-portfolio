"""Reconcile and validate original OpenCode visible output only on the Azure VM."""
import base64,datetime,gzip,hashlib,json,os,subprocess,sys
from pathlib import Path
os.umask(0o077)
R=Path.home()/'migration';Q=R/'execution_20261116/run001/qualification500_v1';D=Q/'kimi_reference350_v1';P=Q/'reference_preflight002'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def immutable(p,b):
 if p.exists():assert p.read_bytes()==b,'immutable_commit_conflict'
 else:
  with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
def write(p,x):immutable(p,(json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
raw=gzip.decompress(base64.b64decode(PAYLOAD_B64));payload=json.loads(raw);digest=hashlib.sha256(raw).hexdigest()
dest=D/'commits'/payload['commit_id'];dest.mkdir(parents=True,exist_ok=True)
receipt=dest/'RECEIPT_PUBLIC.json'
if receipt.exists():
 report=read(receipt);assert report['payload_sha256']==digest;print(json.dumps(report));raise SystemExit(0)
immutable(dest/'PAYLOAD_PRIVATE.json',raw)
assert sha(R/'code/validate_reviews.py')=='f7737143004374f9391a16ad2d1bab2fa47950c589232510045d1eee93bc2c20'
assert sha(R/'astra/extraction/FORMAL800_REVIEW_SCHEMA.json')=='fdc5b0d653bd8f1c98a3e6cd20970156621403154a7ad073e977ea14ddfb310e'
rows={str(x['case']):x for x in map(json.loads,(P/'BLIND_NEW_REFERENCE_INPUTS_PRIVATE.jsonl').read_text().splitlines())}
sys.path.insert(0,str(D/'code'));from opencode_candidate_boundary import parse_candidate
outcomes=[];exclusions={'tasks':[],'context_sha256':[]}
for item in payload['records']:
 case=str(item['case']);inp=rows[case];row=inp['row'];d=D/'results'/case;d.mkdir(parents=True,exist_ok=True)
 assert item.get('finished_at_utc'),'inflight_session_not_committable'
 immutable(d/'INPUT_PRIVATE.jsonl',(json.dumps(row,ensure_ascii=False)+'\n').encode())
 write(d/'EXECUTION_PRIVATE.json',item)
 status=item['status'];validation=None
 if item.get('provider_filtered'):
  exclusions['tasks'].append(inp['qualification_task']);exclusions['context_sha256'].append(row['context_sha256'])
  status='quarantined_provider_filter_no_reroute'
 elif status=='transport_visible_saved':
  try:
   review=parse_candidate(item['visible'],row)
   immutable(d/'REVIEW_PRIVATE.jsonl',(json.dumps(review,ensure_ascii=False)+'\n').encode())
   v=d/'VALIDATION_PUBLIC.json'
   if not v.exists():
    cp=subprocess.run([sys.executable,str(R/'code/validate_reviews.py'),'--packet',str(d/'INPUT_PRIVATE.jsonl'),'--reviews',str(d/'REVIEW_PRIVATE.jsonl'),'--schema',str(R/'astra/extraction/FORMAL800_REVIEW_SCHEMA.json'),'--expected-records','1','--private-validated',str(d/'VALIDATED_PRIVATE.jsonl'),'--private-errors',str(d/'ERRORS_PRIVATE.jsonl'),'--public-receipt',str(v)],capture_output=True)
   validation=read(v);status='frozen_validator_pass_reference_only' if validation['status']=='pass' else 'frozen_validation_failed_preserve_output'
  except (ValueError,TypeError,KeyError,json.JSONDecodeError) as error:
   status='visible_boundary_failed_preserve_output'
 if status!='frozen_validator_pass_reference_only' and item.get('status')=='transport_visible_saved' and validation is None:pass
 result={'status':status,'case':case,'semantic_accuracy_certified':False,'original_result_untouched':True,'new_production_accepted':0}
 write(d/'RESULT_PUBLIC.json',result)
 sums={p.name:sha(p) for p in d.iterdir() if p.is_file() and p.name!='SHA256SUMS_PRIVATE.json'};write(d/'SHA256SUMS_PRIVATE.json',sums);outcomes.append(result)
write(dest/'EXCLUSIONS_PRIVATE.json',exclusions)
report={'status':'reference_batch_cloud_validated','records':len(outcomes),'frozen_pass':sum(x['status']=='frozen_validator_pass_reference_only' for x in outcomes),'quarantined':len(exclusions['tasks']),'payload_sha256':digest,'new_production_accepted':0}
write(receipt,report);print(json.dumps(report))
