#!/usr/bin/env python3
"""Train the locked TF-IDF/LinearSVC baseline and run one bounded real shard.

The program consumes only complete accepted labels from the final ledger, keeps
the deterministic holdout out of all fitting, and writes predictions to a new
private sidecar.  It does not modify the frame, ledger, or semantic queue.
"""
import collections
import datetime as dt
import glob
import hashlib
import importlib.util
import json
import os
import pickle
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import scipy
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
from sklearn.svm import LinearSVC


VERSION = "fixed10k-cpu-tfidf-linearsvc-baseline-v1"
ROOT = Path("/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline")
LEDGER = Path("/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/batch001/final/FIELD_PROVENANCE_LEDGER_PRIVATE.jsonl")
FRAME = Path("/work/home/lilysharp/private/next_stage_20261004/text_handoff_20261007/verified_fixed10000/MERGED_FIXED10000_EXACT_TEXT_PRIVATE.parquet")
NORMALIZER = Path("/work/home/lilysharp/private/formal800_20261012/code/frozen_rulefirst_v1_2/legacy_v5_frozen.py")
SHARD_ROOT = Path("/work/home/lilysharp/dewey_remaining_descriptions/data/linkup_job_descriptions")
MODEL_OUT = ROOT / "artifacts" / "tfidf_linearsvc_holdout_frozen.pkl"
SIDECAR_OUT = ROOT / "sidecar" / "first_linkup_shard_first20000_predictions.parquet"
RESULT_OUT = ROOT / "results" / "BASELINE_RESULT.json"
EXPECTED_LEDGER_SHA = "435c7262700a42c4571160e772158f1344a58d39ee387be4436172b8053f5403"
EXPECTED_FRAME_SHA = "e6083ccacbdfe5a64548168a22ceb11fdce9d6d4bb89943a11f4bae54a17de35"
ALLOWED_SOURCES = {"formal800_final", "fixed10k_batch001"}
COMPLETE = {"known", "not_applicable"}
EXP = ("general_work", "occupation_task", "industry_domain", "tool_specific")
ENTRY = ("explicit_no_experience", "explicit_new_graduate", "current_student_internship", "explicit_junior_or_entry_label")
RESP = ("independent_judgment", "client_ownership", "people_supervision", "training_mentoring")
TECH_FAMILY = ("traditional_software_system", "predictive_ml_ai", "generative_ai")
TECH_ROLE = ("develop_technology", "implement_deploy_technology", "use_tool_for_work", "background_mention")
TARGETS = (
    tuple("experience_presence." + x for x in EXP)
    + tuple("entry_presence." + x for x in ENTRY)
    + tuple("strict_current_duty." + x for x in RESP)
    + tuple("technology_family." + x for x in TECH_FAMILY)
    + tuple("technology_family_role.%s.%s" % (f, r) for f in TECH_FAMILY for r in TECH_ROLE)
)
UNSUPPORTED = ("literal_numeric_years", "open_ended_named_object", "verbatim_evidence", "qualification_branch_relation_reconstruction")


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_json_atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(str(tmp), 0o600)
    os.replace(str(tmp), str(path))


def load_normalizer(path):
    spec = importlib.util.spec_from_file_location("baseline_frozen_normalizer", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "_normalize_with_flags"):
        raise RuntimeError("frozen normalizer lacks _normalize_with_flags")
    return module


def normalize(module, text):
    result = module._normalize_with_flags(text)
    value = result[0] if isinstance(result, tuple) else result
    if not isinstance(value, str):
        raise RuntimeError("normalizer returned non-string")
    return value


def accepted_source(row):
    sources = {x.get("source") for x in row.get("provenance", [])}
    return bool(sources & ALLOWED_SOURCES) and not bool(sources - ALLOWED_SOURCES)


def value_for_target(family, status, value, target):
    if status == "not_applicable":
        return 0
    if family == "experience_object":
        key = target.split(".", 1)[1]
        state = value.get(key)
        if state not in ("present", "not_mentioned"):
            raise RuntimeError("unexpected complete experience outcome: %r" % state)
        return int(state == "present")
    if family == "entry_wording_and_scope":
        key = target.split(".", 1)[1]
        state = value.get("outcomes", {}).get(key)
        if state not in ("present", "not_mentioned"):
            raise RuntimeError("unexpected complete entry outcome: %r" % state)
        return int(state == "present")
    if family == "current_responsibility_subject_and_relation":
        key = target.split(".", 1)[1]
        items = value.get("items", [])
        return int(any(x.get("dimension") == key and x.get("subject") == "advertised_worker" and x.get("relation") == "current_duty" for x in items))
    if family == "technology_category_and_role":
        items = value.get("items", [])
        parts = target.split(".")
        if parts[0] == "technology_family":
            return int(any(x.get("family") == parts[1] for x in items))
        return int(any(x.get("family") == parts[1] and x.get("role") == parts[2] for x in items))
    raise RuntimeError("unsupported family")


def target_family(target):
    if target.startswith("experience_presence."):
        return "experience_object"
    if target.startswith("entry_presence."):
        return "entry_wording_and_scope"
    if target.startswith("strict_current_duty."):
        return "current_responsibility_subject_and_relation"
    return "technology_category_and_role"


def load_labels():
    values = collections.defaultdict(lambda: collections.defaultdict(set))
    accepted_rows = collections.Counter()
    with open(LEDGER, encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            family = row["field_family"]
            status = row["status"]
            if status not in COMPLETE or not accepted_source(row):
                continue
            context = row["normalized_context_sha256"]
            for target in TARGETS:
                if target_family(target) != family:
                    continue
                label = value_for_target(family, status, row.get("structured_value") or {}, target)
                values[target][context].add(label)
            accepted_rows[(family, status)] += 1
    labels = {}
    for target in TARGETS:
        labels[target] = {}
        for context, observed in values[target].items():
            if len(observed) != 1:
                raise RuntimeError("inconsistent duplicate-context label for %s" % target)
            labels[target][context] = next(iter(observed))
    return labels, accepted_rows


def load_context_text(normalizer, needed_contexts):
    table = pq.read_table(FRAME, columns=["exact_text_sha256", "original_text"])
    raw_seen = {}
    result = {}
    for raw_sha, original in zip(table["exact_text_sha256"].to_pylist(), table["original_text"].to_pylist()):
        if raw_sha in raw_seen:
            continue
        normalized = normalize(normalizer, original or "")
        context = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        raw_seen[raw_sha] = context
        if context in needed_contexts:
            previous = result.get(context)
            if previous is not None and previous != normalized:
                raise RuntimeError("SHA collision or inconsistent normalized text")
            result[context] = normalized
    missing = needed_contexts - set(result)
    if missing:
        raise RuntimeError("eligible ledger contexts missing from frozen frame: %d" % len(missing))
    return result


def is_holdout(context):
    digest = hashlib.sha256(("baseline-holdout-v1|" + context).encode("ascii")).hexdigest()
    return int(digest, 16) % 5 == 0


def metric_block(y_true, y_pred):
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    precision, recall, f1, support = precision_recall_fscore_support(y_true, y_pred, labels=[0, 1], zero_division=0)
    return {
        "confusion": {"tn": int(cm[0, 0]), "fp": int(cm[0, 1]), "fn": int(cm[1, 0]), "tp": int(cm[1, 1])},
        "class_0": {"support": int(support[0]), "precision": float(precision[0]), "recall": float(recall[0]), "f1": float(f1[0])},
        "class_1": {"support": int(support[1]), "precision": float(precision[1]), "recall": float(recall[1]), "f1": float(f1[1])},
        "macro_f1": float((f1[0] + f1[1]) / 2.0),
        "predictive_accuracy": float(np.mean(np.asarray(y_true) == np.asarray(y_pred))),
    }


def select_real_shard():
    paths = sorted(glob.glob(str(SHARD_ROOT / "**" / "*.parquet"), recursive=True))
    if not paths:
        raise RuntimeError("no LinkUp parquet shard exists")
    return Path(paths[0])


def read_first_rows(path, limit):
    parquet = pq.ParquetFile(path)
    batches = []
    have = 0
    for batch in parquet.iter_batches(batch_size=min(8192, limit), columns=["JOB_HASH", "DESCRIPTION"]):
        take = min(len(batch), limit - have)
        batches.append(batch.slice(0, take))
        have += take
        if have == limit:
            break
    if not batches:
        return pa.table({"JOB_HASH": pa.array([], type=pa.string()), "DESCRIPTION": pa.array([], type=pa.string())})
    return pa.Table.from_batches(batches)


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    for path in (MODEL_OUT.parent, SIDECAR_OUT.parent, RESULT_OUT.parent):
        path.mkdir(parents=True, exist_ok=True)
    os.umask(0o077)
    ledger_sha = sha_file(LEDGER)
    frame_sha = sha_file(FRAME)
    if ledger_sha != EXPECTED_LEDGER_SHA or frame_sha != EXPECTED_FRAME_SHA:
        raise RuntimeError("frozen baseline input SHA mismatch")
    normalizer = load_normalizer(NORMALIZER)
    labels, accepted_rows = load_labels()
    needed = set().union(*(set(x) for x in labels.values()))
    texts = load_context_text(normalizer, needed)
    models = {}
    results = {}
    for target in TARGETS:
        train_contexts = sorted(c for c in labels[target] if not is_holdout(c))
        hold_contexts = sorted(c for c in labels[target] if is_holdout(c))
        y_train = [labels[target][c] for c in train_contexts]
        y_hold = [labels[target][c] for c in hold_contexts]
        train_counts = collections.Counter(y_train)
        hold_counts = collections.Counter(y_hold)
        base = {
            "eligible_unique_contexts": len(labels[target]),
            "train": {"rows": len(y_train), "class_0": train_counts[0], "class_1": train_counts[1]},
            "holdout": {"rows": len(y_hold), "class_0": hold_counts[0], "class_1": hold_counts[1]},
            "fit_status": "not_fit",
            "evaluation_status": "not_evaluated",
        }
        if min(train_counts[0], train_counts[1]) < 5:
            base["fit_status"] = "insufficient_training_class_support"
            results[target] = base
            continue
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=0.98, max_features=100000, sublinear_tf=True)
        x_train = vectorizer.fit_transform([texts[c] for c in train_contexts])
        model = LinearSVC(C=1.0, class_weight="balanced", random_state=20261017)
        model.fit(x_train, y_train)
        models[target] = {"vectorizer": vectorizer, "classifier": model}
        base["fit_status"] = "fit"
        base["vocabulary_features"] = int(len(vectorizer.vocabulary_))
        if not y_hold:
            base["evaluation_status"] = "insufficient_holdout_class_support"
            results[target] = base
            continue
        pred = model.predict(vectorizer.transform([texts[c] for c in hold_contexts])).astype(int).tolist()
        majority = 1 if train_counts[1] > train_counts[0] else 0
        base["evaluation_status"] = "evaluated" if min(hold_counts[0], hold_counts[1]) >= 5 else "insufficient_holdout_class_support"
        base["model_holdout_metrics"] = metric_block(y_hold, pred)
        base["train_majority_holdout_metrics"] = dict(metric_block(y_hold, [majority] * len(y_hold)), predicted_class=majority)
        results[target] = base

    artifact = {
        "version": VERSION,
        "split": "sha256('baseline-holdout-v1|'+normalized_context_sha256) mod 5; residue 0 is holdout",
        "targets": TARGETS,
        "models": models,
        "input_sha256": {"ledger": ledger_sha, "frame": frame_sha, "normalizer": sha_file(NORMALIZER)},
    }
    model_tmp = Path(str(MODEL_OUT) + ".tmp")
    with open(model_tmp, "wb") as stream:
        pickle.dump(artifact, stream, protocol=4)
    os.chmod(str(model_tmp), 0o600)
    os.replace(str(model_tmp), str(MODEL_OUT))

    shard = select_real_shard()
    timer_start = time.perf_counter()
    real = read_first_rows(shard, 20000)
    descriptions = [normalize(normalizer, x or "") for x in real["DESCRIPTION"].to_pylist()]
    output = {
        "source_row_0based": pa.array(range(len(real)), type=pa.int64()),
        "JOB_HASH": real["JOB_HASH"],
    }
    for target in TARGETS:
        if target in models:
            pair = models[target]
            prediction = pair["classifier"].predict(pair["vectorizer"].transform(descriptions)).astype(np.int8)
            output[target] = pa.array(prediction, type=pa.int8())
        else:
            output[target] = pa.nulls(len(real), type=pa.int8())
    for name in UNSUPPORTED:
        output["unsupported_status." + name] = pa.array(["not_produced_unsupported"] * len(real), type=pa.string())
    sidecar_tmp = Path(str(SIDECAR_OUT) + ".tmp")
    pq.write_table(pa.table(output), sidecar_tmp, compression="snappy")
    os.chmod(str(sidecar_tmp), 0o600)
    os.replace(str(sidecar_tmp), str(SIDECAR_OUT))
    elapsed = time.perf_counter() - timer_start
    row_count = len(real)
    report = {
        "version": VERSION,
        "status": "pass",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "scheduler": {"job_id": os.environ.get("SLURM_JOB_ID"), "host": platform.node(), "cpus": os.environ.get("SLURM_CPUS_PER_TASK")},
        "runtime": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__, "sklearn": sklearn.__version__, "pyarrow": pa.__version__},
        "inputs": {
            "ledger": {"path": str(LEDGER), "sha256": ledger_sha},
            "frame": {"path": str(FRAME), "sha256": frame_sha},
            "normalizer": {"path": str(NORMALIZER), "sha256": sha_file(NORMALIZER)},
            "real_shard": {"path": str(shard), "sha256": sha_file(shard), "selection": "lexicographically_first_existing_recursive_parquet"},
        },
        "label_policy": {"allowed_sources": sorted(ALLOWED_SOURCES), "accepted_statuses": sorted(COMPLETE), "unit": "unique_frozen_normalized_complete_context", "accepted_ledger_rows_by_family_status": [{"family": k[0], "status": k[1], "rows": v} for k, v in sorted(accepted_rows.items())]},
        "split": {"rule": "sha256('baseline-holdout-v1|'+normalized_context_sha256) mod 5", "holdout_residue": 0, "no_refit_after_holdout": True},
        "estimator": {"tfidf": {"analyzer": "word", "ngram_range": [1, 2], "min_df": 2, "max_df": 0.98, "max_features": 100000, "sublinear_tf": True}, "linear_svc": {"C": 1.0, "class_weight": "balanced", "random_state": 20261017}},
        "prediction_semantics": "binary class predictions only; LinearSVC margins are not probabilities and are not written",
        "targets": results,
        "artifacts": {"private_model": {"path": str(MODEL_OUT), "sha256": sha_file(MODEL_OUT), "bytes": MODEL_OUT.stat().st_size}, "private_prediction_sidecar": {"path": str(SIDECAR_OUT), "sha256": sha_file(SIDECAR_OUT), "bytes": SIDECAR_OUT.stat().st_size}},
        "real_inference": {"rows": row_count, "limit": 20000, "timer_scope": "raw DESCRIPTION parquet read, frozen normalization, vectorization, prediction, and sidecar writer close/atomic rename", "includes_model_load": False, "model_state": "freshly_fitted_models_already_in_memory", "elapsed_seconds": elapsed, "rows_per_second": (row_count / elapsed if elapsed else None), "trained_targets_predicted": len(models), "sidecar_only": True},
        "unsupported": list(UNSUPPORTED),
        "claim_boundary": "fixed holdout predictive evaluation against accepted semantic labels; not human accuracy, population prevalence, full-corpus inference, or semantic certification",
    }
    write_json_atomic(RESULT_OUT, report)
    print(json.dumps({"status": "pass", "job_id": os.environ.get("SLURM_JOB_ID"), "result": str(RESULT_OUT), "rows": row_count, "rows_per_second": report["real_inference"]["rows_per_second"], "trained_targets": len(models)}, sort_keys=True))


if __name__ == "__main__":
    main()
