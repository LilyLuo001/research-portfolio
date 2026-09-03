#!/usr/bin/env python3
"""Build treatment-dose and conditional-power artifacts without outcomes.

This script deliberately never reads an outcome or regression-result file.  It
uses the frozen ownership exposure and the design-only variance operator from
the September 3 viability audit.  Absolute MDEs are sensitivity calculations,
not estimates: TAQ outcomes do not exist in the current archive.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from p1.viability.audit_viability import design_stats


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "p1" / "strategic_pivot"
EXPOSURES = {
    "all_sponsors": ROOT / "p1" / "exposure" / "exposure_stock_wave_all.csv",
    "dimensional_only": ROOT / "p1" / "exposure" / "exposure_stock_wave_dimensional_only.csv",
    "exclude_dimensional": ROOT / "p1" / "exposure" / "exposure_stock_wave_ex_dimensional.csv",
}
DIM = "Dimensional Fund Advisors LP"
HIGH_DOSE = 0.005  # frozen P1 threshold; not chosen using outcomes
QUANTILES = {"p10": .10, "p25": .25, "median": .50, "p75": .75,
             "p90": .90, "p95": .95, "p99": .99, "max": 1.00}


def market_cap_bucket(x: float) -> str:
    if x < 300_000_000:
        return "micro_cap_lt_300m"
    if x < 2_000_000_000:
        return "small_cap_300m_2b"
    if x < 10_000_000_000:
        return "mid_cap_2b_10b"
    return "large_cap_ge_10b"


def clean(path: Path, sample: str) -> pd.DataFrame:
    d = pd.read_csv(path)
    d = d.loc[d["primary_ready"].eq(True) & d["exposure_ownership"].gt(0)].copy()
    d["permno"] = d["permno"].astype("Int64")
    d["sponsor"] = d["advisers"].fillna("UNKNOWN_ADVISER_PROXY").str.strip()
    d["market_cap_bucket"] = d["market_cap_usd"].map(market_cap_bucket)
    d["convexp"] = d["exposure_ownership"]
    d["ownership_percentage"] = 100 * d["exposure_ownership"]
    d["market_cap_share"] = d["exposure_value"]
    d["market_cap_share_percentage"] = 100 * d["exposure_value"]
    d["high_dose_ge_0p5pct"] = d["exposure_ownership"].ge(HIGH_DOSE)
    d["sample"] = sample
    return d


def dose_outputs(data: dict[str, pd.DataFrame]) -> None:
    cells = pd.concat(data.values(), ignore_index=True)[[
        "sample", "permno", "wave_id", "effective_date", "sponsor", "is_dimensional",
        "market_cap_bucket", "adjusted_shares_held", "shares_outstanding",
        "convexp", "ownership_percentage", "position_value_usd",
        "market_cap_usd", "market_cap_share", "market_cap_share_percentage",
        "fund_portfolio_weight_sum", "n_positions", "n_events",
        "n_predecessor_funds", "high_dose_ge_0p5pct", "pre_report_date_min",
        "pre_report_date_max", "source_accessions",
    ]].rename(columns={"adjusted_shares_held": "predecessor_fund_holdings_shares",
                       "position_value_usd": "predecessor_holdings_dollar_value"})
    cells.to_csv(OUT / "p1_treatment_dose_cells.csv", index=False)

    d = data["all_sponsors"]
    groups: list[tuple[str, pd.DataFrame]] = [
        ("all_sponsors", data["all_sponsors"]),
        ("dimensional_only", data["dimensional_only"]),
        ("exclude_dimensional", data["exclude_dimensional"]),
    ]
    for bucket in ["micro_cap_lt_300m", "small_cap_300m_2b",
                   "mid_cap_2b_10b", "large_cap_ge_10b"]:
        groups.append((bucket, d.loc[d["market_cap_bucket"].eq(bucket)]))

    rows = []
    for sample, g in groups:
        for metric, col in [
            ("convexp_ownership_share", "convexp"),
            ("predecessor_holdings_dollar_value", "position_value_usd"),
            ("market_cap_share", "market_cap_share"),
        ]:
            for label, q in QUANTILES.items():
                rows.append({
                    "sample": sample,
                    "metric": metric,
                    "statistic": label,
                    "value": float(g[col].max() if q == 1 else g[col].quantile(q)),
                    "stock_wave_cells": len(g),
                    "unique_stocks": g["permno"].nunique(),
                    "waves": g["wave_id"].nunique(),
                    "high_dose_cells_ge_0p5pct": int(g["high_dose_ge_0p5pct"].sum()),
                    "high_dose_waves_ge_0p5pct": g.loc[g["high_dose_ge_0p5pct"], "wave_id"].nunique(),
                    "cutoff_source": "P1 frozen 0.5% binary-treatment threshold; no outcomes inspected",
                })
    pd.DataFrame(rows).to_csv(OUT / "p1_treatment_dose_distribution.csv", index=False)


def power_output(data: dict[str, pd.DataFrame]) -> None:
    def design_frame(g: pd.DataFrame) -> pd.DataFrame:
        x = g[["permno", "wave_id", "sponsor", "exposure_ownership"]].copy()
        x["permno"] = x["permno"].astype(str)
        x["x"] = x["exposure_ownership"] / HIGH_DOSE
        return x

    all_d = data["all_sponsors"]
    ex_d = data["exclude_dimensional"]
    samples = {
        **data,
        "high_dose_all": all_d.loc[all_d["high_dose_ge_0p5pct"]],
        "high_dose_exclude_dimensional": ex_d.loc[ex_d["high_dose_ge_0p5pct"]],
    }
    # Conditional untreated/pre-period residual SD grid. Values are scenarios,
    # not claimed measurements. q_eff is an effective number of independent
    # repeats; R2 is the pre-period ANCOVA explanatory share.
    horizon_sds = {
        "5m": [10, 25, 50], "15m": [20, 50, 100],
        "30m": [30, 75, 150], "60m": [50, 100, 200],
        "close": [75, 150, 300], "+1d": [100, 250, 500],
    }
    rows = []
    for sample, g in samples.items():
        stats = design_stats(design_frame(g))
        for horizon, sd_grid in horizon_sds.items():
            for residual_sd_bps in sd_grid:
                for ancova_r2 in [0.0, 0.5]:
                    for q_eff in [1, 2, 4]:
                        factor = math.sqrt(1 - ancova_r2) / math.sqrt(q_eff)
                        for power, key in [(0.80, "mde80"), (0.90, "mde90")]:
                            std_mde = stats[key]
                            rows.append({
                                "sample": sample, "horizon": horizon,
                                "power": power, "alpha_two_sided": 0.05,
                                "ownership_effect_scale": "one-SD SUE at 0.5% ownership",
                                "waves": g["wave_id"].nunique(),
                                "adviser_proxy_clusters": int(stats["n_sponsors"]),
                                "unique_stocks": g["permno"].nunique(),
                                "stock_wave_cells": len(g), "cluster_df": stats["df"],
                                "design_mde_residual_sd_units": std_mde,
                                "conditional_residual_sd_bps": residual_sd_bps,
                                "preperiod_ancova_r2_assumption": ancova_r2,
                                "effective_independent_repeats_assumption": q_eff,
                                "conditional_mde_bps": (std_mde * residual_sd_bps * factor
                                                        if pd.notna(std_mde) else math.nan),
                                "variance_status": "CONDITIONAL_NOT_FINAL",
                                "variance_note": "No TAQ outcomes in archive; grid is over untreated/pre-period residual SD, ANCOVA R2, and effective repeats",
                                "dependence_note": "Design operator allows wave/sponsor/stock/idiosyncratic dependence; stocks are not independent shocks",
                                "treatment_coefficients_inspected": False,
                            })
    pd.DataFrame(rows).to_csv(OUT / "p1_corrected_power_audit.csv", index=False)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = {sample: clean(path, sample) for sample, path in EXPOSURES.items()}
    d = data["all_sponsors"]
    dose_outputs(data)
    power_output(data)
    print(f"cells={len(d)} stocks={d.permno.nunique()} waves={d.wave_id.nunique()}")
    print(d.groupby(["is_dimensional", "market_cap_bucket"])["exposure_ownership"].agg(["count", "median", "max"]))
    print("high-dose by wave")
    print(d.loc[d.high_dose_ge_0p5pct].groupby(["wave_id", "is_dimensional"]).size())


if __name__ == "__main__":
    main()
