#!/bin/bash -l
#$ -P econdept
#$ -l h_rt=08:00:00
#$ -l mem_per_core=16G
#$ -pe omp 1
#$ -j y
#$ -N yax_r3_honestdid
set -euo pipefail

COMPUTE_ROOT="${YAX_SCC_PROJECT_ROOT:?Set YAX_SCC_PROJECT_ROOT to a writable compute root}"
AGENT="$COMPUTE_ROOT/agents/dynamics"
OUT="$AGENT/results"
PYTHON="${YAX_PYTHON_BIN:-python3}"
export R_LIBS_USER="$AGENT/r-library/4.5-glpk-cvxr182-rust184-highs112"
export CARGO_HOME="$AGENT/r-library/cargo-home-rust184-highs112"
mkdir -p "$R_LIBS_USER"
mkdir -p "$CARGO_HOME"
module load R/4.5.2
module load glpk/5.0
module load rust/1.84.0
GLPK_ROOT=/share/pkg.8/glpk/5.0/install
test -f "$GLPK_ROOT/include/glpk.h"
test -f "$GLPK_ROOT/lib/libglpk.so.40.3.1"
export CPATH="$GLPK_ROOT/include${CPATH:+:$CPATH}"
export LIBRARY_PATH="$GLPK_ROOT/lib${LIBRARY_PATH:+:$LIBRARY_PATH}"
export LD_LIBRARY_PATH="$GLPK_ROOT/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

Rscript -e 'if (!requireNamespace("HonestDiD", quietly=TRUE)) quit(status=42)'
Rscript -e 'if (as.character(packageVersion("CVXR")) != "1.8.2" || !"status" %in% getNamespaceExports("CVXR")) quit(status=43)'
Rscript -e 'if (packageDescription("highs")$Version != "1.12.0-3") quit(status=44)'
Rscript -e 'if (packageDescription("osqp")$Version != "1.0.0") quit(status=45)'
Rscript "$AGENT/run_honestdid.R" "$OUT"
"$PYTHON" "$AGENT/selfcheck.py" --output-dir "$OUT" --require-honestdid
