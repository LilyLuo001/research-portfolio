# Source this on SCC before running anything in src/.
# The login shell has no scientific stack; the module provides pandas/pyarrow/
# statsmodels/scipy/matplotlib in the versions this package was developed against.
module load python3/3.12.4

export PPW_ARCHIVE=/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902
export PPW_WORK=/projectnb/econdept/qluo/news_price_discovery/prepurchase_wrds
export PYTHONPATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/../src" && pwd):${PYTHONPATH}"
