"""Fail-closed simulation skeleton for the CPS young-employment PPML design."""

from __future__ import annotations

import argparse
import json
import math
import pathlib

import numpy as np


PRE_END = "2022-11"
POST_START = (2022, 12)
POST_END = (2026, 7)
POST_GAPS = {"2025-10"}
PRIMARY_BENCHMARK = math.log(0.81)


class RealPowerBlocked(RuntimeError):
    pass


def planned_post_months() -> list[str]:
    result = []
    for year in range(POST_START[0], POST_END[0] + 1):
        for month in range(1, 13):
            if (year, month) < POST_START or (year, month) > POST_END:
                continue
            value = f"{year:04d}-{month:02d}"
            if value not in POST_GAPS:
                result.append(value)
    return result


def validate_preperiod_cells(frame) -> None:
    required = {
        "month", "occ2010", "age_group", "employment_headcount",
        "unweighted_n", "weight_sq_sum",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"cell input missing columns {sorted(missing)}")
    if len(frame) == 0:
        raise ValueError("cell input is empty")
    if frame["month"].astype(str).max() > PRE_END:
        raise ValueError("post-period outcomes prohibited in power input")
    if not set(frame["age_group"]).issubset({"young_22_25", "older_26_65"}):
        raise ValueError("unknown age_group")
    values = np.asarray(frame["employment_headcount"], dtype=float)
    if np.any(~np.isfinite(values)) or np.any(values < 0):
        raise ValueError("employment_headcount must be finite and nonnegative")


def donor_rotation(pre_months: list[str], target_months: list[str]) -> dict[str, str]:
    unique = sorted(set(pre_months))
    if not unique:
        raise ValueError("no pre-period donor months")
    if max(unique) > PRE_END:
        raise ValueError("donor months contain post-period outcomes")
    return {target: unique[index % len(unique)] for index, target in enumerate(target_months)}


def draw_rademacher_by_cluster(clusters, seed: int) -> dict[str, float]:
    labels = sorted({str(value) for value in clusters})
    if len(labels) < 2:
        raise ValueError("wild cluster bootstrap needs at least two occupations")
    rng = np.random.default_rng(seed)
    draws = rng.choice(np.array([-1.0, 1.0]), size=len(labels))
    return dict(zip(labels, draws))


def inject_log_mean_effect(frame, effect: float):
    """Multiply only Q5-young post synthetic means by exp(effect)."""
    result = frame.copy()
    required = {"age_group", "exposure_quintile", "is_post", "mean_headcount"}
    missing = required - set(result.columns)
    if missing:
        raise ValueError(f"synthetic panel missing columns {sorted(missing)}")
    mask = (
        (result["age_group"] == "young_22_25")
        & (result["exposure_quintile"] == 5)
        & result["is_post"].astype(bool)
    )
    result.loc[mask, "mean_headcount"] = (
        result.loc[mask, "mean_headcount"].astype(float) * math.exp(effect)
    )
    return result


def assert_real_power_blocked(c1_receipt: dict[str, object] | None = None) -> None:
    if not c1_receipt or c1_receipt.get("status") != "PASS":
        raise RealPowerBlocked("real power blocked until C1 exposure/crosswalk receipt is PASS")
    raise RealPowerBlocked(
        "real PPML power remains disabled in the skeleton; implement and review the "
        "registered estimator before enabling"
    )


def synthetic_smoke() -> dict[str, object]:
    import pandas as pd

    panel = pd.DataFrame({
        "age_group": ["young_22_25", "older_26_65"] * 2,
        "exposure_quintile": [5, 5, 1, 1],
        "is_post": [True, True, True, True],
        "mean_headcount": [100.0, 100.0, 100.0, 100.0],
    })
    shifted = inject_log_mean_effect(panel, PRIMARY_BENCHMARK)
    q5_young = float(shifted.loc[
        (shifted["exposure_quintile"] == 5)
        & (shifted["age_group"] == "young_22_25"),
        "mean_headcount",
    ].iloc[0])
    return {
        "status": "SYNTHETIC_ENGINE_VALIDATION_NOT_POWER",
        "real_power_executed": False,
        "post_outcomes_read": False,
        "primary_benchmark_log": round(PRIMARY_BENCHMARK, 9),
        "q5_young_shifted_headcount": round(q5_young, 6),
        "planned_post_month_count": len(planned_post_months()),
        "planned_post_missing_months": sorted(POST_GAPS),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthetic-smoke", action="store_true", required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    result = synthetic_smoke()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
