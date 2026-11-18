"""Direct Azure identity-provenance correction. Preserves prior runs and paid outputs."""
import base64,hashlib,json,time,zlib
from pathlib import Path
D=Path(__file__).resolve().parents[1]
FILES=('stage5_common.py','stage5_cloud_worker.py','stage5_kimi_gateway.py','stage5_kimi_worker.py','stage5_prepare.py','stage5_validate_kimi.py')
def prepare(control,base):
 v=D/'runtime_direct_v4';raws={n:(v/n).read_bytes() for n in FILES}
 for n,b in raws.items():compile(b,n,'exec')
 bundle={n:{'b64z':base64.b64encode(zlib.compress(b,9)).decode(),'sha256':hashlib.sha256(b).hexdigest()} for n,b in raws.items()}
 arm=(D/'control/DIRECT_ARM_DEPLOYMENT_PUBLIC.json').read_text()
 source=base+'\nBUNDLE='+repr(bundle)+'\nARM_TEXT='+repr(arm)+'''
import base64,zlib
os.umask(0o077);V=C/'runtime_direct_v4';K=C/'kimi_direct_v4';T=C/'kimi_direct_transition_v4';L=C/'luna'
V.mkdir(exist_ok=True)
for name,x in BUNDLE.items():
 raw=zlib.decompress(base64.b64decode(x['b64z']));assert hashlib.sha256(raw).hexdigest()==x['sha256'];p=V/name
 if p.exists():assert p.read_bytes()==raw,'v4_immutable_code_conflict'
 else:p.write_bytes(raw)
arm=T/'DIRECT_ARM_DEPLOYMENT_PUBLIC.json'
if arm.exists():assert arm.read_text()==ARM_TEXT
else:arm.write_text(ARM_TEXT)
resolution=T/'MODEL_IDENTITY_RESOLUTION_PRIVATE.json'
def run(cmd,name):
 cp=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
 (C/(name+'_EXECUTION_PRIVATE.json')).write_text(json.dumps({'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr}))
 assert cp.returncode==0,name+'_failed_private_details_preserved'
 return json.loads(cp.stdout)
run([sys.executable,'-B',str(V/'stage5_kimi_worker.py'),'--create-identity-resolution','--prior-directory',str(T/'prior'),'--prior-closure',str(T/'KIMI_V3_CLOSURE_PUBLIC.json'),'--arm-metadata',str(arm),'--identity-resolution',str(resolution)],'V4_IDENTITY_RESOLUTION')
assert not (K/'ADMISSION_PRIVATE.sqlite3').exists(),'v4_prior_ledger_no_reprepare'
repo=C/'repo';fv=repo/'linkup/reuse_first_20261115/measurement_protocol_20261117/code/field_validation.py';ov=repo/'linkup/formal800_20261012/code/validate_reviews.py'
run([sys.executable,'-B',str(V/'stage5_prepare.py'),'--leg','Kimi','--directory',str(K),'--inputs',str(D/'fresh_inputs_v1/INPUTS_PRIVATE.jsonl'),'--roster',str(C/'FRAME_PRIVATE.jsonl'),'--schema',str(L/'SCHEMA.json'),'--instructions',str(L/'INSTRUCTIONS.md'),'--exclusions',str(D/'fresh_inputs_v1/EXCLUSIONS_PRIVATE.json'),'--field-validator',str(fv),'--frozen-validator',str(ov),'--predecessor-receipt',str(L/'LUNA_FINAL_PUBLIC.json'),'--predecessor-exclusions',str(L/'EXCLUSIONS_EXPORT_PRIVATE.json')],'V4_PREPARE')
r=run([sys.executable,'-B',str(V/'stage5_kimi_worker.py'),'--directory',str(K),'--import-prior-only','--prior-directory',str(T/'prior'),'--prior-closure',str(T/'KIMI_V3_CLOSURE_PUBLIC.json'),'--identity-resolution',str(resolution)],'V4_PRIOR_IMPORT')
r.update(status='direct_v4_identity_provenance_prepared_no_new_calls',runtime_files_sha256={n:x['sha256'] for n,x in BUNDLE.items()},identity_resolution_sha256=sha(resolution),ARM_metadata_sha256=sha(arm))
(C/'DIRECT_V4_PREPARE_PUBLIC.json').write_text(json.dumps(r,sort_keys=True)+'\\n');print(json.dumps(r))
'''
 compile(source,'<stage5-v4-prepare>','exec');r=control.vm(source,'stage5_prepare_direct_v4_'+str(time.time_ns()))
 control.save(D/'control/DIRECT_V4_PREPARE_PUBLIC.json',r);print(json.dumps(r))
def launch(control,base):
 source=base+'''
os.umask(0o077);V=C/'runtime_direct_v4';K=C/'kimi_direct_v4';receipt=C/'DIRECT_V4_LAUNCH_PUBLIC.json'
assert not receipt.exists() and not (K/'KIMI_FINAL_PUBLIC.json').exists(),'v4_prior_launch_or_final'
p=read(C/'DIRECT_V4_PREPARE_PUBLIC.json');assert p['imported_physical_attempts']==11 and p['imported_logical_calls']==11 and not p['admission_hold']
sys.path.insert(0,str(V));from stage5_common import load_inputs
items,pins=load_inputs(K,'Kimi');assert len(items)==135
with (K/'WORKER_PRIVATE.log').open('ab') as log:
 worker=subprocess.Popen([sys.executable,'-B',str(V/'stage5_kimi_worker.py'),'--directory',str(K),'--execute','--workflow-directory',str(R/'code'),'--max-wall-seconds','14400'],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
r={'status':'direct_Azure_Kimi_v4_launched_not_completion','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':worker.pid,'directory':str(K),'identity_type':'existing_VM_managed_identity','selected':135,'prior_reused_provider_calls':11,'remaining_at_launch':124,'Kimi_cap_usd_including_prior':40,'all_legs_cap_usd':50,'TPM_response_and_ARM_verified':3000000,'TPM_scheduled':240000,'max_wall_seconds':14400,'OpenCode_used':False,'scientific_model_deployment_unchanged':True,'provider_returned_short_identifier_explicitly_retained':True}
receipt.write_text(json.dumps(r,sort_keys=True)+'\\n');print(json.dumps(r))
'''
 r=control.vm(source,'stage5_launch_direct_v4_'+str(time.time_ns()));control.save(D/'control/DIRECT_V4_LAUNCH_PUBLIC.json',r);print(json.dumps(r))
def status(control,base):
 source=base+'''
K=C/'kimi_direct_v4';la=read(C/'DIRECT_V4_LAUNCH_PUBLIC.json');pid=la['pid'];p=Path('/proc')/str(pid)/'cmdline'
r={'status':'direct_Kimi_v4_snapshot','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':pid,'process_active':bool(p.exists() and b'runtime_direct_v4/stage5_kimi_worker.py' in p.read_bytes())}
if (K/'KIMI_FINAL_PUBLIC.json').exists():r['final']=read(K/'KIMI_FINAL_PUBLIC.json')
else:
 db=sqlite3.connect((K/'ADMISSION_PRIVATE.sqlite3').as_uri()+'?mode=ro',uri=True)
 r['attempt_states']=dict(db.execute('select state,count(*) from attempts group by state'));r['physical_attempts']=db.execute('select count(*) from attempts').fetchone()[0];r['reserved_usd']=db.execute('select coalesce(sum(dollars_nano),0)/1e9 from attempts').fetchone()[0]
 details=[json.loads(x[0]) for x in db.execute('select detail from attempts')];db.close()
 r['input_tokens']=sum(x.get('usage',{}).get('prompt_tokens',0) for x in details);r['output_tokens']=sum(x.get('usage',{}).get('completion_tokens',0) for x in details)
 r['rate_limit_tokens_headers']=sorted({str(x.get('rate_headers',{}).get('x-ratelimit-limit-tokens')) for x in details if x.get('rate_headers')})
 if not r['process_active']:
  r['fatal_markers']=[]
  for line in (K/'WORKER_PRIVATE.log').read_text().splitlines():
   try:
    x=json.loads(line)
    if 'fatal_error_type' in x:r['fatal_markers'].append(x['fatal_error_type'])
   except ValueError:pass
print(json.dumps(r))
'''
 r=control.vm(source,'stage5_status_direct_v4_'+str(time.time_ns()));control.save(D/'control'/('DIRECT_V4_STATUS_'+str(time.time_ns())+'_PUBLIC.json'),r)
 if r.get('final',{}).get('terminal_no_active_requests'):control.save(D/'KIMI_FINAL_PUBLIC.json',r['final'])
 print(json.dumps(r))
def dispatch(action,control,base):
 return {'prepare_direct_kimi_v4':prepare,'launch_direct_kimi_v4':launch,'status_direct_kimi_v4':status}[action](control,base)
