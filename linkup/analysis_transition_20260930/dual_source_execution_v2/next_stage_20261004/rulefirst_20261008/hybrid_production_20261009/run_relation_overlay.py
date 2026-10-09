#!/usr/bin/env python3
"""Apply a frozen relation overlay to existing v1.2 results.

No source extraction or model inference occurs here. The runner gates the full
7,635-row pass on synthetic tests and exact dev120 SHA/span validation, then
writes only source keys, evidence indices, offsets, and candidate annotations.
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path


def rows(path):
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except Exception as exc:
                    raise RuntimeError(f"invalid JSONL {path}:{n}: {exc}")


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def dump_jsonl(path, records):
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    os.chmod(path, 0o600)


def load_overlay(path):
    spec = importlib.util.spec_from_file_location("relation_overlay", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def narrow_apply(row, overlay, counters):
    sha = row.get("exact_text_sha256")
    status = row.get("status")
    if status != "complete":
        counters["baseline_failed"] += 1
        return {
            "exact_text_sha256": sha,
            "queue_position_1based": row.get("queue_position_1based"),
            "status": "baseline_not_complete",
            "baseline_status": status,
            "annotation_rules": [],
            "candidate_annotations": [],
        }
    result = row.get("result") or {}
    text = result.get("normalized_text")
    if result.get("source_text_sha256") != sha:
        raise RuntimeError("baseline source SHA binding mismatch")
    if not isinstance(text, str) or hashlib.sha256(text.encode("utf-8")).hexdigest() != result.get("normalized_text_sha256"):
        raise RuntimeError("baseline normalized text SHA mismatch")
    evidence = result.get("evidence") or []
    for e in evidence:
        counters["baseline_span_checks"] += 1
        a, b = e.get("start"), e.get("end")
        if (not isinstance(a, int) or not isinstance(b, int)
                or not (0 <= a <= b <= len(text)) or text[a:b] != e.get("quote")):
            counters["baseline_span_errors"] += 1
    if counters["baseline_span_errors"]:
        raise RuntimeError("baseline evidence span mismatch")

    applied = overlay.apply(result)
    if applied.get("source_text_sha256") != sha or applied.get("normalized_text_sha256") != result.get("normalized_text_sha256"):
        raise RuntimeError("overlay changed source binding")
    narrow = []
    rules = set()
    for item in applied.get("annotations") or []:
        idx = item.get("evidence_index")
        if not isinstance(idx, int) or idx < 0 or idx >= len(evidence):
            raise RuntimeError("overlay evidence index out of range")
        baseline = evidence[idx]
        if (item.get("start"), item.get("end"), item.get("kind")) != (
            baseline.get("start"), baseline.get("end"), baseline.get("kind")
        ):
            raise RuntimeError("overlay evidence coordinates differ from frozen baseline")
        heading = item.get("candidate_heading")
        narrow_heading = None
        if heading is not None:
            a, b = heading.get("start"), heading.get("end")
            if (not isinstance(a, int) or not isinstance(b, int)
                    or not (0 <= a <= b <= len(text)) or text[a:b] != heading.get("quote")):
                raise RuntimeError("overlay heading span mismatch")
            narrow_heading = {"start": a, "end": b, "scope": heading.get("scope")}
        annotations = item.get("annotations") or []
        for annotation in annotations:
            rule = annotation.get("rule")
            if not isinstance(rule, str) or not rule:
                raise RuntimeError("overlay annotation lacks rule")
            rules.add(rule)
            counters[("annotation", rule)] += 1
        narrow.append({
            "evidence_index": idx,
            "start": item.get("start"),
            "end": item.get("end"),
            "kind": item.get("kind"),
            "candidate_heading": narrow_heading,
            "heading_scope_status": item.get("heading_scope_status"),
            "annotations": annotations,
        })
    counters["overlay_complete"] += 1
    if not narrow:
        counters["no_candidate_marker"] += 1
    return {
        "exact_text_sha256": sha,
        "queue_position_1based": row.get("queue_position_1based"),
        "status": "candidate_markers_complete",
        "baseline_normalized_text_sha256": result.get("normalized_text_sha256"),
        "overlay_version": applied.get("version"),
        "annotation_rules": sorted(rules),
        "candidate_annotations": narrow,
        "interpretation": "Candidate markers only; no marker is unknown, not a validated zero.",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev-baseline", required=True)
    ap.add_argument("--full-baseline", required=True)
    ap.add_argument("--represented", required=True)
    ap.add_argument("--overlay", required=True)
    ap.add_argument("--synthetic-test", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()
    started = time.time()
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True, mode=0o700)

    overlay_path = Path(args.overlay)
    test_path = Path(args.synthetic_test)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(overlay_path.parent) + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.run([sys.executable, str(test_path)], check=True, env=env)
    overlay = load_overlay(overlay_path)

    dev_baseline = list(rows(args.dev_baseline))
    if len(dev_baseline) != 120 or len({x.get("exact_text_sha256") for x in dev_baseline}) != 120:
        raise RuntimeError("dev baseline is not the frozen unique 120")
    dev_counters = collections.Counter()
    dev_overlay = [narrow_apply(row, overlay, dev_counters) for row in dev_baseline]
    if dev_counters["baseline_failed"] or dev_counters["baseline_span_errors"]:
        raise RuntimeError("dev gate failed")
    dev_path = outdir / "DEV120_RELATION_OVERLAY_PRIVATE.jsonl"
    dump_jsonl(dev_path, dev_overlay)

    full_baseline = list(rows(args.full_baseline))
    full_shas = [x.get("exact_text_sha256") for x in full_baseline]
    if len(full_baseline) != 7635 or len(set(full_shas)) != 7635:
        raise RuntimeError("full baseline is not the frozen unique 7635")
    full_counters = collections.Counter()
    full_overlay = [narrow_apply(row, overlay, full_counters) for row in full_baseline]
    if full_counters["baseline_failed"] or full_counters["baseline_span_errors"]:
        raise RuntimeError("full baseline gate failed")
    full_path = outdir / "FULL7635_RELATION_OVERLAY_PRIVATE.jsonl"
    dump_jsonl(full_path, full_overlay)

    overlay_by_sha = {x["exact_text_sha256"]: x for x in full_overlay}
    represented = list(rows(args.represented))
    positions = [x.get("fixed_sample_position_1based") for x in represented]
    if len(represented) != 10000 or positions != list(range(1, 10001)):
        raise RuntimeError("represented binding is not ordered 1..10000")
    if {x.get("exact_text_sha256") for x in represented} != set(full_shas):
        raise RuntimeError("represented/full unique SHA sets differ")
    arm_by_sha = collections.defaultdict(set)
    unique_arm_denominator = collections.Counter()
    represented_arm_denominator = collections.Counter()
    represented_sha_count = collections.Counter()
    binding_rows = []
    for meta in represented:
        sha, arm = meta.get("exact_text_sha256"), meta.get("arm")
        if arm not in {"A", "B", "C"}:
            raise RuntimeError("invalid represented arm")
        arm_by_sha[sha].add(arm)
        represented_arm_denominator[arm] += 1
        represented_sha_count[sha] += 1
        overlay_row = overlay_by_sha[sha]
        binding_rows.append({
            "fixed_sample_position_1based": meta.get("fixed_sample_position_1based"),
            "exact_text_sha256": sha,
            "arm": arm,
            "unique_overlay_status": overlay_row["status"],
            "annotation_rules": overlay_row["annotation_rules"],
        })
    if any(len(arms) != 1 for arms in arm_by_sha.values()):
        raise RuntimeError("one exact SHA occurs across multiple arms")
    for sha, arms in arm_by_sha.items():
        unique_arm_denominator[next(iter(arms))] += 1
    binding_path = outdir / "FIXED10000_RELATION_OVERLAY_BINDING_PRIVATE.jsonl"
    dump_jsonl(binding_path, binding_rows)

    unique_rule_docs = collections.Counter()
    represented_rule_rows = collections.Counter()
    for row in full_overlay:
        sha = row["exact_text_sha256"]
        arm = next(iter(arm_by_sha[sha]))
        for rule in row["annotation_rules"]:
            unique_rule_docs[(arm, rule)] += 1
            represented_rule_rows[(arm, rule)] += represented_sha_count[sha]
    public_rows = []
    rules = sorted({rule for _, rule in unique_rule_docs})
    for arm in "ABC":
        for rule in rules:
            public_rows.append({
                "arm": arm,
                "annotation_rule": rule,
                "unique_document_count": unique_rule_docs[(arm, rule)],
                "unique_document_denominator": unique_arm_denominator[arm],
                "represented_posting_count": represented_rule_rows[(arm, rule)],
                "represented_posting_denominator": represented_arm_denominator[arm],
            })
    public_path = outdir / "RELATION_ANNOTATION_COUNTS_PUBLIC.csv"
    with open(public_path, "w", newline="", encoding="utf-8") as f:
        fields = ["arm", "annotation_rule", "unique_document_count", "unique_document_denominator", "represented_posting_count", "represented_posting_denominator"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(public_rows)

    outputs = [dev_path, full_path, binding_path, public_path]
    receipt = {
        "schema_version": "relation_overlay_run_receipt_v1",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "complete_candidate_markers_only",
        "job_id": os.environ.get("JOB_ID"),
        "host": socket.gethostname(),
        "elapsed_seconds": round(time.time() - started, 3),
        "model_calls": 0,
        "api_calls": 0,
        "baseline_sha256": {
            "dev120": digest(args.dev_baseline),
            "full7635": digest(args.full_baseline),
            "represented10000": digest(args.represented),
        },
        "code_sha256": {
            "overlay": digest(overlay_path),
            "runner": digest(Path(__file__)),
            "synthetic_test": digest(test_path),
        },
        "overlay_version": overlay.VERSION,
        "mapping": {
            "unique_rows": len(full_overlay),
            "represented_rows": len(binding_rows),
            "unique_sha_set_matches_represented": True,
            "represented_positions_ordered_1_to_10000": True,
            "one_arm_per_exact_sha": True,
            "unique_document_denominators": dict(sorted(unique_arm_denominator.items())),
            "represented_posting_denominators": dict(sorted(represented_arm_denominator.items())),
        },
        "dev_gate": {
            "rows": len(dev_overlay),
            "failed": dev_counters["baseline_failed"],
            "span_checks": dev_counters["baseline_span_checks"],
            "span_errors": dev_counters["baseline_span_errors"],
        },
        "full": {
            "rows": len(full_overlay),
            "failed": full_counters["baseline_failed"],
            "span_checks": full_counters["baseline_span_checks"],
            "span_errors": full_counters["baseline_span_errors"],
            "documents_with_no_candidate_marker": full_counters["no_candidate_marker"],
            "documents_with_candidate_marker": len(full_overlay) - full_counters["no_candidate_marker"],
            "annotation_counts": {rule: full_counters[("annotation", rule)] for rule in rules},
        },
        "outputs_sha256": {p.name: digest(p) for p in outputs},
        "boundaries": [
            "Outputs are deterministic candidate markers over immutable frozen evidence, not model inference or semantic gold.",
            "No candidate marker means unknown under this bounded overlay, not a validated zero or absence.",
            "The 10,000-row binding preserves sample positions without duplicating normalized or raw text.",
            "Public counts are unweighted fixed-sample descriptions by legacy sampling arm.",
        ],
    }
    receipt_path = outdir / "RELATION_OVERLAY_RUN_RECEIPT_PUBLIC.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "receipt": str(receipt_path)}, sort_keys=True))


if __name__ == "__main__":
    main()
