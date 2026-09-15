#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,tempfile
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
ap=argparse.ArgumentParser()
for x in ['code','gate','manifest','pilot_receipt','facts','mapping','pairs','outdir']:ap.add_argument('--'+x,required=True)
a=ap.parse_args(); results={}
with tempfile.TemporaryDirectory() as td:
 r=subprocess.run([sys.executable,a.code,'--pairs','/definitely/not/opened.csv','--mapping',a.mapping,'--facts',a.facts,'--outdir',td+'/direct','--mode','full'],capture_output=True,text=True)
 results['direct_full_without_gate_rejected_before_source_read']=r.returncode!=0 and 'requires gate token' in (r.stdout+r.stderr)
 stale=json.load(open(a.pilot_receipt)); keys=list(stale['input_sha256']); stale['input_sha256'][keys[-1]]='0'*64
 sp=Path(td)/'stale.json';sp.write_text(json.dumps(stale))
 r=subprocess.run([sys.executable,a.gate,'--manifest',a.manifest,'--pilot_receipt',str(sp),'--code',a.code,'--facts',a.facts,'--mapping',a.mapping,'--pairs',a.pairs,'--outdir',td+'/stale'],capture_output=True,text=True)
 results['stale_pilot_input_hash_rejected_before_full_source_hash']=r.returncode!=0
assert all(results.values())
Path(a.outdir).mkdir(parents=True,exist_ok=True)
o=Path(a.outdir)/'GATE_NEGATIVE_TEST_RECEIPT.json';o.write_text(json.dumps({'status':'GATE_NEGATIVE_TESTS_PASS','tests':results,'code_sha256':sha(a.code),'gate_sha256':sha(a.gate),'manifest_sha256':sha(a.manifest),'protected_rows_exported':False},indent=2)+'\n')
print('2 gate negative tests PASS')
