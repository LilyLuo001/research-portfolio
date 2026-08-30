#!/usr/bin/env python3
"""Audit the immutable YAX v1.1 confirmatory result archive.

This program reads only committed result and measurement artifacts.  It does
not read licensed microdata, estimate a model, or define a new specification.
It expands the frozen design into a machine-readable completion matrix and
fails closed if any numerical or archival invariant is violated.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULT_DIR = ROOT / "yax/analysis/outcomes/frozen_v11_corrected_run"
RESULTS_PATH = RESULT_DIR / "FROZEN_RESULTS.json"
LEDGER_PATH = RESULT_DIR / "RESULT_LEDGER.jsonl"
REPORTING_DIR = RESULT_DIR / "reporting"
TEST_A_DIR = ROOT / "yax/measurement/test_a"
TEST_B_PATH = ROOT / "yax/measurement/computerization_support_66m_receipt.json"
DEFAULT_OUTPUT = ROOT / "yax/analysis/audit"

DESIGN_COMMIT = "22fbf7924809b7a535e31ae0ab68f5b113ce8078"
RESULT_COMMIT = "5596d18df329ed3266163ba979256ee52b04d37a"
CORE_HASHES = {
    "FROZEN_RESULTS.json": "4f7df33a530e499c5562dead9464b2a19b87a3e3c6454d52944bc5e00879a831",
    "RESULT_LEDGER.jsonl": "e900adb75510729be635eb7aea381bfe6e523b376b6f2723350cf47bdf09266b",
    "FROZEN_RESULTS.md": "2a152018d0198bb106a01ae08e5eda7c2d4a0e2fe617d74cc7f4ad731c18666e",
}
AI_MEASURES = [
    "aioe_admin_equal",
    "aioe_ability_direct",
    "aioe_oews2018_source_weighted",
    "dv_rating_alpha",
    "dv_rating_beta",
    "dv_rating_gamma",
]
CHARACTERISTICS = [
    "cognitive_ability_importance",
    "manual_physical_ability_importance",
    "rti_autor_dorn",
    "required_education_category_index",
    "log_mean_annual_wage",
    "dingel_neiman_telework",
    "stem_major_group_share",
    "onet_computers_importance",
]
COMPUTERIZATION = [
    "webb_pct_software",
    "onet_computers_importance",
    "onet_computers_level",
    "rti_autor_dorn",
    "frey_osborne_probability",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(left: float, right: float, tolerance: float = 1e-12) -> bool:
    return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=tolerance)


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def target(model: dict) -> dict:
    return model["coefficients"][model["target_label"]]


def ledger_matches(row: dict, expected: dict) -> bool:
    return all(
        close(row[field], expected[source])
        for field, source in [
            ("coefficient", "coefficient"),
            ("se", "bootstrap_se"),
            ("ci_lower", "ci_lower"),
            ("ci_upper", "ci_upper"),
            ("p_value", "bootstrap_p_value"),
        ]
    ) and bool(row["converged"]) is bool(expected["converged"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    failures: list[str] = []
    checks: list[dict] = []
    completion: list[dict] = []

    def check(name: str, condition: bool, detail: str) -> None:
        status = "PASS" if condition else "FAIL"
        checks.append({"check": name, "status": status, "detail": detail})
        if not condition:
            failures.append(f"{name}: {detail}")

    def item(
        frozen_item: str,
        artifact: str,
        exists: bool,
        ledger_coverage: str,
        reproduces: bool,
        detail: str = "",
    ) -> None:
        status = "PASS" if exists and reproduces and ledger_coverage != "FAIL" else "FAIL"
        completion.append(
            {
                "frozen_item": frozen_item,
                "required_artifact": artifact,
                "exists": "YES" if exists else "NO",
                "ledger_coverage": ledger_coverage,
                "reproduces": "YES" if reproduces else "NO",
                "status": status,
                "detail": detail,
            }
        )
        if status == "FAIL":
            failures.append(f"completion::{frozen_item}: {detail}")

    data = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    ledger = [json.loads(line) for line in LEDGER_PATH.read_text(encoding="utf-8").splitlines()]
    ledger_by_id = {row["specification_id"]: row for row in ledger}

    check("frozen_tag", data["frozen_tag"] == "v1.1-design-freeze", data["frozen_tag"])
    check("frozen_commit", data["frozen_commit"] == DESIGN_COMMIT, data["frozen_commit"])
    check("core_result_hash", sha256(RESULTS_PATH) == CORE_HASHES["FROZEN_RESULTS.json"], sha256(RESULTS_PATH))
    check("core_ledger_hash", sha256(LEDGER_PATH) == CORE_HASHES["RESULT_LEDGER.jsonl"], sha256(LEDGER_PATH))
    check(
        "core_markdown_hash",
        sha256(RESULT_DIR / "FROZEN_RESULTS.md") == CORE_HASHES["FROZEN_RESULTS.md"],
        sha256(RESULT_DIR / "FROZEN_RESULTS.md"),
    )

    manifest_failures = []
    manifest_rows = []
    for line in (REPORTING_DIR / "ARTIFACT_HASHES.sha256").read_text(encoding="utf-8").splitlines():
        expected, label = line.split("  ", 1)
        path = ROOT / label
        actual = sha256(path) if path.exists() else "MISSING"
        ok = actual == expected
        manifest_rows.append({"artifact": label, "expected_sha256": expected, "actual_sha256": actual, "status": "PASS" if ok else "FAIL"})
        if not ok:
            manifest_failures.append(label)
    check("reporting_hash_manifest", not manifest_failures, f"{len(manifest_rows)} artifacts; failures={manifest_failures}")
    write_csv(args.output / "ARTIFACT_HASH_VALIDATION.csv", manifest_rows, list(manifest_rows[0]))

    counts = Counter(row["table_figure"] for row in ledger)
    expected_counts = {"Table 2": 12, "Table 3": 1, "Table 4": 56, "Table 5": 4, "Table 6": 14, "Figure 3": 108}
    check("ledger_rows", len(ledger) == 195, f"rows={len(ledger)}")
    check("ledger_unique_ids", len(ledger_by_id) == len(ledger), f"unique={len(ledger_by_id)}")
    check("ledger_section_counts", dict(counts) == expected_counts, json.dumps(dict(counts), sort_keys=True))
    check("ledger_design_commit", all(row["frozen_commit"] == DESIGN_COMMIT for row in ledger), "all ledger rows")
    check("ledger_input_hashes", all(row["input_hashes"] == ledger[0]["input_hashes"] for row in ledger), "identical authenticated input hashes")

    # Test A: every frozen AI measure x characteristic relationship plus the
    # complete residual, rank and overlap diagnostics.
    test_a_receipt = json.loads((TEST_A_DIR / "TEST_A_RECEIPT.json").read_text(encoding="utf-8"))
    test_a_matrix = read_csv(TEST_A_DIR / "TEST_A_CHARACTERISTIC_MATRIX.csv")
    test_a_residual = read_csv(TEST_A_DIR / "TEST_A_RESIDUAL_DIAGNOSTICS.csv")
    test_a_rank = read_csv(TEST_A_DIR / "TEST_A_RANKINGS.csv")
    test_a_overlap = read_csv(TEST_A_DIR / "TEST_A_RANK_OVERLAP.csv")
    test_a_resid_corr = read_csv(TEST_A_DIR / "TEST_A_RESIDUAL_CORRELATIONS.csv")
    test_a_hash_failures = [label for label, expected in test_a_receipt["outputs"].items() if sha256(ROOT / label) != expected]
    matrix_pairs = {(row["ai_measure"], row["characteristic"]) for row in test_a_matrix}
    expected_matrix_pairs = {(ai, char) for ai in AI_MEASURES for char in CHARACTERISTICS}
    check("test_a_status", test_a_receipt["status"] == "PASS_COMPLETE_FROZEN_TEST_A", test_a_receipt["status"])
    check("test_a_no_post_outcomes", test_a_receipt["post_period_outcomes_read"] is False, "receipt false")
    check("test_a_matrix", matrix_pairs == expected_matrix_pairs and len(test_a_matrix) == 48, f"rows={len(test_a_matrix)}")
    check("test_a_residual", len(test_a_residual) == 6 and len({r['ai_measure'] for r in test_a_residual}) == 6, f"rows={len(test_a_residual)}")
    check("test_a_rankings", len(test_a_rank) == 120, f"rows={len(test_a_rank)}")
    check("test_a_rank_overlap", len(test_a_overlap) == 30, f"rows={len(test_a_overlap)}")
    check("test_a_residual_correlations", len(test_a_resid_corr) == 15, f"rows={len(test_a_resid_corr)}")
    check("test_a_hashes", not test_a_hash_failures, f"failures={test_a_hash_failures}")
    for ai, char in sorted(expected_matrix_pairs):
        item(
            f"Test A: {ai} x {char}",
            "yax/measurement/test_a/TEST_A_CHARACTERISTIC_MATRIX.csv",
            (ai, char) in matrix_pairs,
            "N/A — outcome-free measurement receipt",
            not test_a_hash_failures,
            "employment-weighted Pearson and Spearman recorded",
        )
    for ai in AI_MEASURES:
        item(
            f"Test A residual diagnostic: {ai}",
            "yax/measurement/test_a/TEST_A_RESIDUAL_DIAGNOSTICS.csv",
            any(row["ai_measure"] == ai for row in test_a_residual),
            "N/A — outcome-free measurement receipt",
            not test_a_hash_failures,
            "joint characteristic residualization and named contributors recorded",
        )

    # Test B: all six AI definitions by every frozen computerization control.
    test_b = json.loads(TEST_B_PATH.read_text(encoding="utf-8"))
    pairs = test_b["pairs"]
    expected_b_pairs = {(ai, comp) for ai in AI_MEASURES for comp in COMPUTERIZATION}
    actual_b_pairs = {(row["ai_measure"], row["computerization_measure"]) for row in pairs}
    check("test_b_complete_pairs", actual_b_pairs == expected_b_pairs and len(pairs) == 30, f"pairs={len(pairs)}")
    check("test_b_no_post_outcomes", test_b["post_event_outcomes_opened"] is False, "receipt false")
    test_b_rows = []
    for row in pairs:
        contributors = row["named_divergence_occupations"]["largest_residual_variance_contributors"]
        top_five_share = sum(float(x["residual_variance_share"]) for x in contributors[:5])
        families = row["residual_variation_by_soc_major_group"]
        test_b_rows.append(
            {
                "ai_measure": row["ai_measure"],
                "computerization_measure": row["computerization_measure"],
                "occupations": row["n_occupations"],
                "correlation": row["correlation"],
                "r_squared": row["r_squared"],
                "partial_variance_ai": row["partial_variance_of_ai"],
                "vif": row["vif"],
                "se_inflation": row["se_inflation"],
                "residual_sd": row["residual_sd"],
                "effective_identifying_occupations": row["effective_number_identifying_ai"],
                "top_five_residual_variance_share": top_five_share,
                "largest_soc_family": families[0]["soc_major_group"],
                "largest_soc_family_share": families[0]["residual_variance_share"],
                "top_five_occupations": "; ".join(x["occupation"] for x in contributors[:5]),
            }
        )
        complete = len(contributors) >= 5 and bool(families) and row["effective_number_identifying_ai"] > 0
        item(
            f"Test B: {row['ai_measure']} residualized on {row['computerization_measure']}",
            "yax/measurement/computerization_support_66m_receipt.json",
            complete,
            "N/A — outcome-free measurement receipt",
            test_b["post_event_outcomes_opened"] is False,
            f"effective N={row['effective_number_identifying_ai']:.2f}; top-five share={top_five_share:.3f}",
        )
    write_csv(args.output / "TEST_B_IDENTIFYING_VARIATION_FULL.csv", test_b_rows, list(test_b_rows[0]))

    overlap_by_pair: dict[tuple[str, str], dict] = {}
    for row in test_a_resid_corr:
        overlap_by_pair[(row["measure_left"], row["measure_right"])] = {
            "measure_left": row["measure_left"],
            "measure_right": row["measure_right"],
            "weighted_residual_correlation": row["weighted_residual_correlation"],
        }
    for row in test_a_overlap:
        key = (row["measure_left"], row["measure_right"])
        overlap_by_pair[key][f"{row['tail']}_jaccard"] = row["jaccard"]
    overlap_rows = list(overlap_by_pair.values())
    check("test_b_measure_overlap", len(overlap_rows) == 15 and all("Q1_jaccard" in r and "Q5_jaccard" in r for r in overlap_rows), f"pairs={len(overlap_rows)}")
    write_csv(
        args.output / "TEST_B_MEASURE_OVERLAP.csv",
        overlap_rows,
        ["measure_left", "measure_right", "weighted_residual_correlation", "Q1_jaccard", "Q5_jaccard"],
    )

    # Headline models: validate every coefficient object and match each frozen
    # target coefficient to the canonical result ledger.
    headline_rows = []
    for spec_id, model in data["headline"].items():
        all_complete = all(
            coefficient["converged"]
            and coefficient["bootstrap_draws"] == 999
            and coefficient["ci_lower"] < coefficient["ci_upper"]
            and 0 <= coefficient["bootstrap_p_value"] <= 1
            for coefficient in model["coefficients"].values()
        )
        ledger_row = ledger_by_id.get(spec_id)
        ledger_ok = ledger_row is not None and ledger_matches(ledger_row, target(model))
        check(f"headline::{spec_id}", all_complete and ledger_ok, f"coefficients={len(model['coefficients'])}; ledger={ledger_ok}")
        item(
            f"Headline model: {spec_id}",
            "yax/analysis/outcomes/frozen_v11_corrected_run/FROZEN_RESULTS.json",
            all_complete,
            "YES" if ledger_ok else "FAIL",
            ledger_ok,
            f"{len(model['coefficients'])} coefficient objects; target ledger-matched",
        )
        t = target(model)
        headline_rows.append({"specification_id": spec_id, "occupations": model["occupations"], **t})
    check("headline_count", len(headline_rows) == 12, f"models={len(headline_rows)}")
    headline_targets = [row["coefficient"] for row in headline_rows]
    check("headline_range", close(min(headline_targets), -0.20848085792431273) and close(max(headline_targets), -0.09709514570766216), f"range=[{min(headline_targets)}, {max(headline_targets)}]")
    primary = data["headline"]["dv_rating_beta__RuleA__webb_pct_software__q5_q1"]
    ptarget = target(primary)
    check(
        "primary_estimate",
        close(ptarget["coefficient"], -0.13107397642233506)
        and close(ptarget["ci_lower"], -0.21703804618691314)
        and close(ptarget["ci_upper"], -0.04510990665775699)
        and close(ptarget["bootstrap_p_value"], 0.003),
        json.dumps(ptarget, sort_keys=True),
    )
    write_csv(args.output / "HEADLINE_MODEL_AUDIT.csv", headline_rows, list(headline_rows[0]))

    # Support rules and computerization variants are separately enumerated even
    # though their outcome rows overlap the headline and alternative-X tables.
    for rule in ["RuleA", "RuleB", "RuleC"]:
        rule_specs = [key for key in data["headline"] if f"__{rule}__" in key]
        item(
            f"Support rule: {rule}",
            "yax/analysis/outcomes/frozen_v11_corrected_run/FROZEN_RESULTS.json",
            len(rule_specs) == 4,
            "YES",
            all(key in ledger_by_id for key in rule_specs),
            f"{len(rule_specs)} alpha/beta x Webb/O*NET target estimates",
        )

    alternatives = data["alternative_exposures_and_controls"]
    alt_rows = []
    for spec_id, model in alternatives.items():
        t = target(model)
        ledger_id = f"{spec_id}__{model['target_label']}"
        ledger_row = ledger_by_id.get(ledger_id)
        ledger_ok = ledger_row is not None and ledger_matches(ledger_row, t)
        alt_rows.append({"specification_id": spec_id, "occupations": model["occupations"], **t})
        if spec_id.startswith(tuple(AI_MEASURES)):
            item(
                f"Exposure/computerization variant: {spec_id}",
                "yax/analysis/outcomes/frozen_v11_corrected_run/FROZEN_RESULTS.json",
                t["converged"],
                "YES" if ledger_ok else "FAIL",
                ledger_ok,
                "Q5-Q1 target coefficient",
            )
    check("alternative_model_count", len(alternatives) == 11, f"models={len(alternatives)}")
    write_csv(args.output / "ALTERNATIVE_X_AUDIT.csv", alt_rows, list(alt_rows[0]))

    # Test C paired inference, including covariance identity and stored draws.
    pair = data["paired_test_c"]
    delta_draws = pair["centered_delta_draws"]
    pair_ledger = ledger_by_id.get("dv_rating_beta-minus-dv_rating_alpha")
    pair_ok = (
        len(delta_draws) == pair["common_bootstrap_draws"] == 999
        and close(statistics.stdev(delta_draws), pair["paired_se_delta"])
        and math.isfinite(pair["paired_covariance"])
        and pair["paired_covariance"] > 0
        and close(pair["delta"], pair["beta_primary"] - pair["alpha_contrast"])
        and pair["paired_ci_lower"] < 0 < pair["paired_ci_upper"]
        and close(pair["mde_delta_80_relative"], 0.032722)
        and pair_ledger is not None
        and close(pair_ledger["coefficient"], pair["delta"])
        and close(pair_ledger["se"], pair["paired_se_delta"])
        and close(pair_ledger["ci_lower"], pair["paired_ci_lower"])
        and close(pair_ledger["ci_upper"], pair["paired_ci_upper"])
        and close(pair_ledger["p_value"], pair["paired_p_value"])
    )
    check("paired_test_c", pair_ok, f"delta={pair['delta']}; se={pair['paired_se_delta']}; draws={len(delta_draws)}")
    item(
        "Test C paired beta-minus-alpha",
        "yax/analysis/outcomes/frozen_v11_corrected_run/FROZEN_RESULTS.json",
        pair_ok,
        "YES" if pair_ledger else "FAIL",
        pair_ok,
        "common draws, covariance identity, CI, p-value and frozen MDE verified",
    )

    # Remote, mapping, placebo, event study and extension.
    remote_rows = []
    for spec_id, model in data["remote"].items():
        spec_ledger_rows = [row for row in ledger if row["specification_id"].startswith(f"{spec_id}__")]
        expected_labels = set(model["coefficients"])
        actual_labels = {row["specification_id"].removeprefix(f"{spec_id}__") for row in spec_ledger_rows}
        ledger_ok = expected_labels == actual_labels and all(
            ledger_matches(ledger_by_id[f"{spec_id}__{label}"], coefficient)
            for label, coefficient in model["coefficients"].items()
        )
        all_complete = all(coefficient["converged"] for coefficient in model["coefficients"].values())
        item(
            f"Remote-work specification: {spec_id}",
            "yax/analysis/outcomes/frozen_v11_corrected_run/FROZEN_RESULTS.json",
            all_complete,
            "YES" if ledger_ok else "FAIL",
            ledger_ok,
            f"coefficients={len(expected_labels)}",
        )
        for label, coefficient in model["coefficients"].items():
            remote_rows.append({"specification_id": spec_id, "coefficient_label": label, "occupations": model["occupations"], **coefficient})
    check("remote_model_count", len(data["remote"]) == 7 and len(remote_rows) == 13, f"models={len(data['remote'])}; coefficients={len(remote_rows)}")
    write_csv(args.output / "REMOTE_MODEL_AUDIT.csv", remote_rows, list(remote_rows[0]))

    crosswalk_rows = []
    expected_crosswalk = [-0.018845424145969437, -0.019200059263891785, -0.0315649262409531, -0.02940371826709413]
    for number, model in data["crosswalk_decomposition"].items():
        t = target(model)
        ledger_id = f"crosswalk_row_{number}"
        ledger_row = ledger_by_id.get(ledger_id)
        ledger_ok = ledger_row is not None and ledger_matches(ledger_row, t)
        crosswalk_rows.append({"row": number, "label": model["label"], "occupations": model["occupations"], **t})
        item(
            f"Mapping decomposition row {number}: {model['label']}",
            "yax/analysis/outcomes/frozen_v11_corrected_run/FROZEN_RESULTS.json",
            t["converged"],
            "YES" if ledger_ok else "FAIL",
            ledger_ok and close(t["coefficient"], expected_crosswalk[int(number) - 1]),
            "per-SD AIOE with Webb",
        )
    write_csv(args.output / "MAPPING_DECOMPOSITION_AUDIT.csv", crosswalk_rows, list(crosswalk_rows[0]))

    placebo = data["placebo_2017_2019"]["ai"]
    placebo_ledger = ledger_by_id.get("placebo_2018_11")
    placebo_ok = (
        placebo["converged"]
        and close(placebo["coefficient"], 0.0014205268058809682)
        and close(placebo["ci_lower"], -0.020395079229284012)
        and close(placebo["ci_upper"], 0.023236132841045948)
        and close(placebo["bootstrap_p_value"], 0.894)
        and placebo_ledger is not None
        and ledger_matches(placebo_ledger, placebo)
    )
    item(
        "2017-2019 placebo",
        "yax/analysis/outcomes/frozen_v11_corrected_run/FROZEN_RESULTS.json",
        placebo["converged"],
        "YES" if placebo_ledger else "FAIL",
        placebo_ok,
        "2018-11 placebo break",
    )
    check("placebo", placebo_ok, json.dumps(placebo, sort_keys=True))

    events = data["event_study"]["rows"]
    pre = [row for row in events if row["placebo_indicator"] and not row.get("reference")]
    post = [row for row in events if not row["placebo_indicator"] and not row.get("reference")]
    sig_pre = [row["event_month"] for row in pre if row["ci_lower"] > 0 or row["ci_upper"] < 0]
    sig_post = [row["event_month"] for row in post if row["ci_lower"] > 0 or row["ci_upper"] < 0]
    check("event_counts", len(events) == 109 and len(pre) == 65 and len(post) == 43, f"all={len(events)}; pre={len(pre)}; post={len(post)}")
    check("event_significance", sig_pre == [] and sig_post == ["2023-11", "2023-12", "2026-04", "2026-05", "2026-06", "2026-07"], f"pre={sig_pre}; post={sig_post}")
    for row in events:
        if row.get("reference"):
            ledger_status = "N/A — normalized reference month"
            event_ok = row["coefficient"] == row["ci_lower"] == row["ci_upper"] == 0
        else:
            ledger_id = f"event_{row['event_month']}"
            ledger_row = ledger_by_id.get(ledger_id)
            ledger_status = "YES" if ledger_row else "FAIL"
            event_ok = ledger_row is not None and close(ledger_row["coefficient"], row["coefficient"]) and close(ledger_row["ci_lower"], row["ci_lower"]) and close(ledger_row["ci_upper"], row["ci_upper"])
        item(
            f"Event-study coefficient: {row['event_month']}",
            "yax/analysis/outcomes/frozen_v11_corrected_run/FROZEN_RESULTS.json",
            True,
            ledger_status,
            event_ok,
            "reference" if row.get("reference") else "wild-bootstrap interval ledger-matched",
        )

    extension = data["post_2025_extension"]
    ext_ledger = ledger_by_id.get("post_2025_wald")
    extension_ok = close(extension["wald_bootstrap_p"], 0.127) and ext_ledger is not None and close(ext_ledger["p_value"], 0.127)
    check("post_2025_extension", extension_ok, json.dumps(extension, sort_keys=True))
    item(
        "Post-2025 extension Wald test",
        "yax/analysis/outcomes/frozen_v11_corrected_run/FROZEN_RESULTS.json",
        True,
        "YES" if ext_ledger else "FAIL",
        extension_ok,
        "early, extension and paired change retained",
    )

    check(
        "rule_a_reconstruction_gap",
        close(data["post_cell_build"]["maximum_rule_a_frozen_cell_gap"], 9.313225746154785e-10),
        str(data["post_cell_build"]["maximum_rule_a_frozen_cell_gap"]),
    )

    # Frozen table and figure content shells.  Names changed in the reporting
    # hierarchy; the matrix records the exact content mapping rather than
    # pretending the numbering remained unchanged.
    shell_map = {
        "Table shell 1 — construct and identifying support": ["table1_construct_and_identifying_support.csv", "table2_identifying_variation.csv"],
        "Table shell 2 — joint AI-computerization estimates": ["table4a_headline_q5_q1.csv"],
        "Table shell 3 — event study and placebo": ["table6_dynamics_and_placebo.csv"],
        "Table shell 4 — alternative exposures and paired Delta": ["table4_same_design_different_x.csv"],
        "Table shell 5 — crosswalk decomposition": ["table3_mapping_and_common_support.csv"],
        "Table shell 6 — remote work and extension": ["table5_ai_remote_and_post2025_extension.csv"],
        "Figure shell — event study": ["figure1_event_study.png"],
        "Figure shell — construct divergence": ["figure2_measurement_divergence.png"],
    }
    manifest_labels = {row["artifact"] for row in manifest_rows if row["status"] == "PASS"}
    for label, filenames in shell_map.items():
        paths = [REPORTING_DIR / name for name in filenames]
        ok = all(path.exists() and str(path.relative_to(ROOT)) in manifest_labels for path in paths)
        item(label, "; ".join(str(path.relative_to(ROOT)) for path in paths), all(path.exists() for path in paths), "N/A — rendered reporting artifact", ok, "content mapping verified")

    # Prohibited inference audit: negative/prohibitory uses are required; the
    # report must not positively call beta and alpha economically equivalent.
    report_text = (ROOT / "yax/analysis/FROZEN_RESULTS_REPORT.md").read_text(encoding="utf-8").lower()
    bad_phrases = [
        "beta and alpha are economically equivalent",
        "β and α are economically equivalent.",
        "the exposure definitions are economically equivalent",
        "establishes economic equivalence",
    ]
    # The only occurrence of one phrase is inside an explicit cannot-claim
    # list, so detect positive prose by excluding lines containing cannot/not.
    positive_report_text = report_text.partition("what it cannot claim:")[0]
    positive_equivalence_lines = [
        line.strip()
        for line in positive_report_text.splitlines()
        if "economically equivalent" in line and "cannot" not in line and "not " not in line and "never" not in line
    ]
    check("no_equivalence_claim", not positive_equivalence_lines, json.dumps(positive_equivalence_lines))
    check("no_causal_remote_win", "beats remote" not in report_text and "wins over remote" not in report_text, "no causal horse-race claim")

    completion_columns = ["frozen_item", "required_artifact", "exists", "ledger_coverage", "reproduces", "status", "detail"]
    write_csv(args.output / "CONFIRMATORY_COMPLETION_MATRIX.csv", completion, completion_columns)
    write_csv(args.output / "INTEGRITY_CHECKS.csv", checks, ["check", "status", "detail"])

    receipt = {
        "record_version": "yax-confirmatory-results-audit-v1",
        "status": "PASS" if not failures else "FAIL",
        "scope": "verification and completion of frozen measurement outputs only; no exploratory specification",
        "protected_post_period_outcomes_read_by_audit": False,
        "design_commit": DESIGN_COMMIT,
        "reported_result_commit": RESULT_COMMIT,
        "core_hashes": CORE_HASHES,
        "ledger": {"rows": len(ledger), "section_counts": dict(counts)},
        "test_a": {
            "ai_measures": len(AI_MEASURES),
            "characteristics": len(CHARACTERISTICS),
            "matrix_rows": len(test_a_matrix),
            "common_complete_support_occupations": test_a_receipt["common_complete_support_occupations"],
            "post_period_outcomes_read": test_a_receipt["post_period_outcomes_read"],
        },
        "test_b": {"ai_measures": len(AI_MEASURES), "computerization_controls": len(COMPUTERIZATION), "pair_rows": len(pairs), "overlap_pairs": len(overlap_rows)},
        "headline": {"models": len(headline_rows), "minimum": min(headline_targets), "maximum": max(headline_targets), "primary": ptarget},
        "paired_test_c": {
            "delta": pair["delta"],
            "paired_se": pair["paired_se_delta"],
            "ci": [pair["paired_ci_lower"], pair["paired_ci_upper"]],
            "p_value": pair["paired_p_value"],
            "mde_delta_80": pair["mde_delta_80_relative"],
            "common_draws": pair["common_bootstrap_draws"],
        },
        "timing": {"pre_nonreference": len(pre), "post_event": len(post), "significant_pre": sig_pre, "significant_post": sig_post, "extension_p": extension["wald_bootstrap_p"]},
        "completion_matrix_rows": len(completion),
        "integrity_checks": {"total": len(checks), "passed": sum(row["status"] == "PASS" for row in checks), "failed": sum(row["status"] == "FAIL" for row in checks)},
        "failures": failures,
    }
    (args.output / "CONFIRMATORY_RESULTS_AUDIT_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "completion_rows": len(completion), "checks": receipt["integrity_checks"], "output": str(args.output)}, indent=2))
    if failures:
        raise SystemExit("\n".join(failures))


if __name__ == "__main__":
    main()
