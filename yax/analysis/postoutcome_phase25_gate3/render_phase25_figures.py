#!/usr/bin/env python3
"""Render the two fixed Phase-2.5 figures from stored aggregate outputs."""
from __future__ import annotations

import json
import pathlib

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def main() -> int:
    output = pathlib.Path(__file__).resolve().parent
    agreement = pd.read_csv(output / "YAX_PHASE25_PAIR_SPECIFIC_AGREEMENT.csv")
    support = pd.read_csv(output / "YAX_PHASE25_PAIR_SPECIFIC_SUPPORT.csv")
    agreement = agreement.merge(
        support[["measure_1", "measure_2", "pair_support_weighted_share"]],
        on=["measure_1", "measure_2"],
    )
    labels = [f"{row.measure_1}\nvs {row.measure_2}" for row in agreement.itertuples()]
    x = np.arange(len(agreement))
    fig, left = plt.subplots(figsize=(13, 6.5))
    left.plot(x, agreement.pair_sign_agreement_weighted, "o-", color="#2166ac",
              label="agreement: pair support")
    left.plot(x, agreement.sixway_sign_agreement_weighted, "s--", color="#b2182b",
              label="agreement: six-way support")
    left.set_ylim(0, 1)
    left.set_ylabel("Official-weight sign agreement")
    left.set_xticks(x, labels, rotation=60, ha="right", fontsize=7)
    right = left.twinx()
    right.bar(x, agreement.pair_support_weighted_share, alpha=0.16, color="#4d9221",
              label="pair support share")
    right.set_ylim(0, 1)
    right.set_ylabel("Pair-specific support share")
    lines_left, labels_left = left.get_legend_handles_labels()
    lines_right, labels_right = right.get_legend_handles_labels()
    left.legend(lines_left + lines_right, labels_left + labels_right, loc="lower right", fontsize=8)
    left.set_title("Pair-specific support broadens coverage without erasing architecture disagreement")
    fig.tight_layout()
    fig.savefig(output / "YAX_PHASE25_PAIR_SUPPORT_FIGURE.png", dpi=180)
    plt.close(fig)

    benchmark = json.loads(
        (output / "YAX_PHASE25_REALIZED_VS_MATCHED_BENCHMARK.json").read_text()
    )["primary"]
    draws = np.asarray(benchmark["benchmark_draws"])
    fig, axis = plt.subplots(figsize=(7.5, 4.8))
    axis.hist(draws, bins=30, color="#6baed6", edgecolor="white")
    axis.axvline(
        benchmark["realized_conflict_official_weight"], color="#cb181d", linewidth=2.2,
        label=f"realized: {benchmark['realized_conflict_official_weight']:.3f}",
    )
    axis.axvline(
        benchmark["benchmark_mean"], color="black", linestyle="--", linewidth=1.7,
        label=f"matched mean: {benchmark['benchmark_mean']:.3f}",
    )
    axis.set_xlabel("Six-architecture opposite-direction conflict rate")
    axis.set_ylabel("Matched-remapping draws")
    axis.set_title("Realized switches are more conflict-heavy than matched remappings")
    axis.legend()
    fig.tight_layout()
    fig.savefig(output / "YAX_PHASE25_REALIZED_VS_MATCHED_BENCHMARK_FIGURE.png", dpi=180)
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
