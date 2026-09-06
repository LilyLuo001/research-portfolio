#!/usr/bin/env python3
"""Render only gate-eligible YAX Phase 3 figures from sealed result files.

POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1.
This renderer estimates nothing and cannot alter a result classification.
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd


LABEL = "POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1"
HERE = pathlib.Path(__file__).resolve().parent


def run(directory: pathlib.Path = HERE) -> list[pathlib.Path]:
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    made: list[pathlib.Path] = []
    hard = json.loads((directory / "YAX_PHASE3_HARD_BENCHMARK_RESULTS.json").read_text())
    primary = hard["primary_hard_benchmark"]
    if primary["classification"] in {"HB-A", "HB-B"}:
        draws = np.asarray(primary["benchmark_draws"], float)
        path = directory / "YAX_PHASE3_HARD_BENCHMARK_FIGURE.png"
        fig, ax = plt.subplots(figsize=(7.0, 4.5))
        ax.hist(draws, bins=30, color="#6baed6", edgecolor="white")
        ax.axvline(primary["realized_conflict_official_weight"], color="#cb181d", lw=2, label="Realized")
        ax.axvline(primary["hard_benchmark_mean"], color="black", ls="--", label="Hard benchmark mean")
        ax.set_xlabel("Six-architecture directional-conflict rate")
        ax.set_ylabel("Constrained-rematching draws")
        ax.legend(frameon=False)
        fig.tight_layout(); fig.savefig(path, dpi=200); plt.close(fig)
        made.append(path)

    summary = json.loads((directory / "YAX_PHASE3_REALLOCATION_COMPONENT_RESULTS.json").read_text())
    if summary["classification"] in {"SC-R1", "SC-R2"}:
        rows = pd.read_csv(directory / "YAX_PHASE3_REALLOCATION_COMPONENT_RESULTS.csv")
        selected = rows.loc[
            rows.section.eq("F_distance_bin") & rows.pair.eq("all_six")
        ].copy()
        path = directory / "YAX_PHASE3_REALLOCATION_COMPONENT_FIGURE.png"
        fig, ax = plt.subplots(figsize=(7.0, 4.5))
        for sample, style in [("primary", "o-"), ("persistent", "s--")]:
            values = selected.loc[selected["sample"].eq(sample)].sort_values("bin_or_group")
            ax.plot(values.bin_or_group.astype(int), values.conflict_rate, style, label=sample.capitalize())
        ax.set_xlabel("Weighted quintile of |Δ shared family component|")
        ax.set_ylabel("Official-weight directional-conflict rate")
        ax.set_xticks(range(1, 6))
        ax.legend(frameon=False)
        fig.tight_layout(); fig.savefig(path, dpi=200); plt.close(fig)
        made.append(path)

    stock = json.loads((directory / "YAX_PHASE3_SHARED_STOCK_RESULT.json").read_text())
    if stock["classification"] in {"SC-A", "SC-B"}:
        path = directory / "YAX_PHASE3_SHARED_STOCK_FIGURE.png"
        coefficient = stock["coefficient_log_points"]
        low, high = stock["wild_score_ci_lower"], stock["wild_score_ci_upper"]
        fig, ax = plt.subplots(figsize=(6.0, 2.8))
        ax.errorbar([coefficient], [0], xerr=[[coefficient - low], [high - coefficient]], fmt="o", color="#2171b5", capsize=4)
        ax.axvline(0, color="black", lw=1, ls="--")
        ax.set_yticks([0], ["Shared F: Q5 vs Q1"])
        ax.set_xlabel("Coefficient (log points; 95% wild-score CI)")
        fig.tight_layout(); fig.savefig(path, dpi=200); plt.close(fig)
        made.append(path)
    return made


if __name__ == "__main__":
    for result in run():
        print(result)
