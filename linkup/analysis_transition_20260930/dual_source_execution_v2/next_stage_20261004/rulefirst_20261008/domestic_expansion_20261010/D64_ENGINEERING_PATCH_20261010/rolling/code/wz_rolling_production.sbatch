#!/bin/bash
#SBATCH --job-name=d64-wzroll
#SBATCH --partition=wzhdtest
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=02:00:00
#SBATCH --array=0-2%3
#SBATCH --output=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/d64_engineering_patch_20261010/rolling/logs/prod-%A_%a.out
#SBATCH --error=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/d64_engineering_patch_20261010/rolling/logs/prod-%A_%a.err
set -eo pipefail
umask 077
set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
set -u
BASE=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010
PATCH_BASE="$BASE/d64_engineering_patch_20261010"
ROOT=$(printf "$BASE/wz_wave_%04d" "$WAVE")
OLD=/work/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/domestic_wz_d60
RUNTIME=/work/home/lilysharp/linkup_release_v1/runtime_py38
RESERVE_BYTES=10000000000
SINGLE_SHARD_BUDGET_BYTES=1000000000
export PYTHONPATH="$OLD/code:$RUNTIME"
for IDX in $(seq "$SLURM_ARRAY_TASK_ID" 3 15); do
 eval "$(ROOT="$ROOT" WAVE="$WAVE" IDX="$IDX" python3 - <<'PY'
import json,os,shlex
p='%s/private/WAVE_%04d_MANIFEST_PRIVATE.json'%(os.environ['ROOT'],int(os.environ['WAVE']))
x=json.load(open(p))['selected_entries'][int(os.environ['IDX'])]
for k,v in [('RAW',x['source_path']),('SIDECAR',x['sidecar_path']),('SHARD',x['shard_id']),('RAW_SHA',x['source_sha256_cached']),('SIDECAR_SHA',x['sidecar_sha256'])]:
 print('%s=%s'%(k,shlex.quote(str(v))))
PY
)"
 # This is a conservative pre-shard admission check, not a filesystem quota.
 FREE_BYTES=$(BASE="$BASE" python3 -c 'import os,shutil; print(shutil.disk_usage(os.environ["BASE"]).free)')
 if (( FREE_BYTES < RESERVE_BYTES + SINGLE_SHARD_BUDGET_BYTES )); then
  echo "capacity gate: free=$FREE_BYTES reserve=$RESERVE_BYTES single_shard_budget=$SINGLE_SHARD_BUDGET_BYTES shard=$SHARD" >&2
  exit 1
 fi
 OUT="$ROOT/output/shard_$SHARD"
 mkdir -p "$OUT" "$ROOT/private" "$PATCH_BASE/rolling/logs"
 python3 "$OLD/code/run_one_shard.py" --raw "$RAW" --sidecar "$SIDECAR" --output-dir "$OUT" --public-receipt "$ROOT/private/SHARD_${SHARD}_RECEIPT.json" --expected-raw-sha256 "$RAW_SHA" --expected-sidecar-sha256 "$SIDECAR_SHA" --workers 4
done
