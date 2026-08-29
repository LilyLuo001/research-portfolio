#!/usr/bin/env python3
"""Render frozen YAX v1.1 results without re-estimating any model.

This script reads only the immutable corrected-run JSON plus pre-outcome
measurement facts already frozen in the repository.  It produces publication-
ready CSV/Markdown tables and descriptive figures; it does not read microdata,
change a specification, or calculate a new regression.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS = ROOT / "yax/analysis/outcomes/frozen_v11_corrected_run/FROZEN_RESULTS.json"
DEFAULT_OUTPUT = ROOT / "yax/analysis/outcomes/frozen_v11_corrected_run/reporting"
POWER_RESULTS = ROOT / "yax/power/JOINT_POWER_AGGREGATE_v3.json"


def write_table(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(".csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "| " + " | ".join(columns) + " |",
        "|" + "|".join(["---"] * len(columns)) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(c, "")) for c in columns) + " |")
    path.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def target(model: dict, label: str | None = None) -> dict:
    return model["coefficients"][label or model["target_label"]]


def estimate_row(label: str, model: dict, coefficient: str | None = None, notes: str = "") -> dict:
    value = target(model, coefficient)
    return {
        "specification": label,
        "coefficient_log_points": f"{value['coefficient']:.5f}",
        "bootstrap_se": f"{value['bootstrap_se']:.5f}",
        "ci_95": f"[{value['ci_lower']:.5f}, {value['ci_upper']:.5f}]",
        "p_value": f"{value['bootstrap_p_value']:.3f}",
        "occupations": model["occupations"],
        "notes": notes,
    }


def render_tables(data: dict, power: dict, out: Path) -> None:
    measurement_rows = [
        {"AI measure": "AIOE (administrative equal)", "R2_with_telework": "0.5792", "effective_N_residual_vs_telework": "52.6", "partial_variance_given_Webb_66m": "0.949", "effective_N_given_Webb_66m": "72.2"},
        {"AI measure": "Eloundou alpha", "R2_with_telework": "0.0909", "effective_N_residual_vs_telework": "27.6", "partial_variance_given_Webb_66m": "0.983", "effective_N_given_Webb_66m": "17.4"},
        {"AI measure": "Eloundou beta", "R2_with_telework": "0.4208", "effective_N_residual_vs_telework": "72.2", "partial_variance_given_Webb_66m": "0.997", "effective_N_given_Webb_66m": "53.3"},
        {"AI measure": "Eloundou gamma", "R2_with_telework": "0.4537", "effective_N_residual_vs_telework": "59.3", "partial_variance_given_Webb_66m": "0.982", "effective_N_given_Webb_66m": "84.5"},
    ]
    write_table(
        out / "table1_construct_and_identifying_support",
        measurement_rows,
        ["AI measure", "R2_with_telework", "effective_N_residual_vs_telework", "partial_variance_given_Webb_66m", "effective_N_given_Webb_66m"],
    )

    identifying_rows = []
    for scenario in power["scenarios"]:
        support = scenario["identifying_support"]
        contributors = support["largest_residual_variance_contributors"][:5]
        identifying_rows.append({
            "AI measure": scenario["ai_measure"].replace("dv_rating_", "Eloundou "),
            "computerization control": scenario["computerization_measure"],
            "partial variance": f"{support['weighted_partial_variance_ai_given_computerization']:.3f}",
            "effective occupations": f"{support['effective_occupations_identifying_beta_ai']:.1f}",
            "top-five share": f"{support['top_five_influence_share']:.3f}",
            "five largest contributors": "; ".join(f"{x['occupation']} ({100*x['residual_variance_share']:.1f}%)" for x in contributors),
        })
    write_table(
        out / "table2_identifying_variation",
        identifying_rows,
        ["AI measure", "computerization control", "partial variance", "effective occupations", "top-five share", "five largest contributors"],
    )

    exposure_names = {"dv_rating_beta": "Eloundou beta", "dv_rating_alpha": "Eloundou alpha"}
    control_names = {"webb_pct_software": "Webb software-patent exposure", "onet_computers_importance": "O*NET computer-use importance"}
    headline_rows = []
    for key, model in data["headline"].items():
        exposure, rule, control, _ = key.split("__")
        headline_rows.append(estimate_row(f"{exposure_names[exposure]} / {rule} / {control_names[control]}", model))
    write_table(
        out / "table4a_headline_q5_q1",
        headline_rows,
        ["specification", "coefficient_log_points", "bootstrap_se", "ci_95", "p_value", "occupations", "notes"],
    )

    event_rows = data["event_study"]["rows"]
    pre = [r for r in event_rows if r["placebo_indicator"] and r["event_month"] != data["event_study"]["reference_month"]]
    post = [r for r in event_rows if not r["placebo_indicator"] and r["event_month"] != data["event_study"]["reference_month"]]
    significant_pre = [r for r in pre if r["ci_lower"] > 0 or r["ci_upper"] < 0]
    significant_post = [r for r in post if r["ci_lower"] > 0 or r["ci_upper"] < 0]
    placebo = data["placebo_2017_2019"]
    ai = placebo["ai"]
    dynamics_rows = [
        {"diagnostic": "Frozen 2017-2019 placebo", "estimate_or_count": f"{ai['coefficient']:.5f}", "ci_or_detail": f"[{ai['ci_lower']:.5f}, {ai['ci_upper']:.5f}]", "p_value": f"{ai['bootstrap_p_value']:.3f}"},
        {"diagnostic": "Pre-event monthly coefficients excluding zero", "estimate_or_count": f"{len(significant_pre)} / {len(pre)}", "ci_or_detail": "reference month 2022-10", "p_value": ""},
        {"diagnostic": "Post/reference-era coefficients excluding zero", "estimate_or_count": f"{len(significant_post)} / {len(post)}", "ci_or_detail": ", ".join(r["event_month"] for r in significant_post), "p_value": ""},
    ]
    write_table(out / "table6_dynamics_and_placebo", dynamics_rows, ["diagnostic", "estimate_or_count", "ci_or_detail", "p_value"])

    alternative_labels = {
        "aioe_admin_equal__RuleA__webb__q5_q1": "AIOE administrative equal / Webb",
        "aioe_ability_direct__RuleA__webb__q5_q1": "AIOE ability-direct / Webb",
        "aioe_oews2018_source_weighted__RuleA__webb__q5_q1": "AIOE OEWS source-weighted / Webb",
        "dv_rating_alpha__RuleA__webb__q5_q1": "Eloundou alpha / Webb",
        "dv_rating_beta__RuleA__webb__q5_q1": "Eloundou beta / Webb",
        "dv_rating_gamma__RuleA__webb__q5_q1": "Eloundou gamma / Webb",
        "dv_rating_beta__RuleA__webb_pct_software__q5_q1": "Eloundou beta / Webb",
        "dv_rating_beta__RuleA__onet_computers_importance__q5_q1": "Eloundou beta / O*NET importance",
        "dv_rating_beta__RuleA__onet_computers_level__q5_q1": "Eloundou beta / O*NET level",
        "dv_rating_beta__RuleA__rti_autor_dorn__q5_q1": "Eloundou beta / Autor-Dorn RTI",
        "dv_rating_beta__RuleA__frey_osborne_probability__q5_q1": "Eloundou beta / Frey-Osborne",
    }
    alternative_rows = [estimate_row(alternative_labels[k], m) for k, m in data["alternative_exposures_and_controls"].items()]
    pair = data["paired_test_c"]
    alternative_rows.append({
        "specification": "Paired Test C: beta minus alpha (common Rule-A/Webb support)",
        "coefficient_log_points": f"{pair['delta']:.5f}",
        "bootstrap_se": f"{pair['paired_se_delta']:.5f}",
        "ci_95": f"[{pair['paired_ci_lower']:.5f}, {pair['paired_ci_upper']:.5f}]",
        "p_value": f"{pair['paired_p_value']:.3f}",
        "occupations": pair["occupations"],
        "notes": "common draws preserve covariance; no detected difference is not equivalence",
    })
    write_table(
        out / "table4_same_design_different_x",
        alternative_rows,
        ["specification", "coefficient_log_points", "bootstrap_se", "ci_95", "p_value", "occupations", "notes"],
    )

    crosswalk_rows = []
    for number, model in data["crosswalk_decomposition"].items():
        row = estimate_row(f"{number}. {model['label']}", model)
        crosswalk_rows.append(row)
    write_table(
        out / "table3_mapping_and_common_support",
        crosswalk_rows,
        ["specification", "coefficient_log_points", "bootstrap_se", "ci_95", "p_value", "occupations", "notes"],
    )

    remote_labels = {
        "dv_rating_beta__ai_only": "Beta: AI only",
        "dv_rating_beta__ai_remote_joint": "Beta: AI + remote (AI coefficient)",
        "dv_rating_beta__ai_comp_remote_joint": "Beta: AI + Webb + remote (AI coefficient)",
        "dv_rating_alpha__ai_only": "Alpha: AI only",
        "dv_rating_alpha__ai_remote_joint": "Alpha: AI + remote (AI coefficient)",
        "dv_rating_alpha__ai_comp_remote_joint": "Alpha: AI + Webb + remote (AI coefficient)",
        "remote_only": "Remote only",
    }
    remote_rows = []
    for key, model in data["remote"].items():
        remote_rows.append(estimate_row(remote_labels[key], model))
        if key in {"dv_rating_beta__ai_remote_joint", "dv_rating_alpha__ai_remote_joint", "dv_rating_beta__ai_comp_remote_joint", "dv_rating_alpha__ai_comp_remote_joint"}:
            if "remote_z_x_post" in model["coefficients"]:
                remote_rows.append(estimate_row(remote_labels[key] + " — remote coefficient", model, "remote_z_x_post"))
            if "computerization_z_x_post" in model["coefficients"]:
                remote_rows.append(estimate_row(remote_labels[key] + " — computerization coefficient", model, "computerization_z_x_post"))
    ext = data["post_2025_extension"]
    remote_rows.extend([
        {"specification": "Beta early window, 2023-01 to 2024-12", "coefficient_log_points": f"{ext['ai_early']:.5f}", "bootstrap_se": "", "ci_95": "", "p_value": "", "occupations": ext["occupations"], "notes": "per-SD"},
        {"specification": "Beta extension, 2025-01 to 2026-07", "coefficient_log_points": f"{ext['ai_extension']:.5f}", "bootstrap_se": "", "ci_95": "", "p_value": "", "occupations": ext["occupations"], "notes": "per-SD"},
        {"specification": "Extension minus early", "coefficient_log_points": f"{ext['extension_minus_early']:.5f}", "bootstrap_se": "", "ci_95": "", "p_value": f"{ext['wald_bootstrap_p']:.3f}", "occupations": ext["occupations"], "notes": "frozen joint Wald test"},
    ])
    write_table(
        out / "table5_ai_remote_and_post2025_extension",
        remote_rows,
        ["specification", "coefficient_log_points", "bootstrap_se", "ci_95", "p_value", "occupations", "notes"],
    )


def render_figures(data: dict, out: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    rows = data["event_study"]["rows"]
    dates = [datetime.strptime(r["event_month"], "%Y-%m") for r in rows]
    estimates = [r["coefficient"] for r in rows]
    lower = [r["ci_lower"] for r in rows]
    upper = [r["ci_upper"] for r in rows]
    fig, ax = plt.subplots(figsize=(11.5, 5.8))
    ax.fill_between(dates, lower, upper, color="#4C78A8", alpha=0.16, linewidth=0)
    ax.plot(dates, estimates, color="#1F4E79", linewidth=1.6, marker="o", markersize=2.2)
    ax.axhline(0, color="#333333", linewidth=0.9)
    ax.axvline(datetime(2022, 10, 1), color="#777777", linestyle="--", linewidth=1.0, label="Reference: Oct. 2022")
    ax.axvline(datetime(2023, 1, 1), color="#B14A3B", linestyle=":", linewidth=1.2, label="Frozen post starts: Jan. 2023")
    ax.set_title("Young-relative employment gradient by Eloundou beta exposure")
    ax.set_ylabel("Exposure interaction (log points per SD)")
    ax.set_xlabel("")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.legend(frameon=False, loc="lower left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out / "figure1_event_study.png", dpi=220)
    plt.close(fig)

    labels = ["AIOE", "Alpha", "Beta", "Gamma"]
    r2 = [0.5792, 0.0909, 0.4208, 0.4537]
    eff = [52.6, 27.6, 72.2, 59.3]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.5))
    axes[0].bar(labels, r2, color="#4C78A8")
    axes[0].set_ylabel("Employment-weighted R²")
    axes[0].set_title("Overlap with teleworkability")
    axes[0].set_ylim(0, 0.65)
    axes[1].bar(labels, eff, color="#F58518")
    axes[1].set_ylabel("Effective occupations")
    axes[1].set_title("Residual identifying support")
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("AI exposure definitions load on different occupation variation")
    fig.tight_layout()
    fig.savefig(out / "figure2_measurement_divergence.png", dpi=220)
    plt.close(fig)


def hash_manifest(out: Path, results_path: Path) -> None:
    files = [results_path] + sorted(p for p in out.iterdir() if p.is_file() and p.name != "ARTIFACT_HASHES.sha256")
    lines = []
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            label = path.relative_to(ROOT)
        except ValueError:
            label = path
        lines.append(f"{digest}  {label}")
    (out / "ARTIFACT_HASHES.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    data = json.loads(args.results.read_text(encoding="utf-8"))
    power = json.loads(POWER_RESULTS.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    render_tables(data, power, args.output)
    render_figures(data, args.output)
    hash_manifest(args.output, args.results)
    print(args.output)


if __name__ == "__main__":
    main()
