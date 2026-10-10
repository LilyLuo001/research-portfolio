#!/bin/bash
#SBATCH --job-name=lk_d60_wz_pre
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=00:05:00
#SBATCH --no-requeue
#SBATCH --output=/work/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/domestic_wz_d60/logs/preflight-%j.out
#SBATCH --error=/work/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/domestic_wz_d60/logs/preflight-%j.err
set -euo pipefail
umask 077
ROOT=/work/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/domestic_wz_d60
PLAN=/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen/plan.jsonl
RUNTIME=/work/home/lilysharp/linkup_release_v1/runtime_py38
EXPECTED_RUNNER=3826142b6cddb549e831c8302be1d460ba3e85ee96bb7736af5549f878b3bf44
mkdir -p "$ROOT/logs" "$ROOT/private" "$ROOT/public" "$ROOT/output"
set +u
source /etc/profile >/dev/null 2>&1 || true
module purge >/dev/null 2>&1 || true
module load python/3.8.10
set -u
export PYTHONPATH="$ROOT/code:$RUNTIME"
export ROOT PLAN EXPECTED_RUNNER
python3 - <<'PY'
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
import pathlib
import socket

import pyarrow as pa
import pyarrow.parquet as pq

root = pathlib.Path(os.environ["ROOT"])
plan = pathlib.Path(os.environ["PLAN"])
expected_runner = os.environ["EXPECTED_RUNNER"]

def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()

def atomic_json(path, value):
    tmp = pathlib.Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, path)

rows = [json.loads(line) for line in plan.read_text().splitlines() if line.strip()]
if len(rows) != 1106 or len({row["shard_id"] for row in rows}) != 1106:
    raise RuntimeError("Wuzhen plan cardinality or uniqueness mismatch")
selected = rows[:4]
if len(selected) != 4 or len({row["shard_id"] for row in selected}) != 4:
    raise RuntimeError("four-way selection is not disjoint")
for row in selected:
    if row.get("region") != "wuzhen":
        raise RuntimeError("non-Wuzhen entry in Wuzhen plan")
    raw = pathlib.Path(row["source_path"])
    sidecar = pathlib.Path(row["sidecar_path"])
    if not str(raw).startswith("/work/home/lilysharp/dewey_remaining_descriptions/data/linkup_job_descriptions/"):
        raise RuntimeError("raw path outside frozen Wuzhen source root")
    if not str(sidecar).startswith("/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen/sidecars/"):
        raise RuntimeError("sidecar path outside frozen Wuzhen sidecar root")
    if raw.stat().st_size != row["source_bytes"] or sidecar.stat().st_size != row["sidecar_bytes"]:
        raise RuntimeError("manifest byte count mismatch")

hash_tasks = []
for row in selected:
    hash_tasks.extend([(row["source_path"], row["source_sha256_cached"]),
                       (row["sidecar_path"], row["sidecar_sha256"])])
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    observed = list(pool.map(lambda item: (item, digest(item[0])), hash_tasks))
for (path, expected), got in observed:
    if got != expected:
        raise RuntimeError("frozen input SHA-256 mismatch: " + pathlib.Path(path).name)

runner = root / "code" / "run_one_shard.py"
if digest(runner) != expected_runner:
    raise RuntimeError("frozen runner SHA-256 mismatch")
required = ["run_one_shard.py", "rule_engine.py", "legacy_v5_frozen.py", "relation_overlay.py"]
code_hashes = {name: digest(root / "code" / name) for name in required}
caps = {
    "parquetfile_iter_batches": hasattr(pq.ParquetFile, "iter_batches"),
    "table_to_pydict": hasattr(pa.Table, "to_pydict"),
    "table_from_arrays": hasattr(pa.Table, "from_arrays"),
    "zstd_codec": pa.Codec.is_available("zstd"),
}
if not all(caps.values()):
    raise RuntimeError("runtime capability preflight failed")

now = dt.datetime.now(dt.timezone.utc).isoformat()
private = {
    "status": "passed", "job_id": os.environ.get("SLURM_JOB_ID"),
    "host": socket.gethostname(), "created_utc": now,
    "plan_path": str(plan), "plan_sha256": digest(plan), "plan_rows": len(rows),
    "selected_entries": selected, "code_sha256": code_hashes,
    "python_version": os.sys.version.split()[0], "pyarrow_version": pa.__version__,
    "capabilities": caps, "api_calls": 0, "model_calls": 0,
}
public = {
    "status": "passed", "job_id": os.environ.get("SLURM_JOB_ID"),
    "host": socket.gethostname(), "created_utc": now,
    "scheduler": {"partition": "wzhdtest", "cpus": 4, "memory_gib": 8, "time_limit": "00:05:00", "dcu_requested": 1, "dcu_use": "scheduler-QOS-minimum; CPU-only submission rejected"},
    "plan_rows": len(rows), "selected_shards": len(selected), "disjoint": True,
    "input_bytes_verified": sum(row["source_bytes"] + row["sidecar_bytes"] for row in selected),
    "full_sha256_verified": True, "runner_sha256": code_hashes["run_one_shard.py"],
    "python_version": os.sys.version.split()[0], "pyarrow_version": pa.__version__,
    "capabilities": caps, "api_calls": 0, "model_calls": 0,
}
atomic_json(root / "private" / "PREFLIGHT_PRIVATE.json", private)
atomic_json(root / "public" / "PREFLIGHT_PUBLIC.json", public)
PY
