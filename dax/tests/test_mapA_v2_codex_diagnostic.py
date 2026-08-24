import json
import pathlib
import sys

import pytest

MAPPING = pathlib.Path(__file__).resolve().parents[1] / "mapping"
sys.path.insert(0, str(MAPPING))

from mapA_v2_codex_diagnostic import CATEGORIES, SAMPLE_SIZE, select_diagnostic_rows  # noqa: E402


def rows():
    result = []
    for category in CATEGORIES:
        for split, count in (("development", 20), ("calibration", 12), ("locked_test", 12)):
            for index in range(count):
                result.append({
                    "onet_task_id": f"{category}-{split}-O{index}",
                    "gdpval_task_id": f"{category}-{split}-G{index}",
                    "major_soc_family": f"{index % 22:02d}",
                    "candidate_category": category,
                    "split": split,
                    "relation_label": "",
                })
    return result


def test_selection_is_deterministic_stratified_and_never_uses_locked():
    first = select_diagnostic_rows(rows())
    second = select_diagnostic_rows(reversed(rows()))
    assert first == second
    assert len(first) == SAMPLE_SIZE == 60
    assert {row["split"] for row in first} == {"development", "calibration"}
    for category in CATEGORIES:
        selected = [row for row in first if row["candidate_category"] == category]
        assert sum(row["split"] == "development" for row in selected) == 6
        assert sum(row["split"] == "calibration" for row in selected) == 4


def test_selection_refuses_existing_dev_cal_labels():
    materialized = rows()
    materialized[0]["relation_label"] = "D"
    with pytest.raises(ValueError, match="already labeled"):
        select_diagnostic_rows(materialized)


def test_release_receipts_preserve_diagnostic_only_boundary():
    sampling = json.loads((MAPPING / "mapA_v2_codex_diagnostic_sampling_receipt_20260821.json").read_text())
    result = json.loads((MAPPING / "mapA_v2_codex_diagnostic_result_receipt_20260821.json").read_text())
    assert sampling["sample_pairs"] == result["sample"]["pairs"] == 60
    assert sampling["counts_by_split"] == result["sample"]["splits"] == {
        "calibration": 24,
        "development": 36,
    }
    assert sampling["locked_test_labels_opened"] is result["locked_test_labels_opened"] is False
    assert result["locked_test_rows_read_for_annotation"] == 0
    assert result["independent_multi_vendor_validation"] is False
    assert result["frozen_thresholds_or_methods_changed"] is False
    assert result["incremental_api_spend_usd"] == 0
    assert result["overall"]["label_counts"] == {"D": 0, "F": 24, "N": 36, "U": 0}
    assert "locked_test_pass_fail" in result["formal_metrics_not_claimed"]
