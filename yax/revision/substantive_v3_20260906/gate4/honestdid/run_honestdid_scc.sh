#!/bin/bash -l
#$ -P econdept
#$ -l h_rt=04:00:00
#$ -l mem_per_core=16G
#$ -pe omp 1
#$ -j y
#$ -N yax_v3_honestdid
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: run_honestdid_scc.sh CHECKOUT OUTPUT_DIR R_LIBRARY" >&2
  exit 2
fi
checkout="$(cd "$1" && pwd -P)"
output_dir="$2"
export R_LIBS_USER="$(cd "$3" && pwd -P)"
export CARGO_HOME="${R_LIBS_USER%/*}/cargo-home-rust184-highs112"
mkdir -p "$output_dir" "$CARGO_HOME"

module load R/4.5.2
module load glpk/5.0
module load rust/1.84.0
glpk_root=/share/pkg.8/glpk/5.0/install
test -f "$glpk_root/include/glpk.h"
test -f "$glpk_root/lib/libglpk.so.40.3.1"
export CPATH="$glpk_root/include${CPATH:+:$CPATH}"
export LIBRARY_PATH="$glpk_root/lib${LIBRARY_PATH:+:$LIBRARY_PATH}"
export LD_LIBRARY_PATH="$glpk_root/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

package_dir="$checkout/yax/revision/substantive_v3_20260906/gate4/honestdid"
dynamic_dir="$checkout/yax/revision/substantive_v3_20260906/runs/gate2_dynamic_core_authoritative_20260908"
dynamic_spec="$checkout/yax/revision/substantive_v3_20260906/gate2/dynamic/DYNAMIC_RECONCILIATION_SPEC.json"
python_bin="${YAX_PYTHON_BIN:-/projectnb/econdept/qluo/yax-v3-venv/bin/python}"

"$python_bin" -I "$package_dir/prepare_honestdid_inputs.py" \
  --dynamic-dir "$dynamic_dir" \
  --dynamic-spec "$dynamic_spec" \
  --output-dir "$output_dir"
Rscript "$package_dir/run_honestdid_current.R" "$output_dir"
"$python_bin" -I "$package_dir/validate_honestdid_outputs.py" \
  --output-dir "$output_dir"

