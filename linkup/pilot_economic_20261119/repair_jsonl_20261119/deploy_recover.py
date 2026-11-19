"""Versioned parsing-only recovery; retains all old bytes and admission counters."""
import base64,hashlib,json,sys,time,zlib
from pathlib import Path
P=Path(__file__).resolve().parent;B=P.parent
sys.path.insert(0,str(B.parent/'execution_20261116_continuation02'));import control
files={'control/finite_pipeline_v2.py':(P/'finite_pipeline_v2.py').read_text(),'measurement/publish_physical_v3.py':(P/'publish_physical_v3.py').read_text()}
pins={'control/finite_pipeline.py':hashlib.sha256((B/'control/finite_pipeline.py').read_bytes()).hexdigest(),'measurement/publish_physical_v2.py':hashlib.sha256((B/'measurement/publish_physical.py').read_bytes()).hexdigest()}
bundle=base64.b64encode(zlib.compress(json.dumps({'files':files,'pins':pins}).encode())).decode()
source=r'''import argparse,base64,datetime,hashlib,json,os,sqlite3,subprocess,sys,time,zlib
from pathlib import Path
os.umask(0o077);C=Path.home()/'migration/pilot_economic_20261119/run01';D=C/'control/jsonl_recovery_20261119'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def imm(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():assert p.read_bytes()==b,'immutable_collision'
 else:
  with p.open('xb') as f:f.write(b)
def enc(v):return (json.dumps(v,sort_keys=True)+'\n').encode()
assert not (D/'RECOVERY_PUBLIC.json').exists(),'recovery_already_recorded_no_duplicate'
active=[]
for p in Path('/proc').glob('[0-9]*/cmdline'):
 try:a=p.read_bytes().split(b'\0')
 except OSError:continue
 if any(str(C/n).encode() in a for n in ['control/finite_pipeline.py','control/finite_pipeline_v2.py','runtime/pilot_worker.py','runtime_v2/pilot_worker_v2.py']):active.append(int(p.parent.name))
assert not active,'existing_run_active'
sys.path.insert(0,str(C/'control'));import finite_pipeline as old
with old.controller_lock(C):
 data=json.loads(zlib.decompress(base64.b64decode(__BUNDLE__)))
 for name,h in data['pins'].items():assert sha(C/name)==h,'old_code_pin_mismatch'
 prior=read(C/'control/FINITE_PIPELINE_STATE_PUBLIC.json')
 assert prior['status']=='finite_pipeline_stopped' and prior['stop_reason']=='JSONDecodeError','unexpected_breakpoint'
 assert not (C/'STOP').exists(),'preserve_operator_stop'
 D.mkdir(parents=True,exist_ok=True)
 imm(D/'PRE_RECOVERY_STATE_PUBLIC.json',enc(prior))
 imm(D/'PRE_RECOVERY_CODE_PINS_PUBLIC.json',(C/'control/FINITE_PIPELINE_CODE_PINS_PUBLIC.json').read_bytes())
 protected=['policy.json','SCHEMA.json','INSTRUCTIONS.md','OUTPUTS_LUNA_batch0001_PRIVATE.jsonl','OUTPUTS_LUNA_batch0002_PRIVATE.jsonl','projection/batch0001/PHYSICAL_PROJECTION_PUBLIC.json','projection/batch0001/PHYSICAL_INCREMENT_PRIVATE.jsonl']
 protected += [str(p.relative_to(C)) for p in (C/'results').glob('*/*/RESULT_PRIVATE.json')]
 pre_sha={n:sha(C/n) for n in protected}
 db=sqlite3.connect((C/'ADMISSION_PRIVATE.sqlite3').as_uri()+'?mode=ro',uri=True)
 before={'attempts':db.execute('select count(*) from attempts').fetchone()[0],'claims':db.execute('select count(*) from claims').fetchone()[0],'reserved_nano':db.execute('select sum(dollars_nano) from attempts').fetchone()[0]}
 backup=D/'ADMISSION_PRE_RECOVERY_PRIVATE.sqlite3'
 assert not backup.exists(),'snapshot_already_exists'
 with sqlite3.connect(backup) as dst:db.backup(dst)
 db.close()
 imm(D/'PROTECTED_HASHES_PRIVATE.json',enc(pre_sha))
 for n,t in data['files'].items():compile(t,n,'exec');imm(C/n,t.encode())
 import finite_pipeline_v2 as new
 args=argparse.Namespace(directory=C,concurrency=4,max_wall_seconds=172800,prepare_and_apply_rate_amendment=False)
 obj=new.Supervisor(args);obj.guards();m=new.manifest_chain(C)[-1]
 assert m['batch_id']=='batch0002' and obj.luna_finished(m),'saved_batch_not_accounted'
 # Finishing this batch must use existing results only, never paid inference.
 original_execute=obj.execute
 def recovery_execute(command,stage,**kw):
  assert not kw.get('model',False),'no_model_calls_in_recovery'
  return original_execute(command,stage,**kw)
 obj.execute=recovery_execute
 obj.process_batch(m)
 assert all(sha(C/n)==h for n,h in pre_sha.items()),'protected_file_changed'
 db=sqlite3.connect((C/'ADMISSION_PRIVATE.sqlite3').as_uri()+'?mode=ro',uri=True)
 after={'attempts':db.execute('select count(*) from attempts').fetchone()[0],'claims':db.execute('select count(*) from claims').fetchone()[0],'reserved_nano':db.execute('select sum(dollars_nano) from attempts').fetchone()[0]};db.close()
 assert before==after,'unexpected_admission_or_budget_change'
 receipt=read(C/'projection/batch0002/PHYSICAL_PROJECTION_PUBLIC.json')
 out={'status':'batch0002_recovered_without_model_calls','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cause':'unicode_U2028_splitlines_misframed_valid_jsonl','physical_rows':receipt['physical_rows'],'semantic_physical_states':receipt['semantic_physical_state_counts'],'projection_receipt':str(C/'projection/batch0002/PHYSICAL_PROJECTION_PUBLIC.json'),'projection_receipt_sha256':sha(C/'projection/batch0002/PHYSICAL_PROJECTION_PUBLIC.json'),'model_calls_during_recovery':0,'before':before,'after':after,'protected_file_count':len(pre_sha),'protected_file_sha_unchanged':True,'deferred_oversize_inputs':1,'old_scientific_schema_unchanged':True,'original_start_epoch':prior['started_epoch'],'original_48h_deadline_preserved':True,'code_sha256':{n:sha(C/n) for n in data['files']}}
 imm(D/'RECOVERY_PUBLIC.json',enc(out));print(json.dumps(out))
'''.replace('__BUNDLE__',repr(bundle))
r=control.vm(source,'jsonl_recovery_'+str(time.time_ns()));(P/'RECOVERY_PUBLIC.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
