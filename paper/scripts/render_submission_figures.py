#!/usr/bin/env python3
"""Render submission figures from previously sealed YAX result files only."""
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

mpl.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "legend.fontsize": 8,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def coefficient_figure():
    labels = [
        "AIOE administrative",
        "AIOE ability",
        "AIOE source-weighted",
        "Eloundou alpha",
        "Eloundou beta",
        "Eloundou broad",
    ]
    coef = np.array([-0.07386, -0.10285, -0.10210, -0.10132, -0.12896, -0.14652])
    low = np.array([-0.14915, -0.17722, -0.18040, -0.18547, -0.21614, -0.23285])
    high = np.array([0.00143, -0.02848, -0.02380, -0.01716, -0.04178, -0.06018])
    y = np.arange(len(labels))[::-1]
    fig, ax = plt.subplots(figsize=(6.35, 3.35))
    colors = ["0.35"] * 3 + ["0.05"] * 3
    for index in range(len(labels)):
        ax.errorbar(coef[index], y[index],
                    xerr=np.array([[coef[index] - low[index]], [high[index] - coef[index]]]),
                    fmt="none", ecolor=colors[index], elinewidth=1.25, capsize=2.5, zorder=1)
    ax.scatter(coef, y, c=colors, s=28, zorder=2)
    ax.axvline(0, color="0.55", linewidth=0.8, linestyle="--")
    ax.set_yticks(y, labels)
    ax.set_xlabel("Q5-versus-Q1 young-relative employment-stock coefficient")
    ax.set_title("Six exposure architectures on literal common support")
    ax.grid(axis="x", color="0.9", linewidth=0.6)
    fig.tight_layout()
    fig.savefig(OUT / "figure3_common_support_coefficients.pdf", bbox_inches="tight")
    plt.close(fig)


def mobility_figure():
    labels = ["Independent\nrematching", "Broad-assortative\nrematching", "Realized\nswitches"]
    values = np.array([45.27, 52.32, 53.28])
    fig, ax = plt.subplots(figsize=(5.7, 3.25))
    bars = ax.bar(labels, values, color=["0.78", "0.48", "0.18"], width=0.62)
    ax.set_ylim(0, 60)
    ax.set_ylabel("Switches with conflicting directional labels (percent)")
    ax.set_title("Architecture disagreement is frequent, but broad assortativity accounts for most excess")
    ax.grid(axis="y", color="0.9", linewidth=0.6)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 1.1, f"{value:.2f}",
                ha="center", va="bottom", fontsize=9)
    ax.annotate("0.96 pp", xy=(2, values[2]), xytext=(1, 58),
                ha="center", arrowprops={"arrowstyle": "-[,widthB=2.3", "color": "0.25"})
    fig.tight_layout()
    fig.savefig(OUT / "figure4_mobility_conflict.pdf", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    coefficient_figure()
    mobility_figure()
