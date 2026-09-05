#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -l h_rt=08:00:00
#$ -l mem_per_core=32G

set -euo pipefail
module load python3/3.12.4

run_root=/project/econdept/qluo/P1_Refraction_WRDS/GATE_RUN_20260905
code_root=${GATE_CODE_ROOT:-${run_root}/code}
state_root=${GATE_STATE_ROOT:-${run_root}}
: "${GATE_PILOT_PASS:?GATE_PILOT_PASS must name the matching PILOT_PASS.json}"
export MPLCONFIGDIR="${state_root}/cache/matplotlib"
export XDG_CACHE_HOME="${state_root}/cache"
cd "${code_root}"
gate_output_dir=${GATE_OUTPUT_DIR:-${run_root}/output}
python3 run_gate0_gate1.py \
  --output "${gate_output_dir}" \
  --pilot-pass "${GATE_PILOT_PASS}"
