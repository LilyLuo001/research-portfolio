#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -P econdept
#$ -q econ
#$ -pe omp 4
#$ -l h_rt=02:00:00
#$ -l mem_per_core=2G
#$ -l no_gpu=TRUE
#$ -N lk_full1
set -euo pipefail
umask 077
ROOT=/projectnb/econdept/qluo/linkup_rulefirst_20261008/full_production_20261009
LOG="$ROOT/logs/full_one_shard.${JOB_ID}.log"
FAIL="$ROOT/output/FAILED_SHARD_b605d84d410013b1_JOB_${JOB_ID}_RECEIPT_PUBLIC.json"
mkdir -p "$ROOT/logs" "$ROOT/output"
exec >"$LOG" 2>&1
trap 'rc=$?; if [ "$rc" -ne 0 ]; then python3 - "$FAIL" "$rc" <<'"'"'PY'"'"'
import datetime,json,os,socket,sys
p,rc=sys.argv[1],int(sys.argv[2]);tmp=p+".tmp"
v={"status":"failed","job_id":os.environ.get("JOB_ID"),"host":socket.gethostname(),"exit_code":rc,"created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"note":"See protected scheduler log; no output is marked complete."}
open(tmp,"w").write(json.dumps(v,indent=2,sort_keys=True)+"\n");os.replace(tmp,p)
PY
fi' EXIT
module load python3/3.8.10
PYTHONPATH="$ROOT/code:${PYTHONPATH:-}" python3 "$ROOT/code/run_one_shard.py" \
  --raw "$ROOT/input/job-descriptions_0_0_0.snappy.parquet" \
  --sidecar "$ROOT/input/b605d84d410013b172391b85e09af6012057c75aaf85003a43d4847379931e38.parquet" \
  --output-dir "$ROOT/output/shard_b605d84d410013b1" \
  --public-receipt "$ROOT/output/SHARD_b605d84d410013b1_RECEIPT_PUBLIC.json" \
  --expected-raw-sha256 2b68b1733ccffe74a346158bb3a37ac44fdf9569a2f5fc7fbb90f464b60cd819 \
  --expected-sidecar-sha256 d652778220f808f50fbde7e56324d16d293194e335c9a6d714134399333fc033 \
  --workers "${NSLOTS:-4}"
