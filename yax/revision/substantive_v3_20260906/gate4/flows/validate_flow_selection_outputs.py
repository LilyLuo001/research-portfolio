#!/usr/bin/env python3
"""Recompute public identities in the Gate 4 flow-selection output package."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED = {
    "LINK_ELIGIBILITY_ACCOUNTING.csv", "FLOW_BASELINE_PROBABILITIES.csv",
    "LINKED_UNLINKED_BALANCE.csv", "SELECTION_REWEIGHTED_RATES.csv",
    "SELECTION_REWEIGHTED_CONTRASTS.csv", "MISSING_OUTCOME_GROUP_BOUNDS.csv",
    "MISSING_OUTCOME_CONTRAST_BOUNDS.csv", "ENTRY_DESTINATION_PROBABILITIES.csv",
    "ENTRY_RECONCILIATION.csv", "CONDITIONAL_ENTRY_ALLOCATION.csv",
    "CORE_FLOW_REGRESSION_REFERENCE.csv", "ANNUAL_TIMING_SENSITIVITY.csv",
    "ANNUAL_TIMING_INFLUENCE.csv", "ANNUAL_TIMING_AUDIT.csv",
    "FLOW_SELECTION_FINDINGS.md", "EXECUTION_RECEIPT.json",
}
MARGINS = {"employment_exit", "unemployment_entry", "labor_force_exit"}
ELIGIBILITY_STATUSES = {
    "target_calendar_month_absent", "rotation_ineligible",
    "rotation_eligible_missing_identifier", "eligible_no_validated_endpoint",
    "eligible_validated_zero_official_weight",
    "eligible_positive_official_weight_link",
}
REQUIRED_POSITIVE_ELIGIBILITY_STATUSES = {
    "target_calendar_month_absent", "rotation_ineligible",
    "eligible_no_validated_endpoint", "eligible_positive_official_weight_link",
}
STRUCTURAL_ZERO_ELIGIBILITY_STATUSES = {
    "rotation_eligible_missing_identifier",
    "eligible_validated_zero_official_weight",
}
SIGNS = {
    ("post", "young_22_25", 5): 1, ("post", "older_26_65", 5): -1,
    ("post", "young_22_25", 1): -1, ("post", "older_26_65", 1): 1,
    ("pre", "young_22_25", 5): -1, ("pre", "older_26_65", 5): 1,
    ("pre", "young_22_25", 1): 1, ("pre", "older_26_65", 1): -1,
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def month_add(month: str, amount: int) -> str:
    year, value = map(int, month.split("-"))
    ordinal = year * 12 + value + amount
    return f"{(ordinal - 1) // 12}-{(ordinal - 1) % 12 + 1:02d}"


def exposure_duration(month: str) -> float:
    year, value = map(int, month.split("-"))
    start = year * 12 + value
    onset = 2023 * 12 + 1
    return sum(start + step >= onset for step in range(1, 13)) / 12


def validate_contrasts(rates: pd.DataFrame, contrasts: pd.DataFrame) -> None:
    methods = ["official_link_probability", "origin_WTFINL_complete_case_probability",
               "observable_poststratified_probability"]
    for row in contrasts.itertuples(index=False):
        selected = rates.loc[(rates.horizon == row.horizon) &
                             (rates.margin == row.margin)].set_index(
                                 ["period", "age_group", "beta_quintile"])
        observed = sum(sign * float(selected.at[key, row.weighting_method])
                       for key, sign in SIGNS.items())
        require(abs(observed -
                    row.linear_probability_Q5_minus_Q1_young_minus_older_post_minus_pre)
                <= 1e-12, "selection contrast does not reproduce")
        require(row.weighting_method in methods, "unknown selection weighting method")


def validate_bounds(groups: pd.DataFrame, contrasts: pd.DataFrame) -> None:
    expected_lower = groups.link_share_ell * groups.linked_probability_pL
    expected_upper = expected_lower + 1 - groups.link_share_ell
    require(np.max(np.abs(expected_lower - groups.probability_lower)) <= 1e-12,
            "group lower bounds do not reproduce")
    require(np.max(np.abs(expected_upper - groups.probability_upper)) <= 1e-12,
            "group upper bounds do not reproduce")
    require(((groups.probability_lower >= 0) &
             (groups.probability_lower <= groups.probability_upper) &
             (groups.probability_upper <= 1 + 1e-12)).all(), "invalid group bound")
    for row in contrasts.itertuples(index=False):
        lower = (row.observed_linear_contrast_component +
                 row.missing_negative_coefficient_sum)
        upper = (row.observed_linear_contrast_component +
                 row.missing_positive_coefficient_sum)
        require(abs(lower - row.linear_probability_contrast_lower) <= 1e-12 and
                abs(upper - row.linear_probability_contrast_upper) <= 1e-12,
                "linear missing-outcome contrast bounds do not reproduce")
        require(row.missing_negative_coefficient_sum <= 0 <=
                row.missing_positive_coefficient_sum and
                row.missing_source_record_count > 0,
                "joint missing-record coefficient accounting is invalid")
        require("common outcome per source record" in row.joint_feasibility_scope and
                "not asserted sharp" in row.log_interval_scope,
                "bound sharpness scope is misstated")
        require(not bool(row.Lee_trimming_used) and not bool(row.probabilities_clipped),
                "bounds used a prohibited operation")


def validate_eligibility_inventory(eligibility: pd.DataFrame) -> None:
    statuses = set(eligibility.eligibility_status)
    require(statuses.issubset(ELIGIBILITY_STATUSES),
            "eligibility output contains an unknown status")
    require(REQUIRED_POSITIVE_ELIGIBILITY_STATUSES.issubset(statuses),
            "eligibility output omits a required positive-mass status")
    require(ELIGIBILITY_STATUSES - statuses == STRUCTURAL_ZERO_ELIGIBILITY_STATUSES,
            "structural-zero eligibility inventory differs")
    require(not eligibility.duplicated([
        "horizon", "eligibility_status", "period", "age_group", "origin_state"
    ]).any(), "eligibility output contains duplicate accounting cells")
    require((eligibility.origin_records > 0).all() and
            (eligibility.origin_WTFINL > 0).all(),
            "eligibility output contains nonpositive cells")


def validate_entry_reconciliation(reconcile: pd.DataFrame) -> None:
    require(np.max(np.abs(reconcile.all_destination_probability_sum - 1)) <= 1e-12,
            "entry destination probabilities do not sum to one")
    tolerance = np.maximum(1e-7, np.abs(reconcile.risk_weight.to_numpy(float)) * 1e-12)
    require(np.all(np.abs(reconcile.identity_error.to_numpy(float)) <= tolerance),
            "entry destination weights do not reconcile")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--report", type=Path,
                        help="JSON report path (default: OUTPUT_DIR/VALIDATION_REPORT.json)")
    args = parser.parse_args()
    out = args.output_dir
    require(out.is_dir() and REQUIRED.issubset({path.name for path in out.iterdir()}),
            "required flow-selection output is absent")
    receipt = json.loads((out / "EXECUTION_RECEIPT.json").read_text())
    require(receipt.get("status") == "PASS_GATE4_FLOW_SELECTION", "receipt does not pass")
    for name, expected in receipt["output_hashes"].items():
        require(sha256_file(out / name) == expected, f"output hash differs: {name}")
    require(receipt["current_and_legacy_membership_byte_identical"] is True,
            "current treatment was not bound to certified flow treatment")
    require(receipt["protected_identifiers_written"] is False,
            "receipt says protected identifiers were written")
    require(receipt["poststratification_trimmed_or_capped"] is False and
            receipt["Lee_trimming_used"] is False and
            receipt["probability_bounds_clipped"] is False,
            "prohibited selection manipulation was used")

    eligibility = pd.read_csv(out / "LINK_ELIGIBILITY_ACCOUNTING.csv")
    require(set(eligibility.horizon) == {"adjacent_month", "twelve_month"},
            "eligibility horizon inventory differs")
    validate_eligibility_inventory(eligibility)

    baseline = pd.read_csv(out / "FLOW_BASELINE_PROBABILITIES.csv")
    require(set(baseline.margin) == {"link_retention", *MARGINS, "occupational_outflow"},
            "baseline margin inventory differs")
    require(((baseline.probability >= 0) & (baseline.probability <= 1)).all(),
            "baseline probability is outside [0,1]")
    require((baseline.event_weight <= baseline.risk_weight + 1e-8).all(),
            "baseline event exceeds risk")
    for keys, group in baseline.loc[baseline.margin.isin(MARGINS)].groupby(
            ["horizon", "period", "age_group", "beta_quintile"], observed=True):
        values = group.set_index("margin").event_weight
        require(abs(values["employment_exit"] - values["unemployment_entry"] -
                    values["labor_force_exit"]) <= max(1e-7, abs(values["employment_exit"]) * 1e-10),
                f"exit components do not reconcile: {keys}")

    balance = pd.read_csv(out / "LINKED_UNLINKED_BALANCE.csv")
    require(set(balance.link_status) == {"retained_positive_official_weight",
                                         "eligible_not_retained"},
            "balance link-status inventory differs")
    require(set(balance.characteristic) == {"age_years", "BA_plus", "full_time_35plus",
                                             "wage_salary_class"},
            "balance characteristic inventory differs")
    binary = balance.loc[balance.characteristic.ne("age_years"), "weighted_mean"]
    require(((binary >= 0) & (binary <= 1)).all(), "binary balance mean outside [0,1]")

    rates = pd.read_csv(out / "SELECTION_REWEIGHTED_RATES.csv")
    for field in ("official_link_probability", "origin_WTFINL_complete_case_probability",
                  "observable_poststratified_probability"):
        require(((rates[field] >= 0) & (rates[field] <= 1)).all(),
                f"selection rate outside [0,1]: {field}")
    require((rates.unsupported_eligible_share.between(0, 1)).all(),
            "unsupported selection share outside [0,1]")
    require((rates.poststrat_factor_min > 0).all() and
            (rates.poststrat_factor_max >= rates.poststrat_factor_min).all(),
            "invalid poststratification factor")
    contrasts = pd.read_csv(out / "SELECTION_REWEIGHTED_CONTRASTS.csv")
    require(len(contrasts) == 18, "selection contrast inventory differs")
    validate_contrasts(rates, contrasts)

    groups = pd.read_csv(out / "MISSING_OUTCOME_GROUP_BOUNDS.csv")
    bound_contrasts = pd.read_csv(out / "MISSING_OUTCOME_CONTRAST_BOUNDS.csv")
    require(len(bound_contrasts) == 6 and set(bound_contrasts.margin) == MARGINS,
            "missing-outcome contrast inventory differs")
    validate_bounds(groups, bound_contrasts)

    entry = pd.read_csv(out / "ENTRY_DESTINATION_PROBABILITIES.csv")
    reconcile = pd.read_csv(out / "ENTRY_RECONCILIATION.csv")
    allocation = pd.read_csv(out / "CONDITIONAL_ENTRY_ALLOCATION.csv")
    require((entry.denominator == "all retained nonemployed origins").all(),
            "entry probabilities do not share one denominator")
    require(((entry.probability >= 0) & (entry.probability <= 1)).all(),
            "entry probability is outside [0,1]")
    validate_entry_reconciliation(reconcile)
    for _, group in allocation.groupby(["horizon", "period", "age_group"], observed=True):
        require(abs(float(group.conditional_allocation_share.sum()) - 1) <= 1e-12,
                "conditional entry allocation does not sum to one")
    require(all(category in set(entry.destination_category) for category in
                ["remaining_nonemployed", "employed_valid_occupation_outside_support"]),
            "required entry destination category is absent")

    timing = pd.read_csv(out / "ANNUAL_TIMING_AUDIT.csv")
    require(all(month_add(row.origin_month, 12) == row.destination_month
                for row in timing.itertuples(index=False)), "annual endpoint is not t+12")
    require(max(abs(exposure_duration(row.origin_month) -
                    row.post_onset_destination_month_share)
                for row in timing.itertuples(index=False)) <= 1e-15,
            "annual exposure duration does not reproduce")
    results = pd.read_csv(out / "ANNUAL_TIMING_SENSITIVITY.csv")
    influence = pd.read_csv(out / "ANNUAL_TIMING_INFLUENCE.csv",
                            dtype={"occ_code": str})
    require(len(results) == 8 and set(results.margin) == {*MARGINS, "occupational_outflow"}
            and set(results.timing_rule) == {"exclusion", "exposure_duration"},
            "annual timing model inventory differs")
    for row in results.itertuples(index=False):
        values = influence.loc[influence.model_id.eq(row.model_id), "target_influence"].to_numpy(float)
        require(len(values) > 1 and
                abs(float(np.sqrt(values @ values)) - row.analytic_occupation_cluster_se) <= 1e-11,
                f"annual occupation SE does not reproduce: {row.model_id}")
        require(row.wild_score_ci_lower <= row.coefficient_Q5_x_young_x_timing <=
                row.wild_score_ci_upper, "annual interval ordering failed")
    core = pd.read_csv(out / "CORE_FLOW_REGRESSION_REFERENCE.csv")
    require(len(core) == 10 and core.model_id.nunique() == 10,
            "core flow/person-household reference inventory differs")
    require(np.max(np.abs(core.coefficient - core.coefficient)) == 0,
            "core coefficient is nonfinite")

    for path in out.iterdir():
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore")
            require("/projectnb/" not in text and "/usr3/" not in text,
                    f"protected absolute path leaked: {path.name}")
            require("CPSIDV," not in text and "CPSID," not in text,
                    f"protected identifier column leaked: {path.name}")
    report = {
        "status": "PASS_RECOMPUTED_GATE4_FLOW_SELECTION",
        "baseline_rows": len(baseline), "selection_rows": len(rates),
        "entry_rows": len(entry), "annual_timing_models": len(results),
        "core_flow_models_with_person_household_sensitivity": len(core),
        "structurally_zero_eligibility_statuses":
            sorted(STRUCTURAL_ZERO_ELIGIBILITY_STATUSES),
    }
    report_path = args.report or (out / "VALIDATION_REPORT.json")
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
