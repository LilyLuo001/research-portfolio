#!/usr/bin/env python3
import json
from pathlib import Path
p=Path('/projectnb/econdept/qluo/linkup_rulefirst_20261008/imported/production_standard_20261008/private/full_queue/REPRESENTED_FIXED10000_KEYS_PRIVATE.jsonl')
with p.open() as f: obj=json.loads(next(f))
def walk(x,prefix=''):
    if isinstance(x,dict):
        for k,v in sorted(x.items()):
            q=f'{prefix}.{k}' if prefix else k
            print(q, type(v).__name__)
            walk(v,q)
    elif isinstance(x,list):
        print(prefix+'[]', 'length',len(x))
        if x: walk(x[0],prefix+'[]')
walk(obj)
