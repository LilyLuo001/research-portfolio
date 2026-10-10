#!/bin/bash
#SBATCH --job-name=lk_d60_wz4
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=02:00:00
#SBATCH --no-requeue
#SBATCH --array=0-3%4
#SBATCH --output=/work/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/domestic_wz_d60/logs/production-%A_%a.out
#SBATCH --error=/work/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/domestic_wz_d60/logs/production-%A_%a.err
set -euo pipefail
umask 077
ROOT=/work/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/domestic_wz_d60
PLAN=/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen/plan.jsonl
RUNTIME=/work/home/lilysharp/linkup_release_v1/runtime_py38
EXPECTED_RUNNER=3826142b6cddb549e831c8302be1d460ba3e85ee96bb7736af5549f878b3bf44
test "$(python3 -c 'import json; print(json.load(open("'"$ROOT"'/public/PREFLIGHT_PUBLIC.json"))["status"])')" = passed
test "$(sha256sum "$ROOT/code/run_one_shard.py" | awk '{print $1}')" = "$EXPECTED_RUNNER"
ENTRY=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "$PLAN")
eval "$(ENTRY="$ENTRY" python3 - <<'PY'
import json, os, shlex
x=json.loads(os.environ['ENTRY'])
for k,v in [('RAW',x['source_path']),('SIDECAR',x['sidecar_path']),('SHARD',x['shard_id']),
            ('RAW_SHA',x['source_sha256_cached']),('SIDECAR_SHA',x['sidecar_sha256'])]:
    print('%s=%s' % (k, shlex.quote(str(v))))
PY
)"
OUT="$ROOT/output/shard_$SHARD"
RECEIPT="$ROOT/private/SHARD_${SHARD}_RECEIPT.json"
FAIL="$ROOT/private/SHARD_${SHARD}_FAILURE.json"
mkdir -p "$OUT" "$ROOT/private"
trap 'rc=$?; if [ "$rc" -ne 0 ]; then printf "{\"status\":\"failed\",\"job_id\":\"%s\",\"array_task_id\":\"%s\",\"exit_code\":%d}\n" "${SLURM_ARRAY_JOB_ID:-}" "${SLURM_ARRAY_TASK_ID:-}" "$rc" >"$FAIL"; fi' EXIT
set +u
source /etc/profile >/dev/null 2>&1 || true
module purge >/dev/null 2>&1 || true
module load python/3.8.10
set -u
export PYTHONPATH="$ROOT/code:$RUNTIME"
python3 "$ROOT/code/run_one_shard.py" \
  --raw "$RAW" \
  --sidecar "$SIDECAR" \
  --output-dir "$OUT" \
  --public-receipt "$RECEIPT" \
  --expected-raw-sha256 "$RAW_SHA" \
  --expected-sidecar-sha256 "$SIDECAR_SHA" \
  --workers 4
