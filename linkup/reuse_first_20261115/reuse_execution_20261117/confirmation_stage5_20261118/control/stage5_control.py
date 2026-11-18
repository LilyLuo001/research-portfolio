"""Allowlisted finite-stage cloud controls. Never prints private text/credentials."""
import argparse,json,sys,time
from pathlib import Path
D=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(D.parent/'execution_20261116_continuation02'));import control
BASE=r'''import json,os,sys,hashlib,datetime,subprocess,sqlite3
from pathlib import Path
R=Path.home()/'migration';D=R/'confirmation_stage5_20261118';C=D/'execution_v1'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
'''
LAUNCH=r'''
os.umask(0o077);L=C/'luna';receipt=C/'LUNA_LAUNCH_PUBLIC.json'
assert not receipt.exists(),'existing_launch_receipt_no_resubmission'
freeze=read(C/'EXECUTION_FREEZE_PUBLIC.json');assert freeze['frame_count']==135 and freeze['model_calls']==0
assert sha(L/'INPUT_PINS_PUBLIC.json')==freeze['runtime_input_pin_sha256']
assert sha(C/'FRAME_PRIVATE.jsonl')==freeze['frame_freeze']['frame_sha256']
for name,h in freeze['old_ledger_pins'].items():assert sha(R/name)==h,'old_budget_ledger_changed'
assert not (L/'ADMISSION_PRIVATE.sqlite3').exists(),'prior_admission_ledger_preserve'
sys.path.insert(0,str(C/'runtime'));from stage5_common import load_inputs
load_inputs(L,'Luna')
repo=C/'repo';fv=repo/'linkup/reuse_first_20261115/measurement_protocol_20261117/code/field_validation.py';ov=repo/'linkup/formal800_20261012/code/validate_reviews.py'
cmd=[sys.executable,str(C/'runtime/stage5_cloud_worker.py'),'--leg','Luna','--directory',str(L),'--field-validator',str(fv),'--frozen-validator',str(ov),'--max-wall-seconds','14400']
with (L/'WORKER_PRIVATE.log').open('ab') as log:p=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
r={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'bounded_Luna_worker_launched_not_completion','pid':p.pid,'frame_count':135,'max_wall_seconds':14400,'model_reservation_cap_usd':2,'TPM_scheduled_upper':80000,'run_directory':str(L),'frame_sha256':freeze['frame_freeze']['frame_sha256'],'no_timers_or_old_workers_restarted':True}
receipt.write_text(json.dumps(r,sort_keys=True)+'\n');print(json.dumps(r))
'''
STATUS=r'''
L=C/'luna';r={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
p=C/'LUNA_LAUNCH_PUBLIC.json';la=read(p) if p.exists() else {};pid=la.get('pid');r['launched']=bool(la);r['pid']=pid
r['process_active']=bool(pid and (Path('/proc')/str(pid)/'cmdline').exists() and b'stage5_cloud_worker.py' in (Path('/proc')/str(pid)/'cmdline').read_bytes())
for name in ['LUNA_FINAL_PUBLIC.json','STATUS_PUBLIC.json']:
 p=L/name
 if p.exists():r[name]=read(p)
p=L/'ADMISSION_PRIVATE.sqlite3'
if p.exists():
 c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True);c.execute('PRAGMA query_only=ON')
 r['ledger_tables']=[x[0] for x in c.execute("select name from sqlite_master where type='table'")]
 r['attempt_states']=dict(c.execute('select state,count(*) from attempts group by state'))
 r['physical_attempts']=c.execute('select count(*) from attempts').fetchone()[0]
 r['reserved_usd']=c.execute('select coalesce(sum(dollars_nano),0)/1e9 from attempts').fetchone()[0]
 usage=[json.loads(x[0]) for x in c.execute('select detail from attempts')]
 r['input_tokens']=sum(x.get('usage',{}).get('prompt_tokens',0) for x in usage);r['output_tokens']=sum(x.get('usage',{}).get('completion_tokens',0) for x in usage)
 r['rate_limit_headers']=sorted(set(str(x.get('rate_headers',{}).get('x-ratelimit-limit-tokens')) for x in usage))
 c.close()
r['saved_case_carriers']=len(list((L/'results').glob('*/RESULT_PRIVATE.json')))
if not r['process_active'] and not (L/'LUNA_FINAL_PUBLIC.json').exists():
 p=L/'WORKER_PRIVATE.log';r['private_log_exists']=p.exists()
 if p.exists():
  for line in p.read_text().splitlines():
   try:
    x=json.loads(line)
    if 'fatal_error_type' in x:r['fatal_error_type']=x['fatal_error_type']
   except ValueError:pass
print(json.dumps(r))
'''
PREPARE_KIMI=r'''
import zipfile,urllib.parse
os.umask(0o077);L=C/'luna';K=C/'kimi';final=read(L/'LUNA_FINAL_PUBLIC.json');assert final['terminal_no_active_requests'] and final['outputs_accounted']==135,'Luna_not_terminal'
assert sha(L/'OUTPUTS_PRIVATE.jsonl')==final['output_sha256'],'Luna_final_output_pin_mismatch'
repo=C/'repo';fv=repo/'linkup/reuse_first_20261115/measurement_protocol_20261117/code/field_validation.py';ov=repo/'linkup/formal800_20261012/code/validate_reviews.py'
cmd=[sys.executable,str(C/'runtime/stage5_prepare.py'),'--leg','Kimi','--directory',str(K),'--inputs',str(D/'fresh_inputs_v1/INPUTS_PRIVATE.jsonl'),'--roster',str(C/'FRAME_PRIVATE.jsonl'),'--schema',str(L/'SCHEMA.json'),'--instructions',str(L/'INSTRUCTIONS.md'),'--exclusions',str(D/'fresh_inputs_v1/EXCLUSIONS_PRIVATE.json'),'--field-validator',str(fv),'--frozen-validator',str(ov),'--predecessor-receipt',str(L/'LUNA_FINAL_PUBLIC.json'),'--predecessor-exclusions',str(L/'EXCLUSIONS_EXPORT_PRIVATE.json')]
cp=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
(C/'KIMI_PREPARE_EXECUTION_PRIVATE.json').write_text(json.dumps({'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr}))
assert cp.returncode==0,'Kimi_offline_prepare_failed_private_details_retained'
chosen=['FRAME_ROSTER_PRIVATE.json','SCHEMA.json','INSTRUCTIONS.md','LUNA_FINAL_PUBLIC.json','PREDECESSOR_EXCLUSIONS_PRIVATE.json','INPUTS_PRIVATE.jsonl','EXCLUSIONS_PRIVATE.json','INPUT_PINS_PUBLIC.json','PREFLIGHT_PUBLIC.json']
pins={name:sha(K/name) for name in chosen};bundle=C/'KIMI_INPUT_PRIVATE.zip'
assert not bundle.exists(),'bundle_already_exists_check_receipt_not_recreate'
with zipfile.ZipFile(bundle,'x',zipfile.ZIP_DEFLATED) as z:
 for name in chosen:z.write(K/name,name)
 z.writestr('TRANSPORT_SHA256_PRIVATE.json',json.dumps(pins,sort_keys=True))
assert bundle.stat().st_size<50_000_000
sys.path.insert(0,str(R/'code'));from workflow import call
key='review-delivery/stage5/20261118/KIMI_INPUT_PRIVATE.zip';url='https://stlinkup70d455c0261104.blob.core.windows.net/astra-handoff/'+key
with call(url,'https://storage.azure.com/',method='PUT',body=bundle.read_bytes(),headers={'x-ms-version':'2023-11-03','x-ms-blob-type':'BlockBlob','If-None-Match':'*'}) as response:assert response.status==201
with call(url,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as response:assert hashlib.sha256(response.read(50_000_001)).hexdigest()==sha(bundle)
r={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'Kimi_frozen_input_bundle_verified_no_model_calls','selected':135,'metadata_only_blocked_slots':read(K/'PREFLIGHT_PUBLIC.json')['metadata_only_blocked_slots'],'blob_key':key,'bytes':bundle.stat().st_size,'sha256':sha(bundle),'model_calls':0,'candidate_outputs_in_bundle':False}
(C/'KIMI_INPUT_TRANSPORT_PUBLIC.json').write_text(json.dumps(r,sort_keys=True)+'\n');print(json.dumps(r))
'''
def download_kimi():
 import hashlib,os,zipfile
 sys.path.insert(0,str(D.parent/'continuation_dispatch_20261117'));import storage_transport as storage
 receipts=sorted((D/'control').glob('PREPARE_KIMI_*_PUBLIC.json'));assert receipts,'missing_bundle_receipt'
 r=json.loads(receipts[-1].read_text());assert r['status']=='Kimi_frozen_input_bundle_verified_no_model_calls'
 os.umask(0o077);local=D/'private_transport';local.mkdir(exist_ok=True);p=local/'KIMI_INPUT_PRIVATE.zip'
 if not p.exists():
  with storage.call(storage.HOST+'/'+storage.CONTAINER+'/'+r['blob_key'],storage.storage_token()) as response:b=response.read(50_000_001)
  assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],'download_size_or_hash_failure'
  with p.open('xb') as f:f.write(b)
 assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
 dest=D/'kimi_local';dest.mkdir(exist_ok=True)
 with zipfile.ZipFile(p) as z:
  assert all('/' not in n and '\\' not in n and n not in ('.','..') for n in z.namelist())
  pins=json.loads(z.read('TRANSPORT_SHA256_PRIVATE.json'));assert set(z.namelist())==set(pins)|{'TRANSPORT_SHA256_PRIVATE.json'}
  for name,h in pins.items():
   b=z.read(name);assert hashlib.sha256(b).hexdigest()==h
   q=dest/name
   if q.exists():assert q.read_bytes()==b,'local_frozen_input_collision'
   else:
    with q.open('xb') as f:f.write(b)
 sys.path.insert(0,str(D/'runtime'));from stage5_common import load_inputs;items,pins=load_inputs(dest,'Kimi')
 out={'status':'Kimi_local_transport_SHA_verified_no_model_calls','selected':len(items),'directory':str(dest),'bundle_sha256':r['sha256'],'private_text_printed':False}
 control.save(D/'control/KIMI_LOCAL_TRANSPORT_PUBLIC.json',out);print(json.dumps(out))
def launch_kimi():
 import hashlib,os,subprocess
 os.umask(0o077);dest=D/'kimi_local';receipt=D/'control/KIMI_LAUNCH_PUBLIC.json'
 assert not receipt.exists(),'existing_Kimi_launch_no_duplicate_dispatch'
 assert not (dest/'ADMISSION_PRIVATE.sqlite3').exists(),'existing_Kimi_admission_requires_reconciliation'
 sys.path.insert(0,str(D/'runtime'));from stage5_common import load_inputs;from stage5_kimi_worker import route_preflight
 route=route_preflight();items,pins=load_inputs(dest,'Kimi')
 with (dest/'WORKER_PRIVATE.log').open('ab') as log:
  p=subprocess.Popen([sys.executable,str(D/'runtime/stage5_kimi_worker.py'),'--directory',str(dest),'--max-wall-seconds','14400'],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
 out={'status':'bounded_OpenCode_Kimi_worker_launched_not_completion','pid':p.pid,'selected':len(items),'cap_usd':40,'physical_cap':180,'scheduled_TPM':240000,'max_wall_seconds':14400,'directory':str(dest),'route_metadata_preflight':route,'roster_sha256':pins['roster_sha256'],'at_epoch':time.time()}
 control.save(receipt,out);print(json.dumps(out))
def status_kimi():
 import os,sqlite3
 dest=D/'kimi_local';p=D/'control/KIMI_LAUNCH_PUBLIC.json';launch=json.loads(p.read_text()) if p.exists() else {};pid=launch.get('pid');active=False
 if pid:
  try:os.kill(pid,0);active=True
  except ProcessLookupError:pass
 out={'status':'Kimi_status_snapshot','pid':pid,'process_exists':active,'at_epoch':time.time()}
 for name in ['RUN_STATUS_PUBLIC.json','KIMI_FINAL_PUBLIC.json']:
  p=dest/name
  if p.exists():out[name]=json.loads(p.read_text())
 p=dest/'ADMISSION_PRIVATE.sqlite3'
 if p.exists():
  c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True);c.execute('PRAGMA query_only=ON');out['attempt_states']=dict(c.execute('select state,count(*) from attempts group by state'));out['physical_attempts']=c.execute('select count(*) from attempts').fetchone()[0];out['reserved_usd']=c.execute('select coalesce(sum(dollars_nano),0)/1e9 from attempts').fetchone()[0];c.close()
 p=dest/'WORKER_PRIVATE.log'
 if p.exists():
  for line in p.read_text().splitlines():
   try:
    x=json.loads(line)
    if 'fatal_error_type' in x:out['fatal_error_type']=x['fatal_error_type']
   except ValueError:pass
 control.save(D/'control'/('STATUS_KIMI_'+str(time.time_ns())+'_PUBLIC.json'),out);print(json.dumps(out))
def upload_kimi():
 import hashlib,os,urllib.request,zipfile
 sys.path.insert(0,str(D.parent/'continuation_dispatch_20261117'));import storage_transport as storage
 os.umask(0o077);K=D/'kimi_local';final=json.loads((K/'KIMI_FINAL_PUBLIC.json').read_text());assert final['terminal_no_active_requests'],'Kimi_not_terminal'
 h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 assert h(K/'OUTPUTS_PRIVATE.jsonl')==final['output_sha256'] and h(K/'EXCLUSIONS_EXPORT_PRIVATE.json')==final['exclusions_sha256']
 names=['KIMI_FINAL_PUBLIC.json','OUTPUTS_PRIVATE.jsonl','EXCLUSIONS_EXPORT_PRIVATE.json','ADMISSION_PRIVATE.sqlite3']
 names +=[str(p.relative_to(K)) for p in (K/'results').rglob('*') if p.is_file()]
 assert all('opencode.json' not in n and not Path(n).is_absolute() and '..' not in Path(n).parts for n in names)
 bundle=D/'private_transport/KIMI_OUTPUT_PRIVATE.zip';assert not bundle.exists(),'preserve_existing_output_bundle'
 pins={n:h(K/n) for n in names}
 with zipfile.ZipFile(bundle,'x',zipfile.ZIP_DEFLATED) as z:
  for n in names:z.write(K/n,n)
  z.writestr('TRANSPORT_SHA256_PRIVATE.json',json.dumps(pins,sort_keys=True))
 assert bundle.stat().st_size<50_000_000
 key='review-delivery/stage5/20261118/KIMI_OUTPUT_PRIVATE.zip';url=storage.HOST+'/'+storage.CONTAINER+'/'+key
 token=storage.storage_token();q=urllib.request.Request(url,data=bundle.read_bytes(),method='PUT',headers={'Authorization':'Bearer '+token,'x-ms-version':'2023-11-03','x-ms-blob-type':'BlockBlob','If-None-Match':'*'})
 with urllib.request.urlopen(q,context=storage.azure.CTX,timeout=90) as response:assert response.status==201
 with storage.call(url,token) as response:assert hashlib.sha256(response.read(50_000_001)).hexdigest()==h(bundle)
 out={'status':'Kimi_output_bundle_uploaded_verified','blob_key':key,'sha256':h(bundle),'bytes':bundle.stat().st_size,'credentials_included':False,'source_schema_results_unchanged':True,'new_model_calls':0}
 control.save(D/'control/KIMI_OUTPUT_TRANSPORT_PUBLIC.json',out);print(json.dumps(out))
IMPORT_KIMI=r'''
import io,zipfile
os.umask(0o077);K=C/'kimi';sys.path.insert(0,str(R/'code'));from workflow import call
url='https://stlinkup70d455c0261104.blob.core.windows.net/astra-handoff/'+__OUTPUT_KEY__
with call(url,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as response:b=response.read(50_000_001)
assert len(b)==__OUTPUT_BYTES__ and hashlib.sha256(b).hexdigest()==__OUTPUT_SHA__,'output_transport_mismatch'
z=zipfile.ZipFile(io.BytesIO(b));pins=json.loads(z.read('TRANSPORT_SHA256_PRIVATE.json'))
assert set(z.namelist())==set(pins)|{'TRANSPORT_SHA256_PRIVATE.json'}
for n,h in pins.items():
 assert not Path(n).is_absolute() and '..' not in Path(n).parts and 'opencode.json' not in n
 assert n in ['KIMI_FINAL_PUBLIC.json','OUTPUTS_PRIVATE.jsonl','EXCLUSIONS_EXPORT_PRIVATE.json','ADMISSION_PRIVATE.sqlite3'] or n.startswith('results/')
 raw=z.read(n);assert hashlib.sha256(raw).hexdigest()==h
 p=K/n;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():assert p.read_bytes()==raw,'preserve_existing_Kimi_output_conflict'
 else:p.write_bytes(raw)
repo=C/'repo';fv=repo/'linkup/reuse_first_20261115/measurement_protocol_20261117/code/field_validation.py';ov=repo/'linkup/formal800_20261012/code/validate_reviews.py'
cp=subprocess.run([sys.executable,str(C/'runtime/stage5_validate_kimi.py'),'--directory',str(K),'--transport-outputs',str(K/'OUTPUTS_PRIVATE.jsonl'),'--validated-outputs',str(K/'VALIDATED_OUTPUTS_PRIVATE.jsonl'),'--field-validator',str(fv),'--frozen-validator',str(ov)],capture_output=True,text=True,timeout=90)
(C/'KIMI_VALIDATE_EXECUTION_PRIVATE.json').write_text(json.dumps({'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr}))
assert cp.returncode==0,'Kimi_cloud_validation_failed_details_retained'
r=json.loads(cp.stdout);(K/'VALIDATION_PUBLIC.json').write_text(json.dumps(r,sort_keys=True)+'\n');print(json.dumps(r))
'''
def main():
 if len(sys.argv)==2 and sys.argv[1]=='close_stage5':
  import stage5_closure_control as closure
  return closure.dispatch(sys.argv[1],control,BASE)
 if len(sys.argv)==2 and sys.argv[1]=='inspect_astra_failure':
  source=BASE+'''\nimport re,collections\nA=C/'astra_diagnostic_v1';db=sqlite3.connect((A/'ADMISSION_PRIVATE.sqlite3').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row;rows=[dict(x) for x in db.execute('select * from attempts order by id')];db.close();counts=collections.Counter();messages=[]\nfor x in rows:\n d=json.loads(x['detail']);p=A/'results'/x['case_id']/('HTTP_%04d_PRIVATE.bin'%x['id']);raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==d['raw_sha256'];obj=json.loads(raw);e=obj.get('error',{});code=e.get('code') if isinstance(e,dict) else None;param=e.get('param') if isinstance(e,dict) else None\n safe=lambda v: v if isinstance(v,str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]{0,95}',v) else None\n msg=e.get('message','') if isinstance(e,dict) else '';flags={k:(k in msg.lower()) for k in ['json_object','json_schema','unsupported','not supported','store','reasoning','authentication','permission','maximum','token']};flags['exact_previously_documented_json_input_error']=(msg=="Response input messages must contain the word 'json' in some form to use 'text.format' of type 'json_object'.")\n counts[json.dumps({'http_status':d.get('http_status'),'code':safe(code),'param':safe(param),'message_keyword_flags':flags},sort_keys=True)]+=1\nprint(json.dumps({'status':'saved_Astra_HTTP_errors_inspected_no_new_calls','errors':[dict(json.loads(k),count=v) for k,v in counts.items()],'raw_error_bodies_preserved':True,'new_model_calls':0}))\n'''
  r=control.vm(source,'stage5_astra_error_inspect_'+str(time.time_ns()));control.save(D/'control/ASTRA_FAILURE_INSPECTION_V2_PUBLIC.json',r);print(json.dumps(r));return
 if len(sys.argv)==2 and sys.argv[1] in ['prepare_astra','launch_astra','status_astra','diagnose_astra','download_astra']:
  import stage5_astra_control as astra
  return astra.dispatch(sys.argv[1],control,BASE)
 if len(sys.argv)==2 and sys.argv[1]=='fetch_astra_final':
  source=BASE+'''\nA=C/'astra_diagnostic_v1';x=read(A/'ASTRA_FINAL_PUBLIC.json');assert x['terminal_no_active_requests'] and x['selected']<=6 and x['outputs_accounted']==x['selected'];assert sha(A/'OUTPUTS_PRIVATE.jsonl')==x['output_sha256'];assert len(json.dumps(x))<4096;print(json.dumps(x))\n'''
  r=control.vm(source,'stage5_astra_final_'+str(time.time_ns()));control.save(D/'ASTRA_FINAL_PUBLIC.json',r);print(json.dumps(r));return
 if len(sys.argv)==2 and sys.argv[1]=='inspect_scoring_readiness':
  source=BASE+'''\nP=C/'protocol';freeze=read(P/'PROTOCOL_FREEZE.json');items={}\nfor n,h in freeze['files'].items():\n p=P/n;items[n]={'exists':p.is_file(),'matches_frozen_sha':bool(p.is_file() and sha(p)==h)}\nprint(json.dumps({'status':'read_only_scoring_bundle_presence','files':items,'model_calls':0,'file_writes':0}))\n'''
  r=control.vm(source,'stage5_scoring_presence_'+str(time.time_ns()));control.save(D/'control/SCORING_BUNDLE_PRESENCE_PUBLIC.json',r);print(json.dumps(r));return
 if len(sys.argv)==2 and sys.argv[1] in ['score_direct_kimi','download_scoring']:
  import stage5_scoring_control as scoring
  return scoring.dispatch(sys.argv[1],control,BASE)
 if len(sys.argv)==2 and sys.argv[1] in ['prepare_direct_kimi_v4','launch_direct_kimi_v4','status_direct_kimi_v4']:
  import stage5_direct_v4_control as v4
  return v4.dispatch(sys.argv[1],control,BASE)
 if len(sys.argv)==2 and sys.argv[1] in ['import_direct_transition','prepare_direct_kimi','launch_direct_kimi','status_direct_kimi','inspect_direct_identity','inspect_arm_kimi','prepare_v4_transition']:
  import stage5_direct_control as direct
  return direct.dispatch(sys.argv[1],control,BASE)
 if len(sys.argv)==2 and sys.argv[1]=='probe_direct_kimi':
  source=BASE+'''\nimport urllib.request,urllib.error\nsys.path.insert(0,str(R/'code'));from workflow import token\nauth=token('https://cognitiveservices.azure.com/')\nurl='https://rg-linkup.openai.azure.com/openai/v1/models'\nreq=urllib.request.Request(url,headers={'Authorization':'Bearer '+auth});auth=None\ntry:\n with urllib.request.urlopen(req,timeout=60) as response:\n  raw=response.read(1000001);status=response.status;data=json.loads(raw)\n rows=data.get('data',[]);names=[x.get('id') for x in rows if 'kimi' in str(x.get('id','')).lower()]\n print(json.dumps({'status':'existing_VM_MI_model_metadata_access_verified','http_status':status,'operation':'GET /openai/v1/models','identity_type':'existing_VM_managed_identity','Kimi_model_ids':names,'new_inference_calls':0,'resource':'rg-linkup.openai.azure.com'}))\nexcept urllib.error.HTTPError as exc:\n body=exc.read(100000);code=None\n try:code=json.loads(body).get('error',{}).get('code')\n except Exception:pass\n print(json.dumps({'status':'model_metadata_access_failed','http_status':exc.code,'error_code':code,'operation':'GET /openai/v1/models','identity_type':'existing_VM_managed_identity','resource':'rg-linkup.openai.azure.com','new_inference_calls':0}))\n'''
  r=control.vm(source,'stage5_probe_direct_kimi_'+str(time.time_ns()));control.save(D/'control/DIRECT_KIMI_AUTH_PROBE_PUBLIC.json',r);print(json.dumps(r));return
 if len(sys.argv)==2 and sys.argv[1] in ['prepare_kimi_v2','launch_kimi_v2','status_kimi_v2','upload_kimi_v2','import_kimi_v2','stop_opencode','package_direct_transition','upload_direct_transition']:
  import stage5_transport_repair_control as repair
  return repair.dispatch(sys.argv[1],control,BASE)
 p=argparse.ArgumentParser();p.add_argument('action',choices=['launch_luna','status_luna','prepare_kimi','download_kimi','launch_kimi','status_kimi','upload_kimi','import_kimi']);a=p.parse_args()
 if a.action in ['download_kimi','launch_kimi','status_kimi','upload_kimi']:return {'download_kimi':download_kimi,'launch_kimi':launch_kimi,'status_kimi':status_kimi,'upload_kimi':upload_kimi}[a.action]()
 source=BASE+{'launch_luna':LAUNCH,'status_luna':STATUS,'prepare_kimi':PREPARE_KIMI,'import_kimi':IMPORT_KIMI}[a.action]
 if a.action=='import_kimi':
  t=json.loads((D/'control/KIMI_OUTPUT_TRANSPORT_PUBLIC.json').read_text());source=source.replace('__OUTPUT_KEY__',repr(t['blob_key'])).replace('__OUTPUT_BYTES__',str(t['bytes'])).replace('__OUTPUT_SHA__',repr(t['sha256']))
 compile(source,'<stage5-control>','exec')
 tag='stage5_'+a.action+'_'+('01' if a.action=='launch_luna' else str(time.time_ns()))
 r=control.vm(source,tag);control.save(D/'control'/(a.action.upper()+'_'+str(time.time_ns())+'_PUBLIC.json'),r);print(json.dumps(r))
if __name__=='__main__':main()
