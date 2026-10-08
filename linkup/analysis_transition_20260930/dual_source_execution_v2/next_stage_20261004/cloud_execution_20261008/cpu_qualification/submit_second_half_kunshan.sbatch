#!/bin/bash
#SBATCH --job-name=linkup-q32-chain
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:05:00
set -euo pipefail
: "${BUNDLE:?}"; : "${RUN_ROOT:?}"
mkdir -p "${RUN_ROOT}/control"
FINAL_JOB_ID=$(cat "${RUN_ROOT}/control/FINAL_JOB_ID")
if python3 - "${RUN_ROOT}/PREP_JOB_RECEIPT.json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1])); raise SystemExit(0 if p.get("status")=="complete" else 1)
PY
then
  cd "${BUNDLE}/code"
  SECOND=$(sbatch --parsable --array=16-31%4 --export=ALL,BUNDLE="${BUNDLE}",RUN_ROOT="${RUN_ROOT}",SOURCE_JSONL="${RUN_ROOT}/prepared/SOURCE32_PRIVATE.jsonl",RUNTIME="${BUNDLE}/runtime/bin",MODEL="${BUNDLE}/model/Qwen3-8B-Q4_K_M.gguf",PROMPT="${BUNDLE}/archive/production_standard_20261008/EXTRACTION_PROMPT.md",SCHEMA="${BUNDLE}/archive/compact_measurement_20261007/schema/compact_model_output.schema.json",ARCHIVE="${BUNDLE}/archive" run_fixed32_cpu_array.sbatch)
  scontrol update JobId="${FINAL_JOB_ID}" Dependency="afterany:${SECOND}"
  printf '{"status":"second_half_submitted","second_array_job_id":"%s","final_job_id":"%s"}\n' "${SECOND}" "${FINAL_JOB_ID}" > "${RUN_ROOT}/control/CHAIN_RECEIPT.json"
else
  printf '{"status":"prep_failed_second_half_not_submitted","final_job_id":"%s"}\n' "${FINAL_JOB_ID}" > "${RUN_ROOT}/control/CHAIN_RECEIPT.json"
fi
