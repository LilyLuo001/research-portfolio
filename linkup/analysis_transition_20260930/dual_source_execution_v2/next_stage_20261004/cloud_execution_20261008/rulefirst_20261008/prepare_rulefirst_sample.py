#!/usr/bin/env python3
"""Prepare disjoint rule-design/evaluation samples from the frozen LinkUp queue.

This program performs selection and integrity checks only. It emits no semantic
labels, rule outputs, or model summaries.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

SEED = "linkup-rulefirst-20261008-v1"
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
SHA_KEYS = {
    "exact_text_sha256", "source_text_sha256", "raw_output_source_text_sha256",
    "source_sha256", "text_sha256",
}
WEIGHT_FIELDS = [
    "frame_count_a", "frame_count_b", "selected_cell_arm_n",
    "inclusion_probability", "design_weight", "W_h",
    "stable_rank_in_cell_arm", "sample_rank_in_cell_arm",
    "nested_frame_cell_arm_N", "next_selected_cell_arm_n",
    "original_inclusion_probability", "conditional_inclusion_probability",
    "total_inclusion_probability", "nested_design_weight",
    "pooled_cell_standardization_weight",
]


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rows(path):
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except Exception as exc:
                    raise RuntimeError(f"invalid JSONL at {path.name}:{n}: {exc}")


def gather_shas(obj, out):
    if isinstance(obj, dict):
        text = obj.get("original_text")
        if isinstance(text, str) and text:
            out.add(hashlib.sha256(text.encode("utf-8")).hexdigest())
        for key, value in obj.items():
            if key in SHA_KEYS and isinstance(value, str) and SHA_RE.fullmatch(value.lower()):
                out.add(value.lower())
            gather_shas(value, out)
    elif isinstance(obj, list):
        for value in obj:
            gather_shas(value, out)


def ranked(items, purpose, arm):
    return sorted(items, key=lambda x: hashlib.sha256(
        f"{SEED}|{purpose}|{arm}|{x['exact_text_sha256']}".encode()).hexdigest())


def dump_jsonl(path, data):
    with open(path, "w", encoding="utf-8") as f:
        for obj in data:
            f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")
    os.chmod(path, 0o600)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    args = ap.parse_args()
    root = Path(args.root).resolve()
    imported = root / "imported"
    out = root / "run" / "prep"
    out.mkdir(parents=True, exist_ok=True, mode=0o700)

    marker = root / "control" / "INPUT_STREAM_COMPLETE"
    if not marker.is_file():
        raise RuntimeError("INPUT_STREAM_COMPLETE is absent")
    queue_path = imported / "production_standard_20261008/private/full_queue/UNIQUE_EXACT_TEXT_QUEUE_PRIVATE.jsonl"
    represented_path = imported / "production_standard_20261008/private/full_queue/REPRESENTED_FIXED10000_KEYS_PRIVATE.jsonl"
    expected = {
        queue_path: "5ea54b141e18ebef4468fff8dfff3e81a196679e7caaece138303cf995f25a4e",
        represented_path: "987f4369643bdd353b7e881f7ccf58dcf7be0f29853b9f118a92b4076833b04d",
    }
    input_hashes = {str(p.relative_to(root)): sha_file(p) for p in expected}
    for p, want in expected.items():
        if input_hashes[str(p.relative_to(root))] != want:
            raise RuntimeError(f"input SHA mismatch: {p.name}")

    queue = list(rows(queue_path))
    represented = list(rows(represented_path))
    if len(queue) != 7635 or len(represented) != 10000:
        raise RuntimeError(f"unexpected row counts queue={len(queue)} represented={len(represented)}")
    by_sha = {}
    for q in queue:
        text = q.get("original_text")
        sha = q.get("exact_text_sha256")
        if not isinstance(text, str) or hashlib.sha256(text.encode("utf-8")).hexdigest() != sha:
            raise RuntimeError("queue text/hash mismatch")
        if sha in by_sha:
            raise RuntimeError("duplicate exact SHA in unique queue")
        by_sha[sha] = q

    meta_by_sha = defaultdict(list)
    arm_by_sha = {}
    arms = Counter()
    missing_weight_fields = Counter()
    for r in represented:
        sha, arm = r.get("exact_text_sha256"), r.get("arm")
        if sha not in by_sha or arm not in {"A", "B", "C"}:
            raise RuntimeError("represented binding or arm invalid")
        if sha in arm_by_sha and arm_by_sha[sha] != arm:
            raise RuntimeError("one exact text occurs in multiple arms")
        arm_by_sha[sha] = arm
        meta_by_sha[sha].append(r)
        arms[arm] += 1
        weights = r.get("weights")
        if not isinstance(weights, dict):
            raise RuntimeError("represented row lacks nested weights object")
        for field in WEIGHT_FIELDS:
            if field not in weights:
                missing_weight_fields[field] += 1
    if missing_weight_fields:
        raise RuntimeError(f"required weight fields absent: {dict(missing_weight_fields)}")

    # Conservative union of every transferred prior-review/exposure artifact.
    prior_files = []
    prior_by_file = {}
    prior = set()
    for p in sorted(imported.rglob("*.jsonl")):
        if p in {queue_path, represented_path}:
            continue
        found = set()
        for obj in rows(p):
            gather_shas(obj, found)
        if found:
            prior_files.append(p)
            prior_by_file[str(p.relative_to(root))] = len(found)
            prior.update(found)
    queue_shas = set(by_sha)
    reviewed = prior & queue_shas

    candidates = {a: [] for a in "ABC"}
    for sha, q in by_sha.items():
        arm = arm_by_sha.get(sha)
        if arm:
            item = dict(q)
            item["arm"] = arm
            candidates[arm].append(item)

    dev, dev_counts = [], {}
    for arm in "ABC":
        seen = ranked([x for x in candidates[arm] if x["exact_text_sha256"] in reviewed], "dev-reviewed", arm)
        fresh = ranked([x for x in candidates[arm] if x["exact_text_sha256"] not in reviewed], "dev-fill", arm)
        chosen = (seen + fresh)[:40]
        if len(chosen) != 40:
            raise RuntimeError(f"insufficient development candidates in arm {arm}")
        dev.extend(chosen)
        dev_counts[arm] = {"reviewed_priority": min(40, len(seen)), "unreviewed_fill": max(0, 40-len(seen))}
    dev_shas = {x["exact_text_sha256"] for x in dev}

    eval_quota = {"A": 27, "B": 27, "C": 26}
    evaluation = []
    for arm in "ABC":
        eligible = [x for x in candidates[arm]
                    if x["exact_text_sha256"] not in reviewed
                    and x["exact_text_sha256"] not in dev_shas]
        chosen = ranked(eligible, "evaluation", arm)[:eval_quota[arm]]
        if len(chosen) != eval_quota[arm]:
            raise RuntimeError(f"insufficient untouched evaluation candidates in arm {arm}")
        evaluation.extend(chosen)
    eval_shas = {x["exact_text_sha256"] for x in evaluation}
    if dev_shas & eval_shas or eval_shas & reviewed:
        raise RuntimeError("selection independence failure")

    def materialize(items, prefix):
        output = []
        for i, x in enumerate(items, 1):
            sha = x["exact_text_sha256"]
            output.append({
                "selection_index_1based": i,
                "selection_set": prefix,
                "queue_position_1based": x.get("queue_position_1based"),
                "queue_record_id": x.get("queue_record_id"),
                "exact_text_sha256": sha,
                "arm": x["arm"],
                "source_length_characters": len(x["original_text"]),
                "captured_section_coverage": "full_document",
                "original_text": x["original_text"],
                "represented_rows": meta_by_sha[sha],
            })
        return output

    dev_out = materialize(dev, "development")
    eval_out = materialize(evaluation, "evaluation")
    dev_path = out / "DEV120_SOURCE_PRIVATE.jsonl"
    eval_path = out / "EVAL80_SOURCE_PRIVATE.jsonl"
    dump_jsonl(dev_path, dev_out)
    dump_jsonl(eval_path, eval_out)

    # Twelve full-document packets, four per arm, for bounded root inspection.
    twelve = []
    for arm in "ABC":
        twelve.extend([x for x in dev_out if x["arm"] == arm][:4])
    twelve_path = out / "DEV12_FULLTEXT_PRIVATE.jsonl"
    dump_jsonl(twelve_path, twelve)
    txt_path = out / "DEV12_FULLTEXT_PRIVATE.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        for x in twelve:
            f.write(f"===== DEV {x['selection_index_1based']} | ARM {x['arm']} | SHA {x['exact_text_sha256']} | CHARS {x['source_length_characters']} | COVERAGE full_document =====\n")
            f.write(x["original_text"] + "\n\n")
    os.chmod(txt_path, 0o600)

    outputs = [dev_path, eval_path, twelve_path, txt_path]
    private_manifest = out / "PRIVATE_OUTPUT_MANIFEST.json"
    private_manifest.write_text(json.dumps({
        "inputs": input_hashes,
        "outputs": {p.name: {"sha256": sha_file(p), "bytes": p.stat().st_size} for p in outputs},
    }, indent=2, sort_keys=True) + "\n")
    os.chmod(private_manifest, 0o600)

    receipt = {
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "purpose": "selection_and_integrity_only_no_semantic_outputs",
        "seed": SEED,
        "source_rows": {"unique_exact_text_queue": len(queue), "represented_fixed_sample": len(represented)},
        "represented_arm_rows": dict(sorted(arms.items())),
        "unique_texts_by_arm": {a: len(candidates[a]) for a in "ABC"},
        "weight_fields_verified_all_10000_rows": WEIGHT_FIELDS,
        "prior_artifact_files_with_hashes": prior_by_file,
        "prior_hashes_discovered_total": len(prior),
        "prior_hashes_present_in_frozen_queue": len(reviewed),
        "prior_queue_hashes_by_arm": dict(Counter(arm_by_sha[x] for x in reviewed)),
        "development": {"rows": len(dev_out), "by_arm": dict(Counter(x["arm"] for x in dev_out)), "composition": dev_counts},
        "evaluation": {"rows": len(eval_out), "by_arm": dict(Counter(x["arm"] for x in eval_out)), "excludes_all_prior_hashes": True},
        "independence": {"unique_dev_hashes": len(dev_shas), "unique_eval_hashes": len(eval_shas), "dev_eval_overlap": 0, "eval_prior_overlap": 0},
        "review_packet": {"rows": 12, "by_arm": {"A": 4, "B": 4, "C": 4}, "coverage": "full_document", "semantic_context_windows": "pending_root_frozen_rule_engine"},
        "input_hashes": input_hashes,
        "private_output_manifest_sha256": sha_file(private_manifest),
    }
    receipt_path = out / "PREP_RECEIPT_PUBLIC.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "complete", "receipt": str(receipt_path), "dev": 120, "eval": 80, "review": 12}, sort_keys=True))


if __name__ == "__main__":
    main()
