#!/usr/bin/env python3
import argparse,datetime as dt,hashlib,json,os
from pathlib import Path
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def atomic(p,x):
 p=Path(p);t=Path(str(p)+'.tmp');t.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n');os.replace(t,p)
a=argparse.ArgumentParser();a.add_argument('--root',required=True);a.add_argument('--manifest',required=True);a.add_argument('--output',required=True);z=a.parse_args();root=Path(z.root).resolve();m=json.load(open(z.manifest));checked=[]
for x in m['files']:
 p=(root/x['cohort']/x['relative_path']).resolve();p.relative_to(root)
 if not p.is_file() or p.stat().st_size!=x['size'] or sha(p)!=x['sha256']:raise RuntimeError('return file mismatch: '+x['cohort']+'/'+x['relative_path'])
 checked.append(x['cohort']+'/'+x['relative_path'])
atomic(z.output,{'status':'pass','version':'d60-bu13-target-verification-v1','file_count':len(checked),'total_bytes':sum(x['size'] for x in m['files']),'manifest_sha256':sha(z.manifest),'completed_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'scope':'target size+SHA verification; no source text read'})
