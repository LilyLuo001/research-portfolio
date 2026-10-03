#!/usr/bin/env python3
"""Manifest-bound, resumable batch driver for frozen semantic narrow outputs."""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.parquet as pq

EXPECTED_SHARDS = 2464
EXPECTED_VERSION = "pre_revelio_semantic_narrow_v1"
OBJECTS = ("general_work", "occupation_task", "industry_domain", "specific_tool", "object_unspecified")


def load_json(path):
    return json.loads(Path(path).read_text())


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, path)


class WorkLock:
    def __init__(self, work):
        self.path = Path(work) / "RUNNING.lock"; self.handle = None
    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+")
        try: fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise RuntimeError("another batch process holds the work-directory lock")
        self.handle.seek(0); self.handle.truncate(); self.handle.write(str(os.getpid()) + "\n"); self.handle.flush()
        return self
    def __exit__(self, *unused):
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN); self.handle.close()


def validate_gate(path, expected_shards=EXPECTED_SHARDS):
    gate = load_json(path)
    if (gate.get("status") != "complete" or gate.get("final_publication_complete") is not True
            or gate.get("total_shards") != expected_shards):
        raise RuntimeError("accepted global publication gate with exact shard count required")
    return gate


def load_plan_ids(paths, expected_shards=EXPECTED_SHARDS):
    ids = []
    for path in paths:
        ids += [json.loads(line)["shard_id"] for line in Path(path).read_text().splitlines() if line.strip()]
    if len(ids) != expected_shards or len(set(ids)) != expected_shards:
        raise RuntimeError("frozen plans must contain exact unique shard IDs")
    return set(ids)


def validate_shard(row):
    sid = row["shard_id"]; shard = Path(row["shard_dir"]); source_receipt = Path(row["receipt"])
    receipt = load_json(source_receipt); complete_path = shard / "SHARD_COMPLETE.json"
    if receipt.get("status") != "published_verified" or receipt.get("shard_id") != sid:
        raise RuntimeError(sid + ": published receipt identity mismatch")
    if not complete_path.is_file() or receipt.get("shard_complete_sha256") != sha256(complete_path):
        raise RuntimeError(sid + ": SHARD_COMPLETE hash mismatch")
    complete = load_json(complete_path)
    if receipt.get("shard_complete") != complete or complete.get("status") != "complete":
        raise RuntimeError(sid + ": SHARD_COMPLETE content/status mismatch")
    if complete.get("accounting", {}).get("shard_id") != sid:
        raise RuntimeError(sid + ": accounting shard identity mismatch")
    return {
        "source_receipt_sha256": sha256(source_receipt),
        "shard_complete_sha256": sha256(complete_path),
    }


def load_manifest(path, frozen_ids, expected_shards=EXPECTED_SHARDS):
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    ids = [row.get("shard_id") for row in rows]
    if len(rows) != expected_shards or len(set(ids)) != expected_shards or set(ids) != frozen_ids:
        raise RuntimeError("manifest IDs must exactly equal frozen plan IDs")
    for row in rows:
        if not {"shard_id", "shard_dir", "receipt"} <= set(row):
            raise RuntimeError("manifest row missing required identity field")
        row["source_identity"] = validate_shard(row)
    return sorted(rows, key=lambda row: row["shard_id"])


def paths_for(output_dir, sid):
    output = Path(output_dir) / (sid + ".parquet")
    return output, output.with_suffix(".durations.parquet"), output.with_suffix(".receipt.json"), output.with_suffix(".batch.json")


def complete_valid(row, output_dir, identity):
    output, duration, receipt_path, marker_path = paths_for(output_dir, row["shard_id"])
    try:
        receipt = load_json(receipt_path); marker = load_json(marker_path)
        if not output.is_file() or not duration.is_file(): return False
        if receipt.get("status") != "complete" or receipt.get("version") != EXPECTED_VERSION: return False
        if receipt.get("output_sha256") != sha256(output) or receipt.get("duration_detail_sha256") != sha256(duration): return False
        if receipt.get("source_receipt_sha256") != row["source_identity"]["source_receipt_sha256"]: return False
        if pq.ParquetFile(output).metadata.num_rows != receipt.get("output_rows"): return False
        if pq.ParquetFile(duration).metadata.num_rows != receipt.get("duration_detail_rows"): return False
        expected = {
            "shard_id": row["shard_id"], **row["source_identity"], **identity,
            "output_sha256": receipt["output_sha256"],
            "duration_sha256": receipt["duration_detail_sha256"],
            "receipt_sha256": sha256(receipt_path),
        }
        return marker == expected
    except (OSError, ValueError, TypeError, KeyError):
        return False


def run_one(builder, gate, row, output_dir, identity):
    validate_shard(row)
    if complete_valid(row, output_dir, identity):
        return "resumed"
    output, duration, receipt_path, marker_path = paths_for(output_dir, row["shard_id"])
    output.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
               NUMEXPR_NUM_THREADS="1", ARROW_NUM_THREADS="1")
    subprocess.run([sys.executable, str(builder), "--shard", row["shard_dir"],
                    "--receipt", row["receipt"], "--gate", str(gate),
                    "--output", str(output), "--threads", "1", "--memory-limit", "2GB"],
                   check=True, env=env)
    receipt = load_json(receipt_path)
    marker = {"shard_id": row["shard_id"], **row["source_identity"], **identity,
              "output_sha256": sha256(output), "duration_sha256": sha256(duration),
              "receipt_sha256": sha256(receipt_path)}
    atomic_json(marker_path, marker)
    if not complete_valid(row, output_dir, identity):
        marker_path.unlink(missing_ok=True)
        raise RuntimeError(row["shard_id"] + ": incomplete or identity-invalid output")
    return "built"


def duration_bin(bound_type, value):
    if bound_type == "exact_or_unspecified": return "no_interpretable_lower_bound_exact_or_unspecified"
    if bound_type not in {"minimum", "range"} or value is None: return "no_interpretable_lower_bound_other"
    value = float(value)
    if value == 0: return "explicit_0"
    if 0 < value < 1: return "(0,1)"
    if 1 <= value < 3: return "[1,3)"
    if 3 <= value < 5: return "[3,5)"
    if value >= 5: return ">=5"
    return "no_interpretable_lower_bound_other"


def duration_form(item):
    lower, upper, bound = item.get("MIN_YEARS"), item.get("MAX_YEARS"), item.get("BOUND_TYPE")
    if lower is None and upper is None: return "no_numeric_bound"
    if lower is None: return "upper_only"
    if bound == "exact_or_unspecified": return "exact_or_unspecified"
    if upper is not None: return "range"
    return "minimum"


def true_count(batch, name):
    values = batch.column(batch.schema.get_field_index(name))
    return int(pc.sum(pc.cast(values, "int64")).as_py() or 0)


def and_count(batch, left, right):
    l = batch.column(batch.schema.get_field_index(left)); r = batch.column(batch.schema.get_field_index(right))
    return int(pc.sum(pc.cast(pc.and_(l, r), "int64")).as_py() or 0)


def aggregate_valid(aggregate_dir, identity, shard_count):
    aggregate_dir = Path(aggregate_dir)
    try:
        receipt = load_json(aggregate_dir / "AGGREGATE_RECEIPT.json")
        return (receipt.get("status") == "complete" and receipt.get("shards") == shard_count
                and receipt.get("identity") == identity
                and receipt.get("ad_rates_sha256") == sha256(aggregate_dir / "T2_EXPERIENCE_AD_RATES.csv")
                and receipt.get("duration_distribution_sha256") == sha256(aggregate_dir / "T2_DURATION_BOUND_DISTRIBUTION.csv")
                and receipt.get("technology_role_sha256") == sha256(aggregate_dir / "T3_TECHNOLOGY_ROLE.csv")
                and receipt.get("technology_pair_sha256") == sha256(aggregate_dir / "T3_TECHNOLOGY_PAIR_OVERLAP.csv")
                and receipt.get("technology_experience_sha256") == sha256(aggregate_dir / "T3_TECHNOLOGY_EXPERIENCE_COOCCURRENCE.csv"))
    except (OSError, ValueError, TypeError):
        return False


def aggregate(rows, output_dir, aggregate_dir, identity):
    aggregate_dir = Path(aggregate_dir)
    if aggregate_valid(aggregate_dir, identity, len(rows)):
        return "resumed"
    if aggregate_dir.exists():
        shutil.rmtree(aggregate_dir)
    aggregate_dir.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="aggregate.tmp.", dir=aggregate_dir.parent))
    counts = {obj: Counter() for obj in OBJECTS}
    duration_clause = {obj: Counter() for obj in OBJECTS}; duration_ads = {obj: Counter() for obj in OBJECTS}
    technologies = ("traditional_software", "generative_ai", "predictive_ai", "unspecified_ai")
    roles = ("use", "develop", "implement")
    tech_role = Counter(); tech_pair = Counter(); tech_exp = Counter(); usable_ads = 0
    for row in rows:
        ad_path, duration_path, _, _ = paths_for(output_dir, row["shard_id"])
        for batch in pq.ParquetFile(ad_path).iter_batches(batch_size=65536):
            batch_usable = true_count(batch, "usable"); usable_ads += batch_usable
            for obj in OBJECTS:
                available = obj != "occupation_task"; counts[obj]["canonical_ads"] += batch.num_rows
                if available:
                    counts[obj]["usable_ads_denominator"] += batch_usable
                    for flag in ("main", "required", "preferred", "broad", "exact_or_unspecified"):
                        counts[obj][flag + "_ads"] += and_count(batch, "usable", "exp_%s_%s" % (obj, flag))
            usable_col = batch.column(batch.schema.get_field_index("usable"))
            for tech in technologies:
                tech_role[(tech, "detected_any_role", "candidate_coverage")] += and_count(batch, "usable", "tech_%s_detected" % tech)
                for role in roles:
                    tech_col = "tech_%s_%s_explicit" % (tech, role)
                    tech_role[(tech, role, "explicit_binding")] += and_count(batch, "usable", tech_col)
                    usable_tech = pc.and_(usable_col, batch.column(batch.schema.get_field_index(tech_col)))
                    for obj in OBJECTS:
                        if obj != "occupation_task":
                            exp_col = batch.column(batch.schema.get_field_index("exp_%s_main" % obj))
                            tech_exp[(tech, role, obj)] += int(pc.sum(pc.cast(pc.and_(usable_tech, exp_col), "int64")).as_py() or 0)
            for left_i, left in enumerate(technologies):
                for right in technologies[left_i + 1:]:
                    both_detected = pc.and_(batch.column(batch.schema.get_field_index("tech_%s_detected" % left)), batch.column(batch.schema.get_field_index("tech_%s_detected" % right)))
                    tech_pair[("detected_any_role", left, right)] += int(pc.sum(pc.cast(pc.and_(usable_col, both_detected), "int64")).as_py() or 0)
                    for role in roles:
                        left_col = batch.column(batch.schema.get_field_index("tech_%s_%s_explicit" % (left, role)))
                        right_col = batch.column(batch.schema.get_field_index("tech_%s_%s_explicit" % (right, role)))
                        tech_pair[(role, left, right)] += int(pc.sum(pc.cast(pc.and_(usable_col, pc.and_(left_col, right_col)), "int64")).as_py() or 0)
        local_ads = defaultdict(set)
        for batch in pq.ParquetFile(duration_path).iter_batches(batch_size=65536):
            for item in batch.to_pylist():
                obj = item["OBJECT_TYPE"]; ad_key = tuple(item[x] for x in ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW"))
                for kind, category in (("bound_form", duration_form(item)), ("lower_bound_bin", duration_bin(item["BOUND_TYPE"], item["MIN_YEARS"]))):
                    duration_clause[obj][(kind, category)] += 1; local_ads[(obj, kind, category)].add(ad_key)
        for (obj, kind, category), keys in local_ads.items(): duration_ads[obj][(kind, category)] += len(keys)
    rate_rows = []
    for obj in OBJECTS:
        c = counts[obj]; available = obj != "occupation_task"; denom = c["usable_ads_denominator"] if available else None
        rate_rows.append({"experience_object": obj, "measurement_available": str(available).lower(),
                          "canonical_ads": c["canonical_ads"], "usable_ads_denominator": denom,
                          "main_ads": c["main_ads"] if available else None,
                          "main_rate": c["main_ads"] / denom if denom else None,
                          "required_ads": c["required_ads"] if available else None,
                          "required_rate": c["required_ads"] / denom if denom else None,
                          "preferred_ads": c["preferred_ads"] if available else None,
                          "preferred_rate": c["preferred_ads"] / denom if denom else None,
                          "broad_ads": c["broad_ads"] if available else None,
                          "broad_rate": c["broad_ads"] / denom if denom else None,
                          "exact_or_unspecified_ads": c["exact_or_unspecified_ads"] if available else None,
                          "exact_or_unspecified_rate": c["exact_or_unspecified_ads"] / denom if denom else None,
                          "denominator_definition": "all usable canonical ads; no detection remains in denominator" if available else "unmeasured/NA under D10"})
    with (temp_dir / "T2_EXPERIENCE_AD_RATES.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rate_rows[0])); writer.writeheader(); writer.writerows(rate_rows)
    duration_rows = []
    for obj in OBJECTS:
        if obj == "occupation_task":
            duration_rows.append({"experience_object":obj,"classification":"availability","bound_category":"unmeasured_D10",
                "evidence_rows":"","share_of_object_duration_evidence":"","clause_rows":"","distinct_ads":"","all_main_clauses_denominator":"","main_ads_denominator":"",
                "clause_share":"","ad_share":"","denominator":"unmeasured/NA"})
            continue
        clause_denom = sum(v for (kind, _), v in duration_clause[obj].items() if kind == "bound_form")
        ad_denom = counts[obj]["main_ads"]
        for kind, category in sorted(duration_clause[obj]):
            clauses=duration_clause[obj][(kind,category)]; ads=duration_ads[obj][(kind,category)]
            duration_rows.append({"experience_object":obj,"classification":kind,"bound_category":category,
                "evidence_rows":clauses if kind == "bound_form" else "",
                "share_of_object_duration_evidence":clauses/clause_denom if kind == "bound_form" and clause_denom else "",
                "clause_rows":clauses,"distinct_ads":ads,"all_main_clauses_denominator":clause_denom,
                "main_ads_denominator":ad_denom,"clause_share":clauses/clause_denom if clause_denom else None,
                "ad_share":ads/ad_denom if ad_denom else None,
                "denominator":"all usable-ad explicit required/preferred clauses; ad counts deduplicated within category; categories may overlap across an ad"})
    with (temp_dir / "T2_DURATION_BOUND_DISTRIBUTION.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(duration_rows[0])); writer.writeheader(); writer.writerows(duration_rows)
    tech_role_rows = []
    for tech in technologies:
        for role, level in (("detected_any_role", "candidate_coverage"),
                            ("use", "explicit_binding"), ("develop", "explicit_binding"),
                            ("implement", "explicit_binding")):
            value = tech_role[(tech, role, level)]
            tech_role_rows.append({"technology":tech, "role":role, "measurement_level":level,
                "ads":value, "usable_ads_denominator":usable_ads,
                "share_of_usable_ads":value / usable_ads if usable_ads else None,
                "interpretation":"candidate coverage diagnostic" if level == "candidate_coverage" else "explicit applicant-context technology-role detection"})
    with (temp_dir / "T3_TECHNOLOGY_ROLE.csv").open("w", newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=list(tech_role_rows[0])); writer.writeheader(); writer.writerows(tech_role_rows)
    tech_pair_rows=[]
    for role in ("detected_any_role",) + roles:
        for left_i,left in enumerate(technologies):
            for right in technologies[left_i+1:]:
                value=tech_pair[(role,left,right)]
                tech_pair_rows.append({"role":role,"technology_left":left,"technology_right":right,
                    "intersection_ads":value,"usable_ads_denominator":usable_ads,
                    "share_of_usable_ads":value/usable_ads if usable_ads else None,
                    "interpretation":"same-ad candidate detection intersection" if role == "detected_any_role" else "same-ad intersection of two explicit technology-role detections"})
    with (temp_dir / "T3_TECHNOLOGY_PAIR_OVERLAP.csv").open("w",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=list(tech_pair_rows[0])); writer.writeheader(); writer.writerows(tech_pair_rows)
    tech_exp_rows=[]
    for tech in technologies:
        for role in roles:
            tech_denom=tech_role[(tech,role,"explicit_binding")]
            for obj in OBJECTS:
                available=obj!="occupation_task"; value=tech_exp[(tech,role,obj)] if available else None
                tech_exp_rows.append({"technology":tech,"role":role,"experience_object":obj,
                    "measurement_available":str(available).lower(),"cooccurrence_ads":value,
                    "technology_role_ads":tech_denom,"usable_ads_denominator":usable_ads,
                    "share_within_technology_role":value/tech_denom if available and tech_denom else None,
                    "share_of_usable_ads":value/usable_ads if available and usable_ads else None,
                    "interpretation":"within-ad cooccurrence; not a direct technology-to-experience binding" if available else "unmeasured/NA under D10"})
    with (temp_dir / "T3_TECHNOLOGY_EXPERIENCE_COOCCURRENCE.csv").open("w",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=list(tech_exp_rows[0])); writer.writeheader(); writer.writerows(tech_exp_rows)
    atomic_json(temp_dir / "AGGREGATE_RECEIPT.json", {"status":"complete", "shards":len(rows), "identity":identity,
        "ad_rates_sha256":sha256(temp_dir/"T2_EXPERIENCE_AD_RATES.csv"),
        "duration_distribution_sha256":sha256(temp_dir/"T2_DURATION_BOUND_DISTRIBUTION.csv"),
        "technology_role_sha256":sha256(temp_dir/"T3_TECHNOLOGY_ROLE.csv"),
        "technology_pair_sha256":sha256(temp_dir/"T3_TECHNOLOGY_PAIR_OVERLAP.csv"),
        "technology_experience_sha256":sha256(temp_dir/"T3_TECHNOLOGY_EXPERIENCE_COOCCURRENCE.csv"),
        "limits":["descriptive additive aggregation", "no raw text", "no time-causal interpretation", "occupation_task unmeasured/NA"]})
    os.replace(temp_dir, aggregate_dir)
    if not aggregate_valid(aggregate_dir, identity, len(rows)):
        raise RuntimeError("aggregate verification failed after atomic publication")
    return "built"


def execute(args, expected_shards=EXPECTED_SHARDS):
    if not 1 <= args.workers <= 8: raise ValueError("workers must be 1..8")
    work = Path(args.work_dir).resolve()
    with WorkLock(work):
        validate_gate(args.gate, expected_shards)
        frozen_ids = load_plan_ids(args.plans, expected_shards)
        rows = load_manifest(args.manifest, frozen_ids, expected_shards)
        builder = Path(args.builder).resolve()
        identity = {"runner_sha256":sha256(Path(__file__)), "builder_sha256":sha256(builder),
                    "gate_sha256":sha256(args.gate), "manifest_sha256":sha256(args.manifest),
                    "plan_set_sha256":hashlib.sha256("".join(sorted(sha256(x) for x in args.plans)).encode()).hexdigest()}
        config = {**identity, "expected_shards":expected_shards, "builder":str(builder)}
        config_path = work / "RUN_CONFIG.json"
        if config_path.exists() and load_json(config_path) != config: raise RuntimeError("work directory identity changed")
        if not config_path.exists(): atomic_json(config_path, config)
        output_dir = work / "shards"; counts = Counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(run_one, builder, args.gate, row, output_dir, identity) for row in rows]
            for future in concurrent.futures.as_completed(futures): counts[future.result()] += 1
        if not all(complete_valid(row, output_dir, identity) for row in rows):
            raise RuntimeError("not all exact-manifest shards complete; aggregate blocked")
        aggregate_action = aggregate(rows, output_dir, work / "aggregate", identity)
        atomic_json(work / "BATCH_RECEIPT.json", {"status":"complete", "shards":expected_shards,
            "actions":dict(counts), "aggregate_action":aggregate_action, **identity, "workers":args.workers})


def main():
    p=argparse.ArgumentParser(); p.add_argument("--gate",type=Path,required=True); p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--plans",type=Path,nargs="+",required=True); p.add_argument("--work-dir",type=Path,required=True)
    p.add_argument("--builder",type=Path,default=Path(__file__).with_name("build_semantic_narrow.py")); p.add_argument("--workers",type=int,default=8)
    execute(p.parse_args())


if __name__ == "__main__": main()
