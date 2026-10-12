#!/usr/bin/env python3
"""Emit only deduplicated context hashes from named prior-review manifests."""
import argparse, hashlib, json, os
from pathlib import Path

RAW={"exact_text_sha256","source_exact_text_sha256","source_text_sha256","raw_output_source_text_sha256","source_sha256","text_sha256"}
NORM={"context_sha256","normalized_text_sha256"}
TEXT={"original_text","source_text","full_document"}
def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def walk(x,out):
 if isinstance(x,dict):
  for k,v in x.items():
   if k in RAW and isinstance(v,str) and len(v)==64:out.add(("raw_exact",v))
   elif k in NORM and isinstance(v,str) and len(v)==64:out.add(("normalized",v))
   elif k in TEXT and isinstance(v,str):out.add(("raw_exact",hashlib.sha256(v.encode()).hexdigest()))
   walk(v,out)
 elif isinstance(x,list):
  for v in x:walk(v,out)
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',action='append',required=True);p.add_argument('--output',required=True);p.add_argument('--receipt',required=True);a=p.parse_args();os.umask(0o077)
 values=set(); inputs=[]
 for fn in a.input:
  before=len(values);rows=0
  with open(fn,encoding='utf-8') as f:
   for line in f:
    if line.strip():walk(json.loads(line),values);rows+=1
  inputs.append({'sha256':sha(fn),'rows':rows,'new_hashes':len(values)-before})
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);tmp=Path(str(out)+'.tmp')
 with open(tmp,'w',encoding='utf-8') as f:
  for scope,h in sorted(values):f.write(json.dumps({'hash_scope':scope,'sha256':h},sort_keys=True)+'\n')
 os.replace(tmp,out)
 receipt={'status':'pass','input_manifest_count':len(inputs),'inputs':inputs,'output_sha256':sha(out),'deduplicated_hashes':len(values),'raw_exact_hashes':sum(s=='raw_exact' for s,h in values),'normalized_hashes':sum(s=='normalized' for s,h in values),'privacy':'output has hash values and scope only; no text, row keys, or per-row paths'}
 r=Path(a.receipt);t=Path(str(r)+'.tmp');t.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');os.replace(t,r)
if __name__=='__main__':main()
