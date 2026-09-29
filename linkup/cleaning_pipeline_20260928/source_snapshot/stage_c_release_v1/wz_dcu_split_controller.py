#!/usr/bin/env python3
"""Join two disjoint Wuzhen DCU plan markers, then invoke the frozen mixed gate."""
import argparse, hashlib, json, os, subprocess, sys, time
from pathlib import Path

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p): return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def atomic(p,v):
    t=Path(str(p)+'.tmp'); t.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n'); os.replace(t,p)
def main():
    a=argparse.ArgumentParser()
    a.add_argument('--semantic-root',type=Path,required=True); a.add_argument('--release-root',type=Path,required=True)
    a.add_argument('--full-plan',type=Path,required=True); a.add_argument('--new-plan',type=Path,required=True)
    a.add_argument('--completed-plan',type=Path,required=True); a.add_argument('--part0-plan',type=Path,required=True); a.add_argument('--part1-plan',type=Path,required=True)
    a.add_argument('--old-code',type=Path,required=True); a.add_argument('--new-code',type=Path,required=True); a.add_argument('--new-provenance',type=Path,required=True)
    a.add_argument('--poll-seconds',type=int,default=30); a.add_argument('--max-seconds',type=int,default=180000)
    x=a.parse_args(); cp=x.semantic_root/'checkpoints'; status=x.semantic_root/'WZ_DCU_SPLIT_CONTROLLER_STATUS.json'
    sets=[rows(x.completed_plan),rows(x.part0_plan),rows(x.part1_plan)]; ids=[{r['shard_id'] for r in z} for z in sets]; original={r['shard_id'] for r in rows(x.new_plan)}
    if [len(z) for z in sets] != [6,378,373] or any(ids[i]&ids[j] for i in range(3) for j in range(i)) or set().union(*ids)!=original:
        raise RuntimeError('split plans do not form frozen 6+378+373 cover')
    deadline=time.time()+x.max_seconds
    expected=[('dcu_part0',x.part0_plan,378),('dcu_part1',x.part1_plan,373)]
    while time.time()<deadline:
        ok=True
        for name,plan,count in expected:
            p=cp/('REGION_QUEUE_COMPLETE.'+name+'.json')
            if not p.is_file(): ok=False; break
            v=json.loads(p.read_text())
            if not (v.get('status')=='compute_queue_complete' and v.get('partition_id')==name and v.get('planned_shards')==count and v.get('completed_plan_shards')==count and v.get('plan_sha256')==sha(plan)):
                raise RuntimeError(name+': partition marker mismatch')
        if ok: break
        atomic(status,{'status':'waiting_for_part_markers','at':time.time()}); time.sleep(x.poll_seconds)
    else: atomic(status,{'status':'runtime_limit','at':time.time()}); raise SystemExit(75)
    joined=cp/'REGION_QUEUE_COMPLETE.dcu_remaining.json'
    atomic(joined,{'status':'compute_queue_complete','planned_shards':757,'completed_plan_shards':757,'partition_id':'dcu_remaining','plan_sha256':sha(x.new_plan),'component_plan_sha256':[sha(x.completed_plan),sha(x.part0_plan),sha(x.part1_plan)],'final_publication_complete':False})
    subprocess.run([sys.executable,str(x.release_root/'wz_mixed_completion_gate.py'),'--full-plan',str(x.full_plan),'--new-plan',str(x.new_plan),'--checkpoint-root',str(cp),'--old-code',str(x.old_code),'--new-code',str(x.new_code),'--new-provenance',str(x.new_provenance)],check=True)
    atomic(status,{'status':'complete','at':time.time(),'canonical_queue_marker':str(cp/'REGION_QUEUE_COMPLETE.json')})
if __name__=='__main__': main()
