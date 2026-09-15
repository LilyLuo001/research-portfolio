"""Execute the bounded metadata script, persisting only its aggregate receipt."""
import hashlib, json, subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
script=root/'scc_metadata_readiness.py'
out=root/'scc_metadata_readiness_receipt_v2.json'
if out.exists(): raise SystemExit('Preserve existing receipt; do not rerun silently')
with script.open('rb') as inp:
 run=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','qluo@scc1.bu.edu','python3','-'],stdin=inp,capture_output=True,timeout=60)
if run.returncode: raise SystemExit(run.stderr.decode(errors='replace'))
obj=json.loads(run.stdout)
obj['query_sha256']=hashlib.sha256(script.read_bytes()).hexdigest()
out.write_text(json.dumps(obj,indent=2)+'\n')
print(json.dumps({'status':obj['status'],'receipt':str(out),'rows':obj['source_rows'],
 'per_stock':obj['per_stock'],'inventory_counts':{k:len(v) for k,v in obj['inventory_hits'].items()}}))
