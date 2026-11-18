"""Finite Azure pilot control; aggregate output only, no credentials or source text."""
import datetime as dt
import json
from pathlib import Path
import sys
import time

P=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(P.parent/'execution_20261116_continuation02'))
import control

BASE=r'''import json,os,sys,hashlib,datetime,subprocess,sqlite3,time
from pathlib import Path
R=Path.home()/'migration';C5=R/'confirmation_stage5_20261118/execution_v1';C=R/'pilot_economic_20261119/run01'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
'''

PROBE=r'''
import getpass,socket
active=[]
for path in Path('/proc').glob('[0-9]*/cmdline'):
    try:args=path.read_bytes().split(b'\0')
    except (PermissionError,FileNotFoundError,ProcessLookupError):continue
    kinds=[name for name in ('stage5_cloud_worker.py','stage5_kimi_worker.py','pilot_worker.py','opencode')
           if any(x.endswith(('/'+name).encode()) for x in args)]
    if kinds:active.append({'pid':int(path.parent.name),'kinds':kinds})
legs={}
for leg,folder in [('Luna','luna'),('Kimi','kimi_direct_v4'),('Astra','astra_diagnostic_v1')]:
    p=C5/folder;f=read(p/(leg.upper()+'_FINAL_PUBLIC.json'))
    assert f['terminal_no_active_requests']
    assert sha(p/'OUTPUTS_PRIVATE.jsonl')==f['output_sha256']
    legs[leg]={k:f[k] for k in ['physical_attempts','logical_calls','reserved_usd','outputs_accounted']}
assert abs(sum(x['reserved_usd'] for x in legs.values())-37.2664193)<1e-8
prep=read(R/'confirmation_stage5_20261118/fresh_inputs_v1/FRESH_INPUT_PREPARATION_PUBLIC.json')
score=read(C5/'scoring_v1/SCORING_PUBLIC.json')
print(json.dumps({'status':'new_pilot_read_only_probe','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'host':socket.gethostname(),'execution_user':getpass.getuser(),'control_identity':'existing_ARM_service_principal_to_VM_Agent',
    'data_model_identity':'existing_VM_managed_identity','related_processes':active,'prior_stage5_legs':legs,
    'prior_stage5_score_sha256':sha(C5/'scoring_v1/SCORING_PUBLIC.json'),
    'actual_next_cursor':prep['end_cursor_exclusive'],'prior_frame_sha256':sha(C5/'FRAME_PRIVATE.jsonl'),
    'pilot_directory_exists':C.exists(),'pilot_ledger_exists':(C/'PILOT_LEDGER_PRIVATE.sqlite3').exists(),
    'new_model_calls':0,'new_resources':0,'source_body_reads':0}))
'''

def main():
    action=sys.argv[1]
    if action=='probe':
        result=control.vm(BASE+PROBE,'economic_pilot_probe_'+str(time.time_ns()))
        control.save(P/'control/PROBE_PUBLIC.json',result);print(json.dumps(result));return
    raise SystemExit('unknown_control_action')

if __name__=='__main__':main()
