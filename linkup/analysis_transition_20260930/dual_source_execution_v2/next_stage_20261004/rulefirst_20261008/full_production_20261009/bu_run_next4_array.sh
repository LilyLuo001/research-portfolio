#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -P econdept
#$ -q econ
#$ -pe omp 4
#$ -l h_rt=02:00:00
#$ -l mem_per_core=2G
#$ -l no_gpu=TRUE
#$ -t 1-4
#$ -tc 4
#$ -N lk_full4
set -euo pipefail
umask 077
ROOT=/projectnb/econdept/qluo/linkup_rulefirst_20261008/full_production_20261009
IDX="${TASK_INDEX:-${SGE_TASK_ID:-}}"
case "$IDX" in
  1) SOURCE=job-descriptions_0_0_1.snappy.parquet; SID=b9376a87ec3e8b7c72d028e376524926a10980d849cb84cc3c34e5ef2e254102; RAW_SHA=ce4e9b3255d6e278a86a5f09c25168df317fb123e872a75550af89e8120fe27a; SIDE_SHA=d4e02c11e83139597e6df4990262af987f7934b018226e1fc21a5ded7f804973 ;;
  2) SOURCE=job-descriptions_0_0_10.snappy.parquet; SID=fc4fc3a546b62738be0ed236bb15399906a678796d0cbb08f26c2dfca6ea28aa; RAW_SHA=3d8620881c57ff29d02bb195507baaa78ccef28da0275c0f80cea4e0b644a6e8; SIDE_SHA=4829e4646b44d33d3f9648ae13d9e3a9fcb61fe2b94f1a9d4ea83d471a5f5bb6 ;;
  3) SOURCE=job-descriptions_0_0_11.snappy.parquet; SID=3d07a85fc3160eed1d085e92ec5d7ba2be42240429c786b68b6b1ad62533f0fe; RAW_SHA=3b6d57328eb4fcfdc417f742a8d9782d1662314b01525b89e601f6f23ec4b484; SIDE_SHA=e9143f18c642d8f83666d99e46cb4733cd40500cb0a70b128166a84d4dcfa129 ;;
  4) SOURCE=job-descriptions_0_0_12.snappy.parquet; SID=41305ab79b0f9fcd190f6cbd169bb7f15d05babf7c1e2fe54f17d64a3b0394be; RAW_SHA=d5a22dc28350af5f77de0749403dff180f686322b8eae060ebd7ba15193ddcde; SIDE_SHA=a730fa676145e067404d0737e502984e986c646c903dab02c3f18ce54483c219 ;;
  *) echo "unexpected SGE_TASK_ID" >&2; exit 2 ;;
esac
SHORT="${SID:0:16}"
OUT="$ROOT/output/shard_$SHORT"
FAIL="$ROOT/output/FAILED_SHARD_${SHORT}_JOB_${JOB_ID}_TASK_${IDX}_RECEIPT_PUBLIC.json"
mkdir -p "$ROOT/logs" "$OUT"
exec >"$ROOT/logs/full_next4.${JOB_ID}.${IDX}.${SHORT}.log" 2>&1
trap 'rc=$?; if [ "$rc" -ne 0 ]; then python3 - "$FAIL" "$rc" <<'"'"'PY'"'"'
import datetime,json,os,socket,sys
p,rc=sys.argv[1],int(sys.argv[2]);tmp=p+".tmp"
v={"status":"failed","job_id":os.environ.get("JOB_ID"),"task_id":os.environ.get("SGE_TASK_ID"),"host":socket.gethostname(),"exit_code":rc,"created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"note":"See protected scheduler log; no output is marked complete."}
open(tmp,"w").write(json.dumps(v,indent=2,sort_keys=True)+"\n");os.replace(tmp,p)
PY
fi' EXIT
module load python3/3.8.10
PYTHONPATH="$ROOT/code:${PYTHONPATH:-}" python3 "$ROOT/code/run_one_shard.py" \
  --raw "$ROOT/input/next4/$SOURCE" \
  --sidecar "$ROOT/input/next4/$SID.parquet" \
  --output-dir "$OUT" \
  --public-receipt "$ROOT/output/SHARD_${SHORT}_RECEIPT_PUBLIC.json" \
  --expected-raw-sha256 "$RAW_SHA" \
  --expected-sidecar-sha256 "$SIDE_SHA" \
  --workers "${NSLOTS:-4}"
