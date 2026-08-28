import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RECEIPT = ROOT / "yax" / "measurement" / "webb_occ1990_feasibility_receipt.json"
SPEC = ROOT / "dax" / "memo" / "power_calcs" / "ipums_ai_telework_extract_v1.json"


def test_webb_occ1990_feasibility_receipt_contract():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    spec = json.loads(SPEC.read_text(encoding="utf-8"))

    assert receipt["status"] == "NEED_HUMAN_EXTRACT_ROUTE"
    assert receipt["outcome_data_opened"] is False
    assert receipt["extract_submitted_or_amended"] is False

    availability = receipt["ipums_occ1990"]
    rows = availability["samples"]
    assert [row["sample"] for row in rows] == sorted(spec["samples"])
    assert len(rows) == availability["requested_sample_count"] == 115
    unavailable = [row["sample"] for row in rows if not row["occ1990_available"]]
    assert unavailable == availability["unavailable_samples"] == ["cps2025_10s"]
    assert availability["available_sample_count"] == 114
    assert availability["api_metadata_endpoint_used"] is None

    webb = receipt["webb_software"]
    assert webb["native_taxonomy"] == "occ1990dd"
    assert webb["computerization_measure"] == "pct_software"
    assert webb["data_row_count"] == webb["unique_occ1990dd_count"] == 341
    assert len(webb["source_file_sha256"]) == 64

    taxonomy = receipt["taxonomy_resolution"]
    assert taxonomy["occ1990dd_equals_ipums_occ1990"] is False
    assert receipt["bridge_coverage_estimate"]["unmapped_observed_cps_occ2010_codes"] == 0
    assert receipt["decision"]["need_human"] is True
    assert receipt["decision"]["action_taken"] == "NONE_PENDING_HUMAN_DECISION"

