#!/bin/bash
#SBATCH --job-name=lk-design-corr
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/lilysharp/linkup_design_correction_20261024/logs/correction-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_design_correction_20261024/logs/correction-%j.err
set -euo pipefail
source /etc/profile.d/modules.sh
module load python/3.8.10
umask 077
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
R=/public/home/lilysharp/linkup_design_correction_20261024
H="$R/handoff_private"
test ! -e "$R/run001/public/RUN_RECEIPT_PUBLIC.json" || { echo completed_correction_guard; exit 0; }
test -e "$H/HANDOFF_PUBLIC.json"
cd "$R/code"
python - <<'PYHASH'
import hashlib, json
from pathlib import Path
h = Path('/public/home/lilysharp/linkup_design_correction_20261024/handoff_private')
m = json.loads((h/'HANDOFF_PUBLIC.json').read_text())
for name, expected in m['outputs'].items():
    p = h/name
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    if p.stat().st_size != expected['bytes'] or digest != expected['sha256']:
        raise RuntimeError('handoff transport mismatch: '+name)
print('HANDOFF_TRANSPORT_HASHES_VERIFIED', len(m['outputs']))
PYHASH
python test_correction_core.py
args=()
for p in /public/home/lilysharp/linkup_analysis_execution_oct02/private/comparison_join_v1/joined/[0-9a-f].parquet; do args+=(--parent "$p"); done
test "${#args[@]}" -eq 32
python run_design_correction.py "${args[@]}" \
  --fixed "$H/FIXED_KEYS_WEIGHTS_PRIVATE.parquet" \
  --reference "$H/REFERENCE_AD_LEVEL_PRIVATE.parquet" \
  --reference-receipt "$H/EMPIRICAL_RECEIPT_PUBLIC.json" \
  --isolation-register "$H/ISOLATION_PRIVATE.jsonl" \
  --allocation "$H/cell_allocation.csv" \
  --private-output "$R/run001/private" --public-output "$R/run001/public" \
  --threads 8 --memory-limit 12GB --enable-design-se
python prepare_delivery_summary.py --results-dir "$R/run001/public" --output-dir "$R/run001/public"
