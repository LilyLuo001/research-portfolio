import importlib.util
import hashlib
import json
import pathlib
import re

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "memo" / "power_calcs" / "ipums_extract.py"
SPEC = importlib.util.spec_from_file_location("ipums_extract", MODULE_PATH)
assert SPEC and SPEC.loader
IPUMS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(IPUMS)
FROZEN_SPEC = ROOT / "memo" / "power_calcs" / "ipums_preperiod_extract_v1.json"
WIDE_SPEC = ROOT / "memo" / "power_calcs" / "ipums_ai_telework_extract_v2.json"
WIDE_RECEIPT = (
    ROOT / "memo" / "power_calcs" / "ipums_ai_telework_extract_v2_submission_receipt.json"
)
WIDE_DOWNLOAD_RECEIPT = (
    ROOT / "memo" / "power_calcs" / "ipums_ai_telework_extract_v2_download_receipt.json"
)
WIDE_STRUCTURAL_RECEIPT = (
    ROOT
    / "memo"
    / "power_calcs"
    / "ipums_ai_telework_extract_v2_structural_validation_receipt.json"
)


def test_frozen_spec_is_pre_event_only():
    spec = json.loads(FROZEN_SPEC.read_text(encoding="utf-8"))
    IPUMS.validate_spec(spec)
    assert len(spec["samples"]) == 16


def test_post_event_sample_is_rejected():
    spec = json.loads(FROZEN_SPEC.read_text(encoding="utf-8"))
    spec["samples"]["cps2023_03b"] = {}
    with pytest.raises(ValueError, match="post-event sample prohibited"):
        IPUMS.validate_spec(spec)


def test_missing_preperiod_month_is_rejected():
    spec = json.loads(FROZEN_SPEC.read_text(encoding="utf-8"))
    del spec["samples"]["cps2022_06s"]
    with pytest.raises(ValueError, match="exactly 2021-11 through 2023-02"):
        IPUMS.validate_spec(spec)


def test_wide_spec_matches_superseding_submission_receipt():
    spec_bytes = WIDE_SPEC.read_bytes()
    spec = json.loads(spec_bytes)
    receipt = json.loads(WIDE_RECEIPT.read_text(encoding="utf-8"))

    assert hashlib.sha256(spec_bytes).hexdigest() == receipt["submitted_spec_sha256"]
    assert receipt["status"] == "IPUMS_WIDE_EXTRACT_SUPERSEDING_SUBMITTED"
    assert receipt["supersedes_extract"] == 8
    assert receipt["do_not_analyze_extract"] == 8
    assert receipt["extract_number"] == 9
    assert receipt["sample_count"] == len(spec["samples"]) == 114
    assert receipt["variable_count"] == len(spec["variables"]) == 32


def test_wide_spec_has_exact_month_coverage_and_no_unavailable_october_2025():
    spec = json.loads(WIDE_SPEC.read_text(encoding="utf-8"))
    pattern = re.compile(r"^cps(\d{4})_(\d{2})[bs]$")
    months = []
    for sample in spec["samples"]:
        match = pattern.fullmatch(sample)
        assert match, sample
        months.append((int(match.group(1)), int(match.group(2))))

    expected = [
        (year, month)
        for year in range(2017, 2027)
        for month in range(1, 13)
        if (2017, 1) <= (year, month) <= (2026, 7)
        and (year, month) != (2025, 10)
    ]
    assert sorted(months) == expected
    assert "cps2025_10s" not in spec["samples"]


def test_wide_spec_has_analysis_and_vintage_audit_variables():
    spec = json.loads(WIDE_SPEC.read_text(encoding="utf-8"))
    variables = set(spec["variables"])
    required = {
        "YEAR", "MONTH", "AGE", "WTFINL", "EMPSTAT", "LABFORCE",
        "OCC", "OCC1990", "OCC2010", "STATEFIP", "IND1990",
        "CLASSWKR", "EDUC", "SCHLCOLL", "CPSIDP", "CPSIDV", "MISH",
        "WKSTAT", "TELWRKHR", "TELWRKPAY", "EARNWT",
    }
    assert required <= variables
    ages = spec["variables"]["AGE"]["caseSelections"]["general"]
    assert ages == [str(age) for age in range(16, 76)]


def test_wide_extract_9_completed_with_matching_download_checksums():
    receipt = json.loads(WIDE_DOWNLOAD_RECEIPT.read_text(encoding="utf-8"))
    assert receipt["extract_number"] == 9
    assert receipt["files"]["data"]["bytes"] == 267021345
    assert receipt["files"]["data"]["sha256"] == (
        "3fe42477e6f2ce401e85123f0e278e758595c1c4071a8743f243a92752db38c9"
    )
    for metadata in receipt["files"].values():
        assert metadata["sha256"] == metadata["expected_sha256"]


def test_wide_extract_9_passed_outcome_blind_structural_validation():
    receipt = json.loads(WIDE_STRUCTURAL_RECEIPT.read_text(encoding="utf-8"))
    assert receipt["status"] == "PASS"
    assert receipt["outcomes_inspected"] is False
    assert receipt["source_sha256"] == (
        "3fe42477e6f2ce401e85123f0e278e758595c1c4071a8743f243a92752db38c9"
    )
    assert receipt["row_count"] == 9262480
    assert receipt["month_count"] == 114
    assert (receipt["first_month"], receipt["last_month"]) == (
        "2017-01", "2026-07"
    )
    assert receipt["october_2025_present"] is False
    assert (receipt["age_min"], receipt["age_max"], receipt["distinct_ages"]) == (
        16, 75, 60
    )
    assert receipt["column_count"] == 39
    assert receipt["errors"] == []
