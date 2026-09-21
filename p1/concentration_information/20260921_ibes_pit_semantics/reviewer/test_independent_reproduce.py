import importlib.util
from pathlib import Path

import pandas as pd


MODULE_PATH = Path(__file__).with_name("independent_reproduce.py")
SPEC = importlib.util.spec_from_file_location("independent_reproduce", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def row(source, ticker="A", period="2023-03-31", ann="2023-01-01", act="2023-01-01", ann_time="09:00:00", act_time="10:00:00"):
    common = {"_source": source, "ticker": ticker, "measure": "EPS", "curr": None, "anndats": ann, "anntims": ann_time, "actdats": act, "acttims": act_time}
    if source == "detail_candidate":
        return {**common, "cusip": None, "analys": "1", "estimator": "E", "fpedats": period, "fpi": "6", "pends": None, "pdicity": None, "usfirm": "1"}
    return {**common, "cusip": None, "analys": None, "estimator": None, "fpedats": None, "fpi": None, "pends": period, "pdicity": "QTR", "usfirm": None}


def test_year_boundary_missing_currency_same_day_and_missing_time():
    frame = pd.DataFrame(
        [
            row("detail_candidate", act="2024-01-01"),
            row("detail_candidate", ticker="B", ann_time=None, act_time=None),
            row("actual", act="2026-03-03"),
        ]
    )
    out = MODULE.audit_projection(frame)
    assert out["detail_candidate"]["filtered"]["activation_after_2023"] == 1
    assert out["actual"]["filtered"]["activation_after_2023"] == 1
    assert out["detail_candidate"]["filtered"]["currency"] == {"<MISSING>": 2}
    assert out["detail_candidate"]["filtered"]["activation_vs_announcement"]["same_date_time_missing_or_unparseable"] == 1
    assert out["actual"]["filtered"]["activation_after_2023_max"] == "2026-03-03"


def test_blank_and_null_keys_do_not_match_and_multi_actual_is_ambiguous():
    frame = pd.DataFrame(
        [
            row("detail_candidate", ticker=" "),
            row("detail_candidate", ticker=None),
            row("detail_candidate", ticker="A"),
            row("actual", ticker="A"),
            row("actual", ticker="A", ann="2023-01-02", act="2023-01-02"),
        ]
    )
    out = MODULE.audit_projection(frame)
    match = out["period_identity_match"]
    assert match["detail_period_identity_unmatchable_missing_or_blank_identity_or_period_records"] == 2
    assert match["detail_period_identity_ambiguous_actual_records"] == 1
    assert match["detail_period_identity_unique_actual_records"] == 0
    assert out["actual"]["period_identity_keys_with_multiple_actual_records"] == 1
    assert out["actual"]["actual_duplicate_key_group_records"] == 0


def test_full_quarterly_fpi_set_and_duplicate_key_is_not_release_uniqueness():
    detail = []
    for code in sorted(MODULE.QUARTERLY_FPI):
        item = row("detail_candidate", ticker=f"T{code}")
        item["fpi"] = code.lower()
        detail.append(item)
    duplicate = row("detail_candidate", ticker="DUP")
    detail.extend([duplicate, duplicate.copy()])
    frame = pd.DataFrame(detail + [row("actual", ticker="NO_MATCH")])
    out = MODULE.audit_projection(frame)
    assert out["detail_candidate"]["filtered_rows"] == len(MODULE.QUARTERLY_FPI) + 2
    assert set(out["detail_candidate"]["fpi_filtered"]) == MODULE.QUARTERLY_FPI
    assert out["detail_candidate"]["candidate_duplicate_key_group_records"] == 2
