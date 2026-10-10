#!/usr/bin/env python3
import datetime as dt, hashlib, json, subprocess
from pathlib import Path
ROOT=Path('/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010')
QA=ROOT/'wz_wave_0001/public/WAVE_0001_QA_PUBLIC.json'; MAN=ROOT/'wz_wave_0001/private/WAVE_0001_MANIFEST_PRIVATE.json'; EXPECTED_QA='98f5f46cb27631e74799937c604e89c33c6fe1ed1c01694e528243e2c94f6e6a'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if sha(QA)!=EXPECTED_QA or json.load(open(QA)).get('status')!='pass':raise RuntimeError('new WZ4 QA not accepted')
old=json.load(open(ROOT/'inventory/private/ACCEPTED_17_PRIVATE.json')); new=[x['shard_id'] for x in json.load(open(MAN))['selected_entries']]; ids=old['accepted_shard_ids']+new
if len(ids)!=len(set(ids)) or len(ids)!=21:raise RuntimeError('accepted21 identity failure')
doc={'version':'d63-accepted21-v1','snapshot_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'accepted_shard_ids':ids,'accepted_provenance':dict(old['accepted_provenance'],wz_wave_0001_qa_sha256=EXPECTED_QA,wz_wave_0001_count=4)}
p=ROOT/'inventory/private/ACCEPTED_21_PRIVATE.json';p.write_text(json.dumps(doc,indent=2,sort_keys=True)+'\n')
subprocess.check_call(['python3',str(ROOT/'inventory/code/build_master_inventory.py'),'--master',str(ROOT/'inventory/private/regional_runner_plan.jsonl'),'--accepted',str(p),'--public-output',str(ROOT/'inventory/public/MASTER_INVENTORY_PUBLIC.json'),'--private-remaining',str(ROOT/'inventory/private/REMAINING_MASTER_PRIVATE.json')])
