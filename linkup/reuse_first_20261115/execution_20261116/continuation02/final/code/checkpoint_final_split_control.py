"""Chunk only control transport, never repeat inference or a completed decision."""
import base64,gzip,hashlib,json,os,zlib
from control import HERE,W,vm,save
os.umask(0o077)
assert json.loads((HERE/'QUALIFICATION_DECISION_SUMMARY_PUBLIC.json').read_text())['status']=='fixed_qualification_protocol_completed'
names=['cloud_final_qualification.py','cloud_checkpoint_final.py','cloud_astra_transport_recovery_worker.py','qualification_metrics.py','test_qualification_metrics.py','resume_reference_leg.py','resume_audit_leg.py','prepare_astra_transport_recovery.py','launch_astra_transport_recovery.py','finish_qualification.py','checkpoint_final_split_control.py','cloud_evaluate_prepare_audit.py','continue_fixed_protocol.py','cloud_status.py','export_public_file.py']
files={n:base64.b64encode((HERE/n).read_bytes()).decode() for n in names}
transport={n:base64.b64encode((W/n if n=='GATEWAY_ATTEMPTS_PRIVATE.jsonl' else HERE/n).read_bytes()).decode() for n in ['KIMI_FINAL_PUBLIC.json','GATEWAY_ATTEMPTS_PRIVATE.jsonl','LEASE_RECOVERY_PUBLIC.json']}
payload=gzip.compress(json.dumps({'CODE_B64':files,'TRANSPORT_B64':transport}).encode(),mtime=0);pin=hashlib.sha256(payload).hexdigest();enc=base64.b64encode(payload).decode();chunks=[enc[i:i+40000] for i in range(0,len(enc),40000)]
(W/'FINAL_CHECKPOINT_TRANSPORT_PRIVATE.gz').write_bytes(payload)
root="from pathlib import Path\nimport base64,hashlib,json,gzip,os\nos.umask(0o077)\nD=Path.home()/'migration/execution_20261116/run001/continuation02/checkpoint_transport';D.mkdir(exist_ok=True)\n"
for i,chunk in enumerate(chunks):
 code=root+f"p=D/'part{i:03d}_PRIVATE.b64';b={chunk!r}.encode()\nif p.exists():assert p.read_bytes()==b\nelse:p.write_bytes(b)\nprint(json.dumps({{'chunk_saved':{i},'bytes':len(b)}}))"
 vm(code,'checkpoint_control_chunk'+str(i))
source=root+f"raw=base64.b64decode(''.join((D/f'part{{i:03d}}_PRIVATE.b64').read_text() for i in range({len(chunks)})))\nassert hashlib.sha256(raw).hexdigest()=={pin!r}\nobj=json.loads(gzip.decompress(raw));CODE_B64=obj['CODE_B64'];TRANSPORT_B64=obj['TRANSPORT_B64']\nexec(compile(base64.b64decode(CODE_B64['cloud_checkpoint_final.py']),'<checkpoint-final>','exec'))\n"
r=vm(source,'close_qualification_checkpoint_split001');data=json.loads(zlib.decompress(base64.b64decode(r['aggregate_zlib_b64'])))
for n,x in data.items():save(HERE/n,x)
save(HERE/'CHECKPOINT_TRANSPORT_PUBLIC.json',{'transport_split_only':True,'prior_oversize_control_rejected_locally_before_execution':True,'chunks':len(chunks),'compressed_payload_bytes':len(payload),'compressed_payload_sha256':pin,'cloud_reassembly_verified':True,'extra_model_calls':0})
print(json.dumps(data['CHECKPOINT_PUBLIC.json']),flush=True)
