#!/usr/bin/env python3
"""Build formal800 finite-frame tables from validated private review outputs.

Real-data execution is restricted to scheduled SCNet jobs. This program never
creates semantic labels, imputes unknowns, or expands decisions to unsampled ads.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Callable

VERSION = "formal800-finite-eligible10k-analysis-v1"
MAIN_GROUPS = ("genai_use_with_or_without_software", "traditional_software_use_no_ai")
EXP_DIMS = ("general_work", "occupation_task", "industry_domain", "tool_specific")
ENTRY_TARGETS = ("explicit_no_experience", "explicit_new_graduate")
RESP_DIMS = ("independent_judgment", "client_ownership", "people_supervision", "training_mentoring")
ACTIVE_TECH_ROLES = {"develop_technology", "implement_deploy_technology", "use_tool_for_work"}
ACTIVE_AI_ROLES = ACTIVE_TECH_ROLES
CANONICAL = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
MAP_REQUIRED = {
    "record_id", *CANONICAL, "formal_arm", "entry_stratum", "N_h", "n_h", "pi12",
    "pi3", "nested_design_weight", "occupation_major", "audit_selected",
    "raw_exact_text_sha256", "normalized_context_sha256",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_rows(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix in {".jsonl", ".ndjson"}:
        rows = []
        with path.open(encoding="utf-8") as stream:
            for number, line in enumerate(stream, 1):
                if line.strip():
                    value = json.loads(line)
                    if not isinstance(value, dict):
                        raise RuntimeError(f"non-object JSONL row {path}:{number}")
                    rows.append(value)
        return rows
    if suffix == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
            raise RuntimeError("JSON input must be an array of objects")
        return value
    if suffix == ".csv":
        with path.open(encoding="utf-8", newline="") as stream:
            return list(csv.DictReader(stream))
    if suffix in {".parquet", ".pq"}:
        try:
            import pyarrow.parquet as pq
        except ImportError as exc:
            raise RuntimeError("pyarrow is required for Parquet input") from exc
        return pq.read_table(path).to_pylist()
    raise RuntimeError(f"unsupported input format: {path}")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else ["status"]
    temporary = Path(str(path) + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(str(path) + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def write_private_ad_parquet(path: Path, rows: list[dict[str, Any]],
                             validated_reviews_sha256: str) -> None:
    """Write private ad-level measures without copying review text or evidence."""
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError("pyarrow is required for --private-ad-output") from exc
    output_rows = []
    for row in rows:
        review = row["review"]
        output_rows.append({
            **{name: row[name] for name in CANONICAL},
            "blind_context_id": row["record_id"],
            "blind_context_sha256": review["context_sha256"],
            "validated_nested_review_jsonl_sha256": validated_reviews_sha256,
            "validated_nested_review_record_id": review["record_id"],
            "validated_nested_review_context_sha256": review["context_sha256"],
            "formal_arm": row["formal_arm"],
            "entry_stratum": row["entry_stratum"],
            "N_h": row["N_h"],
            "n_h": row["n_h"],
            "pi12": None if row["pi12"] is None else as_float(row["pi12"], "pi12"),
            "pi3": row["pi3"],
            "nested_design_weight": (None if row["nested_design_weight"] is None else
                                     as_float(row["nested_design_weight"], "nested_design_weight")),
            "w3": row["w3"],
            "occupation_major": row["occupation_major"],
            "semantic_technology_group": row["semantic_technology_group"],
            "analysis_technology_group": row["analysis_technology_group"],
            **{f"experience_{dimension}": outcome_value(review, "experience_outcomes", dimension)
               for dimension in EXP_DIMS},
            "entry_core_including_conditional": core_entry(review, False),
            "entry_core_unconditional": core_entry(review, True),
            "entry_current_student_internship": outcome_value(
                review, "entry_outcomes", "current_student_internship"),
            "entry_junior_or_entry_label": outcome_value(
                review, "entry_outcomes", "explicit_junior_or_entry_label"),
            **{f"strict_current_duty_{dimension}": strict_duty(review, dimension)
               for dimension in RESP_DIMS},
            "strict_current_duty_any": strict_duty_any(review),
        })
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(str(path) + ".tmp")
    pq.write_table(pa.Table.from_pylist(output_rows), temporary)
    os.replace(temporary, path)


def require_passing_validation(receipt_path: Path, validated_path: Path) -> dict[str, Any]:
    """Bind analysis to a successful validator receipt, never a partial output."""
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("status") != "pass":
        raise RuntimeError("review validation receipt is not pass; analysis is prohibited")
    private = receipt.get("private_outputs", {})
    expected = private.get("validated_sha256")
    if not isinstance(expected, str) or expected != sha256_file(validated_path):
        raise RuntimeError("validated reviews do not match the passing validator receipt")
    if private.get("error_entries") != 0:
        raise RuntimeError("passing validation receipt reports errors")
    return receipt


def require_overlay_receipt(receipt_path: Path, overlay_path: Path) -> dict[str, Any]:
    """Fail closed unless the explicit replacement overlay has its own receipt."""
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("status") != "pass":
        raise RuntimeError("resolved overlay receipt is not pass")
    private = receipt.get("private_outputs", {})
    bound = private.get("overlay_sha256") or private.get("validated_sha256")
    if bound != sha256_file(overlay_path):
        raise RuntimeError("resolved overlay does not match its passing receipt")
    if private.get("error_entries", 0) != 0:
        raise RuntimeError("resolved overlay receipt reports errors")
    return receipt


def apply_resolved_overlay(reviews: list[dict[str, Any]], overlay_path: Path | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply only explicit, complete root resolutions to their named primary record.

    The private JSONL overlay is intentionally small and is produced after blind
    audit/root review.  Each row must be exactly ``record_id``,
    ``context_sha256``, ``resolved_review``, and ``resolution_id``.  The
    replacement is a complete already-validated review payload; field-level
    inference, majority votes, and unreviewed-ad propagation are impossible.
    """
    if overlay_path is None:
        return reviews, {"applied": False, "resolved_contexts": 0}
    overlays = read_rows(overlay_path)
    by_id = {row["record_id"]: dict(row) for row in reviews}
    seen: set[str] = set()
    for item in overlays:
        if set(item) != {"record_id", "context_sha256", "resolved_review", "resolution_id"}:
            raise RuntimeError("resolution overlay rows must use the explicit four-field contract")
        record_id = item["record_id"]
        resolved = item["resolved_review"]
        if not isinstance(record_id, str) or record_id in seen or record_id not in by_id:
            raise RuntimeError("resolution overlay has duplicate or unknown primary record_id")
        if not isinstance(resolved, dict):
            raise RuntimeError("resolution overlay resolved_review must be a complete review object")
        original = by_id[record_id]
        if item["context_sha256"] != original.get("context_sha256"):
            raise RuntimeError("resolution overlay context hash does not bind primary record")
        if resolved.get("record_id") != record_id or resolved.get("context_sha256") != item["context_sha256"]:
            raise RuntimeError("resolution overlay review identity does not bind primary record")
        if "trusted_assignment" not in resolved or "evidence_resolution" not in resolved:
            raise RuntimeError("resolution overlay review must be validator-produced")
        by_id[record_id] = resolved
        seen.add(record_id)
    return [by_id[row["record_id"]] for row in reviews], {
        "applied": True, "resolved_contexts": len(seen), "overlay_sha256": sha256_file(overlay_path),
    }


def as_int(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise RuntimeError(f"{name} cannot be boolean")
    try:
        number = int(value)
    except Exception as exc:
        raise RuntimeError(f"{name} is not an integer") from exc
    if str(value).strip() not in {str(number), f"{number}.0"} and not isinstance(value, int):
        raise RuntimeError(f"{name} is not an exact integer")
    return number


def as_float(value: Any, name: str) -> float:
    try:
        number = float(value)
    except Exception as exc:
        raise RuntimeError(f"{name} is not numeric") from exc
    if not math.isfinite(number):
        raise RuntimeError(f"{name} is not finite")
    return number


def semantic_technology(review: dict[str, Any]) -> str:
    items = review["technology_items"]
    status = review["technology_inventory_status"]
    if review["document_status"] != "reviewed_full" or status == "unknown":
        return "uncertain_technology"
    if any(item["family"] == "unresolved" or item["role"] == "unresolved" for item in items):
        return "uncertain_technology"
    active = [item for item in items if item["role"] in ACTIVE_TECH_ROLES]
    gen_use = any(item["family"] == "generative_ai" and item["role"] == "use_tool_for_work" for item in active)
    trad_use = any(item["family"] == "traditional_software_system" and item["role"] == "use_tool_for_work" for item in active)
    # A predictive or background AI mention is retained as its own reviewed
    # category; it cannot silently enter either clean use comparison arm.
    predictive = any(item["family"] == "predictive_ml_ai" and item["role"] in ACTIVE_AI_ROLES for item in items)
    background = any(item["role"] == "background_mention" for item in items)
    ai_develop = any(
        item["family"] in {"generative_ai", "predictive_ml_ai"}
        and item["role"] in {"develop_technology", "implement_deploy_technology"}
        for item in active
    )
    if ai_develop:
        return "ai_develop_implement_other"
    if predictive:
        return "predictive_ai_or_mixed"
    if gen_use and trad_use:
        return "genai_traditional_overlap"
    # Background/company/recruiting mentions do not displace clear active use.
    if background and not (gen_use or trad_use):
        return "background_or_mixed"
    if gen_use:
        return "genai_use_only"
    if trad_use:
        return "traditional_software_use_no_ai"
    if not items and status == "not_mentioned_after_full_review":
        return "no_relevant_technology_mentioned"
    return "other_explicit_technology"


def analysis_technology_group(detail_group: str) -> str:
    """Map detailed T3 labels to the two frozen main comparison groups."""
    if detail_group in {"genai_use_only", "genai_traditional_overlap"}:
        return "genai_use_with_or_without_software"
    return detail_group


def usable_occupation_major(value: Any) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() not in {"", "null", "none", "unknown"}


def outcome_value(review: dict[str, Any], group: str, dimension: str) -> int | None:
    value = review[group][dimension]
    return {"present": 1, "not_mentioned": 0, "unknown": None}[value]


def core_entry(review: dict[str, Any], unconditional_only: bool = False) -> int | None:
    values = [outcome_value(review, "entry_outcomes", target) for target in ENTRY_TARGETS]
    applicable = [
        item for item in review["entry_items"]
        if item["target"] in ENTRY_TARGETS
        and (not unconditional_only or item["conditionality"] == "unconditional")
    ]
    if applicable:
        return 1
    # A conditional positive is a defined strict-sensitivity zero, but an
    # unresolved target could still hide an unconditional entry statement.
    if unconditional_only and 1 in values and None not in values:
        return 0
    if values == [0, 0]:
        return 0
    return None


def strict_duty(review: dict[str, Any], dimension: str) -> int | None:
    if review["responsibility_outcomes"][dimension] == "unknown":
        return None
    matching = [
        item for item in review["responsibility_items"]
        if item["dimension"] == dimension
        and item["subject"] == "advertised_worker"
        and item["relation"] == "current_duty"
    ]
    if matching:
        return 1
    if review["document_status"] == "reviewed_full":
        return 0
    return None


def strict_duty_any(review: dict[str, Any]) -> int | None:
    values = [strict_duty(review, dimension) for dimension in RESP_DIMS]
    if 1 in values:
        return 1
    if all(value == 0 for value in values):
        return 0
    return None


def stratum_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["formal_arm"]), str(row["entry_stratum"])


def validate_and_join(reviews: list[dict[str, Any]], mapping: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {}
    for review in reviews:
        record_id = review.get("record_id")
        if not isinstance(record_id, str) or not record_id or record_id in by_id:
            raise RuntimeError("validated reviews have empty or duplicate record_id")
        if "trusted_assignment" not in review or "evidence_resolution" not in review:
            raise RuntimeError("reviews are not outputs of validate_reviews.py")
        by_id[record_id] = review
    seen_keys = set()
    joined = []
    stratum_contract: dict[tuple[str, str], tuple[int, int, float]] = {}
    observed = collections.Counter()
    for source in mapping:
        missing = MAP_REQUIRED - set(source)
        if missing:
            raise RuntimeError("sampled-ad map missing fields: " + ",".join(sorted(missing)))
        key = tuple(source[name] for name in CANONICAL)
        if key in seen_keys:
            raise RuntimeError("sampled-ad map has duplicate canonical key")
        seen_keys.add(key)
        record_id = source["record_id"]
        if record_id not in by_id:
            raise RuntimeError("sampled ad does not bind a validated review record_id")
        N_h, n_h = as_int(source["N_h"], "N_h"), as_int(source["n_h"], "n_h")
        pi3 = as_float(source["pi3"], "pi3")
        if not (0 < n_h <= N_h) or not math.isclose(pi3, n_h / N_h, rel_tol=0, abs_tol=1e-12):
            raise RuntimeError("invalid N_h/n_h/pi3 contract")
        h = stratum_key(source)
        contract = (N_h, n_h, pi3)
        if h in stratum_contract and stratum_contract[h] != contract:
            raise RuntimeError("stratum has inconsistent N_h/n_h/pi3")
        stratum_contract[h] = contract
        observed[h] += 1
        review = by_id[record_id]
        if source["normalized_context_sha256"] != review["context_sha256"]:
            raise RuntimeError("sample map normalized context hash does not bind validated review")
        row = dict(source)
        row["N_h"], row["n_h"], row["pi3"] = N_h, n_h, pi3
        row["w3"] = 1.0 / pi3
        row["review"] = review
        row["semantic_technology_group"] = semantic_technology(review)
        row["analysis_technology_group"] = analysis_technology_group(row["semantic_technology_group"])
        joined.append(row)
    for h, (_, n_h, _) in stratum_contract.items():
        if observed[h] != n_h:
            raise RuntimeError(f"sample row conservation fails for stratum {h}")
    if set(by_id) != {row["record_id"] for row in mapping}:
        raise RuntimeError("validated review set and sampled-ad map record IDs differ")
    return joined


def ratio_components(rows: list[dict[str, Any]], x_fn: Callable, y_fn: Callable) -> tuple[float | None, float, float]:
    x_total = sum(row["w3"] * float(x_fn(row)) for row in rows)
    y_total = sum(row["w3"] * float(y_fn(row)) for row in rows)
    return (None if x_total <= 0 else y_total / x_total), x_total, y_total


def ratio_result(rows: list[dict[str, Any]], x_fn: Callable, y_fn: Callable) -> dict[str, Any]:
    estimate, x_total, y_total = ratio_components(rows, x_fn, y_fn)
    base = {"estimate": estimate, "weighted_denominator": x_total, "weighted_numerator": y_total}
    if estimate is None:
        return {**base, "se": None, "ci_low": None, "ci_high": None, "variance_status": "no_denominator"}
    variance = 0.0
    for h in sorted({stratum_key(row) for row in rows}):
        sample = [row for row in rows if stratum_key(row) == h]
        N_h, n_h = sample[0]["N_h"], sample[0]["n_h"]
        if n_h == N_h:
            continue
        if n_h < 2:
            return {**base, "se": None, "ci_low": None, "ci_high": None,
                    "variance_status": "NA_n_h_lt_2_non_census"}
        z = [float(y_fn(row)) - estimate * float(x_fn(row)) for row in sample]
        mean = sum(z) / n_h
        sample_variance = sum((value - mean) ** 2 for value in z) / (n_h - 1)
        variance += N_h * N_h * (1.0 - n_h / N_h) * sample_variance / n_h
    variance /= x_total * x_total
    se = math.sqrt(max(0.0, variance))
    return {**base, "se": se, "ci_low": max(0.0, estimate - 1.96 * se),
            "ci_high": min(1.0, estimate + 1.96 * se), "variance_status": "design_linearized"}


def difference_result(rows: list[dict[str, Any]], measure: Callable, scope: Callable) -> dict[str, Any]:
    components = {}
    for group in MAIN_GROUPS:
        x_fn = lambda row, g=group: int(scope(row) and row["analysis_technology_group"] == g and measure(row) is not None)
        y_fn = lambda row, g=group: int(scope(row) and row["analysis_technology_group"] == g and measure(row) == 1)
        components[group] = (*ratio_components(rows, x_fn, y_fn), x_fn, y_fn)
    a, b = MAIN_GROUPS
    ra, xa, _, xfa, yfa = components[a]
    rb, xb, _, xfb, yfb = components[b]
    if ra is None or rb is None:
        return {"group_a_rate": ra, "group_b_rate": rb, "difference_a_minus_b": None,
                "se": None, "ci_low": None, "ci_high": None, "variance_status": "no_denominator"}
    variance = 0.0
    for h in sorted({stratum_key(row) for row in rows}):
        sample = [row for row in rows if stratum_key(row) == h]
        N_h, n_h = sample[0]["N_h"], sample[0]["n_h"]
        if n_h == N_h:
            continue
        if n_h < 2:
            return {"group_a_rate": ra, "group_b_rate": rb, "difference_a_minus_b": ra-rb,
                    "se": None, "ci_low": None, "ci_high": None,
                    "variance_status": "NA_n_h_lt_2_non_census"}
        u = [
            (float(yfa(row)) - ra * float(xfa(row))) / xa
            - (float(yfb(row)) - rb * float(xfb(row))) / xb
            for row in sample
        ]
        mean = sum(u) / n_h
        s2 = sum((value - mean) ** 2 for value in u) / (n_h - 1)
        variance += N_h * N_h * (1.0 - n_h / N_h) * s2 / n_h
    delta = ra - rb
    se = math.sqrt(max(0.0, variance))
    return {"group_a_rate": ra, "group_b_rate": rb, "difference_a_minus_b": delta,
            "se": se, "ci_low": delta - 1.96*se, "ci_high": delta + 1.96*se,
            "variance_status": "design_linearized"}


def measure_rows(rows: list[dict[str, Any]], name: str, measure: Callable,
                 group: str, scope_name: str, scope: Callable) -> dict[str, Any]:
    in_group = lambda row: scope(row) and (group == "all_technology_groups" or row["analysis_technology_group"] == group)
    defined_x = lambda row: int(in_group(row) and measure(row) is not None)
    positive_y = lambda row: int(in_group(row) and measure(row) == 1)
    all_x = lambda row: int(in_group(row))
    unknown_y = lambda row: int(in_group(row) and measure(row) is None)
    defined = ratio_result(rows, defined_x, positive_y)
    lower = ratio_result(rows, all_x, positive_y)
    upper = ratio_result(rows, all_x, lambda row: positive_y(row) + unknown_y(row))
    coverage = ratio_result(rows, all_x, defined_x)
    return {
        "estimand": "eligible_post_exclusion_fixed10k_w3",
        "scope": scope_name, "semantic_group": group, "measure": name,
        "sampled_ads": sum(in_group(row) for row in rows),
        "defined_rate": defined["estimate"], "defined_se": defined["se"],
        "defined_ci_low": defined["ci_low"], "defined_ci_high": defined["ci_high"],
        "variance_status": defined["variance_status"],
        "defined_coverage": coverage["estimate"],
        "unknown_lower_bound": lower["estimate"], "unknown_upper_bound": upper["estimate"],
        "weighted_defined_denominator": defined["weighted_denominator"],
        "model_error_included_in_ci": False,
    }


def entry_conditioned_duties(rows: list[dict[str, Any]], scopes: list) -> list[dict[str, Any]]:
    """Answer Q2 directly: current duties among ads explicitly welcoming entrants."""
    output = []
    measures = [(d, lambda r, d=d: strict_duty(r["review"], d)) for d in RESP_DIMS]
    measures.append(("any_strict_current_duty", lambda r: strict_duty_any(r["review"])))
    for scope_name, scope in scopes:
        for group in ("all_technology_groups", *MAIN_GROUPS):
            in_domain = lambda r, g=group: scope(r) and (g == "all_technology_groups" or r["analysis_technology_group"] == g)
            entry_definitions = [
                ("including_conditional", lambda r: core_entry(r["review"], False)),
                ("unconditional_only", lambda r: core_entry(r["review"], True)),
                ("explicit_new_graduate_only", lambda r: outcome_value(
                    r["review"], "entry_outcomes", "explicit_new_graduate")),
            ]
            for entry_definition, entry in entry_definitions:
                eligible = lambda r: in_domain(r) and entry(r) == 1
                for name, duty in measures:
                    defined = ratio_result(rows, lambda r: int(eligible(r) and duty(r) is not None),
                                           lambda r: int(eligible(r) and duty(r) == 1))
                    lower = ratio_result(rows, lambda r: int(eligible(r)), lambda r: int(eligible(r) and duty(r) == 1))
                    upper = ratio_result(rows, lambda r: int(eligible(r)), lambda r: int(eligible(r) and duty(r) != 0))
                    output.append({
                        "estimand": "current_duty_wording_among_entry_wording_ads_eligible_fixed10k_w3",
                        "scope": scope_name, "technology_scope": group,
                        "entry_definition": entry_definition,
                        "duty_dimension": name, "sampled_entry_ads": sum(eligible(r) for r in rows),
                        "sampled_entry_ads_with_duty_unknown": sum(eligible(r) and duty(r) is None for r in rows),
                        "weighted_entry_ads": sum(r["w3"] for r in rows if eligible(r)),
                        "weighted_entry_membership_unknown": sum(r["w3"] for r in rows if in_domain(r) and entry(r) is None),
                        **defined, "unknown_duty_lower_bound": lower["estimate"],
                        "unknown_duty_upper_bound": upper["estimate"],
                        "bounds_condition": "among_positive_wording_ads_only; unresolved_wording_membership_excluded_and_reported",
                        "entry_claim_boundary": "experience-type waivers do not establish zero total experience eligibility; graduate wording is separately reported",
                        "model_error_included_in_ci": False,
                    })
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validated-reviews", type=Path, required=True)
    parser.add_argument("--validation-receipt", type=Path, required=True,
                        help="public receipt emitted by validate_reviews.py with status=pass")
    parser.add_argument("--sampled-ad-map", type=Path, required=True)
    parser.add_argument("--resolved-overlay", type=Path,
                        help="private, explicit root-resolution overlay; optional only when no root resolution exists")
    parser.add_argument("--resolved-overlay-receipt", type=Path,
                        help="required passing receipt when --resolved-overlay is supplied")
    parser.add_argument("--eligible-occupation-composition", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--private-ad-output", type=Path,
                        help="optional private 800-ad Parquet; must be outside --output-dir")
    parser.add_argument("--old-t1-reference", default="accepted prior full-base T1; not recomputed")
    parser.add_argument("--old-t4-reference", default="accepted prior timing-risk T4; not recomputed")
    args = parser.parse_args()

    validation_receipt = require_passing_validation(args.validation_receipt, args.validated_reviews)
    if args.resolved_overlay and not args.resolved_overlay_receipt:
        raise RuntimeError("--resolved-overlay requires --resolved-overlay-receipt")
    if args.resolved_overlay_receipt and not args.resolved_overlay:
        raise RuntimeError("--resolved-overlay-receipt requires --resolved-overlay")
    overlay_receipt = (require_overlay_receipt(args.resolved_overlay_receipt, args.resolved_overlay)
                       if args.resolved_overlay and args.resolved_overlay_receipt else None)
    reviews, overlay_info = apply_resolved_overlay(read_rows(args.validated_reviews), args.resolved_overlay)
    mapping = read_rows(args.sampled_ad_map)
    rows = validate_and_join(reviews, mapping)
    if len(rows) > 800:
        raise RuntimeError("sampled-ad map exceeds approved 800-ad cap")
    output = args.output_dir
    if args.private_ad_output:
        if args.private_ad_output.suffix.lower() not in {".parquet", ".pq"}:
            raise RuntimeError("--private-ad-output must be a Parquet path")
        try:
            args.private_ad_output.resolve().relative_to(output.resolve())
        except ValueError:
            pass
        else:
            raise RuntimeError("--private-ad-output must be outside --output-dir")
        if len(rows) != 800:
            raise RuntimeError("--private-ad-output requires the complete 800-ad sampled map")
        write_private_ad_parquet(
            args.private_ad_output, rows, sha256_file(args.validated_reviews))
    output.mkdir(parents=True, exist_ok=True)

    tech_counts = collections.Counter(row["semantic_technology_group"] for row in rows)
    support_counts = collections.Counter(
        (str(row["occupation_major"]), row["analysis_technology_group"]) for row in rows
        if usable_occupation_major(row["occupation_major"])
        and row["analysis_technology_group"] in MAIN_GROUPS
    )
    common_majors = {
        occupation for occupation in {key[0] for key in support_counts}
        if all(support_counts[(occupation, group)] >= 5 for group in MAIN_GROUPS)
    }
    scopes = [
        ("all_reviewed_sample", lambda row: True),
        ("common_occupation_major_ge5_each_group", lambda row: usable_occupation_major(row["occupation_major"]) and str(row["occupation_major"]) in common_majors),
    ]
    scopes.extend(("occupation_major_" + occupation, lambda row, o=occupation: str(row["occupation_major"]) == o)
                  for occupation in sorted(common_majors))

    stratum_rows = []
    for h in sorted({stratum_key(row) for row in rows}):
        sample = [row for row in rows if stratum_key(row) == h]
        N_h, n_h, pi3 = sample[0]["N_h"], sample[0]["n_h"], sample[0]["pi3"]
        stratum_rows.append({
            "estimand": "eligible_post_exclusion_fixed10k", "formal_arm": h[0], "entry_stratum": h[1],
            "eligible_ads_N_h": N_h, "sampled_ads_n_h": n_h, "pi3": pi3, "w3": 1/pi3,
            "audited_ads": sum(bool(row["audit_selected"]) for row in sample),
            "unique_review_records": len({row["record_id"] for row in sample}),
        })
    write_csv(output / "T1_FORMAL_SAMPLE.csv", stratum_rows)
    write_csv(output / "T1_OCCUPATION_SUPPORT.csv", [
        {"occupation_major": occupation, "semantic_group": group, "sampled_ads": count,
         "in_common_support": occupation in common_majors}
        for (occupation, group), count in sorted(support_counts.items())
    ])

    measures: list[tuple[str, Callable]] = []
    for dimension in EXP_DIMS:
        measures.append((f"experience_{dimension}", lambda row, d=dimension: outcome_value(row["review"], "experience_outcomes", d)))
    measures.extend([
        ("entry_core_including_conditional", lambda row: core_entry(row["review"], False)),
        ("entry_core_unconditional", lambda row: core_entry(row["review"], True)),
        ("entry_current_student_internship", lambda row: outcome_value(row["review"], "entry_outcomes", "current_student_internship")),
        ("entry_junior_or_entry_label", lambda row: outcome_value(row["review"], "entry_outcomes", "explicit_junior_or_entry_label")),
    ])
    for dimension in RESP_DIMS:
        measures.append((f"strict_current_duty_{dimension}", lambda row, d=dimension: strict_duty(row["review"], d)))
    measures.append(("strict_current_duty_any", lambda row: strict_duty_any(row["review"])))

    rate_rows = [
        measure_rows(rows, name, measure, group, scope_name, scope)
        for scope_name, scope in scopes for group in ("all_technology_groups", *MAIN_GROUPS) for name, measure in measures
    ]
    write_csv(output / "T2_EXPERIENCE_AND_OTHER_RATES.csv", rate_rows)

    clause_acc = collections.defaultdict(lambda: {"sampled_clause_rows": 0, "weighted_clause_rows": 0.0,
                                                   "weighted_years_min_sum": 0.0, "weighted_years_min_mass": 0.0,
                                                   "weighted_years_max_sum": 0.0, "weighted_years_max_mass": 0.0})
    for row in rows:
        group = row["semantic_technology_group"]
        alternative_relations = {a["group"]: a["relation"] for a in row["review"]["qualification_alternatives"]}
        for clause in row["review"]["experience_clauses"]:
            key = (group, clause["object"], clause["strength"], clause["conditionality"],
                   clause["years_relation"], alternative_relations.get(clause["alternative_group"], "no_alternative_group"),
                   bool(clause["alternative_branch"]))
            acc = clause_acc[key]; acc["sampled_clause_rows"] += 1; acc["weighted_clause_rows"] += row["w3"]
            if clause["years_min"] is not None:
                acc["weighted_years_min_sum"] += row["w3"] * clause["years_min"]; acc["weighted_years_min_mass"] += row["w3"]
            if clause["years_max"] is not None:
                acc["weighted_years_max_sum"] += row["w3"] * clause["years_max"]; acc["weighted_years_max_mass"] += row["w3"]
    clause_rows = []
    for key, acc in sorted(clause_acc.items()):
        clause_rows.append({
            "estimand": "clause_level_not_unique_job_minimum", "semantic_group": key[0], "object": key[1],
            "strength": key[2], "conditionality": key[3], "years_relation": key[4],
            "alternative_relation": key[5], "branch_conditioned": key[6],
            "sampled_clause_rows": acc["sampled_clause_rows"], "weighted_clause_rows": acc["weighted_clause_rows"],
            "weighted_mean_years_min": None if not acc["weighted_years_min_mass"] else acc["weighted_years_min_sum"]/acc["weighted_years_min_mass"],
            "weighted_mean_years_max": None if not acc["weighted_years_max_mass"] else acc["weighted_years_max_sum"]/acc["weighted_years_max_mass"],
        })
    write_csv(output / "T2_CLAUSE_SUMMARY.csv", clause_rows)

    transition = collections.defaultdict(lambda: [0, 0.0])
    for row in rows:
        key = (row["formal_arm"], row["semantic_technology_group"])
        transition[key][0] += 1; transition[key][1] += row["w3"]
    transition_rows = [{"estimand": "eligible_post_exclusion_fixed10k_w3", "old_candidate_arm": key[0],
                        "reviewed_semantic_group": key[1], "sampled_ads": value[0], "weighted_ads": value[1]}
                       for key, value in sorted(transition.items())]
    write_csv(output / "T3_OLD_ARM_TO_SEMANTIC_TRANSITION.csv", transition_rows)
    write_csv(output / "T4_PRIOR_TABLE_REFERENCE.csv", [{
        "status": "reference_only_no_full_base_rerun", "old_T1_reference": args.old_t1_reference,
        "old_T4_reference": args.old_t4_reference,
        "claim_boundary": "existing coverage and timing-risk diagnostics; no historical text version claim",
    }])

    combo = collections.defaultdict(lambda: [0, 0.0])
    entry_duty = collections.defaultdict(lambda: [0, 0.0])
    for row in rows:
        if row["analysis_technology_group"] not in MAIN_GROUPS:
            continue
        scope_name = ("common_occupation_major_ge5_each_group"
                      if usable_occupation_major(row["occupation_major"]) and str(row["occupation_major"]) in common_majors else "outside_common_support")
        values = [outcome_value(row["review"], "experience_outcomes", dim) for dim in EXP_DIMS]
        combo_name = "unknown_any" if any(value is None for value in values) else "".join(str(value) for value in values)
        key = (scope_name, row["analysis_technology_group"], combo_name)
        combo[key][0] += 1; combo[key][1] += row["w3"]
        entry, duty = core_entry(row["review"], False), strict_duty_any(row["review"])
        key2 = (scope_name, row["analysis_technology_group"], "unknown" if entry is None else str(entry),
                "unknown" if duty is None else str(duty))
        entry_duty[key2][0] += 1; entry_duty[key2][1] += row["w3"]
    write_csv(output / "T5_EXPERIENCE_COMBINATIONS.csv", [
        {"estimand": "eligible_post_exclusion_fixed10k_w3", "scope": key[0], "semantic_group": key[1],
         "combo_order_general_occupation_industry_tool": key[2], "sampled_ads": value[0], "weighted_ads": value[1]}
        for key, value in sorted(combo.items())
    ])
    write_csv(output / "T5_ENTRY_BY_STRICT_DUTY.csv", [
        {"estimand": "eligible_post_exclusion_fixed10k_w3", "scope": key[0], "semantic_group": key[1],
         "core_entry": key[2], "strict_current_duty_any": key[3], "sampled_ads": value[0], "weighted_ads": value[1]}
        for key, value in sorted(entry_duty.items())
    ])

    comparison_rows = []
    for scope_name, scope in scopes:
        for name, measure in measures:
            result = difference_result(rows, measure, scope)
            comparison_rows.append({"estimand": "eligible_post_exclusion_fixed10k_w3",
                                    "scope": scope_name, "measure": name, **result,
                                    "model_error_included_in_ci": False})
    experience_comparison = [row for row in comparison_rows if row["measure"].startswith("experience_")]
    write_csv(output / "COMPARISON_1_EXPERIENCE.csv", experience_comparison)
    write_csv(output / "COMPARISON_2_ENTRY_DUTY.csv", entry_conditioned_duties(rows, scopes))
    write_csv(output / "SUPPLEMENT_TECH_GROUP_ENTRY_DUTY_DIFFERENCES.csv", [row for row in comparison_rows if not row["measure"].startswith("experience_")])
    write_csv(output / "T6_SENSITIVITY_AND_BOUNDS.csv", rate_rows)

    composition_status = "not_supplied_restricted_pooled_and_within_major_only"
    if args.eligible_occupation_composition:
        composition = read_rows(args.eligible_occupation_composition)
        required = {"occupation_major", "eligible_ads"}
        if any(not required <= set(row) for row in composition):
            raise RuntimeError("eligible occupation composition needs occupation_major and eligible_ads")
        composition_status = "verified_file_supplied_standardized_point_estimates_require_separate_cell_estimator"
        comp = {str(row["occupation_major"]): as_float(row["eligible_ads"], "eligible_ads") for row in composition}
        standardized = []
        for name, measure in measures:
            for group in MAIN_GROUPS:
                weighted_sum = 0.0; mass = 0.0; missing_major = False
                for occupation in sorted(common_majors):
                    subset_scope = lambda row, o=occupation: str(row["occupation_major"]) == o
                    result = measure_rows(rows, name, measure, group, occupation, subset_scope)
                    if result["defined_rate"] is None or occupation not in comp:
                        missing_major = True; continue
                    weighted_sum += comp[occupation] * result["defined_rate"]; mass += comp[occupation]
                standardized.append({"estimand": "eligible10k_common_major_composition_standardized",
                                     "semantic_group": group, "measure": name,
                                     "estimate": None if not mass else weighted_sum/mass,
                                     "composition_mass": mass, "incomplete_major_coverage": missing_major,
                                     "se": None, "ci_low": None, "ci_high": None,
                                     "variance_status": "NA_cell_specific_design_variance_not_implemented"})
        write_csv(output / "T6_COMMON_MAJOR_STANDARDIZED.csv", standardized)

    receipt = {
        "version": VERSION, "status": "complete",
        "code_sha256": sha256_file(Path(__file__)),
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "inputs": {"validated_reviews_sha256": sha256_file(args.validated_reviews),
                   "validation_receipt_sha256": sha256_file(args.validation_receipt),
                   "sampled_ad_map_sha256": sha256_file(args.sampled_ad_map),
                   "eligible_occupation_composition_sha256": None if not args.eligible_occupation_composition else sha256_file(args.eligible_occupation_composition)},
        "counts": {"sampled_ads": len(rows), "validated_context_records": len(reviews),
                   "audited_ads": sum(bool(row["audit_selected"]) for row in rows),
                   "semantic_technology_groups": dict(sorted(tech_counts.items())),
                   "common_support_occupation_majors": len(common_majors)},
        "estimand": "post-exclusion eligible fixed10k advertisements",
        "main_weight": "1/pi3 only",
        "parent_candidate_estimates_in_main": False,
        "common_support_rule": "at least 5 sampled ads in each main semantic group per occupation_major",
        "composition_status": composition_status,
        "variance": "stratified SRS delta-ratio linearization with FPC; NA for non-census n_h<2",
        "ci_limitation": "sampling uncertainty only, conditional on reported semantic groups/support cells; model and support-selection uncertainty excluded",
        "unknown_policy": "field-level unknown, no majority vote or unreviewed propagation; bounds do not cover undetected model error",
        "resolution_overlay": {**overlay_info, "receipt_status": None if overlay_receipt is None else overlay_receipt.get("status")},
        "validator": {"version": validation_receipt.get("version"), "status": validation_receipt.get("status")},
        "claim_boundary": "descriptive delivered-text comparison in the eligible finite frame; no historical, causal, global-accuracy, or full-corpus claim",
        "outputs": {path.name: sha256_file(path) for path in sorted(output.glob("*.csv"))},
        "private_ad_export": (None if not args.private_ad_output else {
            "rows": len(rows), "sha256": sha256_file(args.private_ad_output),
            "contains_raw_text": False, "published_in_git": False,
            "nested_evidence_link": "validated review file hash plus record/context identifiers",
        }),
    }
    atomic_json(output / "ANALYSIS_RECEIPT.json", receipt)


if __name__ == "__main__":
    main()
