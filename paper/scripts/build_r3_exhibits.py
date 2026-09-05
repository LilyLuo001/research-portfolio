#!/usr/bin/env python3
"""Build journal-facing figures for the substantive R3 manuscript.

All inputs are generated aggregate results.  The script never reads restricted
person records or occupation-month stock cells.
"""
from __future__ import annotations

import argparse
import pathlib
import textwrap

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


def build_family_paths() -> pathlib.Path:
    """Plot young and older stocks in the four selected direct-tail families."""
    selection = pd.read_csv(FAMILY_RESULTS / "FAMILY_TRAJECTORY_SELECTION.csv").sort_values(
        "selection_rank"
    )
    trajectories = pd.read_csv(FAMILY_RESULTS / "FAMILY_TAIL_TRAJECTORIES.csv")
    trajectories["date"] = pd.to_datetime(trajectories["month"])
    full_dates = pd.date_range(
        trajectories["date"].min(), trajectories["date"].max(), freq="MS"
    )
    colors = {"Q1": "#636363", "Q5": "#08519c"}
    age_series = {
        "Young (ages 22-25)": ("young_weighted_employment_stock", "-"),
        "Older (ages 26-65)": ("older_weighted_employment_stock", "--"),
    }
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 8,
        "axes.titlesize": 9,
        "axes.labelsize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
    })
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.8), sharex=True)
    for axis, selected in zip(axes.flat, selection.itertuples(index=False)):
        frame = trajectories.loc[trajectories["SOC2"].eq(selected.SOC2)].copy()
        for tail in ("Q1", "Q5"):
            tail_frame = frame.loc[frame["tail"].eq(tail)].sort_values("date").copy()
            for age_label, (variable, linestyle) in age_series.items():
                base = tail_frame.loc[tail_frame["date"].dt.year.eq(2019), variable].mean()
                series = tail_frame.loc[:, ["date", variable]].copy()
                series["index"] = 100 * series[variable] / base
                series = series.set_index("date").reindex(full_dates)
                axis.plot(
                    series.index,
                    series["index"],
                    color=colors[tail],
                    linestyle=linestyle,
                    linewidth=1.05,
                    label=f"{tail} {age_label}",
                )
        axis.axhline(100, color="0.72", linewidth=0.5)
        axis.axvline(pd.Timestamp("2023-01-01"), color="#b30000", linewidth=0.8, linestyle="--")
        axis.set_title(textwrap.fill(str(selected.SOC2_name), 34), loc="left")
        axis.set_ylabel("Employment stock\n(2019=100)")
        axis.grid(axis="y", color="0.9", linewidth=0.4)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, ncol=2, loc="upper center")
    fig.tight_layout(rect=(0, 0, 1, 0.92), h_pad=1.0, w_pad=1.0)
    output = FIGURES / "r3_figure3_family_paths.pdf"
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
            f"{latex_escape(row.quintiles_present)} & {'Yes' if row.contains_Q1_and_Q5 else 'No'} & "
            f"{100 * row.Q5_x_post_conditional_information_share:.2f} \\\\"
        )
    output = TABLES / "r3_appendix_family_support.tex"
    output.write_text(
        "\\begin{center}\n"
        "\\footnotesize\n"
        "\\begin{longtable}{@{}r p{0.25\\textwidth} r r r l c r@{}}\n"
        "\\caption{Broad-family exposure support}\\label{tab:app_family_support}\\\\\n"
        "\\toprule\n"
        "SOC2 & Family & Occs. & Stock (\\%) & Beta range & Quintiles & Q1/Q5 & Q5 info. (\\%) \\\\\n"
        "\\midrule\n"
        "\\endfirsthead\n"
        "\\multicolumn{8}{l}{\\footnotesize\\itshape Table \\thetable{} continued}\\\\\n"
        "\\toprule\n"
        "SOC2 & Family & Occs. & Stock (\\%) & Beta range & Quintiles & Q1/Q5 & Q5 info. (\\%) \\\\\n"
        "\\midrule\n"
        "\\endhead\n"
        "\\midrule\\multicolumn{8}{r}{\\footnotesize Continued on next page}\\\\\n"
        "\\endfoot\n"
        "\\bottomrule\n"
        "\\endlastfoot\n"
        + "\n".join(rows)
        + "\n\\end{longtable}\n"
        "\\tabnote{Stock is each family's share of preperiod employment on the 468-occupation rebuilt support.  Q5 information is the family's share of nuisance-adjusted fitted information for the family-conditioned Q5 target; it is neither a sampling-cluster share nor pre-outcome residual-exposure support.  Beta ranges and memberships use the corrected preperiod treatment contract.  Only Q1/Q5 rows enter the changed-population direct-tail exercise.}\n"
        "\\end{center}\n"
    )
    return output


def build_profile_table() -> pathlib.Path:
    profile = pd.read_csv(FAMILY_RESULTS / "PROFILE_COEFFICIENTS.csv")
    paired = pd.read_csv(FAMILY_RESULTS / "PAIRED_PROFILE_CHANGES.csv")
    baseline = pd.read_csv(REVISION / "rebuilt_baseline/results/BASELINE_DECOMPOSITION.csv")
    baseline = baseline.loc[baseline["row_id"].eq("corrected_113_recomputed_preperiod_treatment")].iloc[0]
    static_pair = pd.read_csv(REVISION / "dynamics/results/STATIC_STRUCTURE_PAIRING.csv")
    static_pair = static_pair.loc[
        static_pair["treatment_contract"].eq("rebuilt_corrected_preperiod_weight")
    ].iloc[0]
    rows = []
    for q in range(2, 6):
        target = f"Q{q}_x_post"
        pooled = profile.loc[(profile["model_id"] == "profile_baseline") & (profile["target"] == target)].iloc[0]
        conditioned = profile.loc[
            (profile["model_id"] == "profile_SOC2_x_calendar_month") & (profile["target"] == target)
        ].iloc[0]
        contrast = f"profile_SOC2_x_calendar_month_minus_profile_baseline__{target}"
        movement = paired.loc[paired["contrast"] == contrast].iloc[0]
        pooled_lo, pooled_hi = pooled.pointwise_ci_lower, pooled.pointwise_ci_upper
        conditioned_lo, conditioned_hi = conditioned.pointwise_ci_lower, conditioned.pointwise_ci_upper
        movement_lo, movement_hi = movement.paired_ci_lower, movement.paired_ci_upper
        if q == 5:
            pooled_lo, pooled_hi = baseline.ci_lower, baseline.ci_upper
            conditioned_lo, conditioned_hi = static_pair.conditioned_ci_lower, static_pair.conditioned_ci_upper
            movement_lo, movement_hi = static_pair.paired_ci_lower, static_pair.paired_ci_upper
        rows.append(
            f"Q{q} & {pooled.coefficient:.4f} & [{pooled_lo:.4f},{pooled_hi:.4f}] & "
            f"[{pooled.simultaneous_ci_lower:.4f},{pooled.simultaneous_ci_upper:.4f}] & "
            f"{conditioned.coefficient:.4f} & [{conditioned_lo:.4f},{conditioned_hi:.4f}] & "
            f"[{conditioned.simultaneous_ci_lower:.4f},{conditioned.simultaneous_ci_upper:.4f}] & "
            f"{movement.coefficient_difference:.4f} [{movement_lo:.4f},{movement_hi:.4f}] \\\\"
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
        "& \\multicolumn{3}{c}{Pooled} & \\multicolumn{3}{c}{SOC2 $\\times$ month} & Paired movement \\\\\n"
        "\\cmidrule(lr){2-4}\\cmidrule(lr){5-7}\n"
        "Group & Coef. & Pointwise 95\\% CI & Simultaneous 95\\% CI & Coef. & Pointwise 95\\% CI & Simultaneous 95\\% CI & Coef. [95\\% CI] \\\\\n"
        "\\midrule\n"
        + "\n".join(rows)
        + "\n\\bottomrule\n"
        "\\end{tabular}}\n"
        "\\tabnote{Q1 is omitted.  Simultaneous intervals use each model's common four-target maximum-$|t|$ critical value.  To prevent the same Q5 target carrying seed-dependent pointwise intervals, the Q5 pointwise and paired cells reproduce the declared single-target canonical intervals; its simultaneous cells remain the four-target family-profile result.  All rows use rebuilt labels and 9,999 common occupation draws within each declared collection.}\n"
        "\\end{table}\n"
    )
    return output


def build_lofo_table() -> pathlib.Path:
    data = pd.read_csv(FAMILY_RESULTS / "LEAVE_ONE_FAMILY_OUT.csv")
    data = data.loc[
        data["parent_model"].eq("profile_SOC2_x_calendar_month")
        & data["target"].eq("Q5_x_post")
    ].copy()
    data["absolute_movement"] = data["movement_from_parent"].abs()
    data = data.sort_values(["absolute_movement", "omitted_SOC2"], ascending=[False, True]).head(8)
    rows = []
    for row in data.itertuples(index=False):
        rows.append(
            f"{int(row.omitted_SOC2)} & {latex_escape(row.omitted_SOC2_name)} & "
            f"{100 * row.omitted_preperiod_stock_share:.2f} & {row.coefficient:.4f} & "
            f"{row.movement_from_parent:.4f} [{row.paired_movement_ci_lower:.4f},{row.paired_movement_ci_upper:.4f}] \\\\"
        )
    output = TABLES / "r3_appendix_lofo.tex"
    output.write_text(
        "\\begin{table}[!htbp]\n"
        "\\centering\n"
        "\\caption{Largest leave-one-family-out movements for the conditioned Q5 target}\\label{tab:app_lofo}\n"
        "\\resizebox{\\textwidth}{!}{%\n"
        "\\begin{tabular}{rlrrr}\n"
        "\\toprule\n"
        "Omitted SOC2 & Family & Preperiod stock (\\%) & Re-estimated coefficient & Movement [95\\% paired CI] \\\\\n"
        "\\midrule\n"
        + "\n".join(rows)
        + "\n\\bottomrule\n"
        "\\end{tabular}}\n"
        "\\tabnote{The parent SOC2-by-calendar-month coefficient is $-0.0217$.  Families are ranked by the absolute coefficient movement, so this is an outcome-informed influence diagnostic rather than a preferred deletion rule.  Quintiles and the continuous centering scale remain fixed; all 22 deletions are available in the machine-readable file.}\n"
        "\\end{table}\n"
    )
    return output


def build_endpoint_table() -> pathlib.Path:
    """Report the declared pre-2025, pre-2026, gap, and full endpoints."""
    data = pd.read_csv(REVISION / "dynamics/results/ENDPOINT_SENSITIVITY.csv")
    data = data.loc[
        data["treatment_contract"].eq("rebuilt_corrected_preperiod_weight")
        & data["status"].eq("PASS")
    ].copy()
    variants = [
        ("through_2024_12", "Through December 2024"),
        ("through_2025_09", "Through September 2025"),
        ("through_2025_12_actual_gap", "Through December 2025 (actual gap)"),
        (
            "full_excluding_September_and_November_2025",
            "Through July 2026, excluding September and November 2025",
        ),
        ("full_through_2026_07", "Through July 2026 (reference)"),
    ]
    structures = [
        ("unconditioned", "Pooled"),
        ("SOC2_x_calendar_month", "SOC2 by calendar month"),
    ]
    expected = {(structure, variant) for structure, _ in structures for variant, _ in variants}
    observed = set(zip(data["structure"], data["variant"]))
    missing = sorted(expected - observed)
    if missing:
        raise RuntimeError(f"mandatory endpoint rows missing: {missing}")

    baseline = pd.read_csv(REVISION / "rebuilt_baseline/results/BASELINE_DECOMPOSITION.csv")
    baseline = baseline.loc[
        baseline["row_id"].eq("corrected_113_recomputed_preperiod_treatment")
    ].iloc[0]
    static_pair = pd.read_csv(REVISION / "dynamics/results/STATIC_STRUCTURE_PAIRING.csv")
    static_pair = static_pair.loc[
        static_pair["treatment_contract"].eq("rebuilt_corrected_preperiod_weight")
    ].iloc[0]

    rows = []
    for structure, structure_label in structures:
        rows.append(f"\\multicolumn{{5}}{{l}}{{\\textit{{{structure_label}}}}} \\\\")
        for variant, variant_label in variants:
            row = data.loc[
                data["structure"].eq(structure) & data["variant"].eq(variant)
            ].iloc[0]
            coefficient = float(row["coefficient"])
            lo, hi = float(row["ci_lower"]), float(row["ci_upper"])
            if variant == "full_through_2026_07":
                if structure == "unconditioned":
                    lo, hi = float(baseline["ci_lower"]), float(baseline["ci_upper"])
                else:
                    lo = float(static_pair["conditioned_ci_lower"])
                    hi = float(static_pair["conditioned_ci_upper"])
                paired = "Reference"
                mde = "---"
            else:
                difference = float(row["difference_vs_reference"])
                paired_lo = float(row["paired_ci_lower_vs_reference"])
                paired_hi = float(row["paired_ci_upper_vs_reference"])
                paired = f"${difference:.4f}\\;[{paired_lo:.4f},{paired_hi:.4f}]$"
                mde = f"{float(row['paired_MDE80_vs_reference']):.4f}"
            rows.append(
                f"{latex_escape(variant_label)} & {int(row['months'])} & "
                f"${coefficient:.4f}\\;[{lo:.4f},{hi:.4f}]$ & {paired} & {mde} \\\\"
            )
        if structure != structures[-1][0]:
            rows.append("\\addlinespace")

    output = TABLES / "r3_appendix_endpoint_sensitivity.tex"
    output.write_text(
        "\\begin{table}[!htbp]\n"
        "\\centering\n"
        "\\caption{Post-outcome exploratory endpoint sensitivity}\\label{tab:app_endpoints}\n"
        "\\scriptsize\n"
        "\\setlength{\\tabcolsep}{3pt}\n"
        "\\resizebox{\\textwidth}{!}{%\n"
        "\\begin{tabular}{lrrrr}\n"
        "\\toprule\n"
        "Endpoint & Months & Coefficient [95\\% CI] & Endpoint $-$ full [paired 95\\% CI] & Paired $\\mathrm{MDE}_{80}$ \\\\\n"
        "\\midrule\n"
        + "\n".join(rows)
        + "\n\\bottomrule\n"
        "\\end{tabular}}\n"
        "\\tabnote{All rows use the rebuilt corrected-preperiod treatment and the same occupation support.  The December 2024 row is the requested pre-2025 endpoint; the December 2025 row retains the actual missing October survey month.  The shutdown-month row excludes September and November 2025 and does not interpolate October.  Nonreference endpoint intervals and paired differences use the common endpoint-grid draws.  To avoid printing a second seed-dependent interval for an identical target, each full-window reference uses its declared canonical single-target interval.  The MDE is the two-sided five-percent, 80-percent normal-theory precision diagnostic, not an economic-equivalence threshold.}\n"
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
        outputs.extend([build_paths(), build_family_paths()])
    if args.only in {"all", "tables"}:
        outputs.extend([
            build_family_support_table(), build_profile_table(), build_lofo_table(),
            build_endpoint_table(),
        ])
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
