#!/bin/bash
#SBATCH --job-name=lk-pro-continuous-inputs
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/public/home/lilysharp/linkup_corpus_pro_review_20261026/logs/prepare-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_corpus_pro_review_20261026/logs/prepare-%j.err
set -euo pipefail
source /etc/profile.d/modules.sh
module load python/3.8.10
umask 077
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export PYTHONDONTWRITEBYTECODE=1

R=/public/home/lilysharp/linkup_corpus_pro_review_20261026
target=${PREPARE_THROUGH_BATCH:-31}
[[ $target =~ ^[0-9]+$ ]] && (( target >= 25 )) || { echo "Invalid PREPARE_THROUGH_BATCH: $target" >&2; exit 2; }
command -v flock >/dev/null || { echo 'flock unavailable' >&2; exit 2; }
exec 9>>"$R/code/ks_prepare_continuous_batch.lock"
flock -n 9 || { echo 'Another continuous preparation holds the lock' >&2; exit 3; }

owners=(
  01a17908-dbb4-7953-8029-96b600f388a4
  01a17909-9995-7b41-a496-52bac348af59
  01a17939-17c4-7811-963f-e48ab4f4b843
  01a17beb-973b-74e2-adbb-20f8d004b1fc
  01a17beb-989b-73a3-a901-b0eb3563020a
  01a17beb-99d3-7f21-a085-33fd51118803
  01a099c3-c4ed-7122-ac5a-71c8aa96ea07
)

# Validate only preparation metadata and packet checksums. A half-created
# output remains a blocker: the frozen preparer never overwrites its output.
verify_and_dispatch() {
  local n=$1 batch=$2 owner=$3
  python - "$R" "$n" "$batch" "$owner" <<'PY'
import hashlib
import json
import os
from pathlib import Path
import sys

root, number, batch, owner = Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4]
private = root / batch / "private"
public = root / batch / "public"
receipt_path = public / "PACKET_PREPARATION_PUBLIC.json"
manifest = private / "PACKET_MANIFEST_PRIVATE.jsonl"
if not (private.is_dir() and public.is_dir() and receipt_path.is_file() and manifest.is_file()):
    raise SystemExit("partial preparation output blocks " + batch)
receipt = json.loads(receipt_path.read_text())
if (receipt.get("status") != "prepared_not_reviewed" or
        receipt.get("prepared_contexts") != 720 or
        receipt.get("packet_capacity") != 720 or
        receipt.get("packet_size") != 5 or
        len(receipt.get("packet_files", [])) != 144 or
        receipt.get("cursor_exhausted") is True):
    raise SystemExit("incomplete or exhausted preparation receipt blocks " + batch)
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
if digest(manifest) != receipt.get("packet_manifest_sha256"):
    raise SystemExit("packet manifest SHA mismatch for " + batch)
for i, item in enumerate(receipt["packet_files"], 1):
    name = "packet_%04d.jsonl" % i
    path = private / name
    if item.get("name") != name or item.get("records") != 5 or not path.is_file():
        raise SystemExit("missing packet or wrong packet size: " + batch + "/" + name)
    if digest(path) != item.get("sha256"):
        raise SystemExit("packet SHA mismatch: " + batch + "/" + name)
if receipt.get("output_sha256", {}).get("packet_manifest_private") != receipt["packet_manifest_sha256"]:
    raise SystemExit("receipt manifest SHA inconsistent for " + batch)

# One whole batch belongs to one chat. The three packet ranges are the
# independent reading checkpoints within that chat, not new owners.
dispatch = {
    "version": "continuous-seven-lane-dispatch-v1",
    "batch": batch,
    "owner_thread_id": owner,
    "lane_index": (number - 25) % 7 + 1,
    "source_thread_id": "01a099c3-c4ed-7122-ac5a-71c8aa96ea07",
    "preparation_job": receipt["scheduled_job_id"],
    "packet_manifest_sha256": receipt["packet_manifest_sha256"],
    "scope": {"packets": 144, "contexts": 720},
    "start_cursor": receipt["start_cursor"],
    "next_cursor": receipt["next_cursor"],
    "reader_ranges": [
        {"first": 1, "last": 48, "owner_thread_id": owner},
        {"first": 49, "last": 96, "owner_thread_id": owner},
        {"first": 97, "last": 144, "owner_thread_id": owner},
    ],
    "packet_owner": {"%04d" % i: owner for i in range(1, 145)},
    "policy": "One chat owns all 144 packets; read complete texts in Pro; create-only primary reviews.",
}
target = root / "code" / ("DISPATCHER_%s_PUBLIC.json" % batch)
payload = (json.dumps(dispatch, sort_keys=True, indent=2) + "\n").encode()
if target.exists():
    if target.read_bytes() != payload:
        raise SystemExit("existing dispatcher differs for " + batch)
else:
    temporary = target.with_name(target.name + ".%s.tmp" % os.getpid())
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.link(str(temporary), str(target))
    finally:
        temporary.unlink()
print(json.dumps({"batch": batch, "owner_thread_id": owner,
                  "prepared_contexts": 720, "start_cursor": receipt["start_cursor"],
                  "next_cursor": receipt["next_cursor"],
                  "dispatcher_sha256": hashlib.sha256(payload).hexdigest()}, sort_keys=True))
PY
}

# Batch005 is the actual main-line boundary before restored shard0 was read.
# Its next cursor is 1:544. Once the restored shard0 is exhausted, never
# restart shard1 before that already-consumed main-line position.
read -r anchor_shard anchor_row < <(python -c 'import json,sys; c=json.load(open(sys.argv[1]))["next_cursor"]; print(c["shard_ordinal"],c["row_offset"])' "$R/batch005/public/PACKET_PREPARATION_PUBLIC.json")
[[ $anchor_shard == 1 && $anchor_row == 544 ]] || { echo 'Original main cursor anchor differs from 1:544' >&2; exit 4; }

for ((n=25; n<=target; n++)); do
  printf -v B 'batch%03d' "$n"
  printf -v P 'batch%03d' "$((n-1))"
  owner=${owners[$(((n-25)%7))]}
  prior_receipt="$R/$P/public/PACKET_PREPARATION_PUBLIC.json"
  [[ -f $prior_receipt ]] || { echo "Missing previous receipt: $prior_receipt" >&2; exit 5; }
  read -r start_shard start_row < <(python -c 'import json,sys; d=json.load(open(sys.argv[1])); c=d["next_cursor"]; print(c["shard_ordinal"],c["row_offset"])' "$prior_receipt")
  if (( start_shard == anchor_shard && start_row < anchor_row )); then
    start_row=$anchor_row
  fi
  if (( start_shard >= 2464 )); then
    echo "Catalog cursor exhausted before $B" >&2
    exit 6
  fi

  prior=()
  for ((i=1; i<n; i++)); do
    printf -v prior_batch 'batch%03d' "$i"
    prior_file="$R/$prior_batch/private/PACKET_MANIFEST_PRIVATE.jsonl"
    [[ -f $prior_file ]] || { echo "Missing prior manifest: $prior_file" >&2; exit 7; }
    prior+=("$prior_file")
  done

  if [[ -e "$R/$B/private" || -e "$R/$B/public" ]]; then
    [[ -d "$R/$B/private" && -d "$R/$B/public" ]] || { echo "Partial existing outputs block $B" >&2; exit 8; }
    echo "Checking existing $B"
  else
    echo "Preparing $B from $start_shard:$start_row"
    python "$R/code/prepare_packets.py" \
      --catalog /public/home/lilysharp/linkup_analysis_execution_oct02/corpus_release_20261012/private/release_v1/CORPUS_RELEASE_CATALOG_PRIVATE.jsonl \
      --reference /public/home/lilysharp/linkup_metadata_research_20261026/run001/private/AD_LEVEL_RESEARCH_PRIVATE.parquet \
      --raw-roots /public/home/lilysharp/dewey_downloads/data/linkup_job_descriptions "$R/restored_raw_private" \
      --normalizer "$R/code/legacy_v5_frozen.py" \
      --private-output "$R/$B/private" --public-output "$R/$B/public" --count 720 \
      --start-shard "$start_shard" --start-row "$start_row" --prior-manifests "${prior[@]}"
  fi
  verify_and_dispatch "$n" "$B" "$owner"
done
