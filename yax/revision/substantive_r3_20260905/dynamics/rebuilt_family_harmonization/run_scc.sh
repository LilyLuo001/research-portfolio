#!/bin/bash -l
#$ -P econdept
#$ -l h_rt=10:00:00
#$ -l mem_per_core=16G
#$ -pe omp 1
#$ -j y
#$ -N yax_r3_fam_rebuilt
set -euo pipefail

REPO="${YAX_REPO_ROOT:-${SGE_O_WORKDIR:-}}"
PROJECT_ROOT="${YAX_SCC_PROJECT_ROOT:?Set YAX_SCC_PROJECT_ROOT to a writable compute root}"
OUT="${OUTPUT_ROOT:-$PROJECT_ROOT/agents/dynamics/rebuilt_family_harmonization/results}"
PYTHON="${YAX_PYTHON_BIN:-python3}"
PRIVATE="${YAX_PRIVATE_ROOT:?Set YAX_PRIVATE_ROOT to the restricted input root}"

if [[ -z "$REPO" || ! -f "$REPO/yax/revision/substantive_r3_20260905/dynamics/rebuilt_family_harmonization/run_rebuilt_family.py" ]]; then
  echo "ERROR: YAX_REPO_ROOT/SGE_O_WORKDIR does not identify the clean worktree" >&2
  exit 2
fi

mkdir -p "$OUT"
cd "$REPO"
if [[ -n "${YAX_LEGACY_PYTHONPATH:-}" ]]; then
  export PYTHONPATH="$YAX_LEGACY_PYTHONPATH${PYTHONPATH:+:$PYTHONPATH}"
fi
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

"$PYTHON" yax/revision/substantive_r3_20260905/dynamics/rebuilt_family_harmonization/run_rebuilt_family.py \
  --microdata "$PRIVATE/ai_telework_2017_2026/cps_00009.csv.gz" \
  --repair-microdata "$PRIVATE/yax_referee_march_repair/cps_00011.csv.gz" \
  --preperiod-cells "$PRIVATE/ai_telework_2017_2026/preperiod_gate_v1/young_relative_employment_cells_v1.csv" \
  --rebuilt-membership "$REPO/yax/revision/substantive_r3_20260905/rebuilt_baseline/results/REBUILT_TREATMENT_MEMBERSHIP.csv" \
  --output-dir "$OUT" \
  --draws 9999

"$PYTHON" yax/revision/substantive_r3_20260905/dynamics/rebuilt_family_harmonization/selfcheck.py \
  --output-dir "$OUT"
