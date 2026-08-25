#!/usr/bin/env python3
"""Measurement-only reproduction of EIG Felten crosswalk variants.

This never reads CPS data or estimates outcomes. Paths are SCC-specific and the
script is an ephemeral audit aid, not a production builder.
"""
import argparse
import hashlib
import io
import json
import os
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


REPO = Path(__file__).resolve().parents[3]
WORK = Path(os.environ.get("DAX_CROSSWALK_TMP", "/tmp/dax_crosswalk_gate"))
WORK.mkdir(parents=True, exist_ok=True)
RAW = Path(os.environ.get(
    "DAX_PUBLIC_RAW_ROOT", "/projectnb/econdept/qluo/dax-private/public_raw"
))
BLS = RAW / "bls/soc_2010_to_2018_crosswalk.xlsx"
CENSUS = RAW / "census/2018-occupation-code-list-and-crosswalk.xlsx"
AIOE = REPO / "dax/w2/exposure_gate/AIOE_DataAppendix.xlsx"
ABILITY_25_0 = RAW / "onet_25_0/db_25_0_excel.zip"
ABILITY_25_1 = RAW / "onet_25_1/db_25_1_excel.zip"
OEWS_2018 = RAW / "oews_2018/oesm18nat.zip"
EIG_CODE = RAW / "eig_ai_unemployment/01 Crosswalks.R"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def archive_xlsx(path, member_suffix):
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.endswith(member_suffix)]
        if len(members) != 1:
            raise ValueError(f"expected one {member_suffix} in {path}, found {members}")
        return io.BytesIO(archive.read(members[0]))


def build_soc18_census(xwalk):
    census = pd.read_excel(
        CENSUS, sheet_name="2018 Census Occ Code List", skiprows=4, dtype=str
    ).rename(columns=lambda c: str(c).strip())
    census = census.drop(
        columns=[c for c in census.columns if c.startswith("Unnamed")]
    ).rename(
        columns={
            "2018 Census Title": "title_census_2018",
            "2018 Census Code": "census_2018",
            "2018 SOC Code": "soc_marker",
        }
    )
    census = census.dropna(
        subset=["title_census_2018", "census_2018", "soc_marker"]
    ).copy()
    census = census[
        ~census.title_census_2018.str.contains(":", na=False)
        & census.soc_marker.ne("none")
    ].copy()
    for column in ("title_census_2018", "census_2018", "soc_marker"):
        census[column] = census[column].str.strip()

    full = pd.DataFrame(
        {"soc_2018": sorted(xwalk.soc_2018.dropna().unique())}
    )
    full["trunc_3dig"] = full.soc_2018.str[:4] + "XXX"
    full["trunc_2dig"] = full.soc_2018.str[:5] + "XX"
    full["trunc_1dig"] = full.soc_2018.str[:6] + "X"
    census["marker2"] = census.soc_marker.str.replace(r"0$", "X", regex=True)
    census["marker2"] = census.marker2.replace(
        {
            "25-100X": "25-1XXX",
            "29-900X": "29-90XX",
            "39-100X": "39-10XX",
            "53-100X": "53-1XXX",
        }
    )
    rows = []
    for row in census.itertuples(index=False):
        hits = []
        for column in ("trunc_1dig", "trunc_2dig", "trunc_3dig"):
            hits = full.loc[full[column].eq(row.marker2), "soc_2018"].tolist()
            if hits:
                break
        if not hits:
            hits = [row.soc_marker]
        for soc in hits:
            rows.append(
                {
                    "census_2018": row.census_2018,
                    "title_census_2018": row.title_census_2018,
                    "soc_2018": soc,
                }
            )
    return census, pd.DataFrame(rows).drop_duplicates()


def source_ability(path):
    frame = pd.read_excel(
        archive_xlsx(path, "Abilities.xlsx"), dtype={"O*NET-SOC Code": str}
    )
    frame = frame.loc[
        frame["Scale Name"].eq("Importance"),
        ["O*NET-SOC Code", "Element Name", "Data Value"],
    ].copy()
    frame["soc_2010"] = frame["O*NET-SOC Code"].str[:7]
    frame = (
        frame.groupby(["soc_2010", "Element Name"], as_index=False)["Data Value"]
        .mean()
        .rename(
            columns={"Element Name": "element_id", "Data Value": "mean_importance"}
        )
    )
    grouped = frame.groupby("element_id").mean_importance
    low, high = grouped.transform("min"), grouped.transform("max")
    frame["norm"] = (frame.mean_importance - low + 1e-6) / (high - low + 1e-6)
    frame["weight_2010"] = frame.norm / frame.groupby("soc_2010").norm.transform("sum")
    return frame[["soc_2010", "element_id", "weight_2010"]]


def target_ability(path, soc18_census):
    frame = pd.read_excel(
        archive_xlsx(path, "Abilities.xlsx"), dtype={"O*NET-SOC Code": str}
    )
    frame = frame.loc[
        frame["Scale Name"].eq("Importance"),
        ["O*NET-SOC Code", "Element Name", "Data Value"],
    ].copy()
    frame["soc_2018"] = frame["O*NET-SOC Code"].str[:7]
    frame = frame.merge(soc18_census, on="soc_2018", how="left")
    frame = (
        frame.groupby(["census_2018", "Element Name"], as_index=False)["Data Value"]
        .mean()
        .rename(
            columns={"Element Name": "element_id", "Data Value": "mean_importance"}
        )
    )
    grouped = frame.groupby("element_id").mean_importance
    low, high = grouped.transform("min"), grouped.transform("max")
    frame["norm"] = (frame.mean_importance - low + 1e-6) / (high - low + 1e-6)
    frame["weight_2018"] = frame.norm / frame.groupby("census_2018").norm.transform("sum")
    return frame[["census_2018", "element_id", "weight_2018"]]


def weighted_value(group):
    usable = group.dropna(subset=["AIOE", "tot_emp_2018"])
    if len(usable) and usable["tot_emp_2018"].sum() > 0:
        return np.average(usable.AIOE, weights=usable.tot_emp_2018)
    return np.nan


def target_coverage(year, soc_values):
    archive = RAW / f"oews_{year}/oesm{str(year)[-2:]}nat.zip"
    with zipfile.ZipFile(archive) as zipped:
        member = [
            name
            for name in zipped.namelist()
            if name.endswith(f"national_M{year}_dl.xlsx")
        ][0]
        book = io.BytesIO(zipped.read(member))
    frame = pd.read_excel(book, dtype=str)
    frame.columns = [column.lower() for column in frame.columns]
    group_column = "o_group" if "o_group" in frame else "occ_group"
    frame = frame.loc[
        frame[group_column].str.lower().eq("detailed"), ["occ_code", "tot_emp"]
    ].copy()
    frame["emp"] = pd.to_numeric(
        frame.tot_emp.str.replace(",", "", regex=False), errors="coerce"
    )
    joined = frame.merge(
        soc_values, left_on="occ_code", right_on="soc_2018", how="left"
    )
    total = joined.emp.sum()
    return {
        "detailed_codes": int(len(joined)),
        "employment_total": float(total),
        "admin_resolved_codes": int(joined.admin_equal.notna().sum()),
        "admin_employment_coverage": float(
            joined.loc[joined.admin_equal.notna(), "emp"].sum() / total
        ),
        "source_weighted_resolved_codes": int(joined.source_weighted.notna().sum()),
        "source_weighted_employment_coverage": float(
            joined.loc[joined.source_weighted.notna(), "emp"].sum() / total
        ),
    }


def main():
    xwalk = pd.read_excel(BLS, skiprows=8, dtype=str)
    xwalk.columns = ["soc_2010", "soc_title_2010", "soc_2018", "soc_title_2018"]
    for column in ("soc_2010", "soc_2018"):
        xwalk[column] = xwalk[column].str.strip()
    census, soc18_census = build_soc18_census(xwalk)
    soc10_census = xwalk.merge(soc18_census, on="soc_2018", how="outer")

    ability_source = source_ability(ABILITY_25_0)
    ability_target = target_ability(ABILITY_25_1, soc18_census)
    felten = pd.read_excel(
        AIOE, sheet_name="Appendix A", dtype={"SOC Code": str}
    ).rename(columns={"SOC Code": "soc_2010"})[["soc_2010", "AIOE"]]
    felten = felten.dropna().copy()
    felten.soc_2010 = felten.soc_2010.str.strip()
    activity = pd.read_excel(AIOE, sheet_name="Appendix E")[[
        "O*NET Abilities", "Ability-Level AI Exposure"
    ]].rename(
        columns={
            "O*NET Abilities": "element_id",
            "Ability-Level AI Exposure": "aioe_ability",
        }
    )

    admin = (
        felten.merge(soc10_census, on="soc_2010", how="left")
        .groupby("census_2018", as_index=False).AIOE.mean()
        .rename(columns={"AIOE": "AIOE_admin"})
    )
    sim = felten.merge(ability_source, on="soc_2010", how="left")
    sim["step1"] = sim.AIOE * sim.weight_2010
    sim = sim.merge(soc10_census, on="soc_2010", how="left").merge(
        ability_target, on=["census_2018", "element_id"], how="left"
    )
    sim["step2"] = sim.step1 * sim.weight_2018
    sim = (
        sim.groupby("census_2018", as_index=False)["step2"]
        .sum(min_count=1)
        .rename(columns={"step2": "AIOE_sim"})
    )

    ability_target_for_felten = ability_target.copy()
    ability_target_for_felten["element_id"] = ability_target_for_felten.element_id.replace(
        {"Visual Color Discrimination": "Visual Color Determination"}
    )
    direct = ability_target_for_felten.merge(activity, on="element_id", how="outer")
    direct["product"] = direct.aioe_ability * direct.weight_2018
    direct = (
        direct.groupby("census_2018", as_index=False)["product"]
        .sum(min_count=1)
        .rename(columns={"product": "AIOE_wgt"})
    )

    oews_2018 = pd.read_excel(
        archive_xlsx(OEWS_2018, "national_M2018_dl.xlsx"), dtype=str
    )
    oews_2018.columns = [column.lower() for column in oews_2018.columns]
    oews_2018 = oews_2018.loc[
        oews_2018.occ_group.str.lower().eq("detailed"), ["occ_code", "tot_emp"]
    ].copy()
    oews_2018["tot_emp_2018"] = pd.to_numeric(
        oews_2018.tot_emp.str.replace(",", "", regex=False), errors="coerce"
    )
    oews_2018 = oews_2018.rename(columns={"occ_code": "soc_2010"})[[
        "soc_2010", "tot_emp_2018"
    ]]

    employment_map = (
        felten.merge(soc10_census, on="soc_2010", how="left")
        .merge(oews_2018, on="soc_2010", how="left")[[
            "census_2018", "soc_2010", "AIOE", "tot_emp_2018"
        ]]
        .drop_duplicates(["census_2018", "soc_2010"])
    )
    employment_variant = (
        employment_map.groupby("census_2018")
        .apply(weighted_value)
        .rename("AIOE_oews2018_source_weighted")
        .reset_index()
    )

    variants = (
        admin.merge(sim, on="census_2018", how="outer")
        .merge(direct, on="census_2018", how="outer")
        .merge(employment_variant, on="census_2018", how="outer")
    )
    variant_export = variants.rename(
        columns={
            "AIOE_admin": "aioe_admin_equal",
            "AIOE_wgt": "aioe_ability_direct",
            "AIOE_oews2018_source_weighted": "aioe_oews2018_source_weighted",
        }
    )[[
        "census_2018",
        "aioe_admin_equal",
        "aioe_ability_direct",
        "aioe_oews2018_source_weighted",
    ]].sort_values("census_2018")
    columns = [
        "AIOE_admin", "AIOE_sim", "AIOE_wgt", "AIOE_oews2018_source_weighted"
    ]
    common = variants.dropna(subset=columns)

    soc_map = (
        felten.merge(xwalk, on="soc_2010", how="right")
        .merge(oews_2018, on="soc_2010", how="left")
    )
    soc_admin = (
        soc_map.groupby("soc_2018", as_index=False).AIOE.mean()
        .rename(columns={"AIOE": "admin_equal"})
    )
    soc_employment = (
        soc_map.groupby("soc_2018")
        .apply(weighted_value)
        .rename("source_weighted")
        .reset_index()
    )
    soc_values = soc_admin.merge(soc_employment, on="soc_2018", how="outer")

    # Common-support diagnostics at the target-SOC level, weighted by OEWS 2021.
    target_2021 = pd.read_excel(
        archive_xlsx(RAW / "oews_2021/oesm21nat.zip", "national_M2021_dl.xlsx"),
        dtype=str,
    )
    target_2021.columns = [column.lower() for column in target_2021.columns]
    target_2021 = target_2021.loc[
        target_2021.o_group.str.lower().eq("detailed"),
        ["occ_code", "occ_title", "tot_emp"],
    ].copy()
    target_2021["emp"] = pd.to_numeric(
        target_2021.tot_emp.str.replace(",", "", regex=False), errors="coerce"
    )
    soc_common = target_2021.merge(
        soc_values, left_on="occ_code", right_on="soc_2018", how="left"
    ).dropna(subset=["admin_equal", "source_weighted", "emp"])
    weights = soc_common.emp.to_numpy(float)
    equal = soc_common.admin_equal.to_numpy(float)
    weighted = soc_common.source_weighted.to_numpy(float)
    mean_equal = np.average(equal, weights=weights)
    mean_weighted = np.average(weighted, weights=weights)
    covariance = np.average(
        (equal - mean_equal) * (weighted - mean_weighted), weights=weights
    )
    weighted_corr = covariance / np.sqrt(
        np.average((equal - mean_equal) ** 2, weights=weights)
        * np.average((weighted - mean_weighted) ** 2, weights=weights)
    )
    absolute_difference = np.abs(equal - weighted)
    difference_order = np.argsort(absolute_difference)
    cumulative_weight = np.cumsum(weights[difference_order]) / weights.sum()
    p90_difference = float(
        absolute_difference[difference_order][np.searchsorted(cumulative_weight, 0.90)]
    )

    # The original exact-code merge is the unrepaired baseline.
    raw_codes = set(felten.soc_2010)
    group15 = target_2021[target_2021.occ_code.str.startswith("15-")].copy()
    group15_total = group15.emp.sum()
    group15_baseline = group15.occ_code.isin(raw_codes)
    group15_admin = group15.occ_code.isin(set(soc_admin.dropna().soc_2018))
    group15_weighted = group15.occ_code.isin(set(soc_employment.dropna().soc_2018))

    flagship = []
    for target in ("15-1252", "15-1211", "15-1232", "13-1082"):
        sources = (
            soc_map.loc[
                soc_map.soc_2018.eq(target),
                ["soc_2010", "soc_title_2010", "AIOE", "tot_emp_2018"],
            ]
            .drop_duplicates()
            .sort_values("soc_2010")
        )
        equal_value = soc_admin.loc[soc_admin.soc_2018.eq(target), "admin_equal"]
        weighted = soc_employment.loc[
            soc_employment.soc_2018.eq(target), "source_weighted"
        ]
        flagship.append(
            {
                "soc_2018": target,
                "sources": sources.where(pd.notna(sources), None).to_dict("records"),
                "admin_equal": None if equal_value.empty else float(equal_value.iloc[0]),
                "source_weighted": (
                    None if weighted.empty or pd.isna(weighted.iloc[0])
                    else float(weighted.iloc[0])
                ),
            }
        )

    output = {
        "record_version": "dax-crosswalk-input-gate-v1",
        "eig_repository_commit": "a65ce97d9fa6ed931af12fb37321fec363a9c15f",
        "counts": {
            "bls_rows": len(xwalk),
            "bls_source_socs": xwalk.soc_2010.nunique(),
            "bls_target_socs": xwalk.soc_2018.nunique(),
            "census_detailed_codes": census.census_2018.nunique(),
            "soc2018_census_links": len(soc18_census),
            "felten_source_socs": felten.soc_2010.nunique(),
            "onet25_0_source_socs": ability_source.soc_2010.nunique(),
            "onet25_1_target_census": ability_target.census_2018.nunique(),
        },
        "variant_nonmissing_counts": {
            column: int(variants[column].notna().sum()) for column in columns
        },
        "common_support_count": int(len(common)),
        "common_support_correlations": common[columns].corr().to_dict(),
        "common_support_spearman_correlations": common[columns].corr(
            method="spearman"
        ).to_dict(),
        "pairwise_correlations": variants[columns].corr().to_dict(),
        "target_soc2018_counts": {
            "admin_equal": int(soc_values.admin_equal.notna().sum()),
            "source_weighted": int(soc_values.source_weighted.notna().sum()),
            "common": int(
                soc_values[["admin_equal", "source_weighted"]]
                .notna().all(axis=1).sum()
            ),
        },
        "target_oews_coverage": {
            "2021": target_coverage(2021, soc_values),
            "2025": target_coverage(2025, soc_values),
        },
        "target_soc2018_common_support_diagnostics": {
            "occupations": int(len(soc_common)),
            "employment": float(weights.sum()),
            "oews2021_employment_weighted_pearson_admin_vs_source_weighted": float(
                weighted_corr
            ),
            "employment_weighted_mean_absolute_native_difference": float(
                np.average(absolute_difference, weights=weights)
            ),
            "employment_weighted_p90_absolute_native_difference": p90_difference,
            "maximum_absolute_native_difference": float(absolute_difference.max()),
        },
        "soc_major_group_15_coverage": {
            "oews2021_detailed_codes": int(len(group15)),
            "oews2021_employment": float(group15_total),
            "exact_code_baseline_codes": int(group15_baseline.sum()),
            "exact_code_baseline_employment_coverage": float(
                group15.loc[group15_baseline, "emp"].sum() / group15_total
            ),
            "admin_repaired_codes": int(group15_admin.sum()),
            "admin_repaired_employment_coverage": float(
                group15.loc[group15_admin, "emp"].sum() / group15_total
            ),
            "source_weighted_repaired_codes": int(group15_weighted.sum()),
            "source_weighted_repaired_employment_coverage": float(
                group15.loc[group15_weighted, "emp"].sum() / group15_total
            ),
        },
        "flagship_mappings": flagship,
        "source_weight_note": (
            "May 2018 OEWS source-code employment. BLS 2018 technical notes "
            "identify the release as 2010 SOC; target-vintage OEWS cannot "
            "distinguish source codes after a many-to-one collapse."
        ),
        "eig_variant_note": (
            "AIOE_admin is equal-mean administrative mapping; AIOE_sim is "
            "EIG O*NET bridge; AIOE_wgt is EIG direct ability-level "
            "reconstruction and is the Felten variable used in EIG main "
            "analysis. These are not interchangeable."
        ),
        "sources": {
            "bls_soc_2010_to_2018": {
                "path": str(BLS),
                "url": "https://www.bls.gov/soc/2018/soc_2010_to_2018_crosswalk.xlsx",
                "file_date": "November 2017 (workbook header)",
                "sha256": sha256(BLS),
            },
            "census_2018_occupation_crosswalk": {
                "path": str(CENSUS),
                "url": "https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/2018-occupation-code-list-and-crosswalk.xlsx",
                "file_date": "2019-09-26 (workbook overview)",
                "sha256": sha256(CENSUS),
            },
            "oews_2018": {
                "path": str(OEWS_2018),
                "url": "https://www.bls.gov/oes/special-requests/oesm18nat.zip",
                "taxonomy_locator": "https://www.bls.gov/oes/2018/may/oes_tec.htm",
                "taxonomy_statement": "BLS technical notes identify 810 detailed occupations based on the 2010 SOC system.",
                "sha256": sha256(OEWS_2018),
            },
            "oews_2019": {
                "path": str(RAW / "oews_2019/oesm19nat.zip"),
                "url": "https://www.bls.gov/oes/special-requests/oesm19nat.zip",
                "sha256": sha256(RAW / "oews_2019/oesm19nat.zip"),
            },
            "oews_2021": {
                "path": str(RAW / "oews_2021/oesm21nat.zip"),
                "url": "https://www.bls.gov/oes/special-requests/oesm21nat.zip",
                "sha256": sha256(RAW / "oews_2021/oesm21nat.zip"),
            },
            "oews_2025": {
                "path": str(RAW / "oews_2025/oesm25nat.zip"),
                "url": "https://www.bls.gov/oes/special-requests/oesm25nat.zip",
                "sha256": sha256(RAW / "oews_2025/oesm25nat.zip"),
            },
            "onet_25_0_excel": {
                "path": str(ABILITY_25_0),
                "url": "https://www.onetcenter.org/dl_files/database/db_25_0_excel.zip",
                "sha256": sha256(ABILITY_25_0),
            },
            "onet_25_1_excel": {
                "path": str(ABILITY_25_1),
                "url": "https://www.onetcenter.org/dl_files/database/db_25_1_excel.zip",
                "sha256": sha256(ABILITY_25_1),
            },
            "eig_crosswalk_code": {
                "path": str(EIG_CODE),
                "url": "https://github.com/EIG-Research/AI-unemployment/blob/a65ce97d9fa6ed931af12fb37321fec363a9c15f/code/01%20Crosswalks.R",
                "sha256": sha256(EIG_CODE),
            },
            "aioe": {
                "path": str(AIOE),
                "url": "https://github.com/AIOE-Data/AIOE",
                "sha256": sha256(AIOE),
            },
        },
    }
    path = Path(os.environ.get(
        "DAX_CROSSWALK_OUTPUT",
        str(Path(__file__).with_name("CROSSWALK_GATE_RESULTS.json")),
    ))
    path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    variant_path = Path(os.environ.get(
        "DAX_CENSUS2018_VARIANT_OUTPUT",
        str(Path(__file__).with_name("CENSUS2018_EXPOSURE_VARIANTS.csv")),
    ))
    variant_export.to_csv(variant_path, index=False, float_format="%.12g")
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    main()
