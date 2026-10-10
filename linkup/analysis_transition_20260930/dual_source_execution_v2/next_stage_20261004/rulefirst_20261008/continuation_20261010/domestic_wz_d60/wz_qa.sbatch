#!/bin/bash
#SBATCH --job-name=lk_d60_wz_qa
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=00:10:00
#SBATCH --no-requeue
#SBATCH --output=/work/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/domestic_wz_d60/logs/qa-%j.out
#SBATCH --error=/work/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/domestic_wz_d60/logs/qa-%j.err
set -euo pipefail
umask 077
ROOT=/work/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/domestic_wz_d60
RUNTIME=/work/home/lilysharp/linkup_release_v1/runtime_py38
EXPECTED_RUNNER=3826142b6cddb549e831c8302be1d460ba3e85ee96bb7736af5549f878b3bf44
set +u
source /etc/profile >/dev/null 2>&1 || true
module purge >/dev/null 2>&1 || true
module load python/3.8.10
set -u
export PYTHONPATH="$ROOT/code:$RUNTIME"
export ROOT EXPECTED_RUNNER
python3 - <<'PY'
import collections
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys

root = pathlib.Path(os.environ["ROOT"])
expected = os.environ["EXPECTED_RUNNER"]
preflight = json.loads((root / "private" / "PREFLIGHT_PRIVATE.json").read_text())
entries = preflight["selected_entries"]
if len(entries) != 4:
    raise RuntimeError("QA expected exactly four admitted entries")

manifest = {"status": "frozen", "scope": "D60 Wuzhen bounded four-shard QA", "shards": []}
for entry in entries:
    shard = entry["shard_id"]
    out = root / "output" / ("shard_" + shard)
    receipt = root / "private" / ("SHARD_" + shard + "_RECEIPT.json")
    subprocess.check_call([
        sys.executable, str(root / "code" / "run_one_shard.py"),
        "--raw", entry["source_path"], "--sidecar", entry["sidecar_path"],
        "--output-dir", str(out), "--public-receipt", str(receipt),
        "--expected-raw-sha256", entry["source_sha256_cached"],
        "--expected-sidecar-sha256", entry["sidecar_sha256"], "--workers", "4",
    ])
    progress = json.loads((out / "PROGRESS_PUBLIC.json").read_text())
    if progress.get("resume_verified") is not True:
        raise RuntimeError("idempotent resume verification absent")
    manifest["shards"].append({
        "shard_id": shard, "verify_new_output": True,
        "posting": str(out / "POSTING_NARROW_PRIVATE.parquet"),
        "evidence": str(out / "EVIDENCE_PRIVATE.parquet"),
        "production_receipt": str(receipt),
        "qa_output": str(root / "private" / ("SHARD_" + shard + "_QA.json")),
        "expected_runner_sha256": expected,
    })

manifest_path = root / "private" / "QA_MANIFEST_PRIVATE.json"
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
set_qa_path = root / "private" / "SHARD_SET_4_QA_PRIVATE.json"
subprocess.check_call([
    sys.executable, str(root / "code" / "verify_shard_set_outputs.py"),
    "--manifest", str(manifest_path),
    "--verifier", str(root / "code" / "verify_one_shard_outputs.py"),
    "--allowed-root", str(root), "--output", str(set_qa_path),
])
set_qa = json.loads(set_qa_path.read_text())
if set_qa.get("status") != "pass" or set_qa.get("shard_count") != 4:
    raise RuntimeError("four-shard set QA did not pass")

totals = collections.Counter()
output_bytes = 0
elapsed = []
for entry in entries:
    shard = entry["shard_id"]
    receipt = json.loads((root / "private" / ("SHARD_" + shard + "_RECEIPT.json")).read_text())
    if receipt.get("status") != "complete" or receipt.get("identity", {}).get("runner_sha256") != expected:
        raise RuntimeError("production receipt identity mismatch")
    if not receipt.get("row_conservation"):
        raise RuntimeError("production row conservation failed")
    totals["raw_rows"] += receipt["raw_rows"]
    totals["posting_rows"] += receipt["outputs"]["posting_rows"]
    totals["evidence_rows"] += receipt["outputs"]["evidence_rows"]
    output_bytes += receipt["outputs"]["posting_bytes"] + receipt["outputs"]["evidence_bytes"]
    elapsed.append(receipt["elapsed_seconds"])
if output_bytes > 1_000_000_000:
    raise RuntimeError("initial output budget exceeded")

public = {
    "status": "pass", "version": "d60-wuzhen-four-shard-qa-v1",
    "scope": "mechanical QA of four in-place Wuzhen rule outputs; no semantic certification",
    "qa_job_id": os.environ.get("SLURM_JOB_ID"),
    "production_array_job_id": "46208844",
    "scheduler": {"partition": "wzhdtest", "cpus": 4, "memory_gib": 8, "time_limit": "00:10:00", "dcu_requested": 1, "dcu_use": "scheduler-QOS-minimum; unused by CPU verifier"},
    "shard_count": 4, "raw_rows": totals["raw_rows"],
    "posting_rows": totals["posting_rows"], "evidence_rows": totals["evidence_rows"],
    "output_bytes": output_bytes, "output_budget_max_bytes": 1_000_000_000,
    "row_conservation_all": True, "full_output_sha256_all": True,
    "frozen_schema_all": True, "evidence_span_structure_errors": 0,
    "evidence_locator_index_and_count_consistent": True,
    "canonical_locator_unique_across_shards": set_qa["canonical_locator_unique_across_shards"],
    "canonical_job_hash_unique_across_shards": set_qa["canonical_job_hash_unique_across_shards"],
    "distinct_source_file_count": set_qa["distinct_source_file_count"],
    "idempotent_resume_verified_all": True,
    "runner_sha256": expected, "plan_rows": preflight["plan_rows"],
    "elapsed_seconds_min": min(elapsed), "elapsed_seconds_max": max(elapsed),
    "api_calls": 0, "model_calls": 0,
    "claim_boundary": "rule-observed candidates; no-match remains unknown; metadata linkage pending",
    "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
}
tmp = root / "public" / "QA_PUBLIC.json.tmp"
tmp.write_text(json.dumps(public, indent=2, sort_keys=True) + "\n")
os.replace(tmp, root / "public" / "QA_PUBLIC.json")
PY
