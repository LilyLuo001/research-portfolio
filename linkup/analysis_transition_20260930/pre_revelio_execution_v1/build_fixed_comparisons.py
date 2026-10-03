#!/usr/bin/env python3
"""Build frozen descriptive C1/C2 contrasts from a joined semantic narrow table."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

import pyarrow.parquet as pq

VERSION = "fixed_c1_c2_descriptive_v1"
OBJECTS = ("general_work", "occupation_task", "industry_domain", "specific_tool")
MEASURED = tuple(obj for obj in OBJECTS if obj != "occupation_task")
AI_DETECTED = ("tech_generative_ai_detected", "tech_predictive_ai_detected", "tech_unspecified_ai_detected")
CORE_FIELDS = {
    "usable", "CREATED", "OCCUPATION_MAJOR", "CENSUS_REGION",
    "tech_generative_ai_use_explicit", "tech_generative_ai_develop_explicit",
    "tech_traditional_software_use_explicit", "tech_traditional_software_develop_explicit",
    *AI_DETECTED,
    *(f"exp_{obj}_{suffix}" for obj in MEASURED for suffix in ("main", "required", "broad")),
}
S2_FIELDS = {"COMPANY_ID"}
S3_FIELDS = {"OBSERVATION_END", "OBSERVATION_CLOSED", "DATE_COMPLETE", "CROSSES_2022_11_30"}
COMPARISONS = {
    "C1_use": ("tech_generative_ai_use_explicit", "tech_traditional_software_use_explicit"),
    "C2_develop": ("tech_generative_ai_develop_explicit", "tech_traditional_software_develop_explicit"),
}
VARIANTS = (
    ("main", "main", "primary"),
    ("s1_required_only", "required", "primary"),
    ("s1_broad_cooccurrence", "broad", "primary"),
    ("s2_same_company_occupation", "main", "same_company"),
    ("s2_include_2016_2017", "main", "extended"),
    ("s3_single_quarter_closed", "main", "single_quarter"),
    ("s3_exclude_cross_2022_11_30", "main", "exclude_cross"),
)


def atomic_json(path, value):
    path = Path(path); tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n"); os.replace(tmp, path)


def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda:handle.read(1<<20),b""): h.update(block)
    return h.hexdigest()


def as_bool(value):
    if value is True or value is False: return value
    if value is None or value == "": return None
    text = str(value).strip().lower()
    if text in {"1", "true", "yes"}: return True
    if text in {"0", "false", "no"}: return False
    return None


def as_date(value):
    if isinstance(value, datetime): return value.date()
    if isinstance(value, date): return value
    if value is None or str(value).strip() == "": return None
    try: return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError: return None


def parquet_paths(path):
    path = Path(path)
    if path.is_file(): return [path]
    return [p for p in sorted(path.rglob("*.parquet")) if not p.name.endswith(".durations.parquet")]


def fields(path):
    path = Path(path)
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as handle: return set(next(csv.reader(handle)))
    paths = parquet_paths(path)
    if not paths: raise FileNotFoundError("no input parquet files")
    result = set(pq.ParquetFile(paths[0]).schema_arrow.names)
    for item in paths[1:]:
        if set(pq.ParquetFile(item).schema_arrow.names) != result:
            raise RuntimeError("joined narrow parquet schemas differ")
    return result


def iter_rows(path, selected):
    path = Path(path)
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            yield from csv.DictReader(handle)
        return
    for item in parquet_paths(path):
        for batch in pq.ParquetFile(item).iter_batches(columns=sorted(selected), batch_size=65536):
            yield from batch.to_pylist()


def arm(row, comparison):
    ai_role, software_role = COMPARISONS[comparison]
    if as_bool(row.get(ai_role)) is True: return "A"
    no_ai = all(as_bool(row.get(field)) is False for field in AI_DETECTED)
    if as_bool(row.get(software_role)) is True and no_ai: return "B"
    return None


def primary_eligible(row, start=date(2018, 1, 1)):
    created = as_date(row.get("CREATED"))
    return (as_bool(row.get("usable")) is True and created is not None
            and start <= created <= date(2026, 6, 30)
            and bool(str(row.get("OCCUPATION_MAJOR") or "").strip())
            and bool(str(row.get("CENSUS_REGION") or "").strip()))


def cell(row):
    created = as_date(row["CREATED"])
    return (str(row["OCCUPATION_MAJOR"]), str(row["CENSUS_REGION"]), created.year)


def prepare(row):
    created=as_date(row.get("CREATED")); occ=str(row.get("OCCUPATION_MAJOR") or "").strip(); region=str(row.get("CENSUS_REGION") or "").strip()
    usable=as_bool(row.get("usable")) is True
    prepared={"row":row,"created":created,"occupation":occ,"region":region,
              "primary":usable and created is not None and date(2018,1,1)<=created<=date(2026,6,30) and bool(occ) and bool(region),
              "extended":usable and created is not None and date(2016,1,1)<=created<=date(2026,6,30) and bool(occ) and bool(region)}
    prepared["cell"]=(occ,region,created.year) if created and occ and region else None
    prepared["arms"]={comparison:arm(row,comparison) for comparison in COMPARISONS}
    return prepared


def variant_eligible(prepared, kind, comparison, pair_support):
    row=prepared["row"]
    if not (prepared["extended"] if kind=="extended" else prepared["primary"]): return False
    if kind == "same_company":
        company = str(row.get("COMPANY_ID") or "").strip()
        return bool(company) and (comparison, company, str(row["OCCUPATION_MAJOR"])) in pair_support
    if kind == "single_quarter":
        created, end = as_date(row.get("CREATED")), as_date(row.get("OBSERVATION_END"))
        return (as_bool(row.get("DATE_COMPLETE")) is True and as_bool(row.get("OBSERVATION_CLOSED")) is True
                and created is not None and end is not None and end >= created
                and (created.year, (created.month - 1)//3) == (end.year, (end.month - 1)//3))
    if kind == "exclude_cross":
        return as_bool(row.get("CROSSES_2022_11_30")) is False
    return True


def blank_aggregates():
    return {comparison: {arm_name: defaultdict(lambda: {"n": 0, "valid":Counter(), "unknown":Counter(), "out":Counter()})
                         for arm_name in ("A", "B")} for comparison in COMPARISONS}


def add(aggregates, comparison, group, prepared, measure):
    bucket = aggregates[comparison][group][prepared["cell"]]; bucket["n"] += 1; row=prepared["row"]
    for obj in MEASURED:
        value=as_bool(row.get(f"exp_{obj}_{measure}"))
        if value is None: bucket["unknown"][obj]+=1
        else:
            bucket["valid"][obj]+=1
            bucket["out"][obj]+=int(value)


def evaluate(aggregates, comparison, measure, variant):
    by_arm = aggregates[comparison]
    cells = set(by_arm["A"]) | set(by_arm["B"])
    support = {x for x in cells if by_arm["A"][x]["n"] >= 20 and by_arm["B"][x]["n"] >= 20}
    full = {g: sum(value["n"] for value in by_arm[g].values()) for g in ("A","B")}
    retained = {g: sum(by_arm[g][x]["n"] for x in support) for g in ("A","B")}
    occupations = len({x[0] for x in support})
    passed = retained["A"] >= 200 and retained["B"] >= 200 and occupations >= 5
    base = {"comparison":comparison,"analysis_variant":variant,"measurement":measure,
            "full_A":full["A"],"full_B":full["B"],"retained_A":retained["A"],"retained_B":retained["B"],
            "retention_A":retained["A"]/full["A"] if full["A"] else None,
            "retention_B":retained["B"]/full["B"] if full["B"] else None,
            "support_cells":len(support),"support_occupation_majors":occupations}
    if not passed:
        return [{**base,"experience_object":obj,"status":"canceled_support","A_numerator":None,"B_numerator":None,
                 "A_raw_proportion":None,"B_raw_proportion":None,"raw_difference_A_minus_B":None,
                 "A_standardized_proportion":None,"B_standardized_proportion":None,"standardized_difference_A_minus_B":None}
                for obj in OBJECTS]
    pooled = sum(by_arm[g][x]["n"] for g in ("A","B") for x in support)
    rows=[]
    for obj in OBJECTS:
        status = "unmeasured_D10" if obj == "occupation_task" else "complete"
        if obj != "occupation_task" and (retained["A"]/full["A"] < .7 or retained["B"]/full["B"] < .7):
            status = "limited_retention_below_70_percent"
        if obj == "occupation_task":
            rows.append({**base,"experience_object":obj,"status":status,"A_numerator":None,"B_numerator":None,
                "A_raw_proportion":None,"B_raw_proportion":None,"raw_difference_A_minus_B":None,
                "A_standardized_proportion":None,"B_standardized_proportion":None,"standardized_difference_A_minus_B":None})
            continue
        numerators={g:sum(by_arm[g][x]["out"][obj] for x in support) for g in ("A","B")}
        denominators={g:sum(by_arm[g][x]["valid"][obj] for x in support) for g in ("A","B")}
        unknown={g:sum(by_arm[g][x]["unknown"][obj] for x in support) for g in ("A","B")}
        all_num={g:sum(v["out"][obj] for v in by_arm[g].values()) for g in ("A","B")}
        all_den={g:sum(v["valid"][obj] for v in by_arm[g].values()) for g in ("A","B")}
        all_unknown={g:sum(v["unknown"][obj] for v in by_arm[g].values()) for g in ("A","B")}
        if not denominators["A"] or not denominators["B"] or any(by_arm[g][x]["valid"][obj]==0 for g in ("A","B") for x in support):
            rows.append({**base,"experience_object":obj,"status":"blocked_unknown_boolean_support_cell",
                "A_numerator":numerators["A"],"B_numerator":numerators["B"],"A_measurement_denominator":denominators["A"],"B_measurement_denominator":denominators["B"],
                "A_unknown_boolean":unknown["A"],"B_unknown_boolean":unknown["B"],
                "A_all_classifiable_numerator":all_num["A"],"B_all_classifiable_numerator":all_num["B"],
                "A_all_classifiable_measurement_denominator":all_den["A"],"B_all_classifiable_measurement_denominator":all_den["B"],
                "A_all_classifiable_unknown_boolean":all_unknown["A"],"B_all_classifiable_unknown_boolean":all_unknown["B"],
                "A_raw_proportion":None,"B_raw_proportion":None,"raw_difference_A_minus_B":None,
                "A_standardized_proportion":None,"B_standardized_proportion":None,"standardized_difference_A_minus_B":None,
                "raw_difference_minus_standardized_difference":None}); continue
        raw={g:numerators[g]/denominators[g] for g in ("A","B")}
        all_raw={g:all_num[g]/all_den[g] if all_den[g] else None for g in ("A","B")}
        std={}
        for g in ("A","B"):
            std[g]=sum(((by_arm["A"][x]["n"]+by_arm["B"][x]["n"])/pooled)
                       *(by_arm[g][x]["out"][obj]/by_arm[g][x]["valid"][obj]) for x in support)
        rows.append({**base,"experience_object":obj,"status":status,"A_numerator":numerators["A"],"B_numerator":numerators["B"],
            "A_measurement_denominator":denominators["A"],"B_measurement_denominator":denominators["B"],
            "A_unknown_boolean":unknown["A"],"B_unknown_boolean":unknown["B"],
            "A_all_classifiable_numerator":all_num["A"],"B_all_classifiable_numerator":all_num["B"],
            "A_all_classifiable_measurement_denominator":all_den["A"],"B_all_classifiable_measurement_denominator":all_den["B"],
            "A_all_classifiable_unknown_boolean":all_unknown["A"],"B_all_classifiable_unknown_boolean":all_unknown["B"],
            "A_all_classifiable_raw_proportion":all_raw["A"],"B_all_classifiable_raw_proportion":all_raw["B"],
            "all_classifiable_raw_difference_A_minus_B":all_raw["A"]-all_raw["B"] if all_raw["A"] is not None and all_raw["B"] is not None else None,
            "A_raw_proportion":raw["A"],"B_raw_proportion":raw["B"],"raw_difference_A_minus_B":raw["A"]-raw["B"],
            "A_standardized_proportion":std["A"],"B_standardized_proportion":std["B"],
            "standardized_difference_A_minus_B":std["A"]-std["B"],
            "raw_difference_minus_standardized_difference":(raw["A"]-raw["B"])-(std["A"]-std["B"])})
    return rows


def blocked_rows(variant, reason):
    return [{"comparison":comparison,"analysis_variant":variant,"measurement":"main","experience_object":obj,
             "status":"blocked_missing_columns:"+",".join(sorted(reason))}
            for comparison in COMPARISONS for obj in OBJECTS]


def input_provenance(input_path, join_manifest):
    if join_manifest:
        return {"mode":"join_manifest_sha256","join_manifest":str(join_manifest),"join_manifest_sha256":sha256(join_manifest)}
    paths=[input_path] if Path(input_path).is_file() else parquet_paths(input_path)
    return {"mode":"file_inventory_size_mtime_not_content_hashed","content_hash":"not_computed",
            "files":[{"path":str(path),"size":path.stat().st_size,"mtime_ns":path.stat().st_mtime_ns} for path in paths]}


def main():
    p=argparse.ArgumentParser();p.add_argument("--input",type=Path,required=True);p.add_argument("--output-dir",type=Path,required=True);p.add_argument("--join-manifest",type=Path)
    args=p.parse_args(); available=fields(args.input); missing=CORE_FIELDS-available; args.output_dir.mkdir(parents=True,exist_ok=True)
    if missing:
        atomic_json(args.output_dir/"COMPARISON_RECEIPT.json",{"status":"blocked_required_columns","missing_columns":sorted(missing),"version":VERSION,
            "script_sha256":sha256(Path(__file__)),"input_provenance":input_provenance(args.input,args.join_manifest)})
        raise SystemExit("blocked: missing required columns: "+", ".join(sorted(missing)))
    selected=CORE_FIELDS | (S2_FIELDS & available) | (S3_FIELDS & available)
    pair_arms=defaultdict(set); coverage=Counter()
    for row in iter_rows(args.input, selected):
        prepared=prepare(row)
        if prepared["primary"]:
            coverage["primary_eligible"]+=1
            company=str(row.get("COMPANY_ID") or "").strip()
            if company:
                for comparison in COMPARISONS:
                    group=prepared["arms"][comparison]
                    if group: pair_arms[(comparison,company,str(row["OCCUPATION_MAJOR"]))].add(group)
        else: coverage["outside_or_unusable_or_unmapped"]+=1
    pair_support={key for key,value in pair_arms.items() if value=={"A","B"}}
    aggs={name:blank_aggregates() for name,_,_ in VARIANTS if not (name.startswith("s2_same") and not S2_FIELDS<=available) and not (name.startswith("s3_") and not S3_FIELDS<=available)}
    for row in iter_rows(args.input, selected):
        prepared=prepare(row)
        if not any(prepared["arms"].values()): continue
        for variant,measure,kind in VARIANTS:
            if variant not in aggs: continue
            for comparison in COMPARISONS:
                group=prepared["arms"][comparison]
                if group and variant_eligible(prepared,kind,comparison,pair_support): add(aggs[variant],comparison,group,prepared,measure)
    output=[]
    for variant,measure,kind in VARIANTS:
        needed = S2_FIELDS if kind=="same_company" else (S3_FIELDS if kind in {"single_quarter","exclude_cross"} else set())
        if not needed<=available:
            output += blocked_rows(variant,needed-available); continue
        for comparison in COMPARISONS: output += evaluate(aggs[variant],comparison,measure,variant)
    out=args.output_dir/"FIXED_COMPARISONS.csv"
    fieldnames=[]
    for row in output:
        for key in row:
            if key not in fieldnames: fieldnames.append(key)
    with out.open("w",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=fieldnames);writer.writeheader();writer.writerows(output)
    atomic_json(args.output_dir/"COMPARISON_RECEIPT.json",{"status":"complete_with_possible_blocked_or_canceled_variants",
        "version":VERSION,"input":str(args.input),"input_columns":sorted(available),"coverage":dict(coverage),
        "script_sha256":sha256(Path(__file__)),"input_provenance":input_provenance(args.input,args.join_manifest),
        "same_company_occupation_pairs_with_both_arms":len(pair_support),"rows":len(output),
        "rules":{"primary_window":"2018-01-01 through 2026-06-30 inclusive","cell":"occupation major x Census region x CREATED year",
        "support":"each arm >=20 per cell; retained total each arm >=200; >=5 occupation majors",
        "standardization":"same pooled common-support record distribution q(x) for both arms; raw proportions use valid measured booleans within common support; all-classifiable raw summaries are also reported","retention_boundary":"below 70% => limited",
        "occupation_task":"unmeasured/NA under D10","inference":"none; descriptive counts and proportions"}})


if __name__=="__main__": main()
