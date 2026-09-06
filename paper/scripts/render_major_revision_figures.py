#!/usr/bin/env python3
"""Render figures for the second-round, evidence-led major revision."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
ROUND2 = ROOT / "yax" / "revision" / "referee_round2_20260905"
OUT = ROOT / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

BLUE = "#1f4e79"
RED = "#a23b3b"
GOLD = "#b07d16"
GRAY = "#707070"
LIGHT = "#d9d9d9"

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.size": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 180,
        "savefig.bbox": "tight",
    }
)


def save(fig, name):
    fig.savefig(OUT / name, format="pdf")
    plt.close(fig)


def composition_figure():
    comp = pd.read_csv(ROUND2 / "composition_influence" / "results" / "COMPOSITION_MODELS.csv")
    comp = comp[comp["calendar"].eq("March_repaired_113_month")].set_index("model")
    services = pd.read_csv(
        ROUND2 / "composition_influence" / "results" / "OCCUPATION_SERVICE_EXCLUSIONS.csv"
    ).set_index("specification")
    joint = pd.read_csv(
        ROUND2 / "composition_influence" / "results" / "JOINT_DELETION_AND_ROBUST_INFLUENCE.csv"
    ).set_index("specification")
    bcc = pd.read_csv(ROUND2 / "bcc_bridge" / "results" / "BCC_GROUPING_ARCHITECTURE_RESULTS.csv")
    bcc = bcc[(bcc["architecture"].eq("dv_rating_beta")) & (bcc["support_rule"].eq("native"))].iloc[0]

    rows = [
        ("Corrected baseline: Q5–Q1", comp.loc["frozen_baseline"]),
        ("Condition on SOC2 × post", comp.loc["SOC2_x_post"]),
        ("Condition on SOC2 × month", comp.loc["SOC2_x_calendar_month"]),
        ("Exclude Q1 food-service occupations", services.loc["exclude_Q1_SOC35_food_preparation_and_serving"]),
        ("Delete five most influential occupations", joint.loc["joint_leave_top_5_frozen_LOCO"]),
        ("BCC top-two vs bottom-three grouping", bcc),
    ]

    labels = [x[0] for x in rows]
    est = np.array([float(x[1]["coefficient"]) for x in rows])
    lo = np.array([float(x[1]["ci_lower"]) for x in rows])
    hi = np.array([float(x[1]["ci_upper"]) for x in rows])
    y = np.arange(len(rows))[::-1]
    colors = [RED, BLUE, BLUE, GRAY, GRAY, GOLD]

    fig, ax = plt.subplots(figsize=(8.2, 4.7))
    for yi, e, l, h, color in zip(y, est, lo, hi, colors):
        ax.errorbar(e, yi, xerr=[[e - l], [h - e]], fmt="o", color=color, capsize=2.5, lw=1.4)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_yticks(y, labels)
    ax.set_xlabel("Young-relative post coefficient (log points)")
    ax.set_title("Broad occupational composition absorbs most of the detailed tail contrast")
    ax.text(
        0.99,
        0.01,
        "Intervals use 9,999 occupation-level wild-score draws; rows change the conditioning set or contrast.",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=7.2,
        color=GRAY,
    )
    save(fig, "figure2_composition_major_revision.pdf")


def architecture_precision_figure():
    d = pd.read_csv(ROUND2 / "precision_rotation" / "results" / "PAIRED_ARCHITECTURE_PRECISION.csv")
    label_map = {
        "dv_rating_beta_minus_aioe_admin_equal": "AIOE administrative",
        "dv_rating_beta_minus_aioe_ability_direct": "AIOE ability/direct",
        "dv_rating_beta_minus_aioe_oews2018_source_weighted": "AIOE OEWS-weighted",
        "dv_rating_beta_minus_dv_rating_alpha": "Eloundou alpha",
        "dv_rating_beta_minus_dv_rating_gamma": "Eloundou broad",
        "dv_rating_beta_minus_webb_ai_patent_task": "Webb AI",
        "dv_rating_beta_minus_oecd_ai_capability_gap_reversed": "OECD capability gap",
    }
    d["label"] = d["contrast"].map(label_map)
    y = np.arange(len(d))[::-1]
    e = d["difference_beta_minus_alternative"].to_numpy()
    lo = d["paired_ci_lower"].to_numpy()
    hi = d["paired_ci_upper"].to_numpy()
    mde = d["paired_normal_theory_mde80_log_points"].to_numpy()

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    ax.hlines(y, -mde, mde, color=LIGHT, lw=7, zorder=1, label="± paired MDE80")
    ax.errorbar(e, y, xerr=[e - lo, hi - e], fmt="o", color=BLUE, capsize=2.5, lw=1.3, zorder=2,
                label="Paired estimate and 95% CI")
    ax.axvline(0, color="black", lw=0.8)
    ax.set_yticks(y, d["label"])
    ax.set_xlabel("Beta minus alternative Q5–Q1 coefficient (log points)")
    ax.set_title("The CPS design does not resolve architecture differences")
    ax.legend(frameon=False, loc="lower left")
    save(fig, "figure4_architecture_precision.pdf")


def pseudo_break_figure():
    d = pd.read_csv(ROUND2 / "precision_rotation" / "results" / "PSEUDO_BREAK_DISTRIBUTION_2017_2019.csv")
    d = d[
        d["classification_rule"].eq("pre_AI_2017_2019_weights")
        & d["balanced_at_least_12_months_each_side"]
    ].copy()
    d["date"] = pd.to_datetime(d["pseudo_break"])
    d = d.sort_values("date")
    observed = -0.131074

    fig, ax = plt.subplots(figsize=(8.2, 4.1))
    ax.plot(d["date"], d["estimate_log_points"], marker="o", color=BLUE, lw=1.2,
            label="Balanced pre-AI pseudo-break estimate")
    ax.axhline(0, color="black", lw=0.8)
    ax.axhline(observed, color=RED, lw=1.2, ls="--", label="January-2023 frozen estimate")
    ax.set_ylabel("Q5–Q1 coefficient (log points)")
    ax.set_xlabel("Pseudo-break month")
    ax.set_title("Balanced 2017–2019 pseudo-breaks are centered near zero")
    ax.legend(frameon=False)
    ax.tick_params(axis="x", rotation=30)
    save(fig, "appendix_pseudo_breaks.pdf")


if __name__ == "__main__":
    composition_figure()
    architecture_precision_figure()
    pseudo_break_figure()
