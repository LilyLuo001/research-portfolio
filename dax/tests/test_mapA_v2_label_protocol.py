import pathlib
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mapping"))
from mapA_v2_label_protocol import validate_independent_labels  # noqa: E402


def row(**updates):
    value = {
        "onet_task_id": "o1",
        "gdpval_task_id": "g1",
        "split": "development",
        "annotator_1_label": "D",
        "annotator_1_vendor_family": "family-a",
        "annotator_2_label": "D",
        "annotator_2_vendor_family": "family-b",
        "third_label": "",
        "third_vendor_family": "",
        "human_label": "",
        "final_label": "D",
    }
    value.update(updates)
    return value


def test_agreement_passes_without_third_family():
    assert validate_independent_labels([row()]) == {
        "pairs": 1,
        "third_family_escalations": 0,
        "human_resolutions": 0,
    }


def test_disagreement_requires_distinct_third_family():
    with pytest.raises(ValueError, match="third"):
        validate_independent_labels([row(annotator_2_label="F", final_label="U")])
    result = validate_independent_labels(
        [
            row(
                annotator_2_label="F",
                third_label="D",
                third_vendor_family="family-c",
                final_label="D",
            )
        ]
    )
    assert result["third_family_escalations"] == 1


def test_unresolved_df_requires_human_and_locked_split_can_be_forbidden():
    dispute = row(
        annotator_2_label="F",
        third_label="N",
        third_vendor_family="family-c",
        final_label="U",
    )
    with pytest.raises(ValueError, match="human"):
        validate_independent_labels([dispute])
    dispute.update(human_label="F", final_label="F")
    assert validate_independent_labels([dispute])["human_resolutions"] == 1
    with pytest.raises(ValueError, match="split"):
        validate_independent_labels([row(split="locked_test")], allowed_splits={"development", "calibration"})
