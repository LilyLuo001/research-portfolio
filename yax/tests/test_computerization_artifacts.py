import csv
import hashlib
import json
import math
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
MEASURES = ROOT / "measurement" / "COMPUTERIZATION_MEASURES.csv"
MEASURE_RECEIPT = ROOT / "measurement" / "COMPUTERIZATION_MEASURES_RECEIPT.json"
SUPPORT_RECEIPT = ROOT / "measurement" / "computerization_support_receipt.json"
WEBB = ROOT / "measurement" / "sources" / "exposure_by_occ1990dd_lswt2010.xls"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_measure_artifact_and_source_hashes_match_receipt():
    receipt = json.loads(MEASURE_RECEIPT.read_text())
    assert receipt["status"] == "PASS"
    assert receipt["post_event_outcomes_opened"] is False
    assert receipt["output"]["rows"] == 522
    assert receipt["output"]["sha256"] == sha256(MEASURES)
    assert receipt["inputs"]["webb"]["sha256"] == sha256(WEBB)
    assert receipt["onet"]["element_id"] == "4.A.3.b.1"
    assert receipt["onet"]["official_element_name"] == "Interacting With Computers"
    assert receipt["onet"]["source_rows_for_element"] == 1936
    assert receipt["frey_osborne"]["appendix_rows"] == 702


def test_measure_table_contains_all_frozen_controls():
    rows = list(csv.DictReader(MEASURES.open(newline="")))
    expected = {
        "webb_pct_software", "onet_computers_importance",
        "onet_computers_level", "rti_autor_dorn",
        "frey_osborne_probability",
    }
    assert len(rows) == 522
    assert expected <= set(rows[0])
    assert all(sum(bool(row[name]) for row in rows) > 400 for name in expected)


def test_support_receipt_is_preperiod_real_measure_diagnostic():
    receipt = json.loads(SUPPORT_RECEIPT.read_text())
    assert receipt["status"] == "PASS_REAL_COMPUTERIZATION_MEASURES"
    assert receipt["post_event_outcomes_opened"] is False
    assert "proxy_warning" not in receipt
    support = receipt["preperiod_support"]
    assert support["last_month"] == "2022-11-01"
    assert support["excluded_post_months"] == [
        "2022-12-01", "2023-01-01", "2023-02-01"
    ]
    assert receipt["execution_correction"]["discarded_initial_support_run"] is True

    required = {
        "correlation", "partial_variance_of_ai", "vif", "se_inflation",
        "effective_number_identifying_ai", "common_support_employment_share",
        "residual_variation_by_soc_major_group", "named_divergence_occupations",
    }
    assert len(receipt["pairs"]) == 30
    for pair in receipt["pairs"]:
        assert required <= set(pair)
        assert math.isclose(pair["vif"], 1 / pair["partial_variance_of_ai"])


def test_all_three_unscored_webb_occupations_are_named_and_weighted():
    receipt = json.loads(SUPPORT_RECEIPT.read_text())
    missing = receipt["webb_unscored_occupations"]
    assert {row["occ1990dd"] for row in missing} == {285, 349, 415}
    assert all(row["occupation"] for row in missing)
    assert math.isclose(
        sum(row["preperiod_employment_weight"] for row in missing),
        receipt["webb_unscored_combined_preperiod_employment_weight"],
    )
