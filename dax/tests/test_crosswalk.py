"""Tests for the CPS <-> O*NET-SOC crosswalk builder.

The pure construction logic is tested without any agency file, because those
cannot be fetched from this environment and a builder that is only testable
where the data lives is a builder nobody checks.
"""

import pathlib
import sys

import pytest
import yaml

CROSSWALK = pathlib.Path(__file__).resolve().parents[1] / "w2" / "crosswalk"
sys.path.insert(0, str(CROSSWALK))

from build_crosswalk import (  # noqa: E402
    EQUAL_SPLIT, FIELDS, attach_dose_dispersion, build_edges,
)


def test_weights_sum_to_one_within_each_cps_code():
    rows, _ = build_edges(
        census_edges=[("1000", "15-1252"), ("1000", "15-1211")],
        onet_edges=[("15-1252", "15-1252.00"), ("15-1211", "15-1211.00")],
        soc_employment={"15-1252": 300.0, "15-1211": 100.0},
    )
    assert sum(r["weight"] for r in rows) == pytest.approx(1.0)
    weights = {r["onet_soc"]: r["weight"] for r in rows}
    assert weights["15-1252.00"] == pytest.approx(0.75), "weights are employment shares"


def test_soc_employment_is_split_equally_across_onet_children():
    """OEWS has no O*NET-SOC detail, so the split is an assumption on the row."""
    rows, _ = build_edges(
        census_edges=[("2000", "29-1141")],
        onet_edges=[("29-1141", "29-1141.00"), ("29-1141", "29-1141.01"),
                    ("29-1141", "29-1141.02")],
        soc_employment={"29-1141": 900.0},
    )
    assert len(rows) == 3
    assert all(r["employment"] == pytest.approx(300.0) for r in rows)
    assert all(r["split_rule"] == EQUAL_SPLIT for r in rows), \
        "the assumption must be visible on every row, not in a footnote"


def test_max_crosswalk_weight_is_per_cps_code_and_drives_decision_12():
    rows, diagnostics = build_edges(
        census_edges=[("3000", "11-1011"), ("3000", "11-1021"),
                      ("4000", "13-2011")],
        onet_edges=[("11-1011", "11-1011.00"), ("11-1021", "11-1021.00"),
                    ("13-2011", "13-2011.00")],
        soc_employment={"11-1011": 100.0, "11-1021": 100.0, "13-2011": 500.0},
    )
    by_code = {r["cps_occ"]: r["max_crosswalk_weight"] for r in rows}
    assert by_code["3000"] == pytest.approx(0.5), "evenly split code concentrates at 0.5"
    assert by_code["4000"] == pytest.approx(1.0), "single-target code is fully concentrated"
    assert "3000" not in diagnostics["cps_flagged_low_max_weight"], \
        "the flag is strictly below 0.50, so exactly 0.5 does not trip it"


def test_suppressed_employment_is_never_zero_filled():
    """A SOC missing from OEWS is reported, not silently treated as zero demand."""
    rows, diagnostics = build_edges(
        census_edges=[("5000", "51-9999")],
        onet_edges=[("51-9999", "51-9999.00")],
        soc_employment={},
    )
    assert diagnostics["soc_with_no_employment"] == ["51-9999"]
    assert rows[0]["coverage_status"] == "equal_weight_fallback_no_employment"
    assert rows[0]["weight"] == pytest.approx(1.0), \
        "the occupation stays in the panel, but labelled"


def test_soc_without_onet_children_is_dropped_and_reported():
    rows, diagnostics = build_edges(
        census_edges=[("6000", "55-1011")],
        onet_edges=[],
        soc_employment={"55-1011": 10.0},
    )
    assert rows == []
    assert diagnostics["soc_with_no_onet_child"] == ["55-1011"], \
        "an unmapped SOC must surface in diagnostics, not vanish"


def test_dose_dispersion_is_weighted_and_only_filled_when_computable():
    rows, _ = build_edges(
        census_edges=[("7000", "15-1252"), ("7000", "15-1211")],
        onet_edges=[("15-1252", "15-1252.00"), ("15-1211", "15-1211.00")],
        soc_employment={"15-1252": 100.0, "15-1211": 100.0},
    )
    assert all(r["dose_sd_within_cps"] == "" for r in rows), \
        "blank until W3 doses exist — blank means not computable, not zero"

    filled = attach_dose_dispersion(rows, {"15-1252.00": 0.30, "15-1211.00": 0.10})
    assert filled == 2
    # equal weights, doses 0.30 and 0.10 -> mean 0.20, sd 0.10
    assert float(rows[0]["dose_sd_within_cps"]) == pytest.approx(0.10)


def test_single_target_code_has_no_defined_dispersion():
    rows, _ = build_edges(
        census_edges=[("8000", "13-2011")],
        onet_edges=[("13-2011", "13-2011.00")],
        soc_employment={"13-2011": 50.0},
    )
    attach_dose_dispersion(rows, {"13-2011.00": 0.4})
    assert rows[0]["dose_sd_within_cps"] == "", \
        "one target has no within-code dispersion; it must not read as 0.0"


def test_emitted_fields_match_the_frozen_contract():
    contract = yaml.safe_load(
        (pathlib.Path(__file__).resolve().parents[2]
         / "ops" / "contracts" / "cps_onet_crosswalk.yaml").read_text())
    assert set(FIELDS) == set(contract["columns"]), "meta-rule 3: schema is frozen"
    for key in contract["primary_key"]:
        assert key in FIELDS


def test_edges_are_unique_on_the_primary_key():
    rows, _ = build_edges(
        census_edges=[("9000", "15-1252"), ("9000", "15-1252")],   # duplicated input
        onet_edges=[("15-1252", "15-1252.00"), ("15-1252", "15-1252.00")],
        soc_employment={"15-1252": 100.0},
    )
    keys = [(r["cps_occ"], r["onet_soc"]) for r in rows]
    assert len(keys) == len(set(keys)), \
        "duplicate source rows must not produce duplicate edges"
