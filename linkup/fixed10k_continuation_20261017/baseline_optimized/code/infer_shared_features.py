#!/usr/bin/env python3
"""Run the frozen baseline with exact fitted-transformer feature sharing.

This program does not fit or alter a model. It loads the frozen TF-IDF /
LinearSVC artifact, reconstructs each target's training-input identity from the
artifact's frozen ledger, and shares a transformed feature matrix only when
both that identity and the complete fitted transformer state match. The output
is a new private sidecar and is compared column-for-column with the frozen
20,000-row prediction sidecar.
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
import resource
import sys
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import scipy
import sklearn


VERSION = "fixed10k-cpu-tfidf-linearsvc-shared-feature-inference-v1"
PRIVATE_ROOT = Path("/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline_optimized")
FROZEN_MODEL = Path("/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline/artifacts/tfidf_linearsvc_holdout_frozen.pkl")
FROZEN_REFERENCE = Path("/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline/sidecar/first_linkup_shard_first20000_predictions.parquet")
TRAINING_LEDGER = Path("/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/batch001/final/FIELD_PROVENANCE_LEDGER_PRIVATE.jsonl")
NORMALIZER = Path("/work/home/lilysharp/private/formal800_20261012/code/frozen_rulefirst_v1_2/legacy_v5_frozen.py")
SHARD_ROOT = Path("/work/home/lilysharp/dewey_remaining_descriptions/data/linkup_job_descriptions")
SIDECAR_OUT = PRIVATE_ROOT / "sidecar" / "first_linkup_shard_first20000_predictions_shared_features.parquet"
RESULT_OUT = PRIVATE_ROOT / "results" / "SHARED_FEATURE_RESULT_PUBLIC.json"

EXPECTED_MODEL_SHA256 = "48dec600da433aa22dd5f9bb4e256af4ce9de92d5e81d2a0e46c71602dba1e4d"
EXPECTED_REFERENCE_SHA256 = "f232c017bf1ff67fec33ca058a9fd2d62da45c3a86f7f788f84ffb22967dc4ee"
EXPECTED_LEDGER_SHA256 = "435c7262700a42c4571160e772158f1344a58d39ee387be4436172b8053f5403"
EXPECTED_NORMALIZER_SHA256 = "336242bed5372e446dbdc2b2d02944e906024ee90138a2fa424b866aee7293dd"
EXPECTED_SHARD_SHA256 = "ce8293e5d7c919ceaef00c68544f0201cb6ae275efe24f82b3652149b8db2c1a"

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
LIMIT = 20000


def sha_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_sequence_sha(values):
    digest = hashlib.sha256()
    for value in values:
        digest.update(value.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def write_json_atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(str(path) + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(str(temporary), 0o600)
    os.replace(str(temporary), str(path))


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
    sources = {item.get("source") for item in row.get("provenance", [])}
    return bool(sources & ALLOWED_SOURCES) and not bool(sources - ALLOWED_SOURCES)


def target_family(target):
    if target.startswith("experience_presence."):
        return "experience_object"
    if target.startswith("entry_presence."):
        return "entry_wording_and_scope"
    if target.startswith("strict_current_duty."):
        return "current_responsibility_subject_and_relation"
    return "technology_category_and_role"


def is_holdout(context):
    digest = hashlib.sha256(("baseline-holdout-v1|" + context).encode("ascii")).hexdigest()
    return int(digest, 16) % 5 == 0


def reconstruct_training_inputs(path):
    family_contexts = collections.defaultdict(set)
    with open(path, encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row["status"] not in COMPLETE or not accepted_source(row):
                continue
            family = row["field_family"]
            if family not in {
                "experience_object",
                "entry_wording_and_scope",
                "current_responsibility_subject_and_relation",
                "technology_category_and_role",
            }:
                continue
            context = row["normalized_context_sha256"]
            if not is_holdout(context):
                family_contexts[family].add(context)
    result = {}
    for target in TARGETS:
        contexts = sorted(family_contexts[target_family(target)])
        result[target] = {"rows": len(contexts), "sha256": stable_sequence_sha(contexts)}
    return result


def fitted_transformer_fingerprint(vectorizer):
    """Hash effective params and complete fitted object state.

    The serialized fitted state includes vocabulary, IDF values, dtype and all
    learned/internal attributes. The params hash is also exposed independently
    so a receipt demonstrates that effective configuration was covered.
    """
    params_payload = pickle.dumps(vectorizer.get_params(deep=True), protocol=4)
    state_payload = pickle.dumps(vectorizer, protocol=4)
    return {
        "class": vectorizer.__class__.__module__ + "." + vectorizer.__class__.__qualname__,
        "effective_params_sha256": hashlib.sha256(params_payload).hexdigest(),
        "complete_fitted_state_sha256": hashlib.sha256(state_payload).hexdigest(),
        "complete_fitted_state_bytes": len(state_payload),
        "serialized_state": state_payload,
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
        return pa.table({"JOB_HASH": pa.array([], type=pa.string()), "DESCRIPTION": pa.array([], type=pa.string())}), parquet.metadata.num_rows
    return pa.Table.from_batches(batches), parquet.metadata.num_rows


def compare_predictions(candidate_path, reference_path):
    columns = ["source_row_0based", "JOB_HASH"] + list(TARGETS)
    candidate = pq.read_table(candidate_path, columns=columns)
    reference = pq.read_table(reference_path, columns=columns)
    if len(candidate) != len(reference):
        raise RuntimeError("candidate/reference row-count mismatch")
    mismatches = {}
    for column in columns:
        left = candidate[column]
        right = reference[column]
        if not left.equals(right):
            left_values = left.to_pylist()
            right_values = right.to_pylist()
            mismatches[column] = sum(a != b for a, b in zip(left_values, right_values))
    if mismatches:
        raise RuntimeError("frozen prediction mismatch: %r" % mismatches)
    return {
        "status": "exact_match",
        "rows": len(candidate),
        "identity_columns_compared": ["source_row_0based", "JOB_HASH"],
        "prediction_columns_compared": len(TARGETS),
        "prediction_cell_mismatches": 0,
    }


def process_cpu_seconds():
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_utime + usage.ru_stime, usage.ru_utime, usage.ru_stime


def main():
    script_started = time.perf_counter()
    cpu_started, user_started, system_started = process_cpu_seconds()
    os.umask(0o077)
    for directory in (SIDECAR_OUT.parent, RESULT_OUT.parent):
        directory.mkdir(parents=True, exist_ok=True)

    validation_started = time.perf_counter()
    input_hashes = {
        "frozen_model": sha_file(FROZEN_MODEL),
        "frozen_reference_sidecar": sha_file(FROZEN_REFERENCE),
        "training_ledger": sha_file(TRAINING_LEDGER),
        "normalizer": sha_file(NORMALIZER),
    }
    expected = {
        "frozen_model": EXPECTED_MODEL_SHA256,
        "frozen_reference_sidecar": EXPECTED_REFERENCE_SHA256,
        "training_ledger": EXPECTED_LEDGER_SHA256,
        "normalizer": EXPECTED_NORMALIZER_SHA256,
    }
    if input_hashes != expected:
        raise RuntimeError("frozen input SHA mismatch: %r" % input_hashes)
    shard = select_real_shard()
    shard_sha = sha_file(shard)
    if shard_sha != EXPECTED_SHARD_SHA256:
        raise RuntimeError("selected real shard SHA mismatch")
    validation_seconds = time.perf_counter() - validation_started

    load_started = time.perf_counter()
    with open(FROZEN_MODEL, "rb") as stream:
        artifact = pickle.load(stream)
    model_load_seconds = time.perf_counter() - load_started
    if tuple(artifact.get("targets", ())) != TARGETS:
        raise RuntimeError("frozen target order differs from locked 27-target order")
    models = artifact.get("models", {})
    if set(models) != set(TARGETS):
        raise RuntimeError("frozen artifact does not contain exactly 27 fitted targets")

    grouping_started = time.perf_counter()
    training_inputs = reconstruct_training_inputs(TRAINING_LEDGER)
    groups = collections.OrderedDict()
    transformer_payload_by_key = {}
    target_fingerprints = {}
    for target in TARGETS:
        vectorizer = models[target]["vectorizer"]
        fingerprint = fitted_transformer_fingerprint(vectorizer)
        key = (training_inputs[target]["sha256"], fingerprint["complete_fitted_state_sha256"])
        previous_payload = transformer_payload_by_key.get(key)
        if previous_payload is not None and previous_payload != fingerprint["serialized_state"]:
            raise RuntimeError("transformer SHA collision")
        transformer_payload_by_key[key] = fingerprint["serialized_state"]
        groups.setdefault(key, []).append(target)
        target_fingerprints[target] = {
            "training_rows": training_inputs[target]["rows"],
            "training_input_sha256": training_inputs[target]["sha256"],
            "transformer_class": fingerprint["class"],
            "effective_params_sha256": fingerprint["effective_params_sha256"],
            "complete_fitted_state_sha256": fingerprint["complete_fitted_state_sha256"],
            "complete_fitted_state_bytes": fingerprint["complete_fitted_state_bytes"],
        }
    grouping_seconds = time.perf_counter() - grouping_started

    normalizer = load_normalizer(NORMALIZER)
    inference_started = time.perf_counter()

    phase_started = time.perf_counter()
    real, source_total_rows = read_first_rows(shard, LIMIT)
    read_seconds = time.perf_counter() - phase_started
    if len(real) != LIMIT:
        raise RuntimeError("selected shard has fewer than 20,000 rows")

    phase_started = time.perf_counter()
    descriptions = [normalize(normalizer, value or "") for value in real["DESCRIPTION"].to_pylist()]
    normalize_seconds = time.perf_counter() - phase_started

    predictions = {}
    transform_seconds = 0.0
    predict_seconds = 0.0
    group_receipts = []
    for index, (key, targets) in enumerate(groups.items(), start=1):
        representative = targets[0]
        vectorizer = models[representative]["vectorizer"]
        phase_started = time.perf_counter()
        feature_matrix = vectorizer.transform(descriptions)
        this_transform_seconds = time.perf_counter() - phase_started
        transform_seconds += this_transform_seconds
        for target in targets:
            phase_started = time.perf_counter()
            predictions[target] = models[target]["classifier"].predict(feature_matrix).astype(np.int8)
            predict_seconds += time.perf_counter() - phase_started
        group_receipts.append({
            "group": index,
            "training_rows": target_fingerprints[representative]["training_rows"],
            "training_input_sha256": key[0],
            "effective_params_sha256": target_fingerprints[representative]["effective_params_sha256"],
            "complete_fitted_state_sha256": key[1],
            "targets": targets,
            "target_count": len(targets),
            "feature_rows": int(feature_matrix.shape[0]),
            "feature_columns": int(feature_matrix.shape[1]),
            "feature_nonzero": int(feature_matrix.nnz),
            "transform_seconds": this_transform_seconds,
        })
        del feature_matrix

    output = {
        "source_row_0based": pa.array(range(len(real)), type=pa.int64()),
        "JOB_HASH": real["JOB_HASH"],
    }
    for target in TARGETS:
        output[target] = pa.array(predictions[target], type=pa.int8())
    for name in UNSUPPORTED:
        output["unsupported_status." + name] = pa.array(["not_produced_unsupported"] * len(real), type=pa.string())

    phase_started = time.perf_counter()
    temporary = Path(str(SIDECAR_OUT) + ".tmp")
    pq.write_table(pa.table(output), temporary, compression="snappy")
    os.chmod(str(temporary), 0o600)
    os.replace(str(temporary), str(SIDECAR_OUT))
    write_seconds = time.perf_counter() - phase_started
    inference_seconds = time.perf_counter() - inference_started

    comparison_started = time.perf_counter()
    equivalence = compare_predictions(SIDECAR_OUT, FROZEN_REFERENCE)
    comparison_seconds = time.perf_counter() - comparison_started
    candidate_sha = sha_file(SIDECAR_OUT)
    cpu_ended, user_ended, system_ended = process_cpu_seconds()
    pre_result_wall_seconds = time.perf_counter() - script_started
    cpu_seconds = cpu_ended - cpu_started

    report = {
        "version": VERSION,
        "status": "pass",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "scope": "frozen-model engineering optimization on the same first 20,000 original-order rows; no fitting, evaluation, model selection, or corpus production",
        "scheduler": {
            "job_id": os.environ.get("SLURM_JOB_ID"),
            "host": platform.node(),
            "requested_cpus": int(os.environ.get("SLURM_CPUS_PER_TASK", "1")),
            "partition": os.environ.get("SLURM_JOB_PARTITION"),
        },
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "sklearn": sklearn.__version__,
            "pyarrow": pa.__version__,
        },
        "frozen_inputs": {
            "model": {"sha256": input_hashes["frozen_model"], "bytes": FROZEN_MODEL.stat().st_size},
            "reference_sidecar": {"sha256": input_hashes["frozen_reference_sidecar"], "bytes": FROZEN_REFERENCE.stat().st_size},
            "training_ledger_sha256": input_hashes["training_ledger"],
            "normalizer_sha256": input_hashes["normalizer"],
            "real_shard": {"sha256": shard_sha, "selection": "lexicographically_first_existing_recursive_parquet", "source_total_rows": source_total_rows},
        },
        "sharing": {
            "key": "sha256(sorted frozen training context identities) plus sha256(pickle of complete fitted transformer state)",
            "effective_parameters_independently_hashed": True,
            "targets": len(TARGETS),
            "unique_feature_matrices": len(groups),
            "avoided_duplicate_transforms": len(TARGETS) - len(groups),
            "groups": group_receipts,
            "target_fingerprints": target_fingerprints,
        },
        "timing_seconds": {
            "frozen_input_hash_validation": validation_seconds,
            "model_load": model_load_seconds,
            "fingerprint_and_group_setup": grouping_seconds,
            "read": read_seconds,
            "normalize": normalize_seconds,
            "feature_transform": transform_seconds,
            "predict": predict_seconds,
            "write_close_atomic_rename": write_seconds,
            "inference_e2e_read_through_atomic_write": inference_seconds,
            "equivalence_check": comparison_seconds,
            "full_payload_pre_result_write": pre_result_wall_seconds,
        },
        "throughput": {
            "rows": len(real),
            "inference_e2e_rows_per_second": len(real) / inference_seconds,
            "full_payload_pre_result_rows_per_second": len(real) / pre_result_wall_seconds,
        },
        "cpu_usage": {
            "process_user_seconds": user_ended - user_started,
            "process_system_seconds": system_ended - system_started,
            "process_total_seconds": cpu_seconds,
            "mean_cores_used_over_pre_result_wall": cpu_seconds / pre_result_wall_seconds,
            "requested_cpus": int(os.environ.get("SLURM_CPUS_PER_TASK", "1")),
        },
        "equivalence": equivalence,
        "output": {
            "private_sidecar_sha256": candidate_sha,
            "private_sidecar_bytes": SIDECAR_OUT.stat().st_size,
            "prediction_columns": len(TARGETS),
            "unsupported_status_columns": len(UNSUPPORTED),
        },
        "code_sha256": sha_file(Path(__file__)),
        "claim_boundary": "Engineering equivalence and speed only. The 27 outputs remain binary presence predictions and do not implement complete seven-family semantics.",
        "class_weight_note": "class_weight='balanced' is inherited unchanged from the frozen model and is not an optimization or new correction.",
    }
    write_json_atomic(RESULT_OUT, report)
    print(json.dumps({
        "status": "pass",
        "job_id": os.environ.get("SLURM_JOB_ID"),
        "result": str(RESULT_OUT),
        "rows": len(real),
        "unique_feature_matrices": len(groups),
        "avoided_duplicate_transforms": len(TARGETS) - len(groups),
        "inference_e2e_rows_per_second": report["throughput"]["inference_e2e_rows_per_second"],
        "prediction_equivalence": equivalence["status"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
