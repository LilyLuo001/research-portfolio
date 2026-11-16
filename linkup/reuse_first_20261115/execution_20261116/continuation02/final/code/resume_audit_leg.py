"""Continue after immutable Kimi completion and tested schema-compatible evaluator repair."""
import json,time,os,subprocess
from control import HERE,save
from continue_fixed_protocol import start_astra,snapshot,note
assert json.loads((HERE/'KIMI_FINAL_PUBLIC.json').read_text())['cloud_validated']==350
assert json.loads((HERE/'METRICS_EXECUTION_REPAIR_PUBLIC.json').read_text())['tests_passed']==19
subprocess.Popen(['/usr/bin/caffeinate','-i','-w',str(os.getpid())],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
start_astra('evaluate_prepare_audit002');deadline=time.time()+5*3600;i=0
while time.time()<deadline:
 s=snapshot('audit_resumed_'+str(i));i+=1;a=s['Astra']
 if a.get('status')=='finite_benchmark_completed' and not a.get('alive_exact_command'):break
 assert a.get('alive_exact_command'),'audit_stopped_reconcile';time.sleep(180)
else:raise RuntimeError('audit_wait_bound')
note('fixed_model_legs_finished_ready_for_final_decision')
