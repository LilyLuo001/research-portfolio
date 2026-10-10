#!/usr/bin/env python3
"""Independent per-shard readback gate for one D59 rolling wave."""
import argparse, datetime as dt, hashlib, json, os, subprocess, sys
from pathlib import Path
RUNNER_SHA='3826142b6cddb549e831c8302be1d460ba3e85ee96bb7736af5549f878b3bf44'
def sha(p):
 h=hashlib.sha256(); f=open(p,'rb')
 for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 f.close(); return h.hexdigest()
def atomic(p,x):
 p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); t=Path(str(p)+'.tmp'); t.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n'); os.replace(t,p)
def main():
 a=argparse.ArgumentParser(); a.add_argument('--manifest',required=True); a.add_argument('--output-root',required=True); a.add_argument('--verifier',required=True); a.add_argument('--public-receipt',required=True); z=a.parse_args()
 m=json.loads(Path(z.manifest).read_text()); rows=[]
 for e in m['entries']:
  short=e['shard_id'][:16]; out=Path(z.output_root)/('shard_'+short); pr=Path(z.output_root)/('SHARD_'+short+'_RECEIPT_PUBLIC.json'); qr=Path(z.output_root)/('SHARD_'+short+'_QA_PUBLIC.json')
  subprocess.check_call([sys.executable,z.verifier,'--posting',str(out/'POSTING_NARROW_PRIVATE.parquet'),'--evidence',str(out/'EVIDENCE_PRIVATE.parquet'),'--production-receipt',str(pr),'--expected-runner-sha256',RUNNER_SHA,'--output',str(qr)])
  q=json.loads(qr.read_text()); p=json.loads(pr.read_text())
  if q.get('status')!='pass' or p.get('status')!='complete': raise RuntimeError('shard readback gate failed')
  rows.append({'shard_id':short,'production_receipt_sha256':sha(pr),'qa_receipt_sha256':sha(qr),'posting_sha256':q['posting_sha256'],'evidence_sha256':q['evidence_sha256'],'posting_rows':q['posting_rows'],'evidence_rows':q['evidence_rows']})
 atomic(z.public_receipt,{'status':'pass','version':'d59-wave-readback-v1','batch_id':m['batch_id'],'manifest_sha256':sha(z.manifest),'runner_sha256':RUNNER_SHA,'shard_count':len(rows),'shards':rows,'job_id':os.environ.get('JOB_ID'),'completed_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'scope':'mechanical narrow-output readback; no semantic certification'})
if __name__=='__main__': main()
