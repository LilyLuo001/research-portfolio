#!/usr/bin/env python3
"""Build bounded descriptive figures from frozen LinkUp aggregate outputs.

This script never reads row-level text and never modifies the frozen T1--T6
products. It reports engineering coverage, delivery-time risk, and old candidate
measurement sensitivity only.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter, PercentFormatter


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
OLD = PROJECT.parent / "pre_revelio_execution_v1" / "results"

INPUTS = {
    "population_funnel": OLD / "01_population_funnel.csv",
    "reverse_coverage": OLD / "T1_USA_RECORDS_REVERSE_COVERAGE.json",
    "occupation_coverage": OLD / "T4_full_v3" / "T4_CONCENTRATION.csv",
    "annual_coverage": OLD / "T4_full_v3" / "T4_ANNUAL_COVERAGE.csv",
    "time_risk": OLD / "T4_full_v3" / "T4_TIME_RISK.csv",
    "candidate_sensitivity": OLD / "T5_T6_fixed_v1" / "T6_SENSITIVITY_AND_CLAIM_STATUS.csv",
    "t5_t6_acceptance": OLD / "T5_T6_NUMERIC_ACCEPTANCE_RECEIPT.json",
    "research_contract": PROJECT / "RESEARCH_CONTRACT.json",
    "historical_decisions": PROJECT / "HISTORICAL_COMPARISON_DECISIONS.json",
    "root_development_decision": PROJECT / "measurement" / "results" / "ROOT_DEVELOPMENT_DECISION.json",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fieldnames: list[str], data: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(data)


def set_style() -> None:
    preferred = ["PingFang SC", "Heiti SC", "STHeiti", "Arial Unicode MS", "DejaVu Sans"]
    installed = {f.name for f in font_manager.fontManager.ttflist}
    font = next((x for x in preferred if x in installed), "DejaVu Sans")
    plt.rcParams.update({
        "font.family": font,
        "axes.unicode_minus": False,
        "figure.dpi": 150,
        "savefig.dpi": 220,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titleweight": "bold",
        "axes.titlesize": 14,
        "axes.labelsize": 10,
    })


def save(fig, stem: str) -> None:
    fig.savefig(HERE / f"{stem}.png", bbox_inches="tight", facecolor="white")
    fig.savefig(HERE / f"{stem}.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def coverage() -> list[dict]:
    funnel = {r["metric"]: r for r in rows(INPUTS["population_funnel"])}
    reverse = json.loads(INPUTS["reverse_coverage"].read_text())
    occ = next(r for r in rows(INPUTS["occupation_coverage"]) if r["dimension"] == "occupation_major")
    canonical = int(funnel["usa_canonical_regional_row_sum"]["count"])
    data = [
        {
            "stage": "美国 Records 记录",
            "numerator": int(reverse["denominator_verified_usa_records"]),
            "denominator": int(reverse["denominator_verified_usa_records"]),
            "rate": 1.0,
            "meaning": "Records 行；不是职位空缺或录用人数",
        },
        {
            "stage": "连接到规范广告键",
            "numerator": int(reverse["numerator_distinct_matched_usa_job_hashes"]),
            "denominator": int(reverse["denominator_verified_usa_records"]),
            "rate": float(reverse["reverse_coverage"]),
            "meaning": "全局键审计后的美国 Records 反向覆盖",
        },
        {
            "stage": "正文可用",
            "numerator": int(funnel["usable_nonempty_complete_parse"]["count"]),
            "denominator": canonical,
            "rate": int(funnel["usable_nonempty_complete_parse"]["count"]) / canonical,
            "meaning": "规范广告中非空且完整解析；失败标记可能重叠",
        },
        {
            "stage": "职业大类可映射",
            "numerator": int(occ["mapped_ads"]),
            "denominator": int(occ["canonical_ads_denominator"]),
            "rate": int(occ["mapped_ads"]) / int(occ["canonical_ads_denominator"]),
            "meaning": "当前快照职业映射；不是个人职业经历",
        },
    ]
    write_csv(HERE / "coverage_summary.csv", list(data[0]), data)

    fig, ax = plt.subplots(figsize=(10, 5.4))
    labels = [d["stage"] for d in data]
    rates = [d["rate"] for d in data]
    colors = ["#637083", "#2F6B8A", "#3A8D7C", "#7A5C9E"]
    bars = ax.barh(labels[::-1], rates[::-1], color=colors[::-1], height=0.62)
    ax.set_xlim(0, 1.08)
    ax.xaxis.set_major_formatter(PercentFormatter(1.0))
    ax.set_title("全库工程覆盖：连接、正文与职业映射")
    ax.set_xlabel("各步骤自己的分母内覆盖率")
    for bar, d in zip(bars, data[::-1]):
        pct = f"{d['rate']:.3%}" if d["rate"] > 0.99 else f"{d['rate']:.2%}"
        ax.text(bar.get_width() + 0.012, bar.get_y() + bar.get_height()/2,
                f"{pct}\n{d['numerator']:,}/{d['denominator']:,}",
                va="center", fontsize=9)
    ax.text(0, -0.24,
            "注：步骤分母不同。81% 是美国 Records 到规范广告键的反向覆盖；其余两项以 204,774,035 条规范广告为分母。",
            transform=ax.transAxes, fontsize=9, color="#4B5563")
    fig.subplots_adjust(left=0.25, bottom=0.25)
    save(fig, "fig1_population_text_occupation_coverage")
    return data


def time_risk() -> tuple[list[dict], list[dict]]:
    annual = rows(INPUTS["annual_coverage"])
    risks = {r["metric"]: r for r in rows(INPUTS["time_risk"])}
    annual_out = [
        {
            "created_year": int(r["created_year"]),
            "canonical_ads": int(r["canonical_ads"]),
            "share_of_all_canonical": int(r["canonical_ads"]) / sum(int(x["canonical_ads"]) for x in annual),
        }
        for r in annual
    ]
    risk_out = []
    canonical_ads = int(risks["canonical_ads"]["numerator"])
    valid_interval_ads = int(risks["valid_main_interval"]["numerator"])
    invalid_interval_ads = canonical_ads - valid_interval_ads
    for metric, label in [
        ("crosses_quarter", "跨日历季度"),
        ("crosses_year", "跨日历年"),
        ("crosses_2022_11_30", "跨 2022-11-30"),
        ("crosses_2023_01_01", "跨 2023-01-01"),
    ]:
        r = risks[metric]
        risk_out.append({
            "metric": metric,
            "label": label,
            "numerator": int(r["numerator"]),
            "denominator": int(r["denominator"]),
            "rate": int(r["numerator"]) / int(r["denominator"]),
            "canonical_ads": canonical_ads,
            "invalid_or_incomplete_interval_ads": invalid_interval_ads,
            "interpretation": r["interpretation"],
        })
    write_csv(HERE / "created_year_summary.csv", list(annual_out[0]), annual_out)
    write_csv(HERE / "time_risk_summary.csv", list(risk_out[0]), risk_out)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.4), gridspec_kw={"width_ratios": [1.65, 1]})
    years = [r["created_year"] for r in annual_out]
    values = [r["canonical_ads"] for r in annual_out]
    colors = ["#2F6B8A"] * len(years)
    colors[-1] = "#9AA8B4"
    bars = ax1.bar(years, values, color=colors, width=0.82)
    bars[-1].set_hatch("//")
    ax1.text(years[-1], values[-1] + max(values) * 0.025, "截至 Q2", ha="center", fontsize=8, color="#4B5563")
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x/1e6:.0f}M"))
    ax1.set_title("首次观察队列（按 CREATED 年）")
    ax1.set_ylabel("规范广告数")
    ax1.set_xticks(years[::2])
    ax1.tick_params(axis="x", rotation=45)

    rlabels = [r["label"] for r in risk_out]
    rrates = [r["rate"] for r in risk_out]
    rbars = ax2.barh(rlabels[::-1], rrates[::-1], color="#C26D3A", height=0.62)
    ax2.xaxis.set_major_formatter(PercentFormatter(1.0))
    ax2.set_xlim(0, 0.42)
    ax2.set_title("交付观察区间的跨期风险")
    for bar, r in zip(rbars, risk_out[::-1]):
        ax2.text(bar.get_width() + 0.008, bar.get_y() + bar.get_height()/2,
                 f"{r['rate']:.2%}", va="center", fontsize=9)
    fig.text(0.5, -0.02,
             "2026 为截至 Q2 的部分年度，不与全年直接比较。跨期率分母为 204,773,879 条有效日期区间；另有 156 条无效／不完整。",
             ha="center", fontsize=9, color="#4B5563")
    fig.text(0.5, -0.065,
             "CREATED 仅表示首次观察；跨期率来自 CREATED–LAST_CHECKED 交付区间，均不证明正文生效或改写时间。",
             ha="center", fontsize=9, color="#4B5563")
    fig.subplots_adjust(bottom=0.24, wspace=0.38)
    save(fig, "fig2_first_observed_and_cross_period_risk")
    return annual_out, risk_out


def sensitivity() -> list[dict]:
    source = rows(INPUTS["candidate_sensitivity"])
    variants = [
        ("main", "主规格"),
        ("s1_required_only", "仅 required"),
        ("s1_broad_cooccurrence", "宽松共现"),
        ("s2_same_company_occupation", "同公司×职业"),
    ]
    objects = [
        ("general_work", "一般工作经验"),
        ("industry_domain", "行业／领域经验"),
        ("specific_tool", "特定工具经验"),
    ]
    out = []
    for variant, vlabel in variants:
        for obj, olabel in objects:
            r = next(x for x in source if x["comparison"] == "C1_use" and x["analysis_variant"] == variant and x["experience_object"] == obj)
            out.append({
                "analysis_variant": variant,
                "variant_label": vlabel,
                "experience_object": obj,
                "object_label": olabel,
                "standardized_difference_A_minus_B": float(r["standardized_difference_A_minus_B"]),
                "retained_A": int(r["retained_A"]),
                "retained_B": int(r["retained_B"]),
                "support_cells": int(r["support_cells"]),
                "support_occupation_majors": int(r["support_occupation_majors"]),
                "status": r["status"],
            })
    write_csv(HERE / "candidate_sensitivity_summary.csv", list(out[0]), out)

    fig, ax = plt.subplots(figsize=(11, 6.1))
    palette = ["#2F6B8A", "#3A8D7C", "#C26D3A"]
    markers = ["o", "s", "^"]
    for (obj, olabel), color, marker in zip(objects, palette, markers):
        vals = [100 * next(r for r in out if r["analysis_variant"] == v and r["experience_object"] == obj)["standardized_difference_A_minus_B"] for v, _ in variants]
        ax.plot(range(len(variants)), vals, marker=marker, markersize=7, linewidth=2, color=color, label=olabel)
    ax.axhline(0, color="#555555", linewidth=1)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.0f}"))
    ax.set_xticks(range(len(variants)), [v[1] for v in variants])
    ax.set_ylabel("旧 C1 候选组 A−B 的标准化比例差（百分点，pp）")
    ax.set_title("旧候选测量对规则与支持限制敏感")
    ax.legend(frameon=False, ncol=3, loc="lower left")
    ax.grid(axis="y", color="#D1D5DB", linewidth=0.7, alpha=0.7)
    ax.text(0, -0.25,
            "注：同公司×职业规格还把支持从 69 格降至 64 格、B 组从 1,064,428 降至 245,055，差异不能全归于测量规则。",
            transform=ax.transAxes, fontsize=9, color="#4B5563")
    ax.text(0, -0.31,
            "旧规则候选信号尚未通过新版语义验收；职业／任务经验未测。差异不是 AI 因果效应，也不是历史正文变化。",
            transform=ax.transAxes, fontsize=9, color="#4B5563")
    fig.subplots_adjust(bottom=0.33)
    save(fig, "fig3_candidate_measurement_sensitivity")
    return out


def receipts(outputs: list[Path]) -> None:
    source_rows = []
    for role, path in INPUTS.items():
        source_rows.append({"role": role, "path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size})
    write_csv(HERE / "source_sha256_receipt.csv", list(source_rows[0]), source_rows)
    receipt = {
        "status": "complete_bounded_existing_aggregate_analysis",
        "scope": "frozen aggregate reuse only; no row-level rescan; no new model extraction",
        "source_files": source_rows,
        "outputs": [
            {"path": str(p), "sha256": sha256(p), "bytes": p.stat().st_size}
            for p in outputs if p.exists()
        ],
        "immutable_inputs_modified": False,
    }
    (HERE / "EXECUTION_RECEIPT.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")


def main() -> None:
    missing = [str(p) for p in INPUTS.values() if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing frozen inputs: " + ", ".join(missing))
    set_style()
    coverage()
    time_risk()
    sensitivity()
    outputs = [p for p in HERE.iterdir() if p.is_file() and p.name != "EXECUTION_RECEIPT.json"]
    receipts(outputs)


if __name__ == "__main__":
    main()
