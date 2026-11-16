"""Read actual finite qualification progress, no outputs or source content."""
import json,os
from pathlib import Path
R=Path.home()/'migration';Q=R/'execution_20261116/run001/qualification500_v1'
result={}
for name,directory,script in [('Luna','luna_revision002','cloud_qualification_luna_worker.py'),('Astra_initial_rejected','astra_audit50_v1','cloud_astra_audit_worker.py'),('Astra','astra_audit50_transport_recovery_v1','cloud_astra_transport_recovery_worker.py')]:
 d=Q/directory;p=d/'RUN_STATUS_PUBLIC.json'
 if not p.exists():result[name]={'status':'not_started'};continue
 s=json.loads(p.read_text());proc=Path('/proc')/str(s.get('pid'))/'cmdline'
 s['alive_exact_command']=proc.exists() and str(d/script).encode() in proc.read_bytes()
 result[name]=s
result['Kimi']={'results_saved':len(list((Q/'kimi_reference350_v1/results').glob('*/RESULT_PUBLIC.json')))}
print(json.dumps(result))
