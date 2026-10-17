#!/usr/bin/env python3
"""Post-run text validity QA and final claim-boundary receipt; never retrains."""
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


ROOT = Path("/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline")
RESULT = ROOT / "results" / "BASELINE_RESULT.json"
FINAL = ROOT / "results" / "BASELINE_RESULT_FINAL.json"
CODE = ROOT / "code" / "train_evaluate_infer.py"
NORMALIZER = Path("/work/home/lilysharp/private/formal800_20261012/code/frozen_rulefirst_v1_2/legacy_v5_frozen.py")
UNSUPPORTED = [
    "experience_strength_required_or_preferred",
    "experience_conditionality_and_logical_branch",
    "literal_numeric_years",
    "open_ended_named_object",
    "verbatim_evidence",
    "qualification_branch_relation_reconstruction",
]


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_normalizer():
    spec = importlib.util.spec_from_file_location("baseline_finalize_normalizer", str(NORMALIZER))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalized(module, value):
    result = module._normalize_with_flags(value)
    return result[0] if isinstance(result, tuple) else result


def first_rows(path, limit):
    pf = pq.ParquetFile(path)
    batches, have = [], 0
    for batch in pf.iter_batches(batch_size=min(8192, limit), columns=["DESCRIPTION"]):
        take = min(len(batch), limit - have)
        batches.append(batch.slice(0, take)); have += take
        if have == limit:
            break
    return pf, pa.Table.from_batches(batches)


def write_json(path, value):
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(str(tmp), 0o600); os.replace(str(tmp), str(path))


def main():
    report = json.loads(RESULT.read_text(encoding="utf-8"))
    source = Path(report["inputs"]["real_shard"]["path"])
    pf, rows = first_rows(source, 20000)
    module = load_normalizer()
    reasons = []
    for value in rows["DESCRIPTION"].to_pylist():
        if value is None:
            reasons.append("null_description")
        else:
            norm = normalized(module, value)
            reasons.append("empty_after_frozen_normalization" if not norm.strip() else "valid")
    counts = {name: reasons.count(name) for name in sorted(set(reasons))}
    invalid = sum(x != "valid" for x in reasons)
    remediation = {"required": bool(invalid), "sidecar_rewritten": False}
    if invalid:
        original = Path(report["artifacts"]["private_prediction_sidecar"]["path"])
        table = pq.read_table(original)
        if len(table) != len(reasons):
            raise RuntimeError("sidecar/source row mismatch")
        arrays = {"source_row_0based": table["source_row_0based"], "JOB_HASH": table["JOB_HASH"], "input_status": pa.array(reasons)}
        valid = [x == "valid" for x in reasons]
        for name in table.column_names:
            if name in arrays or name.startswith("unsupported_status."):
                continue
            values = table[name].to_pylist()
            arrays[name] = pa.array([v if ok else None for v, ok in zip(values, valid)], type=table.schema.field(name).type)
        for name in UNSUPPORTED:
            arrays["unsupported_status." + name] = pa.array(["not_produced_unsupported"] * len(table))
        revised = original.with_name(original.stem + "_input_validated.parquet")
        tmp = Path(str(revised) + ".tmp")
        pq.write_table(pa.table(arrays), tmp, compression="snappy")
        os.chmod(str(tmp), 0o600); os.replace(str(tmp), str(revised))
        report["artifacts"]["private_prediction_sidecar"] = {"path": str(revised), "sha256": sha_file(revised), "bytes": revised.stat().st_size}
        remediation = {"required": True, "sidecar_rewritten": True, "original_sidecar_preserved": str(original)}
    report["finalized_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    report["training_runtime_code"] = {"path": str(CODE), "sha256": sha_file(CODE)}
    report["real_inference"].update({
        "source_total_rows": pf.metadata.num_rows,
        "rows_read": len(rows),
        "invalid_text_rows": invalid,
        "input_status_counts": counts,
        "invalid_text_definition": "DESCRIPTION is null or frozen-normalized text is empty/whitespace",
        "invalid_text_remediation": remediation,
    })
    report["supported_output_scope"] = "27 binary presence targets only (4 experience, 4 entry, 4 strict current-duty responsibility, 3 technology family, 12 family-by-role)"
    report["unsupported"] = UNSUPPORTED
    write_json(FINAL, report)
    print(json.dumps({"status": "pass", "source_total_rows": pf.metadata.num_rows, "rows_read": len(rows), "invalid_text_rows": invalid, "final_result": str(FINAL)}, sort_keys=True))


if __name__ == "__main__":
    main()
