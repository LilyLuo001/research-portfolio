#!/bin/bash -l
#$ -P econdept
#$ -N yax_r3_arch
#$ -j y
#$ -l h_rt=18:00:00
#$ -l mem_per_core=8G
#$ -pe omp 4

set -euo pipefail

COMPUTE_ROOT="${YAX_SCC_PROJECT_ROOT:?Set YAX_SCC_PROJECT_ROOT to a writable compute root}"
REPO_ROOT="${REPO_ROOT:-$COMPUTE_ROOT/repo_git2}"
PYTHON_BIN="${YAX_PYTHON_BIN:-python3}"
PRIVATE_ROOT="${YAX_PRIVATE_ROOT:?Set YAX_PRIVATE_ROOT to the restricted input root}"
OUTPUT_ROOT="${OUTPUT_ROOT:-$COMPUTE_ROOT/results/architecture}"

mkdir -p "$COMPUTE_ROOT/results" "$COMPUTE_ROOT/logs"
if [ -e "$OUTPUT_ROOT" ]; then
  echo "Refusing to overwrite existing architecture output: $OUTPUT_ROOT" >&2
  exit 2
fi
cd "$REPO_ROOT"

if [[ -n "${YAX_LEGACY_PYTHONPATH:-}" ]]; then
  export PYTHONPATH="$YAX_LEGACY_PYTHONPATH${PYTHONPATH:+:$PYTHONPATH}"
fi
export OMP_NUM_THREADS="${NSLOTS:-1}"
export OPENBLAS_NUM_THREADS="${NSLOTS:-1}"
export MKL_NUM_THREADS="${NSLOTS:-1}"

"$PYTHON_BIN" \
  yax/revision/substantive_r3_20260905/architecture/run_architecture.py \
  --repo-root "$REPO_ROOT" \
  --microdata "$PRIVATE_ROOT/ai_telework_2017_2026/cps_00009.csv.gz" \
  --repair-microdata "$PRIVATE_ROOT/yax_referee_march_repair/cps_00011.csv.gz" \
  --lookup "$REPO_ROOT/yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv" \
  --computerization "$REPO_ROOT/yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv" \
  --rule-b-values "$REPO_ROOT/yax/measurement/RULE_B_VALUES_CENSUS2018.csv" \
  --bridge "$REPO_ROOT/yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv" \
  --characteristics "$REPO_ROOT/yax/measurement/test_a/TEST_A_OCCUPATION_CHARACTERISTICS.csv" \
  --baseline-membership "$REPO_ROOT/yax/revision/substantive_r3_20260905/rebuilt_baseline/results/REBUILT_TREATMENT_MEMBERSHIP.csv" \
  --baseline-normalization "$REPO_ROOT/yax/revision/substantive_r3_20260905/rebuilt_baseline/results/REBUILT_NORMALIZATION_AND_CUTS.json" \
  --baseline-decomposition "$REPO_ROOT/yax/revision/substantive_r3_20260905/rebuilt_baseline/results/BASELINE_DECOMPOSITION.csv" \
  --output-dir "$OUTPUT_ROOT"

"$PYTHON_BIN" \
  yax/revision/substantive_r3_20260905/architecture/selfcheck.py \
  --results-dir "$OUTPUT_ROOT"
