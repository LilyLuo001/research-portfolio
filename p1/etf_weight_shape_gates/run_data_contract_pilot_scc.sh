#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -l h_rt=00:30:00
#$ -l mem_per_core=16G

set -euo pipefail
module load python3/3.12.4

run_root=${P1_PILOT_RUN_ROOT:-/project/econdept/qluo/P1_Refraction_WRDS/GATE_RUN_20260905}
code_root=${P1_PILOT_CODE_ROOT:-${run_root}/code}
pilot_output=${P1_PILOT_OUTPUT:-${run_root}/pilot}
archive=${P1_PILOT_ARCHIVE:-/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902}
manifest=${P1_PILOT_MANIFEST:-${archive}/_migration_meta/FINAL_SCC_MANIFEST.tsv}

cd "${code_root}"
python3 run_data_contract_pilot.py \
  --archive "${archive}" \
  --manifest "${manifest}" \
  --code-root "${code_root}" \
  --config "${code_root}/gate01_config.json" \
  --data-contract "${code_root}/data_contract.json" \
  --golden-sample "${code_root}/golden_sample_spec.json" \
  --output "${pilot_output}"
