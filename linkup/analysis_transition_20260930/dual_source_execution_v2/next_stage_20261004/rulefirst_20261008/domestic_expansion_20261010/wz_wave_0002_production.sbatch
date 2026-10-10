#!/bin/bash
#SBATCH --job-name=d63-wz16
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=02:00:00
#SBATCH --no-requeue
#SBATCH --array=0-2%3
#SBATCH --output=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/wz_wave_0002/logs/production-%A_%a.out
#SBATCH --error=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/wz_wave_0002/logs/production-%A_%a.err
set -euo pipefail;umask 077
ROOT=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/wz_wave_0002;OLD=/work/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/domestic_wz_d60;RUNTIME=/work/home/lilysharp/linkup_release_v1/runtime_py38;EXPECTED=3826142b6cddb549e831c8302be1d460ba3e85ee96bb7736af5549f878b3bf44
set +u;source /etc/profile >/dev/null 2>&1||true;module purge >/dev/null 2>&1||true;module load python/3.8.10;set -u;export PYTHONPATH="$OLD/code:$RUNTIME"
test "$(sha256sum "$OLD/code/run_one_shard.py"|awk '{print $1}')" = "$EXPECTED"
for IDX in $(seq "$SLURM_ARRAY_TASK_ID" 3 15); do
 eval "$(ROOT="$ROOT" IDX="$IDX" python3 - <<'PY'
import json,os,shlex
x=json.load(open(os.environ['ROOT']+'/private/WAVE_0002_MANIFEST_PRIVATE.json'))['selected_entries'][int(os.environ['IDX'])]
for k,v in [('RAW',x['source_path']),('SIDECAR',x['sidecar_path']),('SHARD',x['shard_id']),('RAW_SHA',x['source_sha256_cached']),('SIDECAR_SHA',x['sidecar_sha256'])]:print('%s=%s'%(k,shlex.quote(str(v))))
PY
)"
 OUT="$ROOT/output/shard_$SHARD";RECEIPT="$ROOT/private/SHARD_${SHARD}_RECEIPT.json";mkdir -p "$OUT" "$ROOT/private"
 python3 "$OLD/code/run_one_shard.py" --raw "$RAW" --sidecar "$SIDECAR" --output-dir "$OUT" --public-receipt "$RECEIPT" --expected-raw-sha256 "$RAW_SHA" --expected-sidecar-sha256 "$SIDECAR_SHA" --workers 4
done
