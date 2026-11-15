"""Stop admission at a confirmed no-inflight boundary; preserve all prior outputs."""
import datetime,json,os,signal,time
from pathlib import Path
R=Path.home()/'migration';D=R/'execution_20261116/run001/qualification500_v1/luna'
read=lambda p:json.loads(p.read_bytes())
s=read(D/'RUN_STATUS_PUBLIC.json');pid=s['pid'];proc=Path('/proc')/str(pid)
assert b'cloud_qualification_luna_worker.py' in (proc/'cmdline').read_bytes()
deadline=time.monotonic()+260;stopped=False
while time.monotonic()<deadline and proc.exists():
    os.kill(pid,signal.SIGSTOP);time.sleep(.03)
    events={}
    for line in (D/'ATTEMPTS_PRIVATE.jsonl').open():
        try:x=json.loads(line)
        except json.JSONDecodeError:continue
        events[x['ordinal'],x['attempt']]=x
    if not any(x['status']=='forwarding_uncertain' for x in events.values()):
        os.kill(pid,signal.SIGTERM);os.kill(pid,signal.SIGCONT);stopped=True;break
    os.kill(pid,signal.SIGCONT);time.sleep(.1)
assert stopped,'could_not_confirm_no_inflight_do_not_restart'
for _ in range(50):
    if not proc.exists():break
    time.sleep(.1)
state='absent'
if proc.exists():state=(proc/'stat').read_text().split(') ',1)[1].split()[0]
assert state in ['absent','Z'],'worker_not_terminated_no_successor'
report={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'candidate_admission_stopped_at_no_inflight_boundary','physical_attempts_preserved':len(events),'http_status_counts':{str(k):sum(x.get('http_status')==k for x in events.values()) for k in sorted({x.get('http_status') for x in events.values()},key=str)},'worker_state_after_termination':state,'reason':'New input packaging omitted trusted assignment required by the unchanged validator. This is an execution packaging error, not an observed model semantic failure.','model_requests_contain_only_three_semantic_input_keys':True,'repair_policy':'Add trusted qualification assignment in a new validation revision; reuse saved model responses, preserve original files and billing log, do not resend attempted cases.','no_inflight_request_at_stop':True,'new_requests_by_this_script':0}
(D.parent/'PACKAGING_FAULT_STOP_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
