#!/usr/bin/env python3
"""Render existing aggregate estimates; never recalculate research measures."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def number(value):
    return None if value in (None, "", "None", "null") else float(value)


def draw(ax, records, keys, key_column, estimate_column, series):
    colors = ["#225b91", "#b96323"]
    for j, (label, selected) in enumerate(series):
        by_key = {}
        for row in records:
            if selected(row):
                key = row[key_column]
                if key in by_key:
                    raise RuntimeError("duplicate aggregate plot cell")
                by_key[key] = row
        for i, key in enumerate(keys):
            row = by_key.get(key)
            if row is None:
                continue
            value = number(row[estimate_column])
            if value is None:
                continue
            low, high = number(row["ci_low"]), number(row["ci_high"])
            offset = (j - (len(series) - 1) / 2) * 0.20
            y = i + offset
            ax.plot(value * 100, y, "o", color=colors[j], markersize=5)
            if low is not None and high is not None:
                ax.plot([low * 100, high * 100], [y, y], color=colors[j], linewidth=1.4)
        ax.plot([], [], "o-", color=colors[j], label=label)
    ax.set_yticks(range(len(keys)))
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="best", frameon=False, fontsize=9)


def save(fig, output, name, note):
    fig.text(0.02, 0.015, note, fontsize=8, va="bottom")
    fig.tight_layout(rect=(0, 0.10, 1, 1))
    for extension in ("pdf", "png"):
        fig.savefig(output / (name + "." + extension), dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads((args.results_dir / "ANALYSIS_RECEIPT.json").read_text())
    if receipt.get("status") != "complete":
        raise RuntimeError("analysis receipt not complete")
    inputs = [args.results_dir / "COMPARISON_1_EXPERIENCE.csv",
              args.results_dir / "COMPARISON_2_ENTRY_DUTY.csv"]
    for path in inputs:
        if digest(path) != receipt["outputs"].get(path.name):
            raise RuntimeError("aggregate does not bind analysis receipt")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    experience = ["experience_general_work", "experience_occupation_task",
                  "experience_industry_domain", "experience_tool_specific"]
    fig, ax = plt.subplots(figsize=(9.2, 4.5))
    draw(ax, rows(inputs[0]), experience, "measure", "difference_a_minus_b", [
        ("All sampled occupations", lambda r: r["scope"] == "all_reviewed_sample"),
        ("Shared occupation majors", lambda r: r["scope"] == "common_occupation_major_ge5_each_group"),
    ])
    ax.set_yticklabels(["General work", "Occupation / task", "Industry / domain", "Specific tool"])
    ax.axvline(0, color="#777777", linewidth=0.8)
    ax.set_xlabel("GenAI-use minus traditional-software-use rate (percentage points)")
    ax.set_title("Experience wording in saved job descriptions")
    save(fig, args.output_dir, "FIGURE_1_EXPERIENCE", 
         "Finite eligible fixed10k frame; 1/pi3 weights. Shared majors are pooled, not composition-standardized.\n"
         "95% intervals cover sampling uncertainty only; unknown labels excluded. Missing estimates are not plotted.")
    duties = ["independent_judgment", "client_ownership", "people_supervision",
              "training_mentoring", "any_strict_current_duty"]
    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    draw(ax, rows(inputs[1]), duties, "duty_dimension", "estimate", [
        ("Experience-waiver or graduate wording", lambda r: r["scope"] == "all_reviewed_sample"
         and r["technology_scope"] == "all_technology_groups" and r["entry_definition"] == "including_conditional"),
        ("Explicit new-graduate wording only", lambda r: r["scope"] == "all_reviewed_sample"
         and r["technology_scope"] == "all_technology_groups" and r["entry_definition"] == "explicit_new_graduate_only"),
    ])
    ax.set_yticklabels(["Independent judgment", "Client ownership", "People supervision",
                        "Training / mentoring", "Any of these duties"])
    ax.set_xlim(0, 100)
    ax.set_xlabel("Rate among wording-positive ads with a defined duty label (%)")
    ax.set_title("Current responsibilities in ads with entry-related wording")
    save(fig, args.output_dir, "FIGURE_2_ENTRY_DUTIES",
         "All technology groups; current advertised-worker duties. Waiver of one experience type is not global entry eligibility.\n"
         "95% intervals cover sampling uncertainty only. Unknown membership excluded; unknown-duty bounds are in the comparison table.")
    artifacts = {p.name: digest(p) for p in sorted(args.output_dir.iterdir()) if p.suffix in {".pdf", ".png"}}
    (args.output_dir / "FIGURE_RECEIPT.json").write_text(json.dumps({
        "status": "complete", "code_sha256": digest(Path(__file__)),
        "inputs": {p.name: digest(p) for p in inputs}, "outputs": artifacts,
        "new_estimation": False, "private_rows_read": False,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
