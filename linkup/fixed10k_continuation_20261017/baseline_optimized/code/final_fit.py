#!/usr/bin/env python3
"""One fixed final baseline fit, only after the existing reference queue closes.

Reuses the frozen baseline target adapter and hyperparameters. No semantic
model, sampling, imputation, model selection, or corpus inference is performed.
Run freeze, then fit, in the authorized cloud environment. All artifacts private.
"""
import argparse
import collections
import datetime as dt
import hashlib
import importlib.util
import json
import os
import pickle
import platform
import re
import time
from pathlib import Path

HOLDOUT_SHA = "5d37e0d5840d99f6d9f52d7cc6e2573bd0ca89d7bc948d121a7c9684b36e5de1"
FRAME_SHA = "e6083ccacbdfe5a64548168a22ceb11fdce9d6d4bb89943a11f4bae54a17de35"


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rows(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def dump(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.chmod(str(tmp), 0o600)
    os.replace(str(tmp), str(path))


def module(path):
    spec = importlib.util.spec_from_file_location("frozen_presence_baseline", path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def compatible(row):
    sources = {x.get("source", "") for x in row.get("provenance", [])}
    return bool(sources) and all(
        s == "formal800_final" or bool(re.fullmatch(r"fixed10k_batch(?:00[1-9]|0[1-6][0-9])", s))
        for s in sources
    )


def memberships(legacy, ledger, holdout, isolated):
    values = collections.defaultdict(lambda: collections.defaultdict(set))
    excluded = collections.Counter()
    exposure = set()
    for row in ledger:
        context = row["normalized_context_sha256"]
        if row.get("historical_development_evaluation_exposure"):
            exposure.add(context)
        if context in isolated:
            excluded["isolated_source_ad_field_rows"] += 1
            continue
        if row["status"] not in legacy.COMPLETE or not compatible(row):
            excluded["not_complete_compatible_reference_ad_field_rows"] += 1
            continue
        for target in legacy.TARGETS:
            if legacy.target_family(target) == row["field_family"]:
                value = legacy.value_for_target(row["field_family"], row["status"], row.get("structured_value") or {}, target)
                values[target][context].add(value)
    output = {}
    for target in legacy.TARGETS:
        labels = {}
        for context, observed in values[target].items():
            if len(observed) != 1:
                raise RuntimeError("conflicting completed reference labels: " + target)
            labels[context] = next(iter(observed))
        # Keep ALL members of the original hash holdout out of ALL targets,
        # including previous holdout contexts outside the final 1,331 set.
        train = sorted(c for c in labels if c not in holdout and not legacy.is_holdout(c))
        final = sorted(c for c in labels if c in holdout)
        reserved = sorted(c for c in labels if c not in holdout and legacy.is_holdout(c))
        output[target] = {
            "train": [[c, labels[c]] for c in train],
            "final": [[c, labels[c]] for c in final],
            "previous_holdout_reserved_not_final": reserved,
        }
    return output, sorted(exposure & holdout), dict(excluded)


def freeze(a):
    dest = Path(a.output)
    if dest.exists():
        raise RuntimeError("frozen final input manifest already exists")
    receipt = json.loads(Path(a.receipt).read_text(encoding="utf-8"))
    if receipt.get("status") != "pass" or receipt.get("record_batch", {}).get("batch_number") != 69:
        raise RuntimeError("reference continuation must reach its existing final Batch069")
    if rows(a.queue) or receipt["counts"]["remaining_work_contexts"] != 0:
        raise RuntimeError("processable reference queue is not closed")
    if digest(a.ledger) != receipt["outputs"]["private_ledger_sha256"] or digest(a.queue) != receipt["outputs"]["private_queue_sha256"]:
        raise RuntimeError("latest ledger/queue do not match closure receipt")
    if digest(a.holdout) != HOLDOUT_SHA or digest(a.frame) != FRAME_SHA:
        raise RuntimeError("frozen frame or holdout changed")
    holdout = {r["normalized_context_sha256"] for r in rows(a.holdout)}
    if len(holdout) != 1331:
        raise RuntimeError("existing holdout membership mismatch")
    isolated = {r["normalized_context_sha256"] for r in rows(a.isolation)}
    if len(isolated) != receipt["counts"]["blocked_contexts"]:
        raise RuntimeError("isolated contexts disagree with closure receipt")
    legacy = module(a.legacy)
    member, exposed, exclusions = memberships(legacy, rows(a.ledger), holdout, isolated)
    members_path = dest.parent / "FINAL_TRAIN_EVALUATION_MEMBERSHIP_PRIVATE.json"
    if members_path.exists():
        raise RuntimeError("private membership manifest already exists")
    dump(members_path, {"targets": member, "prior_exposed_final_contexts": exposed})
    names = ("ledger", "queue", "receipt", "holdout", "frame", "normalizer", "legacy", "isolation")
    inputs = {n: {"path": getattr(a, n), "sha256": digest(getattr(a, n))} for n in names}
    inputs["memberships"] = {"path": str(members_path), "sha256": digest(members_path)}
    inputs["runner"] = {"path": str(Path(__file__).resolve()), "sha256": digest(__file__)}
    dump(dest, {
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "inputs": inputs, "reference_queue_closed": True,
        "isolated_contexts_unfinished_and_excluded": len(isolated),
        "final_holdout_contexts": len(holdout), "prior_exposed_final_contexts": len(exposed),
        "membership_policy": "existing hash holdout retained; all 1331 final contexts excluded from every training target",
        "reference_policy": "only known/not_applicable Formal800 or direct fixed10k Batch001-069 reference labels; no rule candidates or predictions",
        "excluded_ad_field_rows": exclusions,
        "group_policy": "existing fixed10k frame arm values; unique normalized contexts may occur in several arms; counts are not additive",
        "selection_policy": "fixed original TF-IDF/LinearSVC settings; no search, tuning, or selection using final evaluation",
        "unsupported": ["years_binding", "required_preferred", "conditional_branches", "responsibility_relation_reconstruction", "verbatim_evidence"],
    })


def metrics(legacy, truth, pred):
    if not truth:
        return {"status": "no_eligible_reference", "rows": 0}
    result = legacy.metric_block(truth, pred)
    result.update(rows=len(truth), true_positive_share=sum(truth) / len(truth), predicted_positive_share=sum(pred) / len(pred),
                  status="evaluated" if min(truth.count(0), truth.count(1)) >= 5 else "limited_class_support")
    return result


def fit(a):
    import pyarrow.parquet as pq
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.svm import LinearSVC
    root = Path(a.output)
    root.mkdir(parents=True, exist_ok=True)
    freeze_obj = json.loads(Path(a.freeze).read_text(encoding="utf-8"))
    inputs = freeze_obj["inputs"]
    for name, item in inputs.items():
        if digest(item["path"]) != item["sha256"]:
            raise RuntimeError("frozen input changed: " + name)
    if digest(__file__) != inputs["runner"]["sha256"]:
        raise RuntimeError("runner differs from frozen code")
    # One run per frozen input; execution failures remain visible for diagnosis.
    (root / "FIXED_FINAL_FIT_STARTED").mkdir()
    start = time.perf_counter()
    legacy = module(inputs["legacy"]["path"])
    members = json.loads(Path(inputs["memberships"]["path"]).read_text(encoding="utf-8"))
    exposed = set(members["prior_exposed_final_contexts"])
    wanted = {c for block in members["targets"].values() for split in ("train", "final") for c, _ in block[split]}
    normalizer = legacy.load_normalizer(inputs["normalizer"]["path"])
    timer = time.perf_counter()
    frame = pq.read_table(inputs["frame"]["path"], columns=["exact_text_sha256", "original_text", "arm"])
    all_arms = sorted({str(x) for x in frame["arm"].to_pylist()})
    read_s = time.perf_counter() - timer
    timer = time.perf_counter()
    cache, texts, arms = {}, {}, collections.defaultdict(set)
    for row in frame.to_pylist():
        raw = row["exact_text_sha256"]
        if raw not in cache:
            original = row["original_text"] or ""
            if hashlib.sha256(original.encode("utf-8")).hexdigest() != raw:
                raise RuntimeError("frozen frame raw-text hash mismatch")
            text = legacy.normalize(normalizer, original)
            context = hashlib.sha256(text.encode("utf-8")).hexdigest()
            cache[raw] = context
            if context in wanted:
                if context in texts and texts[context] != text:
                    raise RuntimeError("normalized context collision")
                texts[context] = text
        context = cache[raw]
        if context in wanted:
            arms[context].add(str(row["arm"]))
    if wanted - set(texts):
        raise RuntimeError("compatible reference missing exact full context")
    normalize_s = time.perf_counter() - timer
    matrices, hold_matrices, models, reports = {}, {}, {}, {}
    transform_s = predict_s = fit_s = 0.0
    for target in legacy.TARGETS:
        block = members["targets"][target]
        train_contexts = tuple(c for c, _ in block["train"])
        final_contexts = tuple(c for c, _ in block["final"])
        y_train = [v for _, v in block["train"]]
        truth = [v for _, v in block["final"]]
        counts = collections.Counter(y_train)
        report = {"train_rows": len(y_train), "train_negative": counts[0], "train_positive": counts[1],
                  "final_eligible_rows": len(truth), "final_negative": truth.count(0), "final_positive": truth.count(1),
                  "final_without_eligible_reference": freeze_obj["final_holdout_contexts"] - len(truth),
                  "reserved_prior_holdout_rows": len(block["previous_holdout_reserved_not_final"])}
        reports[target] = report
        if min(counts[0], counts[1]) < 5:
            report["fit_status"] = "insufficient_training_class_support"
            continue
        # An identical ordered training input shares its fitted transformer
        # and sparse training matrix. Different training inputs never share a fit.
        if train_contexts not in matrices:
            timer = time.perf_counter()
            vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=0.98, max_features=100000, sublinear_tf=True)
            matrix = vectorizer.fit_transform([texts[c] for c in train_contexts])
            transform_s += time.perf_counter() - timer
            matrices[train_contexts] = (vectorizer, matrix)
        vectorizer, matrix = matrices[train_contexts]
        timer = time.perf_counter()
        classifier = LinearSVC(C=1.0, class_weight="balanced", random_state=20261017)
        classifier.fit(matrix, y_train)
        fit_s += time.perf_counter() - timer
        models[target] = {"vectorizer": vectorizer, "classifier": classifier}
        report["fit_status"] = "fit"
        if not truth:
            report["final_metrics"] = metrics(legacy, [], [])
            continue
        cache_key = (train_contexts, final_contexts)
        if cache_key not in hold_matrices:
            timer = time.perf_counter()
            hold_matrices[cache_key] = vectorizer.transform([texts[c] for c in final_contexts])
            transform_s += time.perf_counter() - timer
        timer = time.perf_counter()
        pred = classifier.predict(hold_matrices[cache_key]).astype(int).tolist()
        predict_s += time.perf_counter() - timer
        report["final_metrics"] = metrics(legacy, truth, pred)
        report["majority_training_class_metrics"] = metrics(legacy, truth, [int(counts[1] > counts[0])] * len(truth))
        subsets = {"prior_exposed": [i for i, c in enumerate(final_contexts) if c in exposed],
                   "no_recorded_prior_exposure": [i for i, c in enumerate(final_contexts) if c not in exposed]}
        for arm in all_arms:
            subsets["existing_frame_arm=" + arm] = [i for i, c in enumerate(final_contexts) if arm in arms[c]]
        report["subgroups"] = {name: metrics(legacy, [truth[i] for i in ix], [pred[i] for i in ix]) for name, ix in subsets.items()}
    timer = time.perf_counter()
    artifact = {"version": legacy.VERSION, "targets": legacy.TARGETS, "models": models,
                "input_sha256": {name: item["sha256"] for name, item in inputs.items()},
                "freeze_sha256": digest(a.freeze), "semantic_scope": "27 binary presence targets only"}
    model_path = root / "FINAL_PRESENCE_BASELINE_PRIVATE.pkl"
    temp = Path(str(model_path) + ".tmp")
    with open(temp, "wb") as f:
        pickle.dump(artifact, f, protocol=4)
    os.chmod(str(temp), 0o600)
    os.replace(str(temp), str(model_path))
    write_s = time.perf_counter() - timer
    dump(root / "FINAL_EVALUATION_PRIVATE.json", {
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "job_id": os.environ.get("SLURM_JOB_ID"), "host": platform.node(),
        "freeze_sha256": digest(a.freeze), "reference_queue_closed": True,
        "targets": reports, "shared_training_matrix_groups": len(matrices),
        "shared_evaluation_transform_groups": len(hold_matrices),
        "timing_seconds": {"read": read_s, "normalize": normalize_s, "feature_transform": transform_s,
                           "fit": fit_s, "predict": predict_s, "model_write": write_s,
                           "end_to_end_through_model_write": time.perf_counter() - start},
        "private_model": {"path": str(model_path), "sha256": digest(model_path)},
        "group_source": freeze_obj["group_policy"],
        "claim_boundary": "evaluation against Pro reference labels; not human accuracy or automatic field acceptance; no corpus inference",
        "full_corpus_formal_fields_accepted": [], "unsupported": freeze_obj["unsupported"],
    })
    print(json.dumps({"status": "final_fit_and_evaluation_written", "fitted_binary_targets": len(models), "private_output": str(root)}))


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser()
    subs = p.add_subparsers(dest="command", required=True)
    f = subs.add_parser("freeze")
    for name in ("ledger", "queue", "receipt", "holdout", "frame", "normalizer", "legacy", "isolation", "output"):
        f.add_argument("--" + name, required=True)
    f = subs.add_parser("fit")
    f.add_argument("--freeze", required=True)
    f.add_argument("--output", required=True)
    a = p.parse_args()
    freeze(a) if a.command == "freeze" else fit(a)


if __name__ == "__main__":
    main()
