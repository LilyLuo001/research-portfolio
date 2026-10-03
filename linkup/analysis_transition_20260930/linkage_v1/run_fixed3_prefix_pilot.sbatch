#!/bin/bash
#SBATCH --job-name=linkage_v1_pilot
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=24G
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_v1/linkage_v1/results/pilot-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_v1/linkage_v1/results/pilot-%j.err
set -euo pipefail
module load python/3.8.10
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38

ROOT=/public/home/lilysharp/linkup_analysis_v1/linkage_v1
PRIVATE=${ROOT}/private
OUT=${ROOT}/results/fixed3_prefix0_v1_1
mkdir -p "${OUT}"
test ! -e "${OUT}/PILOT_COVERAGE.json"

/public/software/apps/python/3.8.10/bin/python3 - <<'PY'
from pathlib import Path
import duckdb
source='/public/home/lilysharp/linkup_analysis_v1/linkage_v1/private/fixed3_keys.parquet'
target='/public/home/lilysharp/linkup_analysis_v1/linkage_v1/private/fixed3_prefix0_keys.parquet'
Path(target).unlink(missing_ok=True)
con=duckdb.connect()
con.execute("COPY (SELECT JOB_HASH,SOURCE_FILE,SOURCE_ROW,RECORD_SOURCE_ROW FROM read_parquet('%s') WHERE substr(lower(JOB_HASH),1,1)='0') TO '%s' (FORMAT PARQUET,COMPRESSION ZSTD)" % (source,target))
PY

/public/software/apps/python/3.8.10/bin/python3 "${PRIVATE}/build_linkage_coverage.py" \
  --lean "${PRIVATE}/fixed3_prefix0_keys.parquet" \
  --records /public/home/lilysharp/linkup_analysis_v1/stage_b/records_index_v1/hash_prefix=0/*.parquet \
  --onet /public/home/lilysharp/dewey_downloads/data/dewey_ONET_tables/onet-taxonomy/*.parquet \
  --official-codes "${PRIVATE}/official_onet2019_occupations.csv" \
  --rules "${PRIVATE}/RULES.json" \
  --output "${OUT}/PILOT_COVERAGE.json" --threads 4 --memory-limit 12GB \
  --records-lookup-scope complete_lowercase_first_hex_character_prefix_0_index_partition \
  --records-index-builder-sha256 ef29a208674d3963dd5bcb2af5f4f29a6cc10d1b99a8cf8715ab55255b5f05d5 \
  --selection-rule "lowercase JOB_HASH begins with 0; all such ads in conserved fixed-three-shard key projection" \
  --source-projection-rows 252301 \
  --source-projection-sha256 520abef078a99b5b7dc0d14939fff4001ab7943af30cd89bd6717ea97383194d \
  --onet-lookup-scope complete --expected-onet-files 62 --expected-onet-rows 356299258

sha256sum "${OUT}/PILOT_COVERAGE.json" > "${OUT}/PILOT_COVERAGE.sha256"
