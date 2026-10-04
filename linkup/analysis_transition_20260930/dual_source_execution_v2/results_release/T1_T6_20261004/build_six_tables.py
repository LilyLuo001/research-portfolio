#!/usr/bin/env python3
"""Build six compact release tables from frozen aggregate results only."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
SRC = PROJECT / "analysis_transition_20260930/pre_revelio_execution_v1/results"

INPUTS = [
    SRC / "01_population_funnel.csv",
    SRC / "T1_USA_RECORDS_REVERSE_COVERAGE.json",
    SRC / "full_semantic_narrow_v1/aggregate/T2_EXPERIENCE_AD_RATES.csv",
    SRC / "full_semantic_narrow_v1/aggregate/T2_DURATION_BOUND_DISTRIBUTION.csv",
    SRC / "full_semantic_narrow_v1/aggregate/T3_TECHNOLOGY_ROLE.csv",
    SRC / "full_semantic_narrow_v1/aggregate/T3_TECHNOLOGY_EXPERIENCE_COOCCURRENCE.csv",
    SRC / "full_semantic_narrow_v1/aggregate/T3_TECHNOLOGY_PAIR_OVERLAP.csv",
    SRC / "T4_full_v3/T4_ANNUAL_COVERAGE.csv",
    SRC / "T4_full_v3/T4_TIME_RISK.csv",
    SRC / "T4_full_v3/T4_SELECTED_ANNUAL_GROUP_SUMMARY.csv",
    SRC / "T5_T6_fixed_v1/T5_MAIN_COMPARABLE_EXPERIENCE_CONTRASTS.csv",
    SRC / "T5_T6_fixed_v1/T6_SENSITIVITY_AND_CLAIM_STATUS.csv",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(name: str, fields: list[str], rows: list[dict[str, object]]) -> None:
    with (HERE / name).open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def n(value: str | int | float | None) -> str:
    if value in (None, ""):
        return "NA"
    return f"{int(float(value)):,}"


def pct(value: str | float | None, digits: int = 3) -> str:
    if value in (None, ""):
        return "NA"
    return f"{100 * float(value):.{digits}f}%"


def pp(value: str | float | None, digits: int = 3) -> str:
    if value in (None, ""):
        return "NA"
    return f"{100 * float(value):+.{digits}f}"


OBJ = {
    "general_work": "一般工作经验",
    "occupation_task": "职业/任务经验",
    "industry_domain": "行业/领域经验",
    "specific_tool": "特定工具经验",
}
TECH = {
    "traditional_software": "传统软件",
    "generative_ai": "生成式AI",
    "predictive_ai": "预测式AI",
    "unspecified_ai": "未指定AI",
}


def build_t1() -> None:
    source = {r["metric"]: r for r in read_csv(INPUTS[0])}
    specs = [
        ("交付 Records 行", "all_records"),
        ("美国 Records 行", "usa_records"),
        ("原始描述出现次数", "raw_description_rows"),
        ("成功连接 Records 的描述次数", "record_matched_description_rows"),
        ("未连接 Records 的描述次数", "record_unmatched_description_rows"),
        ("美国规范广告对象", "usa_canonical_regional_row_sum"),
        ("正文非空且完整解析", "usable_nonempty_complete_parse"),
    ]
    rows = []
    for label, key in specs:
        r = source[key]
        status = "完成"
        if key == "usa_canonical_regional_row_sum":
            status = "完成；全局唯一键审计已在后续冻结回执完成"
        note = r["unit_note"] or "交付行级工程计数"
        if key == "usa_canonical_regional_row_sum":
            note = "全局唯一键已审计的美国规范广告对象；由描述出现次数转为规范对象，单位变化，不是同单位通过率"
        rows.append({"阶段": label, "数量": n(r["count"]), "分母": n(r["denominator"]),
                     "比例": pct(r["share"]), "状态": status,
                     "口径/限制": note})
    rows.append({"阶段": "美国 Records 反向覆盖", "数量": n(204774035), "分母": n(253210047),
                 "比例": pct(0.8087121242862847), "状态": "完成",
                 "口径/限制": "全局审计规范 JOB_HASH / 美国 Records；不是职位空缺或录用人数"})
    write_csv("T1_coverage_funnel.csv", list(rows[0]), rows)


def build_t2() -> None:
    rates = {r["experience_object"]: r for r in read_csv(INPUTS[2])}
    durations = read_csv(INPUTS[3])
    rows: list[dict[str, object]] = []
    for key in OBJ:
        r = rates[key]
        if r["measurement_available"] == "false":
            rows.append({"经验维度": OBJ[key], "指标": "原规则主口径命中", "数量": "NA", "分母": "NA",
                         "比例": "NA", "状态": "未测量", "口径/限制": "D10 未测量；NA 不等于 0"})
            continue
        rows.append({"经验维度": OBJ[key], "指标": "原规则主口径命中", "数量": n(r["main_ads"]),
                     "分母": n(r["usable_ads_denominator"]), "比例": pct(r["main_rate"]),
                     "状态": "可报告的操作性测量", "口径/限制": "旧文字规则命中；D27 不支持语义构念有效性"})
        for d in durations:
            if d["experience_object"] == key and d["classification"] == "bound_form":
                labels = {"exact_or_unspecified": "精确或未指明界限", "minimum": "最低年限",
                          "range": "区间年限", "no_numeric_bound": "无数字年限"}
                rows.append({"经验维度": OBJ[key], "指标": labels[d["bound_category"]],
                             "数量": n(d["distinct_ads"]), "分母": n(d["main_ads_denominator"]),
                             "比例": pct(d["ad_share"]), "状态": "显式经验条款内的年限形态",
                             "口径/限制": "广告内去重；同一广告可落入多个类别，比例不能相加"})
    unspecified = rates["object_unspecified"]
    rows.append({"经验维度": "经验对象未明确（旧规则）", "指标": "原规则主口径命中",
                 "数量": n(unspecified["main_ads"]), "分母": n(unspecified["usable_ads_denominator"]),
                 "比例": pct(unspecified["main_rate"]), "状态": "可报告的操作性测量",
                 "口径/限制": "单列缺失/未识别对象；不能分配到一般经验；D27 不支持语义构念有效性"})
    write_csv("T2_experience_dimensions.csv", list(rows[0]), rows)


def build_t3() -> None:
    roles = read_csv(INPUTS[4])
    co = read_csv(INPUTS[5])
    overlaps = read_csv(INPUTS[6])
    rows: list[dict[str, object]] = []
    for tech in TECH:
        rr = {r["role"]: r for r in roles if r["technology"] == tech}
        structural = tech == "predictive_ai"
        rows.append({"区块": "A 技术角色", "技术/配对": TECH[tech],
                     "候选/一般经验": "NA" if structural else n(rr["detected_any_role"]["ads"]),
                     "使用/行业经验": "NA" if structural else n(rr["use"]["ads"]),
                     "开发/工具经验": "NA" if structural else n(rr["develop"]["ads"]),
                     "实施/交集": "NA" if structural else n(rr["implement"]["ads"]),
                     "分母": n(rr["use"]["usable_ads_denominator"]),
                     "状态/限制": "字面规则结构性零，按 NA 报告" if structural else "原字面规则候选；非语义构念验证"})
    for tech in TECH:
        if tech == "predictive_ai":
            continue
        for role in ("use", "develop", "implement"):
            rr = {r["experience_object"]: r for r in co if r["technology"] == tech and r["role"] == role}
            rows.append({"区块": f"B 同广告共现（{role}）", "技术/配对": TECH[tech],
                         "候选/一般经验": n(rr["general_work"]["cooccurrence_ads"]),
                         "使用/行业经验": n(rr["industry_domain"]["cooccurrence_ads"]),
                         "开发/工具经验": n(rr["specific_tool"]["cooccurrence_ads"]),
                         "实施/交集": "NA",
                         "分母": n(rr["general_work"]["technology_role_ads"]),
                         "状态/限制": "一般/行业/工具经验共现；不证明技术与经验直接绑定"})
    for r in overlaps:
        if r["role"] != "detected_any_role":
            continue
        if "predictive_ai" in (r["technology_left"], r["technology_right"]):
            val, status = "NA", "涉及预测式AI结构性零，按 NA 报告"
        else:
            val, status = n(r["intersection_ads"]), "同广告候选检测交集；原字面规则"
        rows.append({"区块": "C 技术配对重叠", "技术/配对": f"{TECH[r['technology_left']]} × {TECH[r['technology_right']]}",
                     "候选/一般经验": "NA", "使用/行业经验": "NA", "开发/工具经验": "NA", "实施/交集": val,
                     "分母": n(r["usable_ads_denominator"]), "状态/限制": status})
    write_csv("T3_technology_candidates.csv", list(rows[0]), rows)


def build_t4() -> None:
    annual = read_csv(INPUTS[7])
    risk = {r["metric"]: r for r in read_csv(INPUTS[8])}
    groups = read_csv(INPUTS[9])
    rows: list[dict[str, object]] = []
    for r in annual:
        if int(r["created_year"]) >= 2014:
            status = "部分年度" if r["created_year"] == "2026" else "交付内完整日历年（不保证覆盖）"
            rows.append({"区块": "CREATED 年度队列", "时期/汇总": r["created_year"],
                         "数量": n(r["canonical_ads"]), "分母": n(204774035),
                         "比例": pct(int(r["canonical_ads"]) / 204774035), "状态": status,
                         "口径/限制": "CREATED=首次观察；不是正文版本或生效时间"})
    labels = {"crosses_quarter": "跨日历季度", "crosses_year": "跨日历年",
              "crosses_2022_11_30": "跨 2022-11-30", "crosses_2023_01_01": "跨 2023-01-01"}
    for key, label in labels.items():
        r = risk[key]
        rows.append({"区块": "跨期风险", "时期/汇总": label, "数量": n(r["numerator"]),
                     "分母": n(r["denominator"]), "比例": pct(int(r["numerator"]) / int(r["denominator"])),
                     "状态": "完成", "口径/限制": "交付观察区间；不是正文修改或历史版本"})
    invalid = 204774035 - int(risk["valid_main_interval"]["numerator"])
    rows.append({"区块": "日期质量", "时期/汇总": "无效或不完整 CREATED–LAST_CHECKED",
                 "数量": n(invalid), "分母": n(204774035), "比例": pct(invalid / 204774035),
                 "状态": "完成", "口径/限制": "因此跨期指标分母为 204,773,879 条有效观察区间"})
    years = [int(r["created_years"]) for r in groups]
    keys = [int(r["selected_job_hashes"]) for r in groups]
    rows.append({"区块": "相似职位年度诊断", "时期/汇总": "固定前缀所选 12 组汇总",
                 "数量": n(sum(keys)), "分母": "12 组", "比例": f"每组 {min(years)}–{max(years)} 个 CREATED 年",
                 "状态": "固定种子诊断", "口径/限制": "200 个规范键；非全库概率样本，不含公司或广告标识"})
    write_csv("T4_time_and_annual_diagnostics.csv", list(rows[0]), rows)


def build_t5() -> None:
    source = read_csv(INPUTS[10])
    rows: list[dict[str, object]] = []
    for r in source:
        if r["comparison"] == "C1_use":
            rows.append({"既定比较": "C1 使用：生成式AI vs 传统软件", "经验维度": OBJ[r["experience_object"]],
                         "共同支持 A/B": f"{n(r['retained_A'])} / {n(r['retained_B'])}",
                         "原始差异(pp)": pp(r["raw_difference_A_minus_B"]),
                         "标准化差异(pp)": pp(r["standardized_difference_A_minus_B"]),
                         "状态": "未测量" if r["status"] == "unmeasured_D10" else "支持受限",
                         "口径/限制": "NA 不等于 0" if r["status"] == "unmeasured_D10" else "69 格、9 职业大类；B 保留率 22.2%；描述性、非因果"})
    c2 = next(r for r in source if r["comparison"] == "C2_develop")
    rows.append({"既定比较": "C2 开发：生成式AI vs 传统软件", "经验维度": "全部",
                 "共同支持 A/B": f"{n(c2['retained_A'])} / {n(c2['retained_B'])}",
                 "原始差异(pp)": "NA", "标准化差异(pp)": "NA", "状态": "取消报告",
                 "口径/限制": "仅 2 个职业大类，低于冻结门槛 5；不构造第二比较"})
    write_csv("T5_fixed_comparisons.csv", list(rows[0]), rows)


def build_t6() -> None:
    source = read_csv(INPUTS[11])
    family = {"main": "主规格", "s1_required_only": "S1 测量规则", "s1_broad_cooccurrence": "S1 测量规则",
              "s2_same_company_occupation": "S2 支持/时间窗", "s2_include_2016_2017": "S2 支持/时间窗",
              "s3_single_quarter_closed": "S3 时间风险", "s3_exclude_cross_2022_11_30": "S3 时间风险"}
    labels = {"main": "主规格", "s1_required_only": "仅 required", "s1_broad_cooccurrence": "宽口径共现",
              "s2_same_company_occupation": "同公司×职业", "s2_include_2016_2017": "纳入 2016–2017",
              "s3_single_quarter_closed": "单季度且已关闭", "s3_exclude_cross_2022_11_30": "排除跨 2022-11-30"}
    all_c1 = [r for r in source if r["comparison"] == "C1_use"]
    variants = [r["analysis_variant"] for r in all_c1 if r["experience_object"] == "general_work"]
    rows = []
    for variant in variants:
        by_obj = {r["experience_object"]: r for r in all_c1 if r["analysis_variant"] == variant}
        r = by_obj["general_work"]
        note = "支持受限；描述性"
        if variant in ("s2_include_2016_2017", "s3_exclude_cross_2022_11_30"):
            note += "；共同支持与主规格不变，不算新增独立对照"
        rows.append({"敏感性家族": family[variant], "规格": labels[variant],
                     "共同支持 A/B": f"{n(r['retained_A'])} / {n(r['retained_B'])}",
                     "一般经验标准化(pp)": pp(by_obj["general_work"]["standardized_difference_A_minus_B"]),
                     "领域经验标准化(pp)": pp(by_obj["industry_domain"]["standardized_difference_A_minus_B"]),
                     "工具经验标准化(pp)": pp(by_obj["specific_tool"]["standardized_difference_A_minus_B"]),
                     "支持格/职业大类": f"{r['support_cells']} / {r['support_occupation_majors']}",
                     "结论状态/限制": note + "；职业/任务经验 NA"})
    ranges = {}
    for obj in ("general_work", "industry_domain", "specific_tool"):
        vals = [float(r["standardized_difference_A_minus_B"]) for r in all_c1 if r["experience_object"] == obj]
        ranges[obj] = f"{100*min(vals):+.3f}–{100*max(vals):+.3f}"
    rows.append({"敏感性家族": "结论状态", "规格": "全部 7 规格范围", "共同支持 A/B": "随规格变化",
                 "一般经验标准化(pp)": ranges["general_work"],
                 "领域经验标准化(pp)": ranges["industry_domain"],
                 "工具经验标准化(pp)": ranges["specific_tool"],
                 "支持格/职业大类": "51–69 / 8–9",
                 "结论状态/限制": "一般经验方向一致；领域/工具对规则或支持敏感；D27 拒绝语义构念验证，不能作因果或正式构念结论"})
    write_csv("T6_sensitivity_families.csv", list(rows[0]), rows)


def markdown() -> None:
    sections = [
        ("T1 覆盖与漏斗", "T1_coverage_funnel.csv"),
        ("T2 四类经验及年限形态", "T2_experience_dimensions.csv"),
        ("T3 技术角色、经验共现与技术重叠", "T3_technology_candidates.csv"),
        ("T4 首次观察队列、跨期风险与年度诊断", "T4_time_and_annual_diagnostics.csv"),
        ("T5 冻结比较", "T5_fixed_comparisons.csv"),
        ("T6 三类敏感性", "T6_sensitivity_families.csv"),
    ]
    out = ["# T1–T6 冻结结果六表", "", "仅重排冻结聚合结果；未扫描原始正文、未新增标签、回归或远程任务。", ""]
    for title, name in sections:
        rows = read_csv(HERE / name)
        fields = list(rows[0])
        out += [f"## {title}", "", "| " + " | ".join(fields) + " |",
                "| " + " | ".join(["---"] * len(fields)) + " |"]
        for r in rows:
            out.append("| " + " | ".join(str(r[f]).replace("|", "\\|") for f in fields) + " |")
        out += [""]
    out += ["## 统一解释边界", "",
            "T2–T3 与 T5–T6 是旧字面规则的操作性命中结果。D27 不支持把它们提升为已验证的语义构念；职业/任务经验为 NA。所有比较均为描述性结果，不做显著性、因果、录用或劳动供给推断。CREATED 是交付系统首次观察时间，不是正文版本、生效或修改时间。", ""]
    (HERE / "SIX_TABLES.md").write_text("\n".join(out), encoding="utf-8")


def receipt() -> None:
    rows = []
    for path in INPUTS:
        rows.append({"input_path": str(path.relative_to(PROJECT)),
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                     "bytes": path.stat().st_size})
    write_csv("INPUT_SHA256_RECEIPT.csv", ["input_path", "sha256", "bytes"], rows)


def main() -> None:
    build_t1(); build_t2(); build_t3(); build_t4(); build_t5(); build_t6()
    markdown(); receipt()


if __name__ == "__main__":
    main()
