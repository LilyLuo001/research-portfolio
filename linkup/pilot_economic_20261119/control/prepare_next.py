"""Append one actual successor physical window; no model calls or guessed cursor."""
import json
from pathlib import Path
import sys
import time

P=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(P.parent/'execution_20261116_continuation02'))
import control

batch=sys.argv[1];limit=int(sys.argv[2])
assert batch.startswith('batch') and batch[5:].isdigit() and 1<=limit<=1000
source=r'''import hashlib,json,os,subprocess,sys,time,sqlite3
from pathlib import Path
os.umask(0o077);C=Path.home()/'migration/pilot_economic_20261119/run01'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def imm(p,data):
 if p.exists():assert p.read_bytes()==data,'immutable_file_conflict'
 else:p.write_bytes(data)
def run(cmd,name):
 cp=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
 imm(C/'control'/(name+'_v2_EXECUTION_PRIVATE.json'),json.dumps({'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr}).encode())
 try:r=json.loads(cp.stdout)
 except Exception:r={'status':'no_structured_result','returncode':cp.returncode}
 if cp.returncode:print(json.dumps({'status':'continuation_prepare_stopped','step':name,'detail':r}));raise SystemExit(2)
 return r
batch=__BATCH__;limit=__LIMIT__
folders=sorted(p for p in (C/'preparation').glob('batch[0-9]*') if p.is_dir() and (p/'BATCH_MANIFEST_PUBLIC.json').exists())
previous=folders[-1];expected=f'batch{int(previous.name[5:])+1:04d}'
assert expected==batch,'must_append_actual_next_batch'
links=[];seen=set()
for folder in folders:
 m=read(folder/'BATCH_MANIFEST_PUBLIC.json')
 inputs=folder/'INPUTS_PRIVATE.jsonl';assert sha(inputs)==m['inputs_sha256']
 for line in inputs.read_text().splitlines():
  item=json.loads(line);h=item['row']['context_sha256'];assert h not in seen;seen.add(h)
  links.append({'context_sha256':h,'input_case':item['case'],'batch_id':folder.name})
linkpath=C/'preparation'/(batch+'_PRIOR_CONTEXT_LINKS_PRIVATE.jsonl')
imm(linkpath,b''.join((json.dumps(x,sort_keys=True)+'\n').encode() for x in links))
config=read(C/'preparation/batch0001_CONFIG_PRIVATE.json')
config['previous_manifest']={'path':str(previous/'BATCH_MANIFEST_PUBLIC.json'),'sha256':sha(previous/'BATCH_MANIFEST_PUBLIC.json')}
config['prior_context_links']={'path':str(linkpath),'sha256':sha(linkpath)}
db=sqlite3.connect((C/'ADMISSION_PRIVATE.sqlite3').as_uri()+'?mode=ro',uri=True)
claimed=[r[0] for r in db.execute('select distinct context from claims')]
quarantined=[r[0] for r in db.execute('select context from quarantine')];db.close()
exclusionpath=C/'preparation'/(batch+'_RUNTIME_EXCLUSIONS_PRIVATE.json')
imm(exclusionpath,(json.dumps({'context_sha256':sorted(set(claimed)|seen),'quarantined_contexts':quarantined},sort_keys=True)+'\n').encode())
config['pilot_runtime_exclusions']={'path':str(exclusionpath),'sha256':sha(exclusionpath)}
path=C/'preparation'/(batch+'_v2_CONFIG_PRIVATE.json');imm(path,(json.dumps(config,sort_keys=True,indent=2)+'\n').encode())
B=C/'preparation'/batch
prepared=run([sys.executable,'-B',str(C/'preparation/prepare_physical.py'),'--controller',str(C/'preparation/cloud_controller.py'),'--controller-sha256',sha(C/'preparation/cloud_controller.py'),'--config',str(path),'--config-sha256',sha(path),'--batch-id',batch,'--row-limit',str(limit),'--output',str(B)],batch+'_preparation')
cpu=run([sys.executable,'-B',str(C/'rules/run_cpu_batch.py'),'--input',str(B/'INPUTS_PRIVATE.jsonl'),'--output',str(B/'CPU_RULE_RESULTS_PRIVATE.jsonl'),'--receipt',str(B/'CPU_RULE_RECEIPT_PUBLIC.json'),'--cache',str(C/'cache/cpu_rules.sqlite'),'--max-records','10000'],batch+'_cpu')
m=read(B/'BATCH_MANIFEST_PUBLIC.json')
out={'status':'successor_prepared_no_model_calls','batch':batch,'physical_rows':m['physical_rows'],'new_unique_contexts':m['new_unique_contexts'],'cumulative_physical_rows':m['cumulative_physical_rows'],'cumulative_new_unique_contexts':m['cumulative_new_unique_contexts'],'state_counts':m['state_counts'],'start_cursor':m['start_cursor'],'end_cursor_exclusive':m['end_cursor_exclusive'],'manifest_sha256':sha(B/'BATCH_MANIFEST_PUBLIC.json'),'CPU_status':cpu['status'],'CPU_output_sha256':cpu['output_sha256'],'CPU_wall_seconds':cpu['wall_seconds'],'CPU_records_per_second':cpu['records_per_wall_second'],'model_calls':0}
imm(C/'control'/(batch+'_PREPARED_PUBLIC.json'),(json.dumps(out,sort_keys=True)+'\n').encode());print(json.dumps(out))
'''.replace('__BATCH__',repr(batch)).replace('__LIMIT__',repr(limit))
compile(source,'<successor-prepare>','exec')
result=control.vm(source,'economic_successor_'+batch+'_'+str(time.time_ns()))
control.save(P/'control'/(batch+'_PREPARED_PUBLIC.json'),result);print(json.dumps(result))
