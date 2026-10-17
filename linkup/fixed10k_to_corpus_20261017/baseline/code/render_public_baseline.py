#!/usr/bin/env python3
"""Render the aggregate-only public baseline receipt and 27-row metric table."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path


ROOT = Path("/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline")
SOURCE = ROOT / "results" / "BASELINE_RESULT_FINAL.json"
PUBLIC_JSON = ROOT / "results" / "BASELINE_RESULTS_PUBLIC.json"
PUBLIC_MD = ROOT / "results" / "BASELINE_RESULTS_PUBLIC.md"
CORPUS_ROWS = 204774035


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_text(path, text):
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.chmod(str(tmp), 0o600); os.replace(str(tmp), str(path))


def f(value):
    return "NA" if value is None else ("%.4f" % value)


def main():
    r = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = []
    for target, value in sorted(r["targets"].items()):
        model = value.get("model_holdout_metrics") or {}
        majority = value.get("train_majority_holdout_metrics") or {}
        c0, c1, cm = model.get("class_0", {}), model.get("class_1", {}), model.get("confusion", {})
        rows.append({
            "target": target,
            "fit_status": value["fit_status"],
            "evaluation_status": value["evaluation_status"],
            "train_support_0": value["train"]["class_0"], "train_support_1": value["train"]["class_1"],
            "holdout_support_0": value["holdout"]["class_0"], "holdout_support_1": value["holdout"]["class_1"],
            "tn": cm.get("tn"), "fp": cm.get("fp"), "fn": cm.get("fn"), "tp": cm.get("tp"),
            "class_0_precision": c0.get("precision"), "class_0_recall": c0.get("recall"), "class_0_f1": c0.get("f1"),
            "class_1_precision": c1.get("precision"), "class_1_recall": c1.get("recall"), "class_1_f1": c1.get("f1"),
            "macro_f1": model.get("macro_f1"), "predictive_accuracy": model.get("predictive_accuracy"),
            "majority_predicted_class": majority.get("predicted_class"), "majority_macro_f1": majority.get("macro_f1"),
            "majority_predictive_accuracy": majority.get("predictive_accuracy"),
        })
    speed = r["real_inference"]["rows_per_second"]
    seconds = CORPUS_ROWS / speed
    public = {
        "version": r["version"], "status": r["status"], "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "dependency_probe": {"job_id": "46770224", "state": "COMPLETED", "exit_code": "0:0"},
        "training_inference_job": {"job_id": r["scheduler"]["job_id"], "state": "COMPLETED", "exit_code": "0:0", "partition": "wzhdtest", "requested_cpus": 8, "requested_memory_gib": 16, "required_queue_gres": "dcu:Hygon:1", "compute": "CPU", "elapsed": "00:10:51", "total_cpu": "00:10:46.646", "max_rss_kib": 1284432},
        "runtime": r["runtime"], "training_runtime_code": r["training_runtime_code"], "inputs": r["inputs"],
        "artifacts": r["artifacts"], "label_policy": r["label_policy"], "split": r["split"], "estimator": r["estimator"],
        "prediction_semantics": r["prediction_semantics"], "supported_output_scope": r["supported_output_scope"], "unsupported": r["unsupported"],
        "real_inference": r["real_inference"], "target_metrics": rows,
        "conditional_single_job_projection": {
            "corpus_rows": CORPUS_ROWS, "observed_rows_per_second": speed, "seconds": seconds, "days": seconds / 86400.0,
            "conditions": "One comparable scheduled job; same 27 targets, schema, text-length mix, storage throughput and serial per-target vectorization; model loading excluded as in measured timer; no claim of linear scaling or authorized full-corpus inference.",
        },
        "run_command": "sbatch /work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline/code/wz_train_evaluate_infer.sbatch",
        "claim_boundary": r["claim_boundary"],
    }
    atomic_text(PUBLIC_JSON, json.dumps(public, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    lines = [
        "# CPU 监督文本 baseline：固定 holdout 与真实分片结果", "",
        "作业 46770303 在 WZ `wzhdtest` 完成（0:0）。模型仅在固定训练 contexts 上拟合，holdout 不参与词表或模型拟合，也未用于调参。指标是对既有兼容语义标签的预测评估，不称为人工准确率。", "",
        "真实输入为字典序第一份 LinkUp parquet（总 124,855 行）的原序前 20,000 行；20,000 条正文均有效。读取原文、冻结 normalizer、27 个目标逐模型 vectorize/predict、writer close/原子改名共 %.3f 秒，即 %.3f 行/秒。模型已在内存，计时不含 pickle 加载。" % (r["real_inference"]["elapsed_seconds"], speed), "",
        "| target | fit/eval | train 0/1 | holdout 0/1 | TN/FP/FN/TP | class0 P/R/F1 | class1 P/R/F1 | macro F1 | majority class/macro F1 |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for x in rows:
        lines.append("| %s | %s/%s | %d/%d | %d/%d | %s/%s/%s/%s | %s/%s/%s | %s/%s/%s | %s | %s/%s |" % (
            x["target"], x["fit_status"], x["evaluation_status"], x["train_support_0"], x["train_support_1"],
            x["holdout_support_0"], x["holdout_support_1"], x["tn"], x["fp"], x["fn"], x["tp"],
            f(x["class_0_precision"]), f(x["class_0_recall"]), f(x["class_0_f1"]),
            f(x["class_1_precision"]), f(x["class_1_recall"]), f(x["class_1_f1"]), f(x["macro_f1"]),
            x["majority_predicted_class"], f(x["majority_macro_f1"])))
    lines += [
        "", "`insufficient_holdout_class_support` 表示 holdout 任一类别少于 5；原始混淆矩阵与指标仍保留作透明记录，不能解释为语义通过。", "",
        "支持范围只含 27 个二元 presence 目标。不支持经验强度（必需/优先）、经验条件性与逻辑分支、字面数值年限、开放命名对象、逐字证据及资格分支关系重建。LinearSVC 仅写二元类别；margin 不是概率且未写出。", "",
        "若把实测 %.3f 行/秒机械用于 204,774,035 行，单个同类作业约 %.2f 天。该数仅在相同 27 目标、schema、文本长度分布、存储吞吐、逐目标串行 vectorize 且同样不计模型加载时成立；没有授权全库推断，也不主张线性扩展。" % (speed, seconds / 86400.0), "",
        "私有模型：`%s`" % r["artifacts"]["private_model"]["path"], "",
        "私有 sidecar：`%s`" % r["artifacts"]["private_prediction_sidecar"]["path"], "",
        "复跑：`%s`" % public["run_command"], "",
    ]
    atomic_text(PUBLIC_MD, "\n".join(lines))
    print(json.dumps({"status": "pass", "targets": len(rows), "public_json": str(PUBLIC_JSON), "public_json_sha256": sha_file(PUBLIC_JSON), "public_md": str(PUBLIC_MD), "public_md_sha256": sha_file(PUBLIC_MD)}, sort_keys=True))


if __name__ == "__main__":
    main()
