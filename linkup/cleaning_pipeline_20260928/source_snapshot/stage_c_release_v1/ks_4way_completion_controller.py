#!/usr/bin/env python3
"""Promote Kunshan compute completion after completed+four plans reconcile."""
from __future__ import annotations
import argparse, hashlib, json, os, time
from pathlib import Path

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(p): return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def atomic(p,v):
    p=Path(p); t=Path(str(p)+'.tmp'); t.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n'); os.replace(t,p)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--full-plan',type=Path,required=True)
    ap.add_argument('--handoff-root',type=Path,required=True); ap.add_argument('--checkpoint-root',type=Path,required=True)
    ap.add_argument('--poll-seconds',type=int,default=30); ap.add_argument('--max-seconds',type=int,default=180000)
    x=ap.parse_args(); deadline=time.time()+x.max_seconds
    manifest_path=x.handoff_root/'KS_4WAY_HANDOFF.json'
    while not manifest_path.is_file():
        if time.time() >= deadline: raise SystemExit(75)
        time.sleep(x.poll_seconds)
    manifest=json.loads(manifest_path.read_text())
    if manifest.get('status')!='prepared' or manifest.get('full_plan_sha256')!=sha(x.full_plan):
        raise RuntimeError('invalid 4-way handoff manifest')
    full=rows(x.full_plan); completed=rows(Path(manifest['completed_plan']))
    plans=[rows(Path(item['path'])) for item in manifest['parts']]
    groups=[{r['shard_id'] for r in completed}]+[{r['shard_id'] for r in part} for part in plans]
    if (len(full)!=1358 or sum(len(g) for g in groups)!=1358
            or any(groups[i]&groups[j] for i in range(5) for j in range(i))
            or set().union(*groups)!={r['shard_id'] for r in full}):
        raise RuntimeError('completed plus four plans do not form frozen full plan')
    while time.time()<deadline:
        ready=True
        for item in manifest['parts']:
            marker=x.checkpoint_root/('REGION_QUEUE_COMPLETE.%s.json'%item['partition_id'])
            if not marker.is_file(): ready=False; break
            value=json.loads(marker.read_text())
            if not (value.get('status')=='compute_queue_complete'
                    and value.get('partition_id')==item['partition_id']
                    and value.get('planned_shards')==item['shards']
                    and value.get('completed_plan_shards')==item['shards']
                    and value.get('plan_sha256')==item['sha256']):
                raise RuntimeError(item['partition_id']+': completion marker mismatch')
        if ready: break
        time.sleep(x.poll_seconds)
    else: raise SystemExit(75)
    for row in full:
        sid=row['shard_id']
        if not ((x.checkpoint_root/(sid+'.queued.json')).is_file()
                or (x.checkpoint_root/(sid+'.published.json')).is_file()):
            raise RuntimeError(sid+': full plan lacks queued/published receipt')
    atomic(x.checkpoint_root/'REGION_PARTS_QUEUE_COMPLETE.json', {
        'status':'compute_queue_complete','planned_shards':1358,'completed_plan_shards':1358,
        'partition_count':4,'full_plan_sha256':sha(x.full_plan),
        'completed_before_split':len(completed),'parts':manifest['parts'],
        'final_publication_complete':False,'finished_at':time.time()})

if __name__=='__main__': main()
