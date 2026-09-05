#!/bin/bash -l
#$ -P econdept
#$ -l h_rt=00:30:00
#$ -l mem_per_core=4G
#$ -pe omp 1
#$ -j y
#$ -N yax_r3_hdmeta
set -euo pipefail

compute_root="${YAX_SCC_PROJECT_ROOT:?Set YAX_SCC_PROJECT_ROOT}"
output_dir="${YAX_HONESTDID_OUTPUT_DIR:?Set YAX_HONESTDID_OUTPUT_DIR}"
script="${YAX_HONESTDID_AUGMENT_SCRIPT:?Set YAX_HONESTDID_AUGMENT_SCRIPT}"
selfcheck="${YAX_DYNAMICS_SELFCHECK:?Set YAX_DYNAMICS_SELFCHECK}"
python_bin="${YAX_PYTHON_BIN:-python3}"

export R_LIBS_USER="$compute_root/agents/dynamics/r-library/4.5-glpk-cvxr182-rust184-highs112"
module load R/4.5.2
Rscript "$script" "$output_dir"
"$python_bin" "$selfcheck" --output-dir "$output_dir" --require-honestdid --require-structure-pair
