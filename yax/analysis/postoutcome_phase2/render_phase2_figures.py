#!/usr/bin/env python3
"""Render the two figures fixed in the committed Phase-2 plan."""
from __future__ import annotations

import argparse
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


MEASURES = [
    "aioe_admin_equal", "aioe_ability_direct", "aioe_oews2018_source_weighted",
    "dv_rating_alpha", "dv_rating_beta", "dv_rating_gamma",
]


def render(directory: pathlib.Path) -> None:
    results = pd.read_csv(directory / "YAX_PHASE2_PRIMARY_BETA_FLOW_RESULTS.csv")
    primary = results.loc[
        results.weighting.eq("official")
        & results.margin.isin(["employment_exit", "occupational_outflow", "entry_destination"])
    ].set_index("margin").loc[["employment_exit", "occupational_outflow", "entry_destination"]]
    estimates = primary.coefficient_log_points.to_numpy(float)
    lower = primary.wild_score_ci_lower.to_numpy(float)
    upper = primary.wild_score_ci_upper.to_numpy(float)
    y = np.arange(3)
    fig, ax = plt.subplots(figsize=(7.2, 3.7))
    ax.errorbar(estimates, y, xerr=np.vstack([estimates - lower, upper - estimates]),
                fmt="o", color="#1f4e79", capsize=4)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_yticks(y, ["Employment exit", "Occupational outflow", "Entry destination"])
    ax.invert_yaxis()
    ax.set_xlabel("Beta Q5 vs Q1 young-relative post coefficient (log points)")
    ax.set_title("Phase 2A: primary beta flow margins")
    fig.tight_layout()
    fig.savefig(directory / "figure_phase2A_beta_flow_margins.png", dpi=180)
    plt.close(fig)

    pairs = pd.read_csv(directory / "YAX_PHASE2_PAIRWISE_SIGN_AGREEMENT.csv")
    pairs = pairs.loc[pairs.switch_sample.eq("primary") & pairs.weighting.eq("official")]
    matrix = pd.DataFrame(np.eye(len(MEASURES)), index=MEASURES, columns=MEASURES)
    for row in pairs.to_dict("records"):
        matrix.loc[row["measure_1"], row["measure_2"]] = row["sign_agreement_rate"]
        matrix.loc[row["measure_2"], row["measure_1"]] = row["sign_agreement_rate"]
    fig, ax = plt.subplots(figsize=(7.2, 6.2))
    image = ax.imshow(matrix.to_numpy(float), vmin=0, vmax=1, cmap="Blues")
    ax.set_xticks(range(len(MEASURES)), MEASURES, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(MEASURES)), MEASURES, fontsize=8)
    for i in range(len(MEASURES)):
        for j in range(len(MEASURES)):
            value = matrix.iloc[i, j]
            ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=8,
                    color="white" if value > 0.65 else "black")
    ax.set_title("Sign agreement on realized occupational transitions")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(directory / "figure_phase2B_pairwise_sign_agreement.png", dpi=180)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent)
    args = parser.parse_args()
    render(args.directory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
