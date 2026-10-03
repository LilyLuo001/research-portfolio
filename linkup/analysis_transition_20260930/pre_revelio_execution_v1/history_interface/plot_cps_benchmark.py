#!/usr/bin/env python3
"""Plot the frozen CPS RTI occupation-composition benchmark from its CSV."""
from __future__ import annotations

import argparse
import csv
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter


PERIODS = ("early_window", "late_window")
LABELS = {"early_window": "2004–2006", "late_window": "2023–2025"}
SERIES = (
    ("q1_low_rti_share_all_employed", "Q1: lowest RTI"),
    ("q2_share_all_employed", "Q2"),
    ("q3_share_all_employed", "Q3"),
    ("q4_high_rti_share_all_employed", "Q4: highest RTI"),
)
EXPECTED = {
    "early_window": (0.2500634788564959, 0.24692025188324804,
                     0.24933017165901603, 0.2424043102385248),
    "late_window": (0.27622086840269255, 0.2684629004298277,
                    0.2397915425121621, 0.2024013854607406),
}


def load(path: Path):
    with path.open(encoding="utf-8", newline="") as handle:
        rows = {row["period"]: row for row in csv.DictReader(handle)}
    if set(rows) != set(PERIODS):
        raise ValueError("benchmark CSV must contain exactly the two frozen windows")
    for period in PERIODS:
        values = tuple(float(rows[period][field]) for field, _ in SERIES)
        if any(abs(actual - expected) > 1e-12
               for actual, expected in zip(values, EXPECTED[period])):
            raise ValueError(f"{period} values differ from frozen CPS benchmark")
        mapped = float(rows[period]["rti_mapped_weight_share"])
        unmapped = float(rows[period]["unmapped_share_all_employed"])
        if abs(sum(values) + unmapped - 1) > 1e-9 or abs(mapped + unmapped - 1) > 1e-9:
            raise ValueError(f"{period} shares do not conserve the all-employed denominator")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path(__file__).with_name("CPS_BENCHMARK.csv"))
    parser.add_argument("--output-stem", type=Path, default=Path(__file__).with_name("CPS_BENCHMARK_FIGURE"))
    args = parser.parse_args()
    rows = load(args.input)

    fig, ax = plt.subplots(figsize=(9.2, 5.8))
    x = list(range(len(SERIES)))
    width = 0.34
    colors = ("#4472C4", "#ED7D31")
    for offset, period in enumerate(PERIODS):
        values = [float(rows[period][field]) for field, _ in SERIES]
        positions = [value + (offset - 0.5) * width for value in x]
        bars = ax.bar(positions, values, width=width, label=LABELS[period], color=colors[offset])
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, value + 0.004,
                    f"{value:.1%}", ha="center", va="bottom", fontsize=9)

    ax.set_title("Employment composition across fixed routine-task-intensity quartiles", pad=12)
    ax.set_ylabel("Share of all ASEC-weighted employed respondents")
    ax.set_xticks(x, [label for _, label in SERIES])
    ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.set_ylim(0, 0.32)
    ax.grid(axis="y", alpha=0.25, linewidth=0.7)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper right")

    early = rows["early_window"]; late = rows["late_window"]
    footnote = (
        "Notes: Denominator is all ASEC-weighted respondents employed at the survey date in each pooled "
        "three-year window. Unmapped RTI: "
        f"{float(early['unmapped_share_all_employed']):.2%} "
        f"({float(early['rti_unmapped_weight']):,.0f} pooled weighted person-years) in 2004–2006; "
        f"{float(late['unmapped_share_all_employed']):.2%} "
        f"({float(late['rti_unmapped_weight']):,.0f}) in 2023–2025. "
        "Quartile cutpoints are fixed from the 2004–2006 weighted distribution. Static occupation-level "
        "RTI mapping; descriptive cohort comparison, not a causal computerization estimate."
    )
    fig.text(0.075, 0.015, textwrap.fill(footnote, width=145),
             ha="left", va="bottom", fontsize=8)
    fig.tight_layout(rect=(0.05, 0.20, 0.98, 0.98))
    args.output_stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output_stem.with_suffix(".png"), dpi=220, bbox_inches="tight")
    fig.savefig(args.output_stem.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
