#!/bin/bash
#SBATCH --job-name=linkup-q32-final
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
set -euo pipefail
set +u; source /etc/profile >/dev/null 2>&1 || true; module load python/3.8.10 >/dev/null 2>&1 || true; set -u
: "${BUNDLE:?}"; : "${RUN_ROOT:?}"
mkdir -p "${RUN_ROOT}/final"
if ! python3 - "${RUN_ROOT}/PREP_JOB_RECEIPT.json" <<'PY'
import json,sys
try: p=json.load(open(sys.argv[1]))
except Exception: raise SystemExit(1)
raise SystemExit(0 if p.get("status")=="complete" else 1)
PY
then
  printf '{"schema_version":"linkup-cpu-fixed32-public-v2","status":"prep_failed","records":32,"process_completed":0,"process_missing_or_failed":32,"comparison_performed":false}\n' > "${RUN_ROOT}/final/QUALIFICATION_PUBLIC.json"
  exit 0
fi
export PYTHONPATH="${RUN_ROOT}/python_vendor${PYTHONPATH:+:${PYTHONPATH}}"
python3 "${BUNDLE}/code/finalize_fixed32_cpu.py" --source "${RUN_ROOT}/prepared/SOURCE32_PRIVATE.jsonl" --reference "${RUN_ROOT}/prepared/REFERENCE32_FINAL_CANDIDATES_PRIVATE.jsonl" --run-root "${RUN_ROOT}" --exporter-dir "${BUNDLE}/archive/production_standard_20261008" --output "${RUN_ROOT}/final/results"
