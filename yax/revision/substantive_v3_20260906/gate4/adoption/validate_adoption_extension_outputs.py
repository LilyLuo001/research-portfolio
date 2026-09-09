#!/usr/bin/env python3
"""Independently validate the focused public RPS adoption output package."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
EXPECTED_INPUTS = {
    "rps_adoption_rates_by_occupation_20260806.xlsx":
        "2212465781179782c6f69750af21b00bd545edc21581d9577fbf7affc1bf0c43",
    "REBUILT_TREATMENT_MEMBERSHIP.csv":
        "c76eb85956e4a413e130bab53fe8c50616cf6d7a02c81c266ec369879dd56bc1",
    "BROADER_SUPPORT_MEMBERSHIP.csv":
        "2fe1967db31dea51e007861867e01bd6fa872828a9d589bc0490212e534220fc",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def weighted(frame: pd.DataFrame, weights: np.ndarray) -> dict[str, float]:
    x = frame.rule_A_beta.to_numpy(float)
    y = frame.adoption_rate.to_numpy(float)
    w = np.asarray(weights, float)
    mx, my = float(w @ x / w.sum()), float(w @ y / w.sum())
    xc, yc = x - mx, y - my
    xx = float(w @ (xc * xc))
    yy = float(w @ (yc * yc))
    xy = float(w @ (xc * yc))
    require(xx > 0 and yy > 0, "validation moments are degenerate")
    return {
        "pearson_correlation": xy / np.sqrt(xx * yy),
        "ols_slope_adoption_on_beta": xy / xx,
        "beta_mean": mx,
        "adoption_mean": my,
    }


def within_family(frame: pd.DataFrame, weights: np.ndarray) -> dict[str, float]:
    work = frame.copy()
    work["w"] = np.asarray(weights, float)
    family_weight = work.groupby("family", observed=True).w.transform("sum")
    family_x = (work.w * work.rule_A_beta).groupby(
        work.family, observed=True).transform("sum") / family_weight
    family_y = (work.w * work.adoption_rate).groupby(
        work.family, observed=True).transform("sum") / family_weight
    xr = work.rule_A_beta.to_numpy(float) - family_x.to_numpy(float)
    yr = work.adoption_rate.to_numpy(float) - family_y.to_numpy(float)
    w = work.w.to_numpy(float)
    x = work.rule_A_beta.to_numpy(float)
    xbar = float(w @ x / w.sum())
    total_ss = float(w @ np.square(x - xbar))
    within_ss = float(w @ np.square(xr))
    counts = work.groupby("family", observed=True).size()
    return {
        "within_family_exposure_ss_share": within_ss / total_ss,
        "within_family_slope_adoption_on_beta": float(w @ (xr * yr) / within_ss),
        "matched_families": float(counts.size),
        "families_with_at_least_two_occupations": float((counts >= 2).sum()),
    }


def validate(run: Path) -> dict[str, object]:
    receipt = json.loads((run / "ADOPTION_RUN_RECEIPT.json").read_text())
    require(receipt["status"] == "PASS_FOCUSED_DESCRIPTIVE_ADOPTION_EXTENSION",
            "producer status differs")
    require(receipt["input_sha256"] == EXPECTED_INPUTS,
            "producer input identity differs")
    output_paths = {
        "summary": run / "ADOPTION_SUMMARY.csv",
        "quintiles": run / "ADOPTION_QUINTILES.csv",
        "coverage": run / "ADOPTION_COVERAGE.csv",
        "unmatched_rps": run / "RPS_UNMATCHED_CODES.csv",
    }
    for key, path in output_paths.items():
        require(path.is_file() and digest(path) == receipt["output_sha256"][key],
                f"output hash differs for {key}")
    summary = pd.read_csv(output_paths["summary"], float_precision="round_trip")
    quintiles = pd.read_csv(output_paths["quintiles"], float_precision="round_trip")
    coverage = pd.read_csv(output_paths["coverage"], dtype={"occ_code": str},
                           float_precision="round_trip")
    require(len(coverage) == 468 and coverage.occ_code.nunique() == 468,
            "coverage does not retain the frozen occupation support")
    coverage["occ_code"] = coverage.occ_code.str.zfill(4)
    require(set(coverage.coverage_status) == {
        "matched_nonsuppressed", "rps_suppressed_or_missing_rate", "rps_code_absent",
    }, "coverage status inventory differs")
    matched = coverage.loc[coverage.coverage_status.eq("matched_nonsuppressed")].copy()
    require(len(matched) == receipt["matched_nonsuppressed_occupations"] and
            set(matched.beta_quintile.astype(int)) == {1, 2, 3, 4, 5},
            "matched support differs")
    require(matched.adoption_rate.between(0, 1).all() and
            (matched.number_observations >= 20).all(),
            "matched RPS values violate released bounds")
    require(not any(token in column.lower() for column in summary.columns
                    for token in ("standard_error", "p_value", "ci_lower", "ci_upper")),
            "unsupported detailed-cell inference was published")
    expected_metrics: dict[tuple[str, str], float] = {}
    weightings = {
        "equal_occupation": np.ones(len(matched)),
        "reported_observation_count_sensitivity":
            matched.number_observations.to_numpy(float),
    }
    for label, weights in weightings.items():
        for metric, value in {**weighted(matched, weights),
                              **within_family(matched, weights)}.items():
            expected_metrics[(label, metric)] = value
        q_values: dict[int, float] = {}
        for quintile in range(1, 6):
            mask = matched.beta_quintile.astype(int).eq(quintile).to_numpy()
            q_values[quintile] = float(
                weights[mask] @ matched.loc[mask, "adoption_rate"].to_numpy(float) /
                weights[mask].sum())
            stored = quintiles.loc[
                quintiles.weighting.eq(label) & quintiles.beta_quintile.eq(quintile)]
            require(len(stored) == 1 and
                    int(stored.iloc[0].matched_occupations) == int(mask.sum()) and
                    abs(float(stored.iloc[0].mean_adoption_rate) - q_values[quintile]) <= 5e-14,
                    f"quintile result differs for {label}/Q{quintile}")
        expected_metrics[(label, "Q5_minus_Q1_mean_adoption_rate")] = (
            q_values[5] - q_values[1])
    rank_x = matched.rule_A_beta.rank(method="average").to_numpy(float)
    rank_y = matched.adoption_rate.rank(method="average").to_numpy(float)
    ranks = pd.DataFrame({"rule_A_beta": rank_x, "adoption_rate": rank_y})
    expected_metrics[("equal_occupation", "spearman_rank_correlation")] = weighted(
        ranks, np.ones(len(ranks)))["pearson_correlation"]
    require(len(summary) == len(expected_metrics) and
            not summary.duplicated(["weighting", "metric"]).any(),
            "summary metric inventory differs")
    maximum_gap = 0.0
    for key, expected in expected_metrics.items():
        stored = summary.loc[
            summary.weighting.eq(key[0]) & summary.metric.eq(key[1]), "estimate"]
        require(len(stored) == 1, f"missing summary metric {key}")
        gap = abs(float(stored.iloc[0]) - expected)
        maximum_gap = max(maximum_gap, gap)
        require(gap <= 5e-14, f"summary metric differs for {key}")
    checks = {
        "input_and_output_hashes_match": True,
        "frozen_468_support_retained": True,
        "all_five_quintiles_represented": True,
        "released_suppression_rule_respected": True,
        "descriptive_metrics_recomputed": True,
        "no_unsupported_inference_published": True,
        "future_pooled_noncausal_boundary_recorded": (
            receipt["timing"] == "pooled_future_post_outcome_occupation_classification" and
            receipt["causal_interpretation_permitted"] is False),
    }
    require(all(checks.values()), "interpretation boundary differs")
    return {
        "schema": "yax.rps_adoption_validation.v1",
        "status": "PASS_RECOMPUTED_FOCUSED_ADOPTION_EXTENSION",
        "validated_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "matched_nonsuppressed_occupations": len(matched),
        "maximum_absolute_recomputation_gap": maximum_gap,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    report = validate(args.run)
    path = args.run / "ADOPTION_VALIDATION.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
