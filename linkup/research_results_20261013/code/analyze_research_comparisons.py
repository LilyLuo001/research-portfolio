#!/usr/bin/env python3
"""Finite-frame follow-up comparisons from the frozen formal800 ad measures.

This program consumes only the already-created 800-row ad-level export. It does
not read advertisement text, create labels, change the sample, or estimate a
parent-frame composition.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Callable

VERSION = "research-comparisons-finite800-v1"
EXPECTED_ROWS = 800
EXPECTED_FRAME = 9282
EXPECTED_INPUT_SHA256 = "c3cfbc13db0186b209c7a5a18a33c743b17262c02f46899852e8927e8aaa4f8b"
EXPECTED_REVIEWS_SHA256 = "2939a5846cb6d40f42af94465e764fedcad51b86fc3d387d04d142c51ff63860"
MAJORS = ("11", "13", "15", "17")
ALPHA = {major: 0.25 for major in MAJORS}
GROUP_A = "genai_use_with_or_without_software"
GROUP_B = "traditional_software_use_no_ai"
GROUPS = (GROUP_A, GROUP_B)
EXP = ("general_work", "occupation_task", "industry_domain", "tool_specific")
DUTY = ("independent_judgment", "client_ownership", "people_supervision", "training_mentoring", "any")
REQUIRED = {
    "formal_arm", "entry_stratum", "N_h", "n_h", "pi3", "w3", "occupation_major",
    "analysis_technology_group", "entry_core_including_conditional", "entry_core_unconditional",
    "entry_explicit_new_graduate", *(f"experience_{x}" for x in EXP),
    *(f"strict_current_duty_{x}" for x in DUTY[:-1]), "strict_current_duty_any",
}
BINARY_FIELDS = {"entry_core_including_conditional", "entry_core_unconditional",
                 "entry_explicit_new_graduate", *(f"experience_{x}" for x in EXP),
                 *(f"strict_current_duty_{x}" for x in DUTY[:-1]), "strict_current_duty_any"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    temporary = Path(str(path) + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty table: {path.name}")
    temporary = Path(str(path) + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows=[]
    with path.open(encoding="utf-8") as stream:
        for number,line in enumerate(stream,1):
            if line.strip():
                value=json.loads(line)
                if not isinstance(value,dict):
                    raise RuntimeError(f"non-object structured review at line {number}")
                rows.append(value)
    return rows


def as_int(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise RuntimeError(f"{name} cannot be boolean")
    result = int(value)
    if float(value) != result:
        raise RuntimeError(f"{name} is not integral")
    return result


def as_binary(value: Any, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if value in (0, 1, 0.0, 1.0):
        return int(value)
    raise RuntimeError(f"{name} is not binary/NA: {value!r}")


def major(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def hkey(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["formal_arm"]), str(row["entry_stratum"])


def load_rows(path: Path) -> list[dict[str, Any]]:
    if sha256_file(path) != EXPECTED_INPUT_SHA256:
        raise RuntimeError("frozen ad-level input SHA-256 mismatch")
    import pyarrow.parquet as pq
    table = pq.read_table(path)
    if table.num_rows != EXPECTED_ROWS:
        raise RuntimeError(f"expected {EXPECTED_ROWS} rows, found {table.num_rows}")
    missing = REQUIRED - set(table.column_names)
    if missing:
        raise RuntimeError("missing required fields: " + ",".join(sorted(missing)))
    rows = table.to_pylist()
    contracts: dict[tuple[str, str], tuple[int, int, float]] = {}
    observed: dict[tuple[str, str], int] = {}
    for row in rows:
        N_h, n_h = as_int(row["N_h"], "N_h"), as_int(row["n_h"], "n_h")
        pi3 = float(row["pi3"])
        if not (0 < n_h <= N_h) or not math.isclose(pi3, n_h / N_h, abs_tol=1e-12):
            raise RuntimeError("invalid finite-stratum contract")
        if not math.isclose(float(row["w3"]), 1.0 / pi3, abs_tol=1e-12):
            raise RuntimeError("w3 is not 1/pi3")
        row["N_h"], row["n_h"], row["pi3"], row["w3"] = N_h, n_h, pi3, 1.0 / pi3
        row["occupation_major"] = major(row["occupation_major"])
        for field in BINARY_FIELDS:
            row[field] = as_binary(row[field], field)
        h = hkey(row)
        contract = (N_h, n_h, pi3)
        if h in contracts and contracts[h] != contract:
            raise RuntimeError("inconsistent finite-stratum contract")
        contracts[h] = contract
        observed[h] = observed.get(h, 0) + 1
    if any(observed[h] != contract[1] for h, contract in contracts.items()):
        raise RuntimeError("stratum row conservation failed")
    if sum(contract[0] for contract in contracts.values()) != EXPECTED_FRAME:
        raise RuntimeError("eligible finite frame is not 9,282")
    support = {(m, g): sum(r["occupation_major"] == m and r["analysis_technology_group"] == g for r in rows)
               for m in MAJORS for g in GROUPS}
    if any(support[cell] < 5 for cell in support):
        raise RuntimeError("fixed common-support major no longer has >=5 ads per group")
    return rows


def bind_structured_reviews(rows: list[dict[str, Any]], path: Path) -> dict[str, dict[str, Any]]:
    if sha256_file(path) != EXPECTED_REVIEWS_SHA256:
        raise RuntimeError("frozen validated structured-review SHA-256 mismatch")
    expected_columns={"validated_nested_review_jsonl_sha256","validated_nested_review_record_id",
                      "validated_nested_review_context_sha256"}
    if any(not expected_columns <= set(r) for r in rows):
        raise RuntimeError("ad-level export lacks structured-review binding columns")
    if any(r["validated_nested_review_jsonl_sha256"] != EXPECTED_REVIEWS_SHA256 for r in rows):
        raise RuntimeError("ad-level export is not bound to supplied structured reviews")
    reviews=read_jsonl(path); by_id={}
    for review in reviews:
        rid=review.get("record_id")
        if not isinstance(rid,str) or not rid or rid in by_id:
            raise RuntimeError("structured reviews have empty or duplicate record_id")
        by_id[rid]=review
    for row in rows:
        rid=row["validated_nested_review_record_id"]
        review=by_id.get(rid)
        if review is None or review.get("context_sha256") != row["validated_nested_review_context_sha256"]:
            raise RuntimeError("structured review record/context binding mismatch")
    return by_id


def graduate_unconditional(row: dict[str, Any]) -> int | None:
    grad=row["entry_explicit_new_graduate"]
    if grad is None:
        return None
    if grad == 0:
        return 0
    review=row["structured_review"]
    items=[x for x in review.get("entry_items",[]) if x.get("target")=="explicit_new_graduate"]
    conditions={x.get("conditionality") for x in items}
    if "unconditional" in conditions:
        return 1
    if items and conditions <= {"conditional"}:
        return 0
    return None


def clause_supplement(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    aggregate: dict[tuple[Any,...], dict[str,Any]]={}
    unresolved_ads=0; unresolved_weight=0.0; retained_clauses=0; excluded_clauses=0
    for row in rows:
        if row["entry_explicit_new_graduate"] != 1:
            continue
        seen=set(); unresolved_this=False
        for clause in row["structured_review"].get("experience_clauses",[]):
            obj=clause.get("object"); field=f"experience_{obj}"
            if obj not in EXP or row[field] is None:
                excluded_clauses += 1; unresolved_this=True; continue
            key=(obj,str(clause.get("strength")),str(clause.get("conditionality")),
                 str(clause.get("years_relation")),clause.get("years_min"),clause.get("years_max"),
                 clause.get("alternative_group") is not None,clause.get("alternative_branch") is not None)
            bucket=aggregate.setdefault(key,{"sampled_clauses":0,"sampled_ads":0,"weighted_ads":0.0})
            bucket["sampled_clauses"] += 1; retained_clauses += 1
            if key not in seen:
                bucket["sampled_ads"] += 1; bucket["weighted_ads"] += row["w3"]; seen.add(key)
        if unresolved_this:
            unresolved_ads += 1; unresolved_weight += row["w3"]
    output=[]
    for key,bucket in sorted(aggregate.items(),key=lambda x:tuple(map(str,x[0]))):
        obj,strength,conditionality,years_relation,years_min,years_max,has_group,is_branch=key
        output.append({"estimand":"existing_clause_cooccurrence_among_explicit_new_graduate_ads",
                       "status":"retained_existing_clauses",
                       "object":obj,"strength":strength,"conditionality":conditionality,
                       "years_relation":years_relation,"years_min":years_min,"years_max":years_max,
                       "has_alternative_group":has_group,"is_alternative_branch":is_branch,**bucket,
                       "literal_years_are_not_job_level_minimum":True})
    if not output:
        output.append({"estimand":"existing_clause_cooccurrence_among_explicit_new_graduate_ads",
                       "status":"no_retained_clauses","object":None,"strength":None,
                       "conditionality":None,"years_relation":None,"years_min":None,"years_max":None,
                       "has_alternative_group":None,"is_alternative_branch":None,"sampled_clauses":0,
                       "sampled_ads":0,"weighted_ads":0.0,"literal_years_are_not_job_level_minimum":True})
    return output,{"retained_clauses":retained_clauses,"excluded_masked_or_unrecognized_clauses":excluded_clauses,
                   "ads_with_excluded_unknown_object_clause":unresolved_ads,
                   "weighted_ads_with_excluded_unknown_object_clause":unresolved_weight,
                   "waivers_separate":"strength=explicitly_waived rows are not counted as nonwaived experience"}


def experience_combinations(rows: list[dict[str, Any]], entry_defs: tuple) -> list[dict[str,Any]]:
    output=[]
    selected={"explicit_new_graduate_primary",
              "existing_broad_waiver_or_graduate_including_conditional_secondary"}
    for name,entry in entry_defs:
        if name not in selected:
            continue
        buckets: dict[str,tuple[int,float]]={}
        for row in rows:
            if entry(row) != 1:
                continue
            values=[row[f"experience_{d}"] for d in EXP]
            combo="unknown_any" if any(v is None for v in values) else "".join(str(v) for v in values)
            count,mass=buckets.get(combo,(0,0.0)); buckets[combo]=(count+1,mass+row["w3"])
        for combo,(count,mass) in sorted(buckets.items()):
            output.append({"estimand":"experience_combination_among_positive_eligibility_wording_all_technology_groups",
                           "eligibility_definition":name,
                           "combo_order_general_occupation_industry_tool":combo,
                           "sampled_ads":count,"weighted_ads":mass,
                           "unknown_preserved":combo=="unknown_any"})
    return output


def totals(rows: list[dict[str, Any]], x: Callable, y: Callable) -> tuple[float | None, float, float]:
    X = sum(r["w3"] * float(x(r)) for r in rows)
    Y = sum(r["w3"] * float(y(r)) for r in rows)
    return (None if X <= 0 else Y / X), X, Y


def design_se(rows: list[dict[str, Any]], influence: Callable[[dict[str, Any]], float]) -> tuple[float | None, str]:
    variance = 0.0
    for h in sorted({hkey(r) for r in rows}):
        sample = [r for r in rows if hkey(r) == h]
        N_h, n_h = sample[0]["N_h"], sample[0]["n_h"]
        if n_h == N_h:
            continue
        if n_h < 2:
            return None, "NA_n_h_lt_2_non_census"
        u = [float(influence(r)) for r in sample]
        mean = sum(u) / n_h
        s2 = sum((z - mean) ** 2 for z in u) / (n_h - 1)
        variance += N_h * N_h * (1.0 - n_h / N_h) * s2 / n_h
    return math.sqrt(max(0.0, variance)), "design_linearized"


def ratio(rows: list[dict[str, Any]], domain: Callable, value: Callable) -> dict[str, Any]:
    x = lambda r: int(domain(r) and value(r) is not None)
    y = lambda r: int(domain(r) and value(r) == 1)
    all_x = lambda r: int(domain(r))
    unk = lambda r: int(domain(r) and value(r) is None)
    rate, X, Y = totals(rows, x, y)
    _, A, _ = totals(rows, all_x, lambda r: 0)
    if rate is None:
        return {"sampled_ads": sum(domain(r) for r in rows), "known_ads": sum(x(r) for r in rows),
                "unknown_ads": sum(unk(r) for r in rows), "positive_ads":sum(y(r) for r in rows),
                "weighted_all": A, "weighted_positive":Y,
                "weighted_known": X, "rate": None, "se": None, "ci_low": None, "ci_high": None,
                "lower_bound": None if A <= 0 else Y / A,
                "upper_bound": None if A <= 0 else (Y + A - X) / A,
                "variance_status": "no_known_denominator", "zero_events":Y==0,
                "degenerate_linearized_se":False,"zero_or_degenerate_not_proof_of_absence":True}
    se, status = design_se(rows, lambda r: (float(y(r)) - rate * float(x(r))) / X)
    return {"sampled_ads": sum(domain(r) for r in rows), "known_ads": sum(x(r) for r in rows),
            "unknown_ads": sum(unk(r) for r in rows), "positive_ads":sum(y(r) for r in rows),
            "weighted_all": A, "weighted_known": X, "weighted_positive":Y,
            "rate": rate, "se": se,
            "ci_low": None if se is None else max(0.0, rate - 1.96 * se),
            "ci_high": None if se is None else min(1.0, rate + 1.96 * se),
            "lower_bound": None if A <= 0 else Y / A,
            "upper_bound": None if A <= 0 else (Y + A - X) / A,
            "variance_status": status, "zero_events":Y==0,
            "degenerate_linearized_se":se==0.0,
            "zero_or_degenerate_not_proof_of_absence":bool(Y==0 or se==0.0)}


def contrast(rows: list[dict[str, Any]], scope: Callable, value: Callable) -> dict[str, Any]:
    cells = {}
    for group in GROUPS:
        domain = lambda r, g=group: scope(r) and r["analysis_technology_group"] == g
        x = lambda r, d=domain: int(d(r) and value(r) is not None)
        y = lambda r, d=domain: int(d(r) and value(r) == 1)
        result = ratio(rows, domain, value)
        cells[group] = (result, x, y)
    a, xa, ya = cells[GROUP_A]
    b, xb, yb = cells[GROUP_B]
    if a["rate"] is None or b["rate"] is None:
        delta, se, status = None, None, "no_known_denominator"
    else:
        delta = a["rate"] - b["rate"]
        se, status = design_se(rows, lambda r:
            (float(ya(r)) - a["rate"] * float(xa(r))) / a["weighted_known"]
            - (float(yb(r)) - b["rate"] * float(xb(r))) / b["weighted_known"])
    return {
        "group_a": GROUP_A, "group_b": GROUP_B,
        **{f"group_a_{k}": v for k, v in a.items()},
        **{f"group_b_{k}": v for k, v in b.items()},
        "difference_a_minus_b": delta, "difference_se": se,
        "difference_ci_low": None if se is None else delta - 1.96 * se,
        "difference_ci_high": None if se is None else delta + 1.96 * se,
        "difference_lower_bound": (None if a["lower_bound"] is None or b["upper_bound"] is None
                                   else a["lower_bound"] - b["upper_bound"]),
        "difference_upper_bound": (None if a["upper_bound"] is None or b["lower_bound"] is None
                                   else a["upper_bound"] - b["lower_bound"]),
        "difference_variance_status": status,
        "difference_degenerate_linearized_se":se==0.0,
        "zero_or_degenerate_not_proof_of_absence":bool(a["zero_events"] or b["zero_events"] or se==0.0),
    }


def standardized(rows: list[dict[str, Any]], value: Callable) -> dict[str, Any]:
    cells: dict[tuple[str, str], tuple[dict[str, Any], Callable, Callable]] = {}
    missing = []
    for m in MAJORS:
        for g in GROUPS:
            domain = lambda r, mm=m, gg=g: r["occupation_major"] == mm and r["analysis_technology_group"] == gg
            x = lambda r, d=domain: int(d(r) and value(r) is not None)
            y = lambda r, d=domain: int(d(r) and value(r) == 1)
            result = ratio(rows, domain, value)
            cells[m, g] = (result, x, y)
            if result["rate"] is None:
                missing.append(f"{m}:{g}")
    if missing:
        return {"group_a_rate": None, "group_b_rate": None, "difference_a_minus_b": None,
                "se": None, "ci_low": None, "ci_high": None,
                "group_a_lower_bound":None,"group_a_upper_bound":None,
                "group_b_lower_bound":None,"group_b_upper_bound":None,
                "difference_lower_bound": None, "difference_upper_bound": None,
                "variance_status": "NA_zero_known_denominator:" + "|".join(missing),
                "group_a_zero_events":None,"group_b_zero_events":None,
                "degenerate_linearized_se":False,"zero_or_degenerate_not_proof_of_absence":True}
    rates = {g: sum(ALPHA[m] * cells[m, g][0]["rate"] for m in MAJORS) for g in GROUPS}
    delta = rates[GROUP_A] - rates[GROUP_B]
    def influence(r: dict[str, Any]) -> float:
        total = 0.0
        for m in MAJORS:
            a, xa, ya = cells[m, GROUP_A]
            b, xb, yb = cells[m, GROUP_B]
            total += ALPHA[m] * ((float(ya(r)) - a["rate"] * float(xa(r))) / a["weighted_known"]
                                 - (float(yb(r)) - b["rate"] * float(xb(r))) / b["weighted_known"])
        return total
    se, status = design_se(rows, influence)
    lower = {g: sum(ALPHA[m] * cells[m, g][0]["lower_bound"] for m in MAJORS) for g in GROUPS}
    upper = {g: sum(ALPHA[m] * cells[m, g][0]["upper_bound"] for m in MAJORS) for g in GROUPS}
    return {"group_a_rate": rates[GROUP_A], "group_b_rate": rates[GROUP_B],
            "difference_a_minus_b": delta, "se": se,
            "ci_low": None if se is None else delta - 1.96 * se,
            "ci_high": None if se is None else delta + 1.96 * se,
            "group_a_lower_bound": lower[GROUP_A], "group_a_upper_bound": upper[GROUP_A],
            "group_b_lower_bound": lower[GROUP_B], "group_b_upper_bound": upper[GROUP_B],
            "difference_lower_bound": lower[GROUP_A] - upper[GROUP_B],
            "difference_upper_bound": upper[GROUP_A] - lower[GROUP_B],
            "variance_status": status,
            "group_a_zero_events":sum(cells[m,GROUP_A][0]["positive_ads"] for m in MAJORS)==0,
            "group_b_zero_events":sum(cells[m,GROUP_B][0]["positive_ads"] for m in MAJORS)==0,
            "degenerate_linearized_se":se==0.0,
            "zero_or_degenerate_not_proof_of_absence":bool(se==0.0 or
                sum(cells[m,GROUP_A][0]["positive_ads"] for m in MAJORS)==0 or
                sum(cells[m,GROUP_B][0]["positive_ads"] for m in MAJORS)==0)}


def verify_existing(q1_rows: list[dict[str, Any]], existing_path: Path) -> dict[str, Any]:
    existing = read_csv(existing_path)
    scopes = {"common_occupation_major_ge5_each_group", *(f"occupation_major_{m}" for m in MAJORS)}
    expected = {(r["scope"], r["measure"]): r for r in existing if r["scope"] in scopes}
    if len(expected) != 20:
        raise RuntimeError("existing comparison does not have 20 required Q1 rows")
    for row in q1_rows:
        old = expected.get((row["scope"], "experience_" + row["dimension"]))
        if old is None:
            # Published pooled scope has its original long name.
            if row["scope"] == "pooled_common_support":
                old = next((x for x in existing if x["scope"] == "common_occupation_major_ge5_each_group"
                            and x["measure"] == "experience_" + row["dimension"]), None)
        if old is None:
            raise RuntimeError("missing published Q1 identity row")
        checks = (("group_a_rate", "group_a_rate"), ("group_b_rate", "group_b_rate"),
                  ("difference_a_minus_b", "difference_a_minus_b"), ("difference_se", "se"))
        for new_key, old_key in checks:
            if not math.isclose(float(row[new_key]), float(old[old_key]), rel_tol=0, abs_tol=1e-12):
                raise RuntimeError(f"published Q1 identity mismatch: {row['scope']} {row['dimension']} {new_key}")
    return {"status": "pass", "rows_reproduced": 20, "absolute_tolerance": 1e-12,
            "published_table_sha256": sha256_file(existing_path)}


def numeric_self_test() -> dict[str, Any]:
    # Two strata, including a census stratum. Both group-major residuals are
    # combined in one influence per unit; covariance is therefore retained.
    toy = []
    for g, m, v in [(GROUP_A,"11",1),(GROUP_A,"11",0),(GROUP_B,"11",0),(GROUP_B,"11",0),
                    (GROUP_A,"13",0),(GROUP_A,"13",0),(GROUP_B,"13",1),(GROUP_B,"13",0)]:
        toy.append({"formal_arm":"h1", "entry_stratum":"x", "N_h":16, "n_h":8, "w3":2.0,
                    "analysis_technology_group":g, "occupation_major":m, "v":v})
    for g in GROUPS:
        for m in ("15", "17"):
            toy.append({"formal_arm":"h2", "entry_stratum":"x", "N_h":4, "n_h":4, "w3":1.0,
                        "analysis_technology_group":g, "occupation_major":m, "v":1})
    result = standardized(toy, lambda r: r["v"])
    if not math.isclose(result["difference_a_minus_b"], 0.0, abs_tol=1e-15):
        raise RuntimeError("numeric self-test point identity failed")
    if result["se"] is None or not math.isclose(result["se"], math.sqrt(1.0 / 112.0),
                                                 rel_tol=0, abs_tol=1e-15):
        raise RuntimeError("numeric self-test covariance/FPC path failed")
    census = [{"formal_arm":"c", "entry_stratum":"x", "N_h":2, "n_h":2},
              {"formal_arm":"c", "entry_stratum":"x", "N_h":2, "n_h":2}]
    census_se, census_status = design_se(census, lambda r: 1.0 if r is census[0] else -1.0)
    if census_se != 0.0 or census_status != "design_linearized":
        raise RuntimeError("numeric self-test census FPC identity failed")
    zero = standardized(toy, lambda r: None if r["occupation_major"] == "17" and r["analysis_technology_group"] == GROUP_A else r["v"])
    if not str(zero["variance_status"]).startswith("NA_zero_known_denominator:17:"):
        raise RuntimeError("numeric self-test empty-major fail-closed path failed")
    return {"status":"pass", "joint_influence_difference":result["difference_a_minus_b"],
            "joint_influence_se":result["se"], "expected_se":"sqrt(1/112)",
            "census_nonconstant_influence_se":census_se, "census_fpc_exercised":True,
            "empty_major_status":zero["variance_status"]}


def render_figures(output: Path, q1: list[dict[str, Any]], q2d: list[dict[str, Any]], q2e: list[dict[str, Any]]) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"figure.dpi": 140, "savefig.dpi": 180, "font.size": 9})
    specs = []
    std = q1
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    y = list(range(len(std))); defined=[(i,r) for i,r in enumerate(std)
                                        if r["difference_a_minus_b"] is not None and r["se"] is not None]
    if defined:
        ax.errorbar([r["difference_a_minus_b"] for _,r in defined], [i for i,_ in defined],
                    xerr=[1.96*r["se"] for _,r in defined], fmt="o", color="#2457A7", capsize=3)
    for i,r in enumerate(std):
        if r["difference_a_minus_b"] is None or r["se"] is None:
            ax.annotate("NA",(0,i),xytext=(4,0),textcoords="offset points",va="center",color="#666666")
    ax.axvline(0, color="black", lw=.8); ax.set_yticks(y, [r["dimension"].replace("_", " ") for r in std])
    ax.set_xlabel("GenAI minus traditional software rate"); ax.set_title("Q1: equal-major standardized experience differences")
    ax.grid(axis="x", alpha=.25); fig.tight_layout(); specs.append((fig,"FIG1_Q1_EQUAL_MAJOR"))
    for data, stem, title in [(q2d,"FIG2_Q2_NEW_GRAD_DUTIES","Q2: duties among explicit new-graduate ads"),
                              (q2e,"FIG3_Q2_NEW_GRAD_EXPERIENCE","Q2: experience wording among explicit new-graduate ads")]:
        fig, ax = plt.subplots(figsize=(7.2, 3.8)); y = list(range(len(data)))
        defined=[(i,r) for i,r in enumerate(data) if r["rate"] is not None]
        if defined:
            ax.errorbar([r["rate"] for _,r in defined], [i for i,_ in defined],
                        xerr=[0 if r["se"] is None else 1.96*r["se"] for _,r in defined],
                        fmt="o", color="#9A3E25", capsize=3)
        for i,r in enumerate(data):
            if r["rate"] is None:
                ax.annotate("NA",(0,i),xytext=(4,0),textcoords="offset points",va="center",color="#666666")
        ax.set_xlim(-.05,1.05); ax.set_yticks(y,[r["dimension"].replace("_"," ") for r in data])
        ax.set_xlabel("Defined weighted rate"); ax.set_title(title); ax.grid(axis="x",alpha=.25); fig.tight_layout(); specs.append((fig,stem))
    names=[]
    for fig, stem in specs:
        for suffix in ("png","pdf"):
            name=f"{stem}.{suffix}"; fig.savefig(output/name); names.append(name)
        plt.close(fig)
    return names


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ad-level", type=Path, required=True)
    parser.add_argument("--validated-reviews", type=Path, required=True)
    parser.add_argument("--existing-q1", type=Path, required=True)
    parser.add_argument("--existing-results", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    self_test = numeric_self_test()
    rows = load_rows(args.ad_level)
    reviews=bind_structured_reviews(rows,args.validated_reviews)
    for row in rows:
        row["structured_review"]=reviews[row["validated_nested_review_record_id"]]
    value = {d: (lambda r, dd=d: r[f"experience_{dd}"]) for d in EXP}
    q1_all=[]
    for scope_name, scope in [("pooled_common_support", lambda r: r["occupation_major"] in MAJORS),
                              *((f"occupation_major_{m}", lambda r, mm=m: r["occupation_major"] == mm) for m in MAJORS)]:
        for d in EXP:
            q1_all.append({"estimand":"finite9282_main_weight_1_over_pi3", "scope":scope_name,
                           "dimension":d, **contrast(rows,scope,value[d]), "model_error_included_in_ci":False})
    identity = verify_existing(q1_all,args.existing_q1)
    equal=[]
    for d in EXP:
        equal.append({"estimand":"equal_major_standardized_common_occupation_composition",
                      "composition":"fixed_25pct_each_majors_11_13_15_17_not_population_estimate",
                      "dimension":d, **standardized(rows,value[d]), "model_error_included_in_ci":False})
    q2_elig=[]
    entry_defs=(("explicit_new_graduate_primary",lambda r:r["entry_explicit_new_graduate"]),
                ("explicit_new_graduate_unconditional_sensitivity",graduate_unconditional),
                ("existing_broad_waiver_or_graduate_including_conditional_secondary",lambda r:r["entry_core_including_conditional"]),
                ("existing_broad_waiver_or_graduate_unconditional_secondary",lambda r:r["entry_core_unconditional"]))
    for name, entry in entry_defs:
        r=ratio(rows,lambda x:True,entry)
        q2_elig.append({"estimand":"eligibility_wording_all_technology_groups", "eligibility_definition":name, **r})
    def q2_table(measures: tuple[str,...], prefix: str) -> list[dict[str,Any]]:
        output=[]
        for entry_name, entry in entry_defs:
            for d in measures:
                field=("strict_current_duty_any" if d=="any" else f"{prefix}{d}")
                result=ratio(rows,lambda r,e=entry:e(r)==1,lambda r,f=field:r[f])
                output.append({"estimand":"measure_among_positive_eligibility_wording_all_technology_groups",
                               "eligibility_definition":entry_name,"dimension":d,
                               "entry_membership_unknown_ads":sum(entry(r) is None for r in rows),**result})
                output[-1]["weighted_entry_membership_unknown"] = sum(
                    r["w3"] for r in rows if entry(r) is None)
        return output
    q2d=q2_table(DUTY,"strict_current_duty_")
    q2e=q2_table(EXP,"experience_")
    q2c=experience_combinations(rows,entry_defs)
    clauses,clause_counts=clause_supplement(rows)
    write_csv(args.output_dir/"Q1_WITHIN_MAJOR_AND_POOLED.csv",q1_all)
    write_csv(args.output_dir/"Q1_EQUAL_MAJOR_STANDARDIZED.csv",equal)
    write_csv(args.output_dir/"Q2_ELIGIBILITY_SENSITIVITY.csv",q2_elig)
    write_csv(args.output_dir/"Q2_DUTIES_AMONG_ELIGIBLE.csv",q2d)
    write_csv(args.output_dir/"Q2_EXPERIENCE_AMONG_ELIGIBLE.csv",q2e)
    write_csv(args.output_dir/"Q2_EXPERIENCE_COMBINATIONS.csv",q2c)
    write_csv(args.output_dir/"Q2_EXISTING_CLAUSE_COOCCURRENCES_AMONG_NEW_GRAD.csv",clauses)
    figures=render_figures(args.output_dir,equal,
        [r for r in q2d if r["eligibility_definition"]=="explicit_new_graduate_primary"],
        [r for r in q2e if r["eligibility_definition"]=="explicit_new_graduate_primary"])
    preserved={p.name:sha256_file(p) for p in sorted(args.existing_results.iterdir()) if p.is_file()}
    atomic_json(args.output_dir/"EXISTING_RESULTS_MANIFEST.json",{"source":str(args.existing_results),"files":preserved})
    output_names=["Q1_WITHIN_MAJOR_AND_POOLED.csv","Q1_EQUAL_MAJOR_STANDARDIZED.csv",
                  "Q2_ELIGIBILITY_SENSITIVITY.csv","Q2_DUTIES_AMONG_ELIGIBLE.csv",
                  "Q2_EXPERIENCE_AMONG_ELIGIBLE.csv","Q2_EXPERIENCE_COMBINATIONS.csv",
                  "Q2_EXISTING_CLAUSE_COOCCURRENCES_AMONG_NEW_GRAD.csv",
                  "EXISTING_RESULTS_MANIFEST.json",*figures]
    receipt={"version":VERSION,"status":"pass","created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
             "code_sha256":sha256_file(Path(__file__)),"input":{"path":str(args.ad_level),"sha256":sha256_file(args.ad_level),"rows":len(rows),
                 "validated_structured_reviews_sha256":sha256_file(args.validated_reviews),"validated_structured_review_records":len(reviews)},
             "frame":{"eligible_ads":EXPECTED_FRAME,"sampled_ads":EXPECTED_ROWS,"main_weight":"1/pi3","parent_weight_used":False},
             "fixed_common_support":{"majors":list(MAJORS),"rule":"predecided >=5 sampled ads in each semantic group"},
             "equal_major_composition":{"weights":ALPHA,"interpretation":"fixed hypothetical composition, not estimated population composition"},
             "variance":"stratified SRS linearization of weighted sum of within-major domain ratios; one unit influence over all 800 rows retains covariance; census FPC; NA for unidentified non-census singleton",
             "unknown_policy":"known denominators exclude field unknown; bounds assign unknown outcomes 0/1; zero known denominator in any group-major makes standardized rate/difference NA without dropping major",
             "q1_existing_identity":identity,"numeric_self_test":self_test,
             "q2_main":{"eligibility":"explicit_new_graduate","technology_scope":"all_technology_groups",
                        "expected_sampled_positive_ads":33,"observed_sampled_positive_ads":sum(r["entry_explicit_new_graduate"]==1 for r in rows)},
             "q2_secondary":{"eligibility":"existing broad waiver-or-graduate wording including conditional",
                             "expected_sampled_positive_ads":54,
                             "observed_sampled_positive_ads":sum(r["entry_core_including_conditional"]==1 for r in rows)},
             "q2_clause_supplement":clause_counts,
             "retained_structured_fields":{"literal_year_clause":True,"qualification_alternative":True,"experience_waiver":True,
                 "source":"hash-bound final validated structured reviews; aggregate only; no quote fields accessed"},
             "unavailable_retained_fields":{"contradiction_flag":False,
                 "reason":"no contradiction flag exists; cooccurrences are not interpreted as logical contradictions"},
             "semantic_changes":False,"text_read_or_extracted":False,"sample_or_labels_changed":False,
             "claim_boundary":"descriptive finite-frame delivered-text comparison; sampling CI excludes model/classification and support-selection uncertainty",
             "outputs":{name:sha256_file(args.output_dir/name) for name in output_names}}
    if receipt["q2_main"]["observed_sampled_positive_ads"] != 33:
        raise RuntimeError("explicit-new-graduate positive count is not the predeclared 33")
    if receipt["q2_secondary"]["observed_sampled_positive_ads"] != 54:
        raise RuntimeError("broad-waiver-or-graduate positive count is not the predeclared 54")
    atomic_json(args.output_dir/"ANALYSIS_RECEIPT.json",receipt)


if __name__ == "__main__":
    main()
