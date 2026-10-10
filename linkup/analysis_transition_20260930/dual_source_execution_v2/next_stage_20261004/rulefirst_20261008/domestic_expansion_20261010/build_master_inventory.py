#!/usr/bin/env python3
import argparse, collections, datetime as dt, hashlib, json, os
from pathlib import Path

def atomic(path, obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n'); os.replace(tmp,path)
def sha(path):
    h=hashlib.sha256();
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

ap=argparse.ArgumentParser(); ap.add_argument('--master',required=True); ap.add_argument('--accepted',required=True); ap.add_argument('--public-output',required=True); ap.add_argument('--private-remaining',required=True); a=ap.parse_args()
rows=[json.loads(x) for x in open(a.master) if x.strip()]
accepted_doc=json.load(open(a.accepted)); accepted_tokens=set(accepted_doc['accepted_shard_ids'])
ids=[x['shard_id'] for x in rows]
if len(ids)!=len(set(ids)): raise RuntimeError('master shard_id duplicate')
accepted=set()
for token in accepted_tokens:
    matches=[x for x in ids if x==token or x.startswith(token)]
    if len(matches)!=1: raise RuntimeError('accepted shard prefix does not resolve uniquely')
    accepted.add(matches[0])
if len(accepted)!=len(accepted_tokens): raise RuntimeError('accepted tokens collapse after resolution')
regions=collections.defaultdict(lambda:collections.Counter())
for x in rows:
    r=x['region']; c=regions[r]; c['entries']+=1; c['source_bytes']+=int(x['source_bytes']); c['sidecar_bytes']+=int(x['sidecar_bytes']); c['raw_rows']+=int(x['raw_rows'])
remaining=[x for x in rows if x['shard_id'] not in accepted]
for x in remaining: regions[x['region']]['remaining_entries']+=1
atomic(a.private_remaining,{'version':'d63-master-remaining-v1','master_sha256':sha(a.master),'accepted_ledger_sha256':sha(a.accepted),'entries':remaining})
public={'version':'d63-master-inventory-public-v1','status':'complete','created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'master':{'entries':len(rows),'sha256':sha(a.master),'bytes':Path(a.master).stat().st_size},'accepted_entries':len(accepted),'remaining_entries':len(remaining),'master_shard_exclusions':0,'raw_advertisement_exclusions':'not_assessed_by_inventory','accepted_provenance':accepted_doc.get('accepted_provenance'),'regions':{k:dict(v) for k,v in sorted(regions.items())},'remaining_private_manifest_sha256':sha(a.private_remaining),'rules':{'runner_sha256':'3826142b6cddb549e831c8302be1d460ba3e85ee96bb7736af5549f878b3bf44','api_calls':0,'model_calls':0,'semantic_changes':False},'claim_boundary':'inventory and resume state only; no semantic certification'}
atomic(a.public_output,public)
