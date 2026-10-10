#!/bin/bash
#SBATCH --job-name=d67-mext
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --array=0-3%4
#SBATCH --output=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010/metadata_69/public/ext-%A_%a.out
#SBATCH --error=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010/metadata_69/public/ext-%A_%a.err
set -eo pipefail
source /etc/profile.d/modules.sh
set +u
module load python/3.8.10
set -u
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
ROOT=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010; META="$ROOT/metadata_69"; OLD=/public/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/metadata_join_first5_d60
SPEC=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["entries"][int(sys.argv[2])]["spec"])' "$META/work/ARRAY_MAP_PRIVATE.json" "$SLURM_ARRAY_TASK_ID")
python3 "$ROOT/code/metadata64_pipeline.py" extract --base-code "$OLD/code/targeted_metadata_join.py" --batch-spec "$SPEC"
