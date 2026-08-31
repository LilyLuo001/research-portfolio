#!/usr/bin/env python3
"""Build the YAX V3 presentation package from stored confirmatory and supplementary artifacts.

This script performs presentation-only transformations. It estimates no model,
reads no protected microdata, and never writes to the immutable v1.1 archive.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "yax" / "manuscript" / "v3"
TABLES = OUT / "tables"
FIGURES = OUT / "figures"
V1 = ROOT / "yax" / "manuscript" / "v1"
SUPP = ROOT / "yax" / "analysis" / "postoutcome_v3_supplementary"
FROZEN = ROOT / "yax" / "analysis" / "outcomes" / "frozen_v11_corrected_run"

CONFIRMATORY = "CONFIRMATORY — FROZEN YAX v1.1"
SUPPLEMENTARY = "POST-OUTCOME SUPPLEMENTARY — NOT PART OF CONFIRMATORY YAX v1.1"

AI_LABEL = {
    "aioe_admin_equal": "AIOE, administrative equal",
    "aioe_ability_direct": "AIOE, ability direct",
    "aioe_oews2018_source_weighted": "AIOE, OEWS source weighted",
    "dv_rating_alpha": "Eloundou alpha",
    "dv_rating_beta": "Eloundou beta",
    "dv_rating_gamma": "Eloundou broad",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def markdown_table(df: pd.DataFrame) -> str:
    def esc(value: object) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(esc, cols)) + " |"]
    lines.append("|" + "|".join(["---"] * len(cols)) + "|")
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(esc(row[col]) for col in cols) + " |")
    return "\n".join(lines) + "\n"


def write_table(stem: str, df: pd.DataFrame, status: str, note: str) -> None:
    csv = df.copy()
    csv.insert(0, "analysis_status", status)
    csv.to_csv(TABLES / f"{stem}.csv", index=False)
    body = f"**Analysis status: {status}.**\n\n" + markdown_table(df)
    body += "\n**Note.** " + note.strip() + "\n"
    (TABLES / f"{stem}.md").write_text(body, encoding="utf-8")


def copy_confirmatory_tables() -> None:
    for source in sorted((V1 / "tables").glob("*")):
        if source.suffix not in {".csv", ".md"}:
            continue
        target = TABLES / source.name
        if source.suffix == ".csv":
            df = pd.read_csv(source)
            if "analysis_status" not in df.columns:
                df.insert(0, "analysis_status", CONFIRMATORY)
            df.to_csv(target, index=False)
        else:
            text = source.read_text(encoding="utf-8")
            text = text.replace("occupation-cluster wild bootstrap inference", "one-step occupation-cluster wild-score inference")
            if source.stem.startswith(("table4_", "table5", "table6")):
                text += "\nReported intervals condition on realized CPS weighted employment-stock cells and do not separately propagate first-stage survey-sampling or calibration-weight uncertainty.\n"
            target.write_text(f"**Analysis status: {CONFIRMATORY}.**\n\n{text}", encoding="utf-8")


def build_supplementary_tables() -> None:
    bridge = pd.read_csv(SUPP / "CONTINUOUS_VS_HEADLINE_SUPPORT.csv")
    out = pd.DataFrame({
        "Architecture": bridge["specification"].str.replace("dv_rating_", "", regex=False)
            .str.replace("__RuleA__", " / ", regex=False)
            .str.replace("__q5_q1", "", regex=False)
            .str.replace("webb_pct_software", "Webb software patents", regex=False)
            .str.replace("onet_computers_importance", "O*NET computer use", regex=False),
        "Continuous effective support": bridge["continuous_effective_occupations"].map(lambda x: f"{x:.1f}"),
        "Headline effective information": bridge["headline_effective_occupations"].map(lambda x: f"{x:.1f}"),
        "Continuous top-five share": bridge["continuous_top_five_share"].map(lambda x: f"{100*x:.1f}%"),
        "Headline top-five share": bridge["headline_top_five_share"].map(lambda x: f"{100*x:.1f}%"),
        "Share-rank correlation": bridge["occupation_share_spearman"].map(lambda x: f"{x:.3f}"),
        "Top-five overlap": bridge["top_five_intersection"].map(lambda x: f"{int(x)}/5"),
    })
    write_table(
        "table3c_continuous_vs_headline_support", out, SUPPLEMENTARY,
        "Continuous support is the pre-outcome residual-treatment diagnostic. Headline support is the exact fitted conditional-information decomposition for the Q5-Q1 coefficient. The latter was requested and executed after outcome access."
    )

    split = pd.read_csv(SUPP / "TEST_A_VALIDATOR_SPLIT_SUMMARY.csv")
    split["AI measure"] = split["ai_measure"].map(AI_LABEL)
    split["Validator group"] = split["validator_group"].map({
        "construction_linked_onet": "Construction-linked O*NET",
        "more_external": "More external",
    })
    out = pd.DataFrame({
        "AI measure": split["AI measure"],
        "Validator group": split["Validator group"],
        "Occupations": split["occupations"].astype(int),
        "Weighted R-squared": split["weighted_r_squared"].map(lambda x: f"{x:.3f}"),
        "Residual SD": split["residual_sd"].map(lambda x: f"{x:.3f}"),
        "Effective residual support": split["effective_residual_support"].map(lambda x: f"{x:.1f}"),
        "Top-five residual share": split["top_five_residual_variance_share"].map(lambda x: f"{100*x:.1f}%"),
    })
    write_table(
        "table2c_validator_source_split", out, SUPPLEMENTARY,
        "The sample is fixed at 348 occupations. The construction-linked group contains four O*NET-derived characteristics; the more-external group contains RTI, wages, teleworkability, and STEM share."
    )

    remote = json.loads((SUPP / "REMOTE_INTERACTION_RESULT.json").read_text())
    rows = []
    for key, label in [
        ("AI_z_x_post", "AI exposure"),
        ("Webb_z_x_post", "Webb software exposure"),
        ("Remote_z_x_post", "Remotability"),
        ("AI_z_x_Remote_z_x_post", "AI exposure × remotability"),
    ]:
        item = remote["coefficients"][key]
        rows.append({
            "Coefficient": label,
            "Estimate": f"{item['coefficient']:.5f}",
            "One-step wild-score SE": f"{item['bootstrap_se']:.5f}",
            "95% CI": f"[{item['ci_lower']:.5f}, {item['ci_upper']:.5f}]",
            "p-value": f"{item['bootstrap_p_value']:.3f}",
        })
    write_table(
        "table6b_remote_interaction", pd.DataFrame(rows), SUPPLEMENTARY,
        "One predeclared continuous Rule-A beta/Webb/remotability interaction model; 408 occupations, 108 months, and 999 common occupation-cluster Rademacher draws. No detected interaction is not evidence of homogeneous effects."
    )

    pre = json.loads((SUPP / "JOINT_PRETREND_RESULT.json").read_text())
    out = pd.DataFrame([{
        "Pre-event coefficients": pre["tested_coefficients"],
        "Maximum absolute t": f"{pre['observed_max_abs_t']:.3f}",
        "Simultaneous 95% critical value": f"{pre['simultaneous_95_critical']:.3f}",
        "Bootstrap p-value": f"{pre['bootstrap_p_value']:.3f}",
        "Simultaneous bands excluding zero": pre["simultaneous_intervals_excluding_zero"],
    }])
    write_table(
        "table7_joint_pretrend", out, SUPPLEMENTARY,
        "Maximum-absolute-t joint test of all 65 pre-event coefficients using 999 common occupation-cluster multipliers. Failure to reject does not establish parallel trends."
    )


def build_figure2() -> None:
    pre = pd.read_csv(ROOT / "yax" / "analysis" / "audit" / "TEST_B_IDENTIFYING_VARIATION_FULL.csv")
    bridge = pd.read_csv(SUPP / "CONTINUOUS_VS_HEADLINE_SUPPORT.csv")
    ai_order = ["aioe_admin_equal", "aioe_ability_direct", "aioe_oews2018_source_weighted", "dv_rating_alpha", "dv_rating_beta", "dv_rating_gamma"]
    comp_order = ["webb_pct_software", "onet_computers_importance", "onet_computers_level", "rti_autor_dorn", "frey_osborne_probability"]
    grid = pre.pivot(index="ai_measure", columns="computerization_measure", values="effective_identifying_occupations").loc[ai_order, comp_order]
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), constrained_layout=True)
    im = axes[0].imshow(grid.to_numpy(), aspect="auto", cmap="viridis")
    axes[0].set_title("A. Confirmatory design: continuous residual-treatment support", weight="bold")
    axes[0].set_xticks(range(5), ["Webb", "O*NET imp.", "O*NET level", "RTI", "Frey-Osborne"], rotation=22, ha="right")
    axes[0].set_yticks(range(6), [AI_LABEL[x] for x in ai_order])
    for r in range(6):
        for c in range(5):
            axes[0].text(c, r, f"{grid.iloc[r,c]:.1f}", ha="center", va="center", color="white" if grid.iloc[r,c] < 45 else "black", fontsize=8)
    fig.colorbar(im, ax=axes[0], shrink=.75, label="Effective occupations")

    labels = ["beta / Webb", "beta / O*NET", "alpha / Webb", "alpha / O*NET"]
    x = np.arange(4)
    width = .36
    axes[1].bar(x-width/2, bridge["continuous_effective_occupations"], width, label="Continuous diagnostic", color="#4C78A8")
    axes[1].bar(x+width/2, bridge["headline_effective_occupations"], width, label="Headline information", color="#F58518")
    axes[1].set_xticks(x, labels, rotation=20, ha="right")
    axes[1].set_ylabel("Effective occupations")
    axes[1].set_title("B. Post-outcome supplementary: exact headline bridge", weight="bold")
    axes[1].axhline(0, color="black", lw=.6)
    axes[1].legend(frameon=False)
    fig.savefig(FIGURES / "figure2_support_bridge.png", dpi=300, bbox_inches="tight")
    fig.savefig(FIGURES / "figure2_support_bridge.pdf", bbox_inches="tight")
    plt.close(fig)


def build_figure3() -> None:
    frozen = json.loads((FROZEN / "FROZEN_RESULTS.json").read_text())
    event = pd.DataFrame(frozen["event_study"]["rows"])
    event["date"] = pd.to_datetime(event["event_month"])
    pre = pd.read_csv(SUPP / "JOINT_PRETREND_SIMULTANEOUS_BANDS.csv")
    pre["date"] = pd.to_datetime(pre["event_month"])
    fig, axes = plt.subplots(2, 1, figsize=(14, 9), sharex=False, constrained_layout=True)
    ax = axes[0]
    ax.fill_between(event["date"], event["ci_lower"], event["ci_upper"], color="#4C78A8", alpha=.18)
    ax.plot(event["date"], event["coefficient"], color="#1F4E79", lw=1.1)
    ax.axhline(0, color="black", lw=.7)
    ax.axvline(pd.Timestamp("2023-01-01"), color="#B24C3D", ls="--", lw=1)
    ax.set_title("A. Confirmatory event study: pointwise 95% intervals", weight="bold")
    ax.set_ylabel("Log coefficient per SD")
    ax = axes[1]
    ax.fill_between(pre["date"], pre["simultaneous_ci_lower"], pre["simultaneous_ci_upper"], color="#F58518", alpha=.22)
    ax.plot(pre["date"], pre["coefficient"], color="#B04A00", lw=1.1)
    ax.axhline(0, color="black", lw=.7)
    ax.set_title("B. Post-outcome supplementary: simultaneous 95% pretrend bands", weight="bold")
    ax.set_ylabel("Log coefficient per SD")
    ax.set_xlabel("Month")
    fig.savefig(FIGURES / "figure3_dynamics_and_pretrends.png", dpi=300, bbox_inches="tight")
    fig.savefig(FIGURES / "figure3_dynamics_and_pretrends.pdf", bbox_inches="tight")
    plt.close(fig)


def build_clean() -> None:
    source = OUT / "YAX_MANUSCRIPT_v3_AUDITABLE.md"
    text = source.read_text(encoding="utf-8")
    text = re.sub(r"[ \t]*<!--\s*prov:[^>]+-->", "", text)
    (OUT / "YAX_MANUSCRIPT_v3_CLEAN.md").write_text(text, encoding="utf-8")


def build_receipt() -> None:
    receipt_path = OUT / "MANUSCRIPT_RECEIPT_v3.json"
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path != receipt_path)
    receipt = {
        "record": "YAX manuscript revision round 3",
        "presentation_only_builder": True,
        "confirmatory_result_set_altered": False,
        "supplementary_analyses_in_confirmatory_ledger": False,
        "frozen_authority": {
            "design_tag": "v1.1-design-freeze",
            "result_tag": "v1.1-confirmatory-results",
            "result_commit": "b16109482c3bf5ca176f6f08976e120b04769945",
        },
        "canonical_result_json_sha256": sha256(FROZEN / "FROZEN_RESULTS.json"),
        "canonical_result_ledger_sha256": sha256(FROZEN / "RESULT_LEDGER.jsonl"),
        "clean_word_count": len((OUT / "YAX_MANUSCRIPT_v3_CLEAN.md").read_text().split()),
        "files": [{"path": str(path.relative_to(ROOT)), "sha256": sha256(path)} for path in files],
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    copy_confirmatory_tables()
    shutil.copy2(V1 / "figures" / "figure1_measurement_genealogy.png", FIGURES / "figure1_measurement_genealogy.png")
    shutil.copy2(V1 / "figures" / "figure1_measurement_genealogy.pdf", FIGURES / "figure1_measurement_genealogy.pdf")
    build_supplementary_tables()
    build_figure2()
    build_figure3()
    build_clean()
    build_receipt()


if __name__ == "__main__":
    main()
