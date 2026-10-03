#!/usr/bin/env python3
import argparse, json, os
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('--plans',type=Path,nargs='+',required=True); p.add_argument('--sink',type=Path,required=True); p.add_argument('--receipts',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
rows=[]; seen=set()
for plan in a.plans:
    for line in plan.read_text().splitlines():
        if not line.strip(): continue
        item=json.loads(line); sid=item['shard_id']
        if sid in seen: raise RuntimeError('duplicate shard_id')
        seen.add(sid); shard=a.sink/sid; receipt=a.receipts/(sid+'.published.json')
        if not shard.is_dir() or not (shard/'SHARD_COMPLETE.json').is_file() or not receipt.is_file(): raise FileNotFoundError(sid)
        rows.append({'shard_id':sid,'shard_dir':str(shard),'receipt':str(receipt)})
if len(rows)!=2464: raise RuntimeError('expected 2464 frozen shards')
a.output.parent.mkdir(parents=True,exist_ok=True); temp=Path(str(a.output)+'.tmp')
temp.write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in sorted(rows,key=lambda x:x['shard_id']))); os.replace(temp,a.output)
