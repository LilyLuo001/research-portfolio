"""Deploy a finite, additive pilot and prepare its first 100 physical rows.

Transport contains code/public policy only. Actual rows stay on the existing VM.
"""
import base64
import hashlib
import json
from pathlib import Path
import sys
import time
import zlib

P = Path(__file__).resolve().parents[1]
D5 = P.parent / 'confirmation_stage5_20261118'
sys.path.insert(0, str(P.parent / 'execution_20261116_continuation02'))
import control

files = {}
for folder in ('runtime', 'preparation', 'rules', 'measurement'):
    for path in (P / folder).glob('*.py'):
        if not path.name.startswith('test_'):
            files[folder + '/' + path.name] = path.read_text()
files['measurement/ECONOMIC_RELEASE_PUBLIC.json'] = (P / 'measurement/ECONOMIC_RELEASE_PUBLIC.json').read_text()
files['DIRECT_ARM_DEPLOYMENT_PUBLIC.json'] = (D5 / 'control/DIRECT_ARM_DEPLOYMENT_PUBLIC.json').read_text()
for name, source in files.items():
    if name.endswith('.py'):
        compile(source, name, 'exec')
pins = {name: hashlib.sha256(source.encode()).hexdigest() for name, source in files.items()}
extractor = hashlib.sha256(json.dumps({name: sha for name, sha in pins.items()
    if name.startswith(('runtime/', 'rules/')) or name.endswith('ECONOMIC_RELEASE_PUBLIC.json')}, sort_keys=True).encode()).hexdigest()
bundle = base64.b64encode(zlib.compress(json.dumps(files).encode(), 9)).decode()
source = r'''
import base64,datetime,hashlib,json,os,subprocess,sys,time,traceback,zlib
from pathlib import Path
os.umask(0o077)
R=Path.home()/'migration';C=R/'pilot_economic_20261119/run01';C5=R/'confirmation_stage5_20261118/execution_v1'
C.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def imm(p,data):
 p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():assert p.read_bytes()==data,'immutable_collision'
 else:p.write_bytes(data)
def run(cmd,name,timeout=300):
 cp=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
 imm(C/'control'/(name+'_EXECUTION_PRIVATE.json'),json.dumps({'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr}).encode())
 try:result=json.loads(cp.stdout)
 except Exception:result={'status':'no_structured_receipt','returncode':cp.returncode}
 if cp.returncode:
  print(json.dumps({'status':'pilot_prepare_stopped','step':name,'diagnostic':result,'model_calls':0}));raise SystemExit(2)
 return result
try:
 for name,text in json.loads(zlib.decompress(base64.b64decode(__BUNDLE__))).items():imm(C/name,text.encode())
 for name,old in [('SCHEMA.json',C5/'kimi_direct_v4/SCHEMA.json'),('INSTRUCTIONS.md',C5/'kimi_direct_v4/INSTRUCTIONS.md')]:imm(C/name,old.read_bytes())
 config=C/'preparation/batch0001_CONFIG_PRIVATE.json'
 if not config.exists():run([sys.executable,'-B',str(C/'preparation/make_config.py'),'--schema-sha256',sha(C/'SCHEMA.json'),'--extractor-sha256',__EXTRACTOR__,'--out',str(config)],'config')
 B=C/'preparation/batch0001';M=B/'BATCH_MANIFEST_PUBLIC.json'
 if M.exists():raise RuntimeError('initial_preparation_already_exists_use_readonly_status')
 prep=run([sys.executable,'-B',str(C/'preparation/prepare_physical.py'),'--controller',str(C/'preparation/cloud_controller.py'),'--controller-sha256',sha(C/'preparation/cloud_controller.py'),'--config',str(config),'--config-sha256',sha(config),'--output',str(B),'--row-limit','100'],'batch0001_preparation')
 m=read(M)
 cpu=run([sys.executable,'-B',str(C/'rules/run_cpu_batch.py'),'--input',str(B/'INPUTS_PRIVATE.jsonl'),'--output',str(B/'CPU_RULE_RESULTS_PRIVATE.jsonl'),'--receipt',str(B/'CPU_RULE_RECEIPT_PUBLIC.json'),'--cache',str(C/'cache/cpu_rules.sqlite'),'--max-records','10000'],'batch0001_cpu_rules')
 policy=read(C/'measurement/ECONOMIC_RELEASE_PUBLIC.json')
 policy['pins']={n:sha(C/n) for n in ['SCHEMA.json','INSTRUCTIONS.md','measurement/ECONOMIC_RELEASE_PUBLIC.json','DIRECT_ARM_DEPLOYMENT_PUBLIC.json']}
 for name in ['INPUTS_PRIVATE.jsonl','PHYSICAL_ROWS_PRIVATE.jsonl','EXCLUSIONS_PRIVATE.json']:
  n='preparation/batch0001/'+name;policy['pins'][n]=sha(C/n)
 policy['code_sha256']={n:sha(C/'runtime'/n) for n in ['pilot_common.py','pilot_worker.py']}
 field=C5/'repo/linkup/reuse_first_20261115/measurement_protocol_20261117/code/field_validation.py'
 frozen=C5/'repo/linkup/formal800_20261012/code/validate_reviews.py'
 policy['runtime_sha256']={'field_validator':sha(field),'frozen_validator':sha(frozen)}
 policy['initial_batch_manifest_sha256']=sha(M)
 policy['kimi_arm_evidence']={'path':'DIRECT_ARM_DEPLOYMENT_PUBLIC.json','sha256':sha(C/'DIRECT_ARM_DEPLOYMENT_PUBLIC.json')}
 imm(C/'policy.json',(json.dumps(policy,sort_keys=True,indent=2)+'\n').encode())
 sys.path.insert(0,str(C/'runtime'));import pilot_common as common
 policy,items,excluded,batch=common.load_bundle(C,C/'policy.json',M,sha(M))
 sizes=[len(common.encoded(common.model_payload(C,'Luna',item,excluded))) for item in items]
 result={'status':'pilot_prepared_no_model_calls','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'run_directory':str(C),'physical_rows':m['physical_rows'],'new_unique_contexts':m['new_unique_contexts'],
 'state_counts':m['state_counts'],'source_read_statistics':m.get('source_read_statistics'),
 'preparation_seconds':m.get('preparation_elapsed_before_commit_seconds'),
 'manifest_sha256':sha(M),'policy_sha256':sha(C/'policy.json'),
 'model_calls':0,'Astra_JSON_input_patch_deployed':True,
 'CPU_status':cpu['status'],'CPU_output_sha256':cpu['output_sha256'],
 'CPU_receipt_path':str(B/'CPU_RULE_RECEIPT_PUBLIC.json'),
 'Luna_request_bytes_min':min(sizes),'Luna_request_bytes_max':max(sizes),
 'Luna_first_attempt_reserved_usd':sum((x+1024)*100+12000*500 for x in sizes)/1e9,
 'end_cursor_exclusive':m['end_cursor_exclusive']}
 imm(C/'PREPARE_PUBLIC.json',(json.dumps(result,sort_keys=True)+'\n').encode());print(json.dumps(result))
except SystemExit:raise
except Exception as e:
 (C/'DEPLOY_FAILURE_PRIVATE.txt').write_text(traceback.format_exc())
 print(json.dumps({'status':'pilot_deploy_stopped_preserve_state','error_type':type(e).__name__,'private_diagnostic_retained':True,'model_calls':0}))
'''.replace('__BUNDLE__', repr(bundle)).replace('__EXTRACTOR__', repr(extractor))
compile(source, '<pilot-deploy-prepare>', 'exec')
result = control.vm(source, 'pilot_deploy_initial_' + str(time.time_ns()))
control.save(P / 'control/DEPLOY_PREPARE_PUBLIC.json', result)
control.save(P / 'control/DEPLOY_CODE_PINS_PUBLIC.json', {'pins': pins, 'extractor_sha256': extractor})
print(json.dumps(result))
