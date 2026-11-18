"""Versioned recovery of a proven pre-provider transport rejection, never a semantic rerun."""
import hashlib,json,os,sqlite3,subprocess,sys,time,zipfile
from pathlib import Path
D=Path(__file__).resolve().parents[1]
OLD=D/'kimi_local'
K=D/'kimi_local_transport_v2'
R=D/'runtime_transport_v2'
FILES=('stage5_common.py','stage5_cloud_worker.py','stage5_kimi_gateway.py',
       'stage5_kimi_worker.py','stage5_prepare.py','stage5_validate_kimi.py')
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True)
 raw=(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
 if p.exists():assert p.read_bytes()==raw,'immutable_control_receipt_conflict'
 else:
  with p.open('xb') as f:f.write(raw)
def old_terminal():
 final=read(OLD/'KIMI_FINAL_PUBLIC.json')
 assert final['terminal_no_active_requests'] and final['physical_attempts']==0 and final['logical_calls']==0 and final['reserved_nano']==0
 assert final['output_sha256']==sha(OLD/'OUTPUTS_PRIVATE.jsonl') and final['outputs_accounted']==135
 c=sqlite3.connect((OLD/'ADMISSION_PRIVATE.sqlite3').as_uri()+'?mode=ro',uri=True)
 assert c.execute('select count(*) from attempts').fetchone()[0]==0
 assert c.execute('select count(*) from claims').fetchone()[0]==0
 c.close()
 pid=read(D/'control/KIMI_LAUNCH_PUBLIC.json')['pid']
 try:os.kill(pid,0)
 except ProcessLookupError:pass
 else:raise AssertionError('old_worker_still_exists')
 return final
def prepare():
 os.umask(0o077);old=old_terminal();repair=read(R/'REPAIR_PUBLIC.json')
 assert not (K/'ADMISSION_PRIVATE.sqlite3').exists(),'v2_existing_admission_do_not_reprepare'
 # Agent's diagnosed pre-forward local rejection is independently consistent
 # with the immutable terminal receipt and empty gateway admission ledger.
 assert (R/'test_stage5_transport.py').exists()
 cp=subprocess.run([sys.executable,'-B','-m','unittest','-v','test_stage5_transport'],cwd=R,capture_output=True,text=True,timeout=90)
 assert cp.returncode==0,'transport_synthetic_tests_failed'
 K.mkdir(exist_ok=True)
 pins=read(OLD/'INPUT_PINS_PUBLIC.json')
 for name,h in pins['sha256'].items():
  assert '/' not in name and sha(OLD/name)==h
  p=K/name
  if p.exists():assert p.read_bytes()==(OLD/name).read_bytes()
  else:p.write_bytes((OLD/name).read_bytes())
 pins['code_sha256']={name:sha(R/name) for name in FILES}
 pins['transport_revision']='transport_v2_preprovider_envelope_repair'
 save(K/'INPUT_PINS_PUBLIC.json',pins)
 sys.path.insert(0,str(R));from stage5_common import load_inputs
 items,bound=load_inputs(K,'Kimi');assert len(items)==135
 receipt={'status':'same_frozen_Kimi_inputs_transport_v2_prepared_no_calls',
  'selected':135,'roster_sha256':bound['roster_sha256'],'input_pins_sha256':sha(K/'INPUT_PINS_PUBLIC.json'),
  'scientific_input_pins_unchanged':bound['sha256']==read(OLD/'INPUT_PINS_PUBLIC.json')['sha256'],
  'old_final_sha256':sha(OLD/'KIMI_FINAL_PUBLIC.json'),'old_provider_attempts':old['physical_attempts'],
  'repair_receipt_sha256':sha(R/'REPAIR_PUBLIC.json'),'code_sha256':pins['code_sha256'],
  'tests_exit':cp.returncode,'model_calls':0,'original_outputs_modified':False}
 save(D/'control/KIMI_V2_PREPARE_PUBLIC.json',receipt);print(json.dumps(receipt))
def launch():
 os.umask(0o077);old_terminal();receipt=D/'control/KIMI_V2_LAUNCH_PUBLIC.json'
 assert not receipt.exists() and not (K/'ADMISSION_PRIVATE.sqlite3').exists(),'v2_prior_launch_or_admission'
 prepared=read(D/'control/KIMI_V2_PREPARE_PUBLIC.json');assert sha(K/'INPUT_PINS_PUBLIC.json')==prepared['input_pins_sha256']
 sys.path.insert(0,str(R));from stage5_common import load_inputs;from stage5_kimi_worker import route_preflight
 items,pins=load_inputs(K,'Kimi');route=route_preflight()
 with (K/'WORKER_PRIVATE.log').open('ab') as log:
  p=subprocess.Popen([sys.executable,'-B',str(R/'stage5_kimi_worker.py'),'--directory',str(K),'--max-wall-seconds','14400'],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
 out={'status':'Kimi_transport_v2_launched_not_completion','at_epoch':time.time(),'pid':p.pid,
  'selected':len(items),'cap_usd':40,'physical_cap':180,'scheduled_TPM':240000,'max_wall_seconds':14400,
  'directory':str(K),'roster_sha256':pins['roster_sha256'],'route_metadata_preflight':route}
 save(receipt,out);print(json.dumps(out))
def status():
 p=D/'control/KIMI_V2_LAUNCH_PUBLIC.json';la=read(p) if p.exists() else {};pid=la.get('pid');active=False
 if pid:
  try:os.kill(pid,0);active=True
  except ProcessLookupError:pass
 out={'status':'Kimi_transport_v2_snapshot','at_epoch':time.time(),'pid':pid,'process_exists':active}
 for name in ('RUN_STATUS_PUBLIC.json','KIMI_FINAL_PUBLIC.json'):
  if (K/name).exists():out[name]=read(K/name)
 db=K/'ADMISSION_PRIVATE.sqlite3'
 if db.exists():
  c=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True);out['physical_attempts']=c.execute('select count(*) from attempts').fetchone()[0]
  out['attempt_states']=dict(c.execute('select state,count(*) from attempts group by state'))
  out['reserved_usd']=c.execute('select coalesce(sum(dollars_nano),0)/1e9 from attempts').fetchone()[0]
  details=[json.loads(x[0]) for x in c.execute('select detail from attempts')]
  out['input_tokens']=sum(x.get('usage',{}).get('prompt_tokens',0) for x in details)
  out['output_tokens']=sum(x.get('usage',{}).get('completion_tokens',0) for x in details)
  out['rate_limit_tokens_headers']=sorted({str(x.get('rate_headers',{}).get('x-ratelimit-limit-tokens')) for x in details if x.get('rate_headers')})
  c.close()
 if (K/'WORKER_PRIVATE.log').exists():
  for line in (K/'WORKER_PRIVATE.log').read_text().splitlines():
   try:
    x=json.loads(line)
    if 'fatal_error_type' in x:out['fatal_error_type']=x['fatal_error_type']
   except ValueError:pass
 save(D/'control'/('STATUS_KIMI_V2_'+str(time.time_ns())+'_PUBLIC.json'),out);print(json.dumps(out))
def stop_opencode():
 import signal
 os.umask(0o077);p=D/'control/KIMI_V2_USER_DIRECT_SWITCH_PUBLIC.json'
 if p.exists():print(json.dumps(read(p)));return
 la=read(D/'control/KIMI_V2_LAUNCH_PUBLIC.json');pid=la['pid']
 cp=subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True,check=True)
 assert str(R/'stage5_kimi_worker.py') in cp.stdout and str(K) in cp.stdout,'owned_worker_identity_mismatch'
 c=sqlite3.connect((K/'ADMISSION_PRIVATE.sqlite3').as_uri()+'?mode=ro',uri=True)
 out={'status':'user_requested_direct_Azure_switch_stop_OpenCode_dispatch','at_epoch':time.time(),'pid':pid,
  'physical_attempts_before_signal':c.execute('select count(*) from attempts').fetchone()[0],
  'attempt_states_before_signal':dict(c.execute('select state,count(*) from attempts group by state')),
  'method':'SIGINT_to_owned_main_process_finally_drains_existing_provider_handler_up_to_310s',
  'no_new_OpenCode_launch':True,'inflight_requests_not_replayed':True,'user_reported_Kimi_TPM':3000000}
 c.close();save(p,out);os.kill(pid,signal.SIGINT);print(json.dumps(out))
def package_direct_transition():
 os.umask(0o077);la=read(D/'control/KIMI_V2_LAUNCH_PUBLIC.json')
 try:os.kill(la['pid'],0)
 except ProcessLookupError:pass
 else:raise AssertionError('old_OpenCode_worker_not_stopped')
 pins=read(K/'INPUT_PINS_PUBLIC.json');files=set(pins['sha256'])|{'INPUT_PINS_PUBLIC.json','ADMISSION_PRIVATE.sqlite3'}
 files|={str(p.relative_to(K)) for p in (K/'results').rglob('*') if p.is_file()}
 assert all('opencode' not in n.lower() and '..' not in Path(n).parts for n in files)
 for name,h in pins['sha256'].items():assert sha(K/name)==h
 c=sqlite3.connect((K/'ADMISSION_PRIVATE.sqlite3').as_uri()+'?mode=ro',uri=True)
 count,reserved=c.execute('select count(*),coalesce(sum(dollars_nano),0) from attempts').fetchone()
 states=dict(c.execute('select state,count(*) from attempts group by state'))
 assert not any(x in states for x in ['forwarding_uncertain','transport_uncertain_no_retry','usage_reservation_breach_stop','returned_model_identity_mismatch_hold'])
 logical=c.execute('select count(*) from claims').fetchone()[0]
 details=[json.loads(x[0]) for x in c.execute('select detail from attempts')]
 headerlimits=sorted({str(x.get('rate_headers',{}).get('x-ratelimit-limit-tokens')) for x in details if x.get('rate_headers')})
 c.close()
 closure={'status':'stopped_prior_transport_closed','worker_stopped':True,'terminal_no_active_requests':True,
  'roster_sha256':pins['roster_sha256'],'physical_attempts':count,'logical_calls':logical,
  'reserved_nano':reserved,'reserved_usd':reserved/1e9,'attempt_states':states,
  'input_tokens':sum(x.get('usage',{}).get('prompt_tokens',0) for x in details),
  'output_tokens':sum(x.get('usage',{}).get('completion_tokens',0) for x in details),
  'verified_response_TPM_headers':headerlimits,'prior_files_sha256':{n:sha(K/n) for n in sorted(files)},
  'at_epoch':time.time(),'no_prior_output_rerun':True,'user_requested_direct_Azure':True}
 cp=D/'control/KIMI_V2_CLOSURE_PUBLIC.json';save(cp,closure)
 bundle=D/'private_transport/KIMI_DIRECT_TRANSITION_PRIVATE.zip';assert not bundle.exists()
 with zipfile.ZipFile(bundle,'x',zipfile.ZIP_DEFLATED) as z:
  for n in sorted(files):z.write(K/n,'prior/'+n)
  z.write(cp,'KIMI_V2_CLOSURE_PUBLIC.json')
 transport={'status':'direct_transition_packaged_no_calls','physical_attempts':count,'reserved_usd':reserved/1e9,
  'bytes':bundle.stat().st_size,'sha256':sha(bundle),'closure_sha256':sha(cp),'verified_response_TPM_headers':headerlimits}
 save(D/'control/KIMI_DIRECT_TRANSITION_PACKAGE_PUBLIC.json',transport);print(json.dumps(transport))
def upload_direct_transition():
 import urllib.request
 sys.path.insert(0,str(D.parent/'continuation_dispatch_20261117'));import storage_transport as storage
 bundle=D/'private_transport/KIMI_DIRECT_TRANSITION_PRIVATE.zip';p=read(D/'control/KIMI_DIRECT_TRANSITION_PACKAGE_PUBLIC.json')
 assert sha(bundle)==p['sha256'] and bundle.stat().st_size==p['bytes']<50000000
 key='review-delivery/stage5/20261118/KIMI_DIRECT_TRANSITION_PRIVATE.zip';url=storage.HOST+'/'+storage.CONTAINER+'/'+key
 token=storage.storage_token();req=urllib.request.Request(url,data=bundle.read_bytes(),method='PUT',headers={'Authorization':'Bearer '+token,'x-ms-version':'2023-11-03','x-ms-blob-type':'BlockBlob','If-None-Match':'*'})
 with urllib.request.urlopen(req,context=storage.azure.CTX,timeout=90) as response:assert response.status==201
 with storage.call(url,token) as response:assert hashlib.sha256(response.read(50000001)).hexdigest()==p['sha256']
 p.update(status='direct_transition_blob_verified_no_calls',blob_key=key)
 save(D/'control/KIMI_DIRECT_TRANSITION_TRANSPORT_PUBLIC.json',p);print(json.dumps(p))
def upload():
 import urllib.request
 os.umask(0o077);final=read(K/'KIMI_FINAL_PUBLIC.json')
 assert final['terminal_no_active_requests'] and sha(K/'OUTPUTS_PRIVATE.jsonl')==final['output_sha256']
 assert sha(K/'EXCLUSIONS_EXPORT_PRIVATE.json')==final['exclusions_sha256']
 sys.path.insert(0,str(D.parent/'continuation_dispatch_20261117'));import storage_transport as storage
 pins=read(K/'INPUT_PINS_PUBLIC.json')
 names=set(pins['sha256'])|{'INPUT_PINS_PUBLIC.json','KIMI_FINAL_PUBLIC.json','OUTPUTS_PRIVATE.jsonl','EXCLUSIONS_EXPORT_PRIVATE.json','ADMISSION_PRIVATE.sqlite3'}
 names|={str(p.relative_to(K)) for p in (K/'results').rglob('*') if p.is_file()}
 sources={'kimi/'+n:K/n for n in sorted(names)}
 sources.update({'runtime/'+n:R/n for n in FILES});sources['runtime/REPAIR_PUBLIC.json']=R/'REPAIR_PUBLIC.json'
 bundle=D/'private_transport/KIMI_V2_OUTPUT_PRIVATE.zip'
 if not bundle.exists():
  with zipfile.ZipFile(bundle,'x',zipfile.ZIP_DEFLATED) as z:
   for n,p in sources.items():
    assert 'opencode.json' not in n and '..' not in Path(n).parts
    z.write(p,n)
   z.writestr('TRANSPORT_SHA256_PRIVATE.json',json.dumps({n:sha(p) for n,p in sources.items()},sort_keys=True))
 assert bundle.stat().st_size<50_000_000
 key='review-delivery/stage5/20261118/KIMI_V2_OUTPUT_PRIVATE.zip';url=storage.HOST+'/'+storage.CONTAINER+'/'+key
 token=storage.storage_token();req=urllib.request.Request(url,data=bundle.read_bytes(),method='PUT',headers={'Authorization':'Bearer '+token,'x-ms-version':'2023-11-03','x-ms-blob-type':'BlockBlob','If-None-Match':'*'})
 with urllib.request.urlopen(req,context=storage.azure.CTX,timeout=90) as response:assert response.status==201
 with storage.call(url,token) as response:assert hashlib.sha256(response.read(50_000_001)).hexdigest()==sha(bundle)
 out={'status':'Kimi_v2_output_bundle_uploaded_verified','blob_key':key,'bytes':bundle.stat().st_size,'sha256':sha(bundle),'credentials_included':False,'new_model_calls':0}
 save(D/'control/KIMI_V2_OUTPUT_TRANSPORT_PUBLIC.json',out);save(D/'KIMI_FINAL_PUBLIC.json',final);print(json.dumps(out))
def cloud_import(control,base):
 receipt=read(D/'control/KIMI_V2_OUTPUT_TRANSPORT_PUBLIC.json')
 source=base+'''\nimport io,zipfile\nos.umask(0o077);K=C/'kimi_transport_v2';V=C/'runtime_transport_v2'\nsys.path.insert(0,str(R/'code'));from workflow import call\nurl='https://stlinkup70d455c0261104.blob.core.windows.net/astra-handoff/'+KEY\nwith call(url,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as response:b=response.read(50_000_001)\nassert len(b)==SIZE and hashlib.sha256(b).hexdigest()==SHA\nz=zipfile.ZipFile(io.BytesIO(b));pins=json.loads(z.read('TRANSPORT_SHA256_PRIVATE.json'))\nassert set(z.namelist())==set(pins)|{'TRANSPORT_SHA256_PRIVATE.json'}\nfor n,h in pins.items():\n assert not Path(n).is_absolute() and '..' not in Path(n).parts and 'opencode.json' not in n\n kind,rel=n.split('/',1);assert kind in ('kimi','runtime')\n raw=z.read(n);assert hashlib.sha256(raw).hexdigest()==h\n p=(K if kind=='kimi' else V)/rel;p.parent.mkdir(parents=True,exist_ok=True)\n if p.exists():assert p.read_bytes()==raw,'immutable_cloud_transport_conflict'\n else:p.write_bytes(raw)\nrepo=C/'repo';fv=repo/'linkup/reuse_first_20261115/measurement_protocol_20261117/code/field_validation.py';ov=repo/'linkup/formal800_20261012/code/validate_reviews.py'\ncp=subprocess.run([sys.executable,'-B',str(V/'stage5_validate_kimi.py'),'--directory',str(K),'--transport-outputs',str(K/'OUTPUTS_PRIVATE.jsonl'),'--validated-outputs',str(K/'VALIDATED_OUTPUTS_PRIVATE.jsonl'),'--field-validator',str(fv),'--frozen-validator',str(ov)],capture_output=True,text=True,timeout=120)\n(C/'KIMI_V2_VALIDATE_EXECUTION_PRIVATE.json').write_text(json.dumps({'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr}))\nassert cp.returncode==0,'Kimi_v2_validation_failure_private_details_saved'\nr=json.loads(cp.stdout);(K/'VALIDATION_PUBLIC.json').write_text(json.dumps(r,sort_keys=True)+'\\n');print(json.dumps(r))\n'''
 source=source.replace('url=','KEY='+repr(receipt['blob_key'])+';SIZE='+str(receipt['bytes'])+';SHA='+repr(receipt['sha256'])+'\nurl=',1)
 compile(source,'<stage5-v2-import>','exec')
 r=control.vm(source,'stage5_import_kimi_v2_'+str(time.time_ns()));save(D/'control/KIMI_V2_VALIDATION_PUBLIC.json',r);print(json.dumps(r))
def dispatch(action,control,base):
 if action=='stop_opencode':return stop_opencode()
 if action=='package_direct_transition':return package_direct_transition()
 if action=='upload_direct_transition':return upload_direct_transition()
 if action=='import_kimi_v2':return cloud_import(control,base)
 return {'prepare_kimi_v2':prepare,'launch_kimi_v2':launch,'status_kimi_v2':status,'upload_kimi_v2':upload}[action]()
