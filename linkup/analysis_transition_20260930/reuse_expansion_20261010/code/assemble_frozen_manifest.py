#!/usr/bin/env python3
"""Assemble D67's frozen 69-shard control manifest from accepted receipts."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--current", required=True)
    p.add_argument("--old-narrow", required=True)
    p.add_argument("--scope", required=True)
    p.add_argument("--private-output", required=True)
    p.add_argument("--public-output", required=True)
    args = p.parse_args()
    current = json.load(open(args.current)); old = json.load(open(args.old_narrow))
    old_by_id = {x["shard_id"]: x for x in old}
    first5 = {"b605d84d410013b1", "b9376a87ec3e8b7c", "fc4fc3a546b62738",
              "3d07a85fc3160eed", "41305ab79b0f9fcd"}
    if len(current) != 69 or len(old_by_id) != 69:
        raise RuntimeError("frozen manifest must contain exactly 69 shards")
    if len({x["shard_id"] for x in current}) != 69:
        raise RuntimeError("duplicate shard identity")
    shards = []
    for x in current:
        if x["status"] != "complete" or x["qa_status"] != "pass":
            raise RuntimeError("non-accepted current shard")
        o = old_by_id[x["shard_id"]]
        if not o["exists"] or not o["receipt_exists"] or o["status"] != "complete":
            raise RuntimeError("missing accepted old narrow shard")
        if o["rows"] != x["posting_rows"]:
            # Different country/disposition versions may legitimately differ; preserve
            # both denominators and let the exact-key join report the difference.
            row_denominator_relation = "different_denominators_exact_key_join_required"
        else:
            row_denominator_relation = "equal_counts_exact_key_join_still_required"
        item = dict(x)
        item.update({
            "old_narrow_path_hz": o["path"], "old_narrow_receipt_hz": o["receipt_path"],
            "old_narrow_rows": o["rows"], "old_narrow_sha256": o["sha256"],
            "old_narrow_version": o["version"], "row_denominator_relation": row_denominator_relation,
            "old_v6_audit_glob_region_local": ("/public/home/lilysharp/linkup_release_v1/full_semantic_v1/" if x["region"] == "kunshan" else
                                                 "/work/home/lilysharp/linkup_release_v1/full_semantic_v1/") + x["shard_id"] + "/chunk_*/v6_audit.parquet",
            "metadata_status_at_freeze": "present_verified_first5" if x["short_id"] in first5 else "pending_one_pass_targeted_projection",
        })
        shards.append(item)
    manifest = {
        "version": "d67-frozen-69-v1", "status": "ready",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "scope_sha256": sha256(args.scope), "shard_count": 69,
        "current_posting_rows": sum(x["posting_rows"] for x in shards),
        "current_evidence_rows": sum(x["evidence_rows"] for x in shards),
        "old_narrow_rows": sum(x["old_narrow_rows"] for x in shards),
        "regions": {"kunshan": sum(x["region"] == "kunshan" for x in shards),
                    "wuzhen": sum(x["region"] == "wuzhen" for x in shards)},
        "metadata_status_shards": {"present_verified_first5": 5,
                                   "pending_one_pass_targeted_projection": 64},
        "shards": shards,
    }
    dump(args.private_output, manifest)
    public = {
        "version": manifest["version"], "status": "pass", "created_utc": manifest["created_utc"],
        "scope_sha256": manifest["scope_sha256"], "private_manifest_sha256": sha256(args.private_output),
        "shard_count": 69, "regions": manifest["regions"],
        "current_posting_rows": manifest["current_posting_rows"],
        "current_evidence_rows": manifest["current_evidence_rows"],
        "old_narrow_rows": manifest["old_narrow_rows"],
        "current_complete_and_qa_pass_shards": 69, "old_narrow_complete_receipts": 69,
        "metadata_status_shards": manifest["metadata_status_shards"],
        "selection": "frozen KS13 plus WZ56; one verified regional copy per shard",
        "exclusions": "running, failed, partial and unverified outputs; no later rolling expansion",
        "claim_boundary": "completed-output convenience wave; not a probability sample or full-corpus prevalence estimate",
    }
    dump(args.public_output, public)


if __name__ == "__main__":
    main()
