#!/usr/bin/env python3
"""Reconcile legacy intervals and audit the round-2 precision outputs."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import pathlib

import pandas as pd


HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[4]
RESULTS = HERE / "results"
EXPECTED = -0.13107397642233506
MDE_FACTOR = 1.959963984540054 + 0.8416212335729143


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def one(path: pathlib.Path, **match):
    frame = pd.read_csv(path)
    for key, value in match.items():
        frame = frame.loc[frame[key].astype(str).eq(str(value))]
    if len(frame) != 1:
        raise RuntimeError(f"expected one row from {path}: {match}; got {len(frame)}")
    return frame.iloc[0]


def write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    fields: list[str] = []
    for row in rows:
        fields.extend(key for key in row if key not in fields)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def reconciliation() -> list[dict]:
    frozen = json.loads((
        ROOT / "yax/revision/referee_20260905/baseline_reproduction/FROZEN_RESULTS.json"
    ).read_text())["headline"]["dv_rating_beta__RuleA__webb_pct_software__q5_q1"][
        "coefficients"
    ]["AI_Q5_x_post"]
    calendar = one(
        ROOT / "yax/revision/referee_20260905/results/cells/CALENDAR_TAXONOMY_SENSITIVITIES.csv",
        specification="frozen_calendar_reproduction",
    )
    reference = one(
        ROOT / "yax/revision/referee_20260905/results/core/REFERENCE_CONTRASTS.csv",
        contrast="Q5_minus_Q1",
    )
    age = one(
        ROOT / "yax/revision/referee_20260905/results/balanced_cells/AGE_COMPARISON_RESULTS.csv",
        comparison="22_25_vs_26_65",
    )
    threshold = one(
        ROOT / "yax/revision/referee_20260905/results/balanced_cells/MINIMUM_SIZE_SENSITIVITIES.csv",
        specification="minimum_full_panel_respondent_equivalent_100",
    )
    canonical = one(RESULTS / "CANONICAL_PRIMARY_INTERVAL.csv")
    return [
        {
            "source": "frozen_confirmatory_result", "coefficient": frozen["coefficient"],
            "se": frozen["analytic_cluster_se"], "ci_lower": frozen["ci_lower"],
            "ci_upper": frozen["ci_upper"], "draws": frozen["bootstrap_draws"],
            "seed_or_draw_set": frozen["bootstrap_seed"], "support_occupations": 468,
            "same_point_estimator_and_sample": True,
            "explanation": "Original confirmatory 999-draw interval",
        },
        {
            "source": "first_round_calendar_reproduction", "coefficient": calendar.coefficient,
            "se": calendar.analytic_or_paired_se, "ci_lower": calendar.ci_lower,
            "ci_upper": calendar.ci_upper, "draws": calendar.draws,
            "seed_or_draw_set": "referee_cells_SEED+20", "support_occupations": calendar.support_occupations,
            "same_point_estimator_and_sample": True,
            "explanation": "Same coefficient; different finite multiplier draw set",
        },
        {
            "source": "first_round_reference_contrast", "coefficient": reference.coefficient,
            "se": reference.analytic_or_paired_se, "ci_lower": reference.ci_lower,
            "ci_upper": reference.ci_upper, "draws": reference.draws,
            "seed_or_draw_set": "referee_core_SEED+20", "support_occupations": reference.support_occupations,
            "same_point_estimator_and_sample": True,
            "explanation": "Same coefficient; different finite common contrast draw set",
        },
        {
            "source": "first_round_age_comparison", "coefficient": age.coefficient,
            "se": age.analytic_or_paired_se, "ci_lower": age.ci_lower,
            "ci_upper": age.ci_upper, "draws": age.draws,
            "seed_or_draw_set": "referee_cells_SEED+10", "support_occupations": age.support_occupations,
            "same_point_estimator_and_sample": True,
            "explanation": "Same ages and sample; different finite common age-comparison draw set",
        },
        {
            "source": "first_round_minimum_100_sensitivity", "coefficient": threshold.coefficient,
            "se": threshold.analytic_or_paired_se, "ci_lower": threshold.ci_lower,
            "ci_upper": threshold.ci_upper, "draws": threshold.draws,
            "seed_or_draw_set": "referee_cells_SEED+20", "support_occupations": threshold.support_occupations,
            "same_point_estimator_and_sample": False,
            "explanation": "Different 463-occupation threshold sample; never a primary interval",
        },
        {
            "source": "round2_canonical_primary", "coefficient": canonical.estimate_log_points,
            "se": canonical.occupation_cluster_se, "ci_lower": canonical.ci_lower,
            "ci_upper": canonical.ci_upper, "draws": canonical.draws,
            "seed_or_draw_set": canonical.bootstrap_seed,
            "support_occupations": canonical.support_occupations,
            "same_point_estimator_and_sample": True,
            "explanation": "Sole canonical primary interval for revised reporting",
        },
    ]


def audit() -> dict:
    checks = {}
    primary = one(RESULTS / "CANONICAL_PRIMARY_INTERVAL.csv")
    checks["primary_reproduces_frozen"] = math.isclose(
        primary.estimate_log_points, EXPECTED, abs_tol=1e-10
    )
    checks["primary_MDE_formula"] = math.isclose(
        primary.normal_theory_mde80_log_points,
        MDE_FACTOR * primary.occupation_cluster_se, rel_tol=1e-12,
    )
    reference = pd.read_csv(RESULTS / "REFERENCE_CONTRAST_PRECISION.csv")
    q51 = reference.loc[reference.contrast.eq("Q5_minus_Q1")].iloc[0]
    checks["reference_table_uses_canonical_primary"] = (
        math.isclose(q51.ci_lower, primary.ci_lower, abs_tol=1e-12)
        and math.isclose(q51.ci_upper, primary.ci_upper, abs_tol=1e-12)
    )
    pairs = pd.read_csv(RESULTS / "PAIRED_ARCHITECTURE_PRECISION.csv")
    checks["seven_architecture_pairs"] = len(pairs) == 7
    checks["all_pairs_common_multipliers"] = bool(pairs.common_occupation_multipliers.all())
    checks["all_pair_MDEs_reconcile"] = bool((
        (pairs.paired_normal_theory_mde80_log_points -
         MDE_FACTOR * pairs.paired_se_difference).abs() < 1e-12
    ).all())
    repaired = one(RESULTS / "REPAIRED_MONTHLY_BASELINE.csv")
    checks["repaired_calendar_is_113_months"] = int(repaired.months) == 113
    quarter = pd.read_csv(RESULTS / "QUARTERLY_ESTIMATES.csv")
    frozen_q = quarter.loc[quarter.specification.eq("frozen_108_month_calendar")].iloc[0]
    repaired_q = quarter.loc[quarter.specification.eq("repaired_113_month_calendar")].iloc[0]
    checks["quarterly_point_estimates_track_monthly"] = (
        abs(frozen_q.estimate_log_points - EXPECTED) < .001
        and abs(repaired_q.estimate_log_points - repaired.estimate_log_points) < .001
    )
    pseudo = pd.read_csv(RESULTS / "PSEUDO_BREAK_DISTRIBUTION_2017_2019.csv")
    checks["pseudo_break_two_classifications"] = (
        pseudo.classification_rule.nunique() == 2 and len(pseudo) == 68
    )
    pseudo_summary = json.loads((RESULTS / "PSEUDO_BREAK_SUMMARY.json").read_text())
    checks["pseudo_breaks_use_no_actual_post"] = (
        pseudo_summary["actual_post_2022_outcomes_used_in_pseudo_break_models"] is False
    )
    hac = pd.read_csv(RESULTS / "ROTATION_TIME_HAC_SENSITIVITY.csv")
    checks["HAC12_finite"] = math.isfinite(
        hac.loc[hac.time_HAC_lag_months.eq(12), "se"].iloc[0]
    )
    simulation_path = RESULTS / "HISTORICAL_CROSS_OCCUPATION_SIMULATION.json"
    if simulation_path.exists():
        simulation = json.loads(simulation_path.read_text())
        checks["simulation_uses_no_post_outcomes"] = (
            simulation["post_2022_outcomes_read_by_simulation"] is False
        )
        checks["simulation_enumerates_132_paths"] = simulation["draws_per_effect"] == 132
    checks = {key: bool(value) for key, value in checks.items()}
    failures = [key for key, passed in checks.items() if not passed]
    return {
        "status": "PASS" if not failures else "FAIL",
        "checks": checks, "failures": failures,
        "output_hashes_before_this_audit": {
            path.name: sha256(path) for path in sorted(RESULTS.iterdir()) if path.is_file()
        },
    }


def main() -> int:
    rows = reconciliation()
    write_csv(RESULTS / "INTERVAL_RECONCILIATION.csv", rows)
    report = audit()
    (RESULTS / "AUDIT_REPORT.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    files = sorted(path for path in RESULTS.iterdir()
                   if path.is_file() and path.name != "FINAL_OUTPUT_MANIFEST.json")
    (RESULTS / "FINAL_OUTPUT_MANIFEST.json").write_text(json.dumps({
        "record": "Final local manifest after interval reconciliation and audit",
        "analysis_status": "POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1",
        "files": {path.name: sha256(path) for path in files},
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": len(report["checks"])}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
