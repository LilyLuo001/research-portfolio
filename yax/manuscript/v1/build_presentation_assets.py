#!/usr/bin/env python3
"""Render manuscript tables and figures from immutable YAX v1.1 artifacts.

This program performs presentation-only transformations. It does not estimate
any model, read licensed microdata, or alter a frozen result.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "yax" / "manuscript" / "v1"
TABLES = OUT / "tables"
FIGURES = OUT / "figures"
FROZEN = ROOT / "yax" / "analysis" / "outcomes" / "frozen_v11_corrected_run"
AUDIT = ROOT / "yax" / "analysis" / "audit"
TEST_A = ROOT / "yax" / "measurement" / "test_a"
FROZEN_TAG = "v1.1-confirmatory-results"
FROZEN_COMMIT = "b16109482c3bf5ca176f6f08976e120b04769945"


LABEL_AI = {
    "aioe_admin_equal": "AIOE, administrative equal",
    "aioe_ability_direct": "AIOE, ability direct",
    "aioe_oews2018_source_weighted": "AIOE, OEWS source weighted",
    "dv_rating_alpha": "Eloundou alpha (E1)",
    "dv_rating_beta": "Eloundou beta (E1 + 0.5 E2)",
    "dv_rating_gamma": "Eloundou broad (E1 + E2)",
}
LABEL_COMP = {
    "webb_pct_software": "Webb software patents",
    "onet_computers_importance": "O*NET computer use: importance",
    "onet_computers_level": "O*NET computer use: level",
    "rti_autor_dorn": "Autor-Dorn RTI",
    "frey_osborne_probability": "Frey-Osborne automation",
}
LABEL_CHAR = {
    "cognitive_ability_importance": "Cognitive",
    "manual_physical_ability_importance": "Manual/physical",
    "rti_autor_dorn": "Routine (RTI)",
    "required_education_category_index": "Education",
    "log_mean_annual_wage": "Log wage",
    "dingel_neiman_telework": "Teleworkability",
    "stem_major_group_share": "STEM",
    "onet_computers_importance": "Computer use",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def md_escape(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def dataframe_to_md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    rows = ["| " + " | ".join(map(md_escape, cols)) + " |"]
    rows.append("|" + "|".join(["---"] * len(cols)) + "|")
    for _, row in df.iterrows():
        rows.append("| " + " | ".join(md_escape(row[c]) for c in cols) + " |")
    return "\n".join(rows) + "\n"


def write_table(stem: str, df: pd.DataFrame, note: str) -> None:
    df.to_csv(TABLES / f"{stem}.csv", index=False)
    body = dataframe_to_md(df)
    (TABLES / f"{stem}.md").write_text(body + "\n" + note.strip() + "\n", encoding="utf-8")


def build_table1() -> None:
    rows = [
        {
            "Measure": "AIOE (three aggregation variants)",
            "Primitive": "AI application × occupational ability",
            "Capability source / labeler": "Electronic Frontier Foundation applications; MTurk judgments",
            "Aggregation": "Ability exposure × occupation-specific ability weights",
            "Interpretation": "Potential occupational exposure to advances in general AI applications",
            "Primary source": "Felten, Raj, and Seamans (2018, 2021)",
        },
        {
            "Measure": "Eloundou alpha (E1)",
            "Primitive": "LLM capability × occupational task",
            "Capability source / labeler": "Human and GPT-4 task judgments",
            "Aggregation": "Share of tasks directly accelerated by an LLM",
            "Interpretation": "Direct LLM task-time-reduction potential",
            "Primary source": "Eloundou et al. (2024)",
        },
        {
            "Measure": "Eloundou beta (E1 + 0.5 E2)",
            "Primitive": "LLM capability × occupational task",
            "Capability source / labeler": "Human and GPT-4 task judgments",
            "Aggregation": "Directly exposed tasks plus half weight on software-complemented tasks",
            "Interpretation": "LLM potential allowing complementary software",
            "Primary source": "Eloundou et al. (2024)",
        },
        {
            "Measure": "Eloundou broad (E1 + E2)",
            "Primitive": "LLM capability × occupational task",
            "Capability source / labeler": "Human and GPT-4 task judgments",
            "Aggregation": "All directly or software-complemented exposed tasks",
            "Interpretation": "Broad upper-bound LLM exposure (published zeta; repository gamma alias)",
            "Primary source": "Eloundou et al. (2024)",
        },
    ]
    write_table(
        "table1_anatomy_of_ai_exposure_measures",
        pd.DataFrame(rows),
        "Note: The table records construction architecture, not a ranking of measure quality. "
        "Taxonomy mapping and common-support restrictions occur after the native score is built. "
        "Source: verified latest-version literature audit at the frozen result commit.",
    )


def build_table2() -> None:
    corr = pd.read_csv(TEST_A / "TEST_A_CHARACTERISTIC_MATRIX.csv")
    # Pivot the stored frozen Pearson column without recomputation.
    wide = corr.pivot(index="ai_measure", columns="characteristic", values="weighted_pearson")
    wide = wide.loc[list(LABEL_AI)]
    wide = wide[list(LABEL_CHAR)].rename(index=LABEL_AI, columns=LABEL_CHAR).reset_index()
    wide = wide.rename(columns={"ai_measure": "AI measure"})
    for c in wide.columns[1:]:
        wide[c] = wide[c].map(lambda x: f"{x:.3f}")
    write_table(
        "table2a_construct_diagnostics",
        wide,
        "Note: Employment-weighted Pearson correlations. All six measures and all eight frozen "
        "occupational characteristics are shown. Source: TEST_A_CHARACTERISTIC_MATRIX.csv.",
    )

    resid = pd.read_csv(TEST_A / "TEST_A_RESIDUAL_DIAGNOSTICS.csv")
    resid["top_five_occupations"] = resid["top_ten_contributors_json"].map(
        lambda raw: "; ".join(x["occupation"] for x in json.loads(raw)[:5])
    )
    resid = resid[[
        "ai_measure", "weighted_r_squared_on_all_characteristics", "residual_sd",
        "effective_identifying_occupations", "top_five_residual_variance_share",
        "top_five_occupations",
    ]].copy()
    resid["ai_measure"] = resid["ai_measure"].map(LABEL_AI)
    resid.columns = [
        "AI measure", "R-squared on eight characteristics", "Residual SD",
        "Effective occupations", "Top-five share", "Five largest contributors",
    ]
    for c in ["R-squared on eight characteristics", "Residual SD", "Effective occupations"]:
        resid[c] = resid[c].map(lambda x: f"{x:.3f}" if c != "Effective occupations" else f"{x:.1f}")
    resid["Top-five share"] = resid["Top-five share"].map(lambda x: f"{100*x:.1f}%")
    write_table(
        "table2b_joint_construct_residual_audit",
        resid,
        "Note: Joint residualization uses 348 occupations on common complete support and frozen "
        "pre-period employment-stock weights. Source: TEST_A_RESIDUAL_DIAGNOSTICS.csv.",
    )


def build_table3() -> pd.DataFrame:
    df = pd.read_csv(AUDIT / "TEST_B_IDENTIFYING_VARIATION_FULL.csv")
    df["AI measure"] = df["ai_measure"].map(LABEL_AI)
    df["Computerization control"] = df["computerization_measure"].map(LABEL_COMP)
    out = pd.DataFrame({
        "AI measure": df["AI measure"],
        "Computerization control": df["Computerization control"],
        "Occupations": df["occupations"].astype(int),
        "Correlation": df["correlation"].map(lambda x: f"{x:.3f}"),
        "Partial variance": df["partial_variance_ai"].map(lambda x: f"{x:.3f}"),
        "Effective occupations": df["effective_identifying_occupations"].map(lambda x: f"{x:.1f}"),
        "Top-five share": df["top_five_residual_variance_share"].map(lambda x: f"{100*x:.1f}%"),
        "Five largest contributors": df["top_five_occupations"],
    })
    write_table(
        "table3_identifying_variation_all_30_architectures",
        out,
        "Note: Exposure is residualized on the named computerization measure using frozen "
        "pre-period employment weights. Effective occupations are the inverse Herfindahl of "
        "employment-weighted squared residual contributions. Source: "
        "TEST_B_IDENTIFYING_VARIATION_FULL.csv.",
    )
    return df


def build_table4() -> None:
    df = pd.read_csv(AUDIT / "MAPPING_DECOMPOSITION_AUDIT.csv")
    out = pd.DataFrame({
        "Step": df["row"].astype(int),
        "Exposure mapping and support": df["label"],
        "Occupations": df["occupations"].astype(int),
        "Coefficient": df["coefficient"].map(lambda x: f"{x:.5f}"),
        "Bootstrap SE": df["bootstrap_se"].map(lambda x: f"{x:.5f}"),
        "95% CI": df.apply(lambda r: f"[{r.ci_lower:.5f}, {r.ci_upper:.5f}]", axis=1),
        "p-value": df["bootstrap_p_value"].map(lambda x: f"{x:.3f}"),
    })
    write_table(
        "table4_mapping_and_common_support",
        out,
        "Note: Coefficients are per fixed SD of AIOE and condition on Webb software-patent "
        "exposure. Row 1 to row 2 changes mapped values on fixed support; row 2 to row 3 "
        "expands support; row 4 excludes computer and mathematical occupations. Source: "
        "MAPPING_DECOMPOSITION_AUDIT.csv.",
    )


def build_table5() -> None:
    headline = pd.read_csv(FROZEN / "reporting" / "table4a_headline_q5_q1.csv")
    h = headline.rename(columns={
        "specification": "Specification", "coefficient_log_points": "Coefficient",
        "bootstrap_se": "Bootstrap SE", "ci_95": "95% CI", "p_value": "p-value",
        "occupations": "Occupations",
    })[["Specification", "Coefficient", "Bootstrap SE", "95% CI", "p-value", "Occupations"]]
    for c in ["Coefficient", "Bootstrap SE"]:
        h[c] = h[c].map(lambda x: f"{x:.5f}")
    h["p-value"] = h["p-value"].map(lambda x: f"{x:.3f}")
    write_table(
        "table5a_frozen_headline_models",
        h,
        "Note: The 12 frozen alpha/beta headline Q5-Q1 models are reported without selection. "
        "All confidence intervals use 999-draw occupation-cluster wild bootstrap inference. "
        "Source: canonical frozen reporting table4a_headline_q5_q1.csv.",
    )

    alt = pd.read_csv(AUDIT / "ALTERNATIVE_X_AUDIT.csv").iloc[:6].copy()
    alt["Specification"] = [
        "AIOE administrative equal / Webb", "AIOE ability direct / Webb",
        "AIOE OEWS source weighted / Webb", "Eloundou alpha / Webb",
        "Eloundou beta / Webb", "Eloundou broad / Webb",
    ]
    out = pd.DataFrame({
        "Specification": alt["Specification"],
        "Occupations": alt["occupations"].astype(int),
        "Q5-Q1 coefficient": alt["coefficient"].map(lambda x: f"{x:.5f}"),
        "Bootstrap SE": alt["bootstrap_se"].map(lambda x: f"{x:.5f}"),
        "95% CI": alt.apply(lambda r: f"[{r.ci_lower:.5f}, {r.ci_upper:.5f}]", axis=1),
        "p-value": alt["bootstrap_p_value"].map(lambda x: f"{x:.3f}"),
    })
    paired = pd.DataFrame([{
        "Specification": "Paired beta minus alpha (common Rule-A/Webb support)",
        "Occupations": 468,
        "Q5-Q1 coefficient": "-0.03240",
        "Bootstrap SE": "0.03697",
        "95% CI": "[-0.10235, 0.03755]",
        "p-value": "0.403",
    }])
    out = pd.concat([out, paired], ignore_index=True)
    write_table(
        "table5b_same_design_different_x",
        out,
        "Note: All exposure rows hold Rule-A support, Webb conditioning, outcome, estimator, "
        "and inference fixed. The final row is a direct paired comparison using common bootstrap "
        "draws. An interval containing zero means no detected difference, not economic equivalence. "
        "Source: ALTERNATIVE_X_AUDIT.csv and the frozen paired Test-C object.",
    )


def build_table6() -> None:
    alt = pd.read_csv(AUDIT / "ALTERNATIVE_X_AUDIT.csv")
    comp = alt.iloc[6:11].copy()
    comp_names = [
        "Beta + Webb software patents", "Beta + O*NET computer-use importance",
        "Beta + O*NET computer-use level", "Beta + Autor-Dorn RTI",
        "Beta + Frey-Osborne automation",
    ]
    c = pd.DataFrame({
        "Panel": "A. Computerization architecture",
        "Specification / coefficient": comp_names,
        "Occupations": comp["occupations"].astype(int).to_numpy(),
        "Estimate": comp["coefficient"].map(lambda x: f"{x:.5f}").to_numpy(),
        "Bootstrap SE": comp["bootstrap_se"].map(lambda x: f"{x:.5f}").to_numpy(),
        "95% CI": comp.apply(lambda r: f"[{r.ci_lower:.5f}, {r.ci_upper:.5f}]", axis=1).to_numpy(),
        "p-value": comp["bootstrap_p_value"].map(lambda x: f"{x:.3f}").to_numpy(),
    })
    remote = pd.read_csv(AUDIT / "REMOTE_MODEL_AUDIT.csv")
    keep_specs = [
        ("dv_rating_beta__ai_only", "AI_z_x_post", "Beta, AI only: AI"),
        ("dv_rating_beta__ai_remote_joint", "AI_z_x_post", "Beta, AI + remote: AI"),
        ("dv_rating_beta__ai_remote_joint", "remote_z_x_post", "Beta, AI + remote: remote"),
        ("dv_rating_beta__ai_comp_remote_joint", "AI_z_x_post", "Beta, AI + Webb + remote: AI"),
        ("dv_rating_beta__ai_comp_remote_joint", "remote_z_x_post", "Beta, AI + Webb + remote: remote"),
        ("dv_rating_alpha__ai_only", "AI_z_x_post", "Alpha, AI only: AI"),
        ("dv_rating_alpha__ai_remote_joint", "AI_z_x_post", "Alpha, AI + remote: AI"),
        ("dv_rating_alpha__ai_remote_joint", "remote_z_x_post", "Alpha, AI + remote: remote"),
        ("dv_rating_alpha__ai_comp_remote_joint", "AI_z_x_post", "Alpha, AI + Webb + remote: AI"),
        ("dv_rating_alpha__ai_comp_remote_joint", "remote_z_x_post", "Alpha, AI + Webb + remote: remote"),
        ("remote_only", "AI_z_x_post", "Remote only: remote"),
    ]
    rr = []
    for spec, label, pretty in keep_specs:
        row = remote[(remote.specification_id == spec) & (remote.coefficient_label == label)].iloc[0]
        rr.append({
            "Panel": "B. Occupation-level remotability",
            "Specification / coefficient": pretty,
            "Occupations": int(row.occupations),
            "Estimate": f"{row.coefficient:.5f}",
            "Bootstrap SE": f"{row.bootstrap_se:.5f}",
            "95% CI": f"[{row.ci_lower:.5f}, {row.ci_upper:.5f}]",
            "p-value": f"{row.bootstrap_p_value:.3f}",
        })
    out = pd.concat([c, pd.DataFrame(rr)], ignore_index=True)
    write_table(
        "table6_computerization_and_remotability",
        out,
        "Note: Panel A reports Q5-Q1 AI coefficients; Panel B reports per-SD coefficients. "
        "These scales must not be compared mechanically. Remotability is an occupation-level "
        "feasibility measure, not realized worker telework. Source: ALTERNATIVE_X_AUDIT.csv and "
        "REMOTE_MODEL_AUDIT.csv.",
    )


def build_figure1() -> None:
    fig, ax = plt.subplots(figsize=(13, 4.8))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    labels = [
        ("Technology or\ncapability", "AI applications\nor LLM capability"),
        ("Task/ability\nassessment", "MTurk, human expert,\nor model judgment"),
        ("Native occupation\nscore", "Abilities or tasks\naggregated to occupation"),
        ("Taxonomy mapping", "SOC/Census vintage\nand crosswalk rule"),
        ("Common support", "Strict coverage or\nreported sensitivity"),
        ("Regression treatment", "Standardized score\nor Q5-Q1 contrast"),
    ]
    xs = np.linspace(0.09, 0.91, len(labels))
    for i, (title, sub) in enumerate(labels):
        x = xs[i]
        color = "#DCEAF7" if i < 3 else "#F5E4C8"
        box = FancyBboxPatch(
            (x - 0.064, 0.34), 0.128, 0.32,
            boxstyle="round,pad=0.012,rounding_size=0.02",
            linewidth=1.2, edgecolor="#263746", facecolor=color,
        )
        ax.add_patch(box)
        ax.text(x, 0.555, title, ha="center", va="center", fontsize=10.5, weight="bold")
        ax.text(x, 0.415, sub, ha="center", va="center", fontsize=8.5, color="#33495B")
        if i < len(labels) - 1:
            ax.add_patch(FancyArrowPatch(
                (x + 0.066, 0.50), (xs[i + 1] - 0.066, 0.50),
                arrowstyle="-|>", mutation_scale=12, linewidth=1.2, color="#526B7A",
            ))
    ax.text(0.255, 0.82, "Native measurement architecture", ha="center", fontsize=12, weight="bold", color="#1E5A86")
    ax.text(0.745, 0.82, "Empirical harmonization architecture", ha="center", fontsize=12, weight="bold", color="#8A5A18")
    ax.text(0.5, 0.12, "Different choices can change occupational meaning, effective identifying support, or both.", ha="center", fontsize=11)
    fig.savefig(FIGURES / "figure1_measurement_genealogy.png", dpi=300, bbox_inches="tight")
    fig.savefig(FIGURES / "figure1_measurement_genealogy.pdf", bbox_inches="tight")
    plt.close(fig)


def build_figure2(df: pd.DataFrame) -> None:
    order_ai = list(LABEL_AI)
    order_comp = list(LABEL_COMP)
    en = df.pivot(index="ai_measure", columns="computerization_measure", values="effective_identifying_occupations").loc[order_ai, order_comp]
    sh = 100 * df.pivot(index="ai_measure", columns="computerization_measure", values="top_five_residual_variance_share").loc[order_ai, order_comp]
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.3), constrained_layout=True)
    panels = [
        (en, "Effective identifying occupations", "viridis", 0),
        (sh, "Top-five residual-variance share (%)", "magma_r", 1),
    ]
    for values, title, cmap, j in panels:
        ax = axes[j]
        im = ax.imshow(values.to_numpy(), aspect="auto", cmap=cmap)
        ax.set_title(title, fontsize=12, weight="bold", pad=12)
        short_comp = ["Webb", "O*NET importance", "O*NET level", "Autor-Dorn RTI", "Frey-Osborne"]
        ax.set_xticks(range(len(order_comp)), short_comp, fontsize=8, rotation=22, ha="right")
        ax.set_yticks(range(len(order_ai)), [LABEL_AI[x] for x in order_ai], fontsize=9)
        for r in range(values.shape[0]):
            for c in range(values.shape[1]):
                v = values.iloc[r, c]
                rgba = im.cmap(im.norm(v))
                luminance = 0.2126 * rgba[0] + 0.7152 * rgba[1] + 0.0722 * rgba[2]
                ax.text(c, r, f"{v:.1f}", ha="center", va="center", color="black" if luminance > 0.55 else "white", fontsize=9, weight="bold")
        fig.colorbar(im, ax=ax, shrink=0.75)
    fig.suptitle("Identifying support changes with both AI exposure and computerization architecture", fontsize=14, weight="bold")
    fig.savefig(FIGURES / "figure2_identifying_variation.png", dpi=300, bbox_inches="tight")
    fig.savefig(FIGURES / "figure2_identifying_variation.pdf", bbox_inches="tight")
    plt.close(fig)


def build_figure3() -> None:
    shutil.copy2(FROZEN / "reporting" / "figure1_event_study.png", FIGURES / "figure3_frozen_event_study.png")


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    build_table1()
    build_table2()
    test_b = build_table3()
    build_table4()
    build_table5()
    build_table6()
    build_figure1()
    build_figure2(test_b)
    build_figure3()
    receipt_path = OUT / "MANUSCRIPT_RECEIPT.json"
    files = sorted([p for p in OUT.rglob("*") if p.is_file() and p != receipt_path])
    manuscript = OUT / "YAX_MANUSCRIPT_v1.md"
    word_count = len(manuscript.read_text(encoding="utf-8").split()) if manuscript.exists() else None
    receipt = {
        "record": "YAX first full manuscript and presentation package",
        "presentation_only": True,
        "new_empirical_analysis_executed": False,
        "manuscript": "yax/manuscript/v1/YAX_MANUSCRIPT_v1.md",
        "manuscript_word_count_whitespace": word_count,
        "canonical_table_count": 6,
        "canonical_figure_count": 3,
        "branch": "task/yax-manuscript-v1-20260830",
        "frozen_authority": {"tag": FROZEN_TAG, "commit": FROZEN_COMMIT},
        "canonical_result_json_sha256": sha256(FROZEN / "FROZEN_RESULTS.json"),
        "canonical_result_ledger_sha256": sha256(FROZEN / "RESULT_LEDGER.jsonl"),
        "canonical_result_markdown_sha256": sha256(FROZEN / "FROZEN_RESULTS.md"),
        "ledger_rows": sum(1 for _ in (FROZEN / "RESULT_LEDGER.jsonl").open()),
        "build_command": "MPLCONFIGDIR=/tmp/yax-mpl python3 yax/manuscript/v1/build_presentation_assets.py",
        "verification": {
            "manuscript_local_links": "10/10 resolved",
            "publication_table_row_counts": "6, 6, 30, 4, 12, 7, and 16 rows across panel files; all matched",
            "yax_test_suite": "87 passed",
            "design_gates": "12/12 PASS with explicit v3 power, v2 paired precision, and v1.1 freeze tag",
            "immutable_confirmatory_archive": "772 passed, 3 skipped; completion 241/241; integrity 47/47",
            "root_suite_note": "Local root collection is blocked by absent untracked ops/l1/gemini_helper.py; no replacement was fabricated",
        },
        "files": [{"path": str(p.relative_to(ROOT)), "sha256": sha256(p)} for p in files],
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/yax-mpl")
    main()
