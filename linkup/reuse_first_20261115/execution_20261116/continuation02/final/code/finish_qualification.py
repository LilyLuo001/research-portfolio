"""Observe the finite audit to completion and save a real decision and verified checkpoint."""
import base64,json,os,subprocess,time,zlib
from control import HERE,W,vm,save
os.umask(0o077)
subprocess.Popen(['/usr/bin/caffeinate','-i','-w',str(os.getpid())],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
deadline=time.time()+4*3600;i=0
while time.time()<deadline:
 s=vm((HERE/'cloud_status.py').read_text(),'final_audit_poll_'+str(i));i+=1;save(HERE/'LATEST_CLOUD_STATUS_PUBLIC.json',s);a=s['Astra']
 if a['status']=='finite_benchmark_completed' and not a['alive_exact_command']:break
 assert a['alive_exact_command'],'audit_stopped_before_completion_reconcile';time.sleep(180)
else:raise RuntimeError('bounded_audit_wait_elapsed')
r=vm((HERE/'cloud_final_qualification.py').read_text(),'close_qualification_decision001');save(HERE/'QUALIFICATION_DECISION_SUMMARY_PUBLIC.json',r);print(json.dumps(r),flush=True)
# Final code, public controls and private transport events are checkpointed only
# after both input/results and all worker processes have reached their true end.
files={n:base64.b64encode((HERE/n).read_bytes()).decode() for n in ['cloud_final_qualification.py','cloud_checkpoint_final.py','cloud_astra_transport_recovery_worker.py','qualification_metrics.py','test_qualification_metrics.py','resume_reference_leg.py','resume_audit_leg.py','prepare_astra_transport_recovery.py','launch_astra_transport_recovery.py','finish_qualification.py']}
transport={n:base64.b64encode((W/n if n=='GATEWAY_ATTEMPTS_PRIVATE.jsonl' else HERE/n).read_bytes()).decode() for n in ['KIMI_FINAL_PUBLIC.json','GATEWAY_ATTEMPTS_PRIVATE.jsonl','LEASE_RECOVERY_PUBLIC.json']}
source='CODE_B64='+repr(files)+'\nTRANSPORT_B64='+repr(transport)+'\n'+(HERE/'cloud_checkpoint_final.py').read_text()
r=vm(source,'close_qualification_checkpoint001');data=json.loads(zlib.decompress(base64.b64decode(r['aggregate_zlib_b64'])))
for n,x in data.items():save(HERE/n,x)
print(json.dumps(data['CHECKPOINT_PUBLIC.json']),flush=True)
