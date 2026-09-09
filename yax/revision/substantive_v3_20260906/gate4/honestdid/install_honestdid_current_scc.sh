#!/bin/bash -l
#$ -P econdept
#$ -l h_rt=06:00:00
#$ -l mem_per_core=8G
#$ -pe omp 1
#$ -j y
#$ -N yax_v3_install_honestdid
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: install_honestdid_current_scc.sh CHECKOUT R_LIBRARY" >&2
  exit 2
fi
checkout="$(cd "$1" && pwd -P)"
export R_LIBS_USER="$2"
export CARGO_HOME="${R_LIBS_USER%/*}/cargo-home-rust184-highs112"
mkdir -p "$R_LIBS_USER" "$CARGO_HOME"

module load R/4.5.2
module load glpk/5.0
module load rust/1.84.0
glpk_root=/share/pkg.8/glpk/5.0/install
test -f "$glpk_root/include/glpk.h"
test -f "$glpk_root/lib/libglpk.so.40.3.1"
export CPATH="$glpk_root/include${CPATH:+:$CPATH}"
export LIBRARY_PATH="$glpk_root/lib${LIBRARY_PATH:+:$LIBRARY_PATH}"
export LD_LIBRARY_PATH="$glpk_root/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

Rscript \
  "$checkout/yax/revision/substantive_r3_20260905/dynamics/install_honestdid_scc.R"
