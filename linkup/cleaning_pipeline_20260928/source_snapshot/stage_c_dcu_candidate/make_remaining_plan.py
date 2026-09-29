#!/usr/bin/env python3
"""Create a deterministic plan containing only unsealed Wuzhen shards."""
import argparse
import hashlib
import json
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--full-plan", type=Path, required=True)
ap.add_argument("--checkpoint-root", type=Path, required=True)
ap.add_argument("--output", type=Path, required=True)
args = ap.parse_args()
rows = [json.loads(line) for line in args.full_plan.read_text().splitlines() if line.strip()]
remaining = []
for row in rows:
    sid = row["shard_id"]
    sealed = ((args.checkpoint_root / (sid + ".queued.json")).is_file()
              or (args.checkpoint_root / (sid + ".published.json")).is_file())
    if not sealed: remaining.append(row)
if args.output.exists():
    raise SystemExit("refusing to overwrite remaining plan")
payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in remaining)
args.output.write_text(payload)
print(json.dumps({"full_shards": len(rows), "remaining_shards": len(remaining),
                  "sealed_shards": len(rows) - len(remaining),
                  "remaining_plan_sha256": hashlib.sha256(payload.encode()).hexdigest()}, sort_keys=True))

