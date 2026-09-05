#!/usr/bin/env python3
"""Build journal-facing figures for the substantive R3 manuscript.

All inputs are generated aggregate results.  The script never reads restricted
person records or occupation-month stock cells.
"""
from __future__ import annotations

import argparse
import pathlib

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = pathlib.Path(__file__).resolve().parents[2]
REVISION = ROOT / "yax/revision/substantive_r3_20260905"
FIGURES = ROOT / "paper/figures"
TABLES = ROOT / "paper/tables"
FAMILY_RESULTS = REVISION / "dynamics/rebuilt_family_harmonization/results"


def quarter_index(value: str) -> int:
    year, quarter = value.split("Q")
    return int(year) * 4 + int(quarter) - 1


def quarter_label(index: int) -> str:
    return f"{index // 4}Q{index % 4 + 1}"


def build_dynamics() -> pathlib.Path:
    source = REVISION / "dynamics/results/DYNAMIC_Q5_Q1_PROFILE.csv"
    data = pd.read_csv(source)
    data = data.loc[
        (data["treatment_contract"] == "rebuilt_corrected_preperiod_weight")
        & (data["quintile"] == 5)
    ].copy()
    structures = ["unconditioned", "SOC2_x_calendar_month"]
    titles = ["Pooled occupational comparison", "Broad-family monthly paths"]
    reference = quarter_index("2022Q4")
    minimum = min(data["event_bin"].map(quarter_index).min(), reference)
    maximum = max(data["event_bin"].map(quarter_index).max(), reference)
    grid = np.arange(minimum, maximum + 1)

    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
    })
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 6.1), sharex=True)
    for axis, structure, title in zip(axes, structures, titles):
        frame = data.loc[data["structure"] == structure].copy()
        frame["x"] = frame["event_bin"].map(quarter_index)
        frame = frame.sort_values("x")
        axis.fill_between(
            frame["x"].to_numpy(float),
            frame["ci_lower"].to_numpy(float),
            frame["ci_upper"].to_numpy(float),
            color="#9ecae1", alpha=0.42, linewidth=0,
        )
        axis.plot(
            frame["x"], frame["coefficient"], color="#08519c",
            linewidth=1.25, marker="o", markersize=2.7,
        )
        axis.scatter([reference], [0], color="black", marker="s", s=15, zorder=4)
        axis.axhline(0, color="0.25", linewidth=0.7)
        axis.axvline(reference + 0.5, color="#b30000", linewidth=0.9, linestyle="--")
        axis.set_title(title, loc="left")
        axis.set_ylabel("Log-point coefficient")
        axis.grid(axis="y", color="0.88", linewidth=0.45)
        axis.set_xlim(grid.min() - 0.4, grid.max() + 0.4)
    ticks = [value for value in grid if value % 4 == 0]
    axes[-1].set_xticks(ticks)
    axes[-1].set_xticklabels([str(value // 4) for value in ticks])
    axes[-1].set_xlabel("Calendar quarter (2022Q4 omitted)")
    fig.tight_layout(h_pad=1.0)
    output = FIGURES / "r3_figure2_dynamics.pdf"
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    return output


def build_paths() -> pathlib.Path:
    source = FAMILY_RESULTS / "REBUILT_Q1_Q5_AGGREGATE_PATHS.csv"
    data = pd.read_csv(source)
    data["date"] = pd.to_datetime(data["month"])
    full_dates = pd.date_range(data["date"].min(), data["date"].max(), freq="MS")
    variables = [
        ("young_weighted_employment_stock", "A. Ages 22--25"),
        ("older_weighted_employment_stock", "B. Ages 26--65"),
        ("young_to_older_stock_ratio", "C. Young-to-older stock ratio"),
    ]

    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
    })
    fig, axes = plt.subplots(3, 1, figsize=(7.2, 7.5), sharex=True)
    colors = {"Q1": "#636363", "Q5": "#08519c"}
    for axis, (variable, title) in zip(axes, variables):
        for tail in ("Q1", "Q5"):
            frame = data.loc[data["tail"].eq(tail), ["date", variable]].copy()
            base = frame.loc[frame["date"].dt.year.eq(2019), variable].mean()
            frame["index"] = 100 * frame[variable] / base
            frame = frame.set_index("date").reindex(full_dates)
            axis.plot(frame.index, frame["index"], color=colors[tail], linewidth=1.15, label=tail)
        axis.axhline(100, color="0.72", linewidth=0.55)
        axis.axvline(pd.Timestamp("2023-01-01"), color="#b30000", linewidth=0.9, linestyle="--")
        axis.set_title(title, loc="left")
        axis.set_ylabel("2019 = 100")
        axis.grid(axis="y", color="0.9", linewidth=0.45)
    axes[0].legend(frameon=False, ncol=2, loc="upper left")
    axes[-1].set_xlabel("Month")
    fig.tight_layout(h_pad=0.9)
    output = FIGURES / "r3_figure1_q1_q5_paths.pdf"
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    return output


def latex_escape(value: object) -> str:
    text = str(value)
    for old, new in [
        ("&", r"\&"), ("%", r"\%"), ("_", r"\_"), ("#", r"\#"),
    ]:
        text = text.replace(old, new)
    return text


def build_family_support_table() -> pathlib.Path:
    data = pd.read_csv(FAMILY_RESULTS / "FAMILY_QUINTILE_SUPPORT.csv")
    rows = []
    for row in data.itertuples(index=False):
        rows.append(
            f"{int(row.SOC2)} & {latex_escape(row.SOC2_name)} & {int(row.occupations)} & "
            f"{100 * row.preperiod_stock_share:.2f} & {row.beta_min:.3f}--{row.beta_max:.3f} & "
            f"{latex_escape(row.quintiles_present)} & {'Yes' if row.contains_Q1_and_Q5 else 'No'} \\\\"
        )
    output = TABLES / "r3_appendix_family_support.tex"
    output.write_text(
        "\\begin{center}\n"
        "\\footnotesize\n"
        "\\begin{longtable}{@{}r p{0.31\\textwidth} r r r l c@{}}\n"
        "\\caption{Broad-family exposure support}\\label{tab:app_family_support}\\\\\n"
        "\\toprule\n"
        "SOC2 & Family & Occs. & Stock (\\%) & Beta range & Quintiles & Q1 and Q5 \\\\ \n"
        "\\midrule\n"
        "\\endfirsthead\n"
        "\\multicolumn{7}{l}{\\footnotesize\\itshape Table \\thetable{} continued}\\\\\n"
        "\\toprule\n"
        "SOC2 & Family & Occs. & Stock (\\%) & Beta range & Quintiles & Q1 and Q5 \\\\ \n"
        "\\midrule\n"
        "\\endhead\n"
        "\\midrule\\multicolumn{7}{r}{\\footnotesize Continued on next page}\\\\\n"
        "\\endfoot\n"
        "\\bottomrule\n"
        "\\endlastfoot\n"
        + "\n".join(rows)
        + "\n\\end{longtable}\n"
        "\\tabnote{Stock is each family's share of preperiod employment on the 468-occupation rebuilt support.  Beta ranges and quintile memberships use the corrected 2017--2022 preperiod treatment contract.  Only rows marked Yes enter the changed-population direct-tail exercise.}\n"
        "\\end{center}\n"
    )
    return output


def build_profile_table() -> pathlib.Path:
    profile = pd.read_csv(FAMILY_RESULTS / "PROFILE_COEFFICIENTS.csv")
    paired = pd.read_csv(FAMILY_RESULTS / "PAIRED_PROFILE_CHANGES.csv")
    rows = []
    for q in range(2, 6):
        target = f"Q{q}_x_post"
        pooled = profile.loc[(profile["model_id"] == "profile_baseline") & (profile["target"] == target)].iloc[0]
        conditioned = profile.loc[
            (profile["model_id"] == "profile_SOC2_x_calendar_month") & (profile["target"] == target)
        ].iloc[0]
        contrast = f"profile_SOC2_x_calendar_month_minus_profile_baseline__{target}"
        movement = paired.loc[paired["contrast"] == contrast].iloc[0]
        rows.append(
            f"Q{q} & {pooled.coefficient:.4f} & [{pooled.pointwise_ci_lower:.4f},{pooled.pointwise_ci_upper:.4f}] & "
            f"[{pooled.simultaneous_ci_lower:.4f},{pooled.simultaneous_ci_upper:.4f}] & "
            f"{conditioned.coefficient:.4f} & [{conditioned.pointwise_ci_lower:.4f},{conditioned.pointwise_ci_upper:.4f}] & "
            f"[{conditioned.simultaneous_ci_lower:.4f},{conditioned.simultaneous_ci_upper:.4f}] & "
            f"{movement.coefficient_difference:.4f} [{movement.paired_ci_lower:.4f},{movement.paired_ci_upper:.4f}] \\\\"
        )
    output = TABLES / "r3_appendix_profile.tex"
    output.write_text(
        "\\begin{table}[!htbp]\n"
        "\\centering\n"
        "\\caption{Exposure profile before and after broad-family monthly paths}\\label{tab:app_profile}\n"
        "\\scriptsize\n"
        "\\resizebox{\\textwidth}{!}{%\n"
        "\\begin{tabular}{lrrrrrrr}\n"
        "\\toprule\n"
        "& \\multicolumn{3}{c}{Pooled} & \\multicolumn{3}{c}{SOC2 $\\times$ month} & Paired movement \\\\ \n"
        "\\cmidrule(lr){2-4}\\cmidrule(lr){5-7}\n"
        "Group & Coef. & Pointwise 95\\% CI & Simultaneous 95\\% CI & Coef. & Pointwise 95\\% CI & Simultaneous 95\\% CI & Coef. [95\\% CI] \\\\ \n"
        "\\midrule\n"
        + "\n".join(rows)
        + "\n\\bottomrule\n"
        "\\end{tabular}}\n"
        "\\tabnote{Q1 is omitted.  Simultaneous intervals use each model's common four-target maximum-$|t|$ critical value.  Paired movements are SOC2-by-calendar-month minus pooled coefficients on common occupation draws.  All rows use the rebuilt corrected-preperiod treatment contract and 9,999 draws.}\n"
        "\\end{table}\n"
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=["all", "dynamics", "paths", "tables"], default="all")
    args = parser.parse_args()
    FIGURES.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    outputs = []
    if args.only in {"all", "dynamics"}:
        outputs.append(build_dynamics())
    if args.only in {"all", "paths"}:
        outputs.append(build_paths())
    if args.only in {"all", "tables"}:
        outputs.extend([build_family_support_table(), build_profile_table()])
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
