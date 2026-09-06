#!/bin/bash -l
#$ -P econdept
#$ -N yax_r3_inf_rebuilt
#$ -j y
#$ -l h_rt=12:00:00
#$ -l mem_per_core=8G
#$ -pe omp 4

set -euo pipefail

COMPUTE_ROOT="${YAX_SCC_PROJECT_ROOT:?Set YAX_SCC_PROJECT_ROOT to a writable compute root}"
AGENT_ROOT="$COMPUTE_ROOT/agents/inference_rebuilt"
# Prefer an explicitly supplied clean worktree, then the directory from which
# qsub was invoked.  The shared repo_git2 fallback is retained only for the
# original compute layout.  No checkout or mutation is performed here.
REPO_ROOT="${YAX_REPO_ROOT:-${SGE_O_WORKDIR:-$COMPUTE_ROOT/repo_git2}}"
PRIVATE_ROOT="${YAX_PRIVATE_ROOT:?Set YAX_PRIVATE_ROOT to the restricted input root}"
PYTHON_BIN="${YAX_PYTHON_BIN:-python3}"

mkdir -p "$AGENT_ROOT/results"
test -f "$REPO_ROOT/yax/revision/substantive_r3_20260905/inference_rebuilt/run_inference_rebuilt.py"
cd "$REPO_ROOT"

if [[ -n "${YAX_LEGACY_PYTHONPATH:-}" ]]; then
  export PYTHONPATH="$YAX_LEGACY_PYTHONPATH${PYTHONPATH:+:$PYTHONPATH}"
fi
export OMP_NUM_THREADS="${NSLOTS:-1}"
export OPENBLAS_NUM_THREADS="${NSLOTS:-1}"
export MKL_NUM_THREADS="${NSLOTS:-1}"

"$PYTHON_BIN" \
  yax/revision/substantive_r3_20260905/inference_rebuilt/run_inference_rebuilt.py \
  --microdata "$PRIVATE_ROOT/ai_telework_2017_2026/cps_00009.csv.gz" \
  --repair-microdata "$PRIVATE_ROOT/yax_referee_march_repair/cps_00011.csv.gz" \
  --membership "$REPO_ROOT/yax/revision/substantive_r3_20260905/rebuilt_baseline/results/REBUILT_TREATMENT_MEMBERSHIP.csv" \
  --bridge "$REPO_ROOT/yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv" \
  --computerization "$REPO_ROOT/yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv" \
  --output-dir "$AGENT_ROOT/results"

"$PYTHON_BIN" \
  yax/revision/substantive_r3_20260905/inference_rebuilt/selfcheck.py \
  --results-dir "$AGENT_ROOT/results"
