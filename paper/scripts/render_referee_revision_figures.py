#!/usr/bin/env python3
"""Render all figures added in the 2026-09-05 referee revision."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "yax" / "revision" / "referee_20260905" / "results"
OUT = ROOT / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

BLUE = "#1f4e79"
RED = "#a23b3b"
GOLD = "#b07d16"
GRAY = "#707070"

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 180,
    "savefig.bbox": "tight",
})


def save(fig, name):
    fig.savefig(OUT / name, format="pdf")
    plt.close(fig)


def architecture_figure():
    fig, ax = plt.subplots(figsize=(10.2, 4.1))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    boxes = [
        (0.2, 3.45, 2.1, 1.05, "Ability family\nAIOE", BLUE),
        (0.2, 1.25, 2.1, 1.05, "Task family\nEloundou D + λS", RED),
        (3.0, 3.45, 2.3, 1.05, "Three implementations\nshared ability links", BLUE),
        (3.0, 1.25, 2.3, 1.05, "Three λ choices\n0, 1/2, 1", RED),
        (6.0, 3.45, 1.7, 1.05, "Mapping\nand support", GRAY),
        (6.0, 1.25, 1.7, 1.05, "Mapping\nand support", GRAY),
        (8.25, 2.35, 1.55, 1.05, "Economic\nstatement", GOLD),
    ]
    for x, y, w, h, label, color in boxes:
        ax.add_patch(plt.Rectangle((x, y), w, h, facecolor="white", edgecolor=color, lw=1.6))
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", color=color, fontweight="bold")
    for y in (3.98, 1.78):
        ax.annotate("", xy=(2.95, y), xytext=(2.35, y), arrowprops=dict(arrowstyle="->", color=GRAY, lw=1.4))
        ax.annotate("", xy=(5.95, y), xytext=(5.35, y), arrowprops=dict(arrowstyle="->", color=GRAY, lw=1.4))
        ax.annotate("", xy=(8.2, 2.88), xytext=(7.75, y), arrowprops=dict(arrowstyle="->", color=GRAY, lw=1.4))
    ax.text(5.0, 0.45, "External concepts: Webb AI patent–task exposure and OECD capability gap", ha="center", color=GRAY)
    ax.text(5.0, 4.83, "Two selected families; six implementations—not six independent measurements", ha="center", fontweight="bold")
    save(fig, "figure1_architecture_genealogy_revised.pdf")


def employment_benchmarks():
    place = pd.read_csv(RESULTS / "core" / "PLACEBO_BENCHMARK.csv")
    ext = pd.read_csv(RESULTS / "external" / "EXTERNAL_ARCHITECTURE_OUTCOMES.csv")
    labels = ["Eloundou beta", "Wage", "Education", "Cognitive", "Telework", "STEM",
              "Webb AI", "OECD capability"]
    est = list(place["coefficient"]) + list(ext["coefficient"])
    lo = list(place["ci_lower"]) + list(ext["ci_lower"])
    hi = list(place["ci_upper"]) + list(ext["ci_upper"])
    colors = [RED] + [GRAY] * 5 + [BLUE, BLUE]
    y = np.arange(len(labels))[::-1]
    fig, ax = plt.subplots(figsize=(7.7, 4.8))
    for yi, e, l, h, c in zip(y, est, lo, hi, colors):
        ax.errorbar(e, yi, xerr=[[e-l], [h-e]], fmt="o", color=c, capsize=2.5, lw=1.4)
    ax.axvline(0, color="black", lw=.8)
    ax.set_yticks(y, labels)
    ax.set_xlabel("Q5−Q1 young-relative post coefficient (log points)")
    ax.set_title("Same-design occupational benchmarks and external architectures")
    ax.text(.99, .01, "Gray: identical 363-occupation benchmark support; blue: native external support",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=7.5, color=GRAY)
    save(fig, "figure2_employment_benchmarks.pdf")


def tail_paths():
    d = pd.read_csv(RESULTS / "core" / "Q1_Q5_STOCK_PATHS.csv")
    d["date"] = pd.to_datetime(d["month"])
    fig, axes = plt.subplots(2, 3, figsize=(11, 6.3), sharex=True)
    titles = {"young_stock": "Young employment stock", "older_stock": "Older employment stock", "young_older_ratio": "Young/older stock ratio"}
    for row, norm in enumerate(["mean_observed_2019", "mean_observed_2022"]):
        for col, obj in enumerate(["young_stock", "older_stock", "young_older_ratio"]):
            ax = axes[row, col]
            s = d[(d.normalization == norm) & (d.object == obj)]
            for q, color in [(1, BLUE), (5, RED)]:
                z = s[s.quintile == q]
                ax.plot(z.date, z.index_100, lw=1.2, color=color, label=f"Q{q}")
            ax.axvline(pd.Timestamp("2023-01-01"), color=GRAY, ls="--", lw=.8)
            ax.axhline(100, color="#bbbbbb", lw=.6)
            ax.set_title(titles[obj])
            if col == 0:
                ax.set_ylabel("2019=100" if row == 0 else "2022=100")
            if row == 0 and col == 2:
                ax.legend(frameon=False)
            ax.tick_params(axis="x", rotation=30)
    fig.suptitle("Q1 and Q5 employment paths under the frozen beta classification", y=1.01, fontweight="bold")
    fig.tight_layout()
    save(fig, "figure3_q1_q5_paths.pdf")


def age_time():
    age = pd.read_csv(RESULTS / "balanced_cells" / "AGE_COMPARISON_RESULTS.csv")
    tim = pd.read_csv(RESULTS / "balanced_cells" / "TIME_HETEROGENEITY_RESULTS.csv").iloc[:3]
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.2))
    a = age.iloc[:5].copy()
    y = np.arange(len(a))[::-1]
    axes[0].errorbar(a.coefficient, y,
                     xerr=[a.coefficient-a.ci_lower, a.ci_upper-a.coefficient],
                     fmt="o", color=BLUE, capsize=2.5)
    axes[0].axvline(0, color="black", lw=.8)
    axes[0].set_yticks(y, [x.replace("_", "–").replace("vs", " vs ") for x in a.comparison])
    axes[0].set_xlabel("Q5−Q1 coefficient")
    axes[0].set_title("Alternative comparison ages")
    y2 = np.arange(3)[::-1]
    axes[1].errorbar(tim.coefficient, y2,
                     xerr=[tim.coefficient-tim.ci_lower, tim.ci_upper-tim.coefficient],
                     fmt="o", color=RED, capsize=2.5)
    axes[1].axvline(0, color="black", lw=.8)
    axes[1].set_yticks(y2, ["2023", "2024", "2025–26"])
    axes[1].set_xlabel("Q5−Q1 coefficient")
    axes[1].set_title("Post-period heterogeneity")
    fig.tight_layout()
    save(fig, "figure4_age_time_heterogeneity.pdf")


def mobility_thresholds():
    d = pd.read_csv(RESULTS / "mobility" / "MOBILITY_THRESHOLD_RESULTS.csv")
    d = d[(d.architecture_set == "all_six") & (d.scale == "standardized_score") & (d["sample"] == "all_switches")]
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.plot(d.threshold, 100*d.directional_conflict_conditional_on_eligibility, marker="o", color=BLUE, label="Any directional conflict | eligible")
    ax.plot(d.threshold, 100*d.substantial_opposition_share_all_switches, marker="s", color=RED, label="Substantial opposition | all switches")
    ax.axhline(100*float(d.iloc[0].movement_mass_weighted_conflict), color=GOLD, ls="--", label="Movement-mass weighted conflict")
    ax.set_xlabel("Standardized movement threshold")
    ax.set_ylabel("Percent")
    ax.set_ylim(0, 60)
    ax.set_title("Ranking conflict falls when movement size matters")
    ax.legend(frameon=False)
    save(fig, "figure5_mobility_thresholds.pdf")


if __name__ == "__main__":
    architecture_figure()
    employment_benchmarks()
    tail_paths()
    age_time()
    mobility_thresholds()
