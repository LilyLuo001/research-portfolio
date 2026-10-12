#!/bin/bash
#SBATCH --job-name=pro-wave02-runtime
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=/public/home/lilysharp/linkup_rulefirst_20261008/pro_review_wave02_20261012/public/runtime-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_rulefirst_20261008/pro_review_wave02_20261012/public/runtime-%j.err
set -eo pipefail
source /etc/profile.d/modules.sh
set +u
module load python/3.8.10
set -u
ROOT=/public/home/lilysharp/linkup_rulefirst_20261008/pro_review_wave02_20261012
python3 -m pip install --no-index --find-links "$ROOT/vendor" --target "$ROOT/runtime_py38" jsonschema==4.17.3
PYTHONPATH="$ROOT/runtime_py38" python3 -c 'import jsonschema; from jsonschema import Draft202012Validator; assert jsonschema.__version__ == "4.17.3"; print(jsonschema.__version__, Draft202012Validator.__name__)'
