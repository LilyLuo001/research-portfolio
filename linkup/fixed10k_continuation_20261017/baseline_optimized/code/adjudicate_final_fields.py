#!/usr/bin/env python3
"""Apply the frozen pre-result field-adoption rules to final aggregate metrics.

Reads no text, record identifiers, membership lists, or model coefficients. The
only outputs are aggregate per-target/per-scope metrics and field decisions.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path


EXPECTED_RULES_SHA256 = "31f4207ac953d01863af4bb58e344883d73b134def3f890846cf744f05036039"
EXPECTED_RULES_VERSION = "one_time_pre_result_decision_20261023"
Z_95 = 1.959963984540054


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path):
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def atomic_json(path, value):
    path = Path(path)
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.chmod(temp, 0o644)
    os.replace(temp, path)


def wilson_lower(successes, total):
    if total <= 0:
        return 0.0
    p = successes / total
    z2 = Z_95 * Z_95
    center = p + z2 / (2 * total)
    margin = Z_95 * math.sqrt((p * (1 - p) + z2 / (4 * total)) / total)
    return (center - margin) / (1 + z2 / total)


def enriched_metrics(block):
    if not block or "confusion" not in block:
        return {
            "status": (block or {}).get("status", "not_evaluated"),
            "rows": int((block or {}).get("rows", 0)),
        }
    cm = block["confusion"]
    tn, fp, fn, tp = (int(cm[x]) for x in ("tn", "fp", "fn", "tp"))
    rows = tn + fp + fn + tp
    support_0, support_1 = tn + fp, fn + tp
    if int(block["class_0"]["support"]) != support_0 or int(block["class_1"]["support"]) != support_1:
        raise RuntimeError("metric support does not reconcile with confusion matrix")
    result = {
        "status": block.get("status", "evaluated"),
        "rows": rows,
        "confusion": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "class_0": dict(block["class_0"]),
        "class_1": dict(block["class_1"]),
        "macro_f1": block.get("macro_f1"),
        "predictive_accuracy": block.get("predictive_accuracy"),
        "true_positive_share": (support_1 / rows) if rows else None,
        "predicted_positive_share": ((fp + tp) / rows) if rows else None,
    }
    result["absolute_predicted_minus_reference_positive_share"] = (
        abs(result["predicted_positive_share"] - result["true_positive_share"]) if rows else None
    )
    result["class_0"]["wilson_95_lower_precision"] = wilson_lower(tn, tn + fn)
    result["class_0"]["wilson_95_lower_recall"] = wilson_lower(tn, tn + fp)
    result["class_1"]["wilson_95_lower_precision"] = wilson_lower(tp, tp + fp)
    result["class_1"]["wilson_95_lower_recall"] = wilson_lower(tp, tp + fn)
    return result


def metric_failures(metric, prefix, minimum_support, minimum_precision_recall,
                    maximum_share_gap, minimum_wilson=None):
    failures = []
    if not metric or "confusion" not in metric:
        return [prefix + ".not_evaluated"]
    for label in ("class_0", "class_1"):
        values = metric[label]
        if int(values["support"]) < minimum_support:
            failures.append(f"{prefix}.{label}.true_support<{minimum_support}")
        for name in ("precision", "recall"):
            if float(values[name]) < minimum_precision_recall:
                failures.append(f"{prefix}.{label}.{name}<{minimum_precision_recall}")
            if minimum_wilson is not None and float(values[f"wilson_95_lower_{name}"]) < minimum_wilson:
                failures.append(f"{prefix}.{label}.wilson95_lower_{name}<{minimum_wilson}")
    gap = metric["absolute_predicted_minus_reference_positive_share"]
    if gap is None or gap > maximum_share_gap:
        failures.append(f"{prefix}.absolute_predicted_minus_reference_positive_share>{maximum_share_gap}")
    return failures


def decide_target(name, report, rules):
    formal = rules["formal_adoption"]
    overall_rules = formal["overall_and_no_recorded_prior_exposure"]
    arm_rules = formal["each_existing_research_frame_arm"]
    overall = enriched_metrics(report.get("final_metrics"))
    subgroup_metrics = {key: enriched_metrics(value) for key, value in sorted(report.get("subgroups", {}).items())}
    failures = []
    if report.get("fit_status") != "fit":
        failures.append("target.fit_status!=fit")
    train_minimum = int(formal["training_min_each_class"])
    for label, key in (("class_0", "train_negative"), ("class_1", "train_positive")):
        if int(report.get(key, 0)) < train_minimum:
            failures.append(f"training.{label}.support<{train_minimum}")
    failures.extend(metric_failures(
        overall, "overall",
        int(overall_rules["minimum_each_true_class"]),
        float(overall_rules["minimum_precision_and_recall_each_class"]),
        float(overall_rules["maximum_absolute_predicted_minus_reference_positive_fraction"]),
        float(overall_rules["minimum_wilson_95_lower_precision_and_recall_each_class"]),
    ))
    no_exposure_name = "no_recorded_prior_exposure"
    failures.extend(metric_failures(
        subgroup_metrics.get(no_exposure_name), no_exposure_name,
        int(overall_rules["minimum_each_true_class"]),
        float(overall_rules["minimum_precision_and_recall_each_class"]),
        float(overall_rules["maximum_absolute_predicted_minus_reference_positive_fraction"]),
        float(overall_rules["minimum_wilson_95_lower_precision_and_recall_each_class"]),
    ))
    arm_names = sorted(k for k in subgroup_metrics if k.startswith("existing_frame_arm="))
    if not arm_names:
        failures.append("existing_frame_arms.missing")
    for arm_name in arm_names:
        failures.extend(metric_failures(
            subgroup_metrics[arm_name], arm_name,
            int(arm_rules["minimum_each_true_class"]),
            float(arm_rules["minimum_precision_and_recall_each_class"]),
            float(arm_rules["maximum_absolute_predicted_minus_reference_positive_fraction"]),
        ))
    candidate_failures = []
    if report.get("fit_status") != "fit":
        candidate_failures.append("target.fit_status!=fit")
    if "confusion" not in overall:
        candidate_failures.append("overall.not_evaluated")
    else:
        for label in ("class_0", "class_1"):
            values = overall[label]
            if int(values["support"]) < 20:
                candidate_failures.append(f"overall.{label}.true_support<20")
            for metric_name in ("precision", "recall"):
                if float(values[metric_name]) < 0.60:
                    candidate_failures.append(f"overall.{label}.{metric_name}<0.6")
    numeric_formal_pass = not failures
    if numeric_formal_pass:
        decision = "eligible_pending_execution"
        decision_reason = "all frozen numeric gates pass; exact candidate filter exists; deployment adapter and independent sidecar execution remain pending"
    elif not candidate_failures:
        decision = "candidate_only"
        decision_reason = "candidate floor passes but one or more frozen formal gates fail"
    else:
        decision = "not_adopted"
        decision_reason = "candidate floor, fit, or support requirement fails"
    return {
        "target": name,
        "decision": decision,
        "decision_reason": decision_reason,
        "fit_status": report.get("fit_status", "missing"),
        "training": {
            "rows": int(report.get("train_rows", 0)),
            "class_0_support": int(report.get("train_negative", 0)),
            "class_1_support": int(report.get("train_positive", 0)),
        },
        "evaluation": {
            "eligible_rows": int(report.get("final_eligible_rows", 0)),
            "class_0_support": int(report.get("final_negative", 0)),
            "class_1_support": int(report.get("final_positive", 0)),
            "without_eligible_reference": int(report.get("final_without_eligible_reference", 0)),
            "reserved_prior_holdout_rows": int(report.get("reserved_prior_holdout_rows", 0)),
        },
        "overall": overall,
        "subgroups": subgroup_metrics,
        "numeric_formal_gates_pass": numeric_formal_pass,
        "failed_formal_gates": failures,
        "candidate_floor_pass": not candidate_failures,
        "failed_candidate_floor_gates": candidate_failures,
        "scope_gate": {
            "candidate_filter": "existing_reproducible_exact_filter",
            "deployment_adapter": "pending",
            "independent_sidecar_execution": "pending",
        },
    }


def csv_rows(decisions):
    for item in decisions:
        scopes = [("overall", "overall", item["overall"])]
        scopes.extend(("subgroup", name, metric) for name, metric in item["subgroups"].items())
        for scope_type, scope_name, metric in scopes:
            row = {
                "target": item["target"], "decision": item["decision"],
                "numeric_formal_gates_pass": item["numeric_formal_gates_pass"],
                "candidate_floor_pass": item["candidate_floor_pass"],
                "fit_status": item["fit_status"], "scope_type": scope_type, "scope_name": scope_name,
                "train_class_0_support": item["training"]["class_0_support"],
                "train_class_1_support": item["training"]["class_1_support"],
                "metric_status": metric.get("status"), "rows": metric.get("rows", 0),
                "failed_formal_gates": ";".join(item["failed_formal_gates"]),
                "failed_candidate_floor_gates": ";".join(item["failed_candidate_floor_gates"]),
            }
            cm = metric.get("confusion", {})
            for key in ("tn", "fp", "fn", "tp"):
                row[key] = cm.get(key)
            for label in ("class_0", "class_1"):
                for key in ("support", "precision", "recall", "f1", "wilson_95_lower_precision", "wilson_95_lower_recall"):
                    row[f"{label}_{key}"] = metric.get(label, {}).get(key)
            for key in ("true_positive_share", "predicted_positive_share", "absolute_predicted_minus_reference_positive_share"):
                row[key] = metric.get(key)
            yield row


def main():
    os.umask(0o022)
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation", required=True)
    parser.add_argument("--rules", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    if sha256(args.rules) != EXPECTED_RULES_SHA256:
        raise RuntimeError("adoption rules differ from the frozen pre-result rules")
    rules = load_json(args.rules)
    if rules.get("version") != EXPECTED_RULES_VERSION:
        raise RuntimeError("unexpected adoption-rules version")
    evaluation = load_json(args.evaluation)
    model = evaluation.get("private_model") or {}
    if not model.get("path") or not model.get("sha256"):
        raise RuntimeError("evaluation lacks private model reference")
    if sha256(model["path"]) != model["sha256"]:
        raise RuntimeError("private model hash differs from final evaluation")
    targets = evaluation.get("targets") or {}
    if not targets:
        raise RuntimeError("evaluation contains no target reports")
    decisions = [decide_target(name, targets[name], rules) for name in sorted(targets)]
    counts = {name: sum(x["decision"] == name for x in decisions)
              for name in ("eligible_pending_execution", "candidate_only", "not_adopted")}
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "FINAL_FIELD_ADJUDICATION_PUBLIC.json"
    csv_path = output_dir / "FINAL_FIELD_ADJUDICATION_PUBLIC.csv"
    if json_path.exists() or csv_path.exists():
        raise RuntimeError("final adjudication output already exists")
    result = {
        "version": "fixed10k-final-field-adjudication-v1",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "complete",
        "rules": {"version": rules["version"], "sha256": EXPECTED_RULES_SHA256},
        "evaluation": {"sha256": sha256(args.evaluation), "job_id": evaluation.get("job_id")},
        "private_model_reference": {"path": model["path"], "sha256": model["sha256"]},
        "decision_counts": counts,
        "decisions": decisions,
        "unsupported_tasks": [{"task": task, "decision": "not_adopted", "reason": "unimplemented_task"}
                              for task in rules["unsupported_tasks"]],
        "deployment_scope": {
            "candidate_filter": "existing reproducible exact 69-cell technology-screened candidate filter",
            "deployment_adapter": "pending",
            "independent_sidecar_execution": "pending",
            "numeric_pass_interpretation": "eligible_pending_execution; not already in production",
        },
        "claim_boundary": rules["permitted_use"],
        "reference_boundary": rules["reference"],
        "fixed_stop": rules["fixed_stop"],
    }
    atomic_json(json_path, result)
    rows = list(csv_rows(decisions))
    temp = Path(str(csv_path) + ".tmp")
    with temp.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    os.chmod(temp, 0o644)
    os.replace(temp, csv_path)
    print(json.dumps({"status": "complete", "targets": len(decisions), "decision_counts": counts,
                      "json": str(json_path), "csv": str(csv_path)}, sort_keys=True))


if __name__ == "__main__":
    main()
