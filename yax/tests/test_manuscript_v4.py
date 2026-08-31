from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
V4 = ROOT / "yax" / "manuscript" / "v4"
SUPP4 = ROOT / "yax" / "analysis" / "postoutcome_v4_supplementary"
FROZEN = ROOT / "yax" / "analysis" / "outcomes" / "frozen_v11_corrected_run"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_v4_required_deliverables_exist() -> None:
    required = [
        "YAX_MANUSCRIPT_v4_CLEAN.md",
        "YAX_MANUSCRIPT_v4_AUDITABLE.md",
        "YAX_V4_SUPPLEMENTARY_APPENDIX.md",
        "YAX_V4_ESTIMAND_ALIGNMENT_AUDIT.md",
        "YAX_V4_REFEREE_RESPONSE_MATRIX.md",
        "YAX_REFEREE_REDTEAM_v4.md",
        "MANUSCRIPT_RECEIPT_v4.json",
        "figures/figure3_categorical_q5_q1_event_study.png",
        "figures/appendix_figure_continuous_event_study.png",
        "tables/table5a_frozen_headline_models.md",
        "tables/table5b_literal_common_support.md",
        "tables/appendix_table5b_native_support.md",
        "tables/table7_categorical_headline_pretrend.md",
    ]
    assert all((V4 / rel).is_file() for rel in required)


def test_clean_manuscript_has_no_internal_or_referee_rhetoric() -> None:
    text = (V4 / "YAX_MANUSCRIPT_v4_CLEAN.md").read_text()
    assert "<!-- prov:" not in text
    assert ".csv" not in text.lower()
    assert not re.search(r"\bYAX\b", text)
    assert "repository" not in text.lower()
    assert "referee-requested" not in text.lower()
    assert "external validator" not in text.lower()
    assert "bootstrap se" not in text.lower()


def test_clean_and_auditable_differ_only_by_provenance() -> None:
    clean = (V4 / "YAX_MANUSCRIPT_v4_CLEAN.md").read_text()
    audit = (V4 / "YAX_MANUSCRIPT_v4_AUDITABLE.md").read_text()
    stripped = re.sub(r"[ \t]*<!--\s*prov:[^>]+-->", "", audit)
    assert clean == stripped


def test_scientific_tables_have_no_bootstrap_se_mislabel() -> None:
    for path in (V4 / "tables").glob("*"):
        if path.suffix in {".csv", ".md"}:
            assert "bootstrap se" not in path.read_text().lower(), path


def test_literal_common_support_is_machine_aligned() -> None:
    audit = pd.read_csv(SUPP4 / "TABLE5B_SUPPORT_AUDIT.csv")
    assert audit["support_hash_sha256"].nunique() > 1
    common = pd.read_csv(SUPP4 / "TABLE5B_COMMON_SUPPORT_RESULTS.csv")
    assert len(common) == 6
    assert common["n_occupations"].eq(444).all()
    assert common["support_hash_sha256"].nunique() == 1
    assert common["coefficient_log_points"].lt(0).all()


def test_categorical_event_study_is_headline_aligned() -> None:
    result = json.loads((SUPP4 / "CATEGORICAL_Q5_Q1_EVENT_STUDY_RESULT.json").read_text())
    assert result["occupations"] == 468
    assert result["q2_q4_monthly_interactions_included"] is True
    assert result["reference_month"] == "2022-10"
    assert result["transition_month"] == "2022-12"
    assert result["pre_coefficients_tested"] == 65
    assert result["simultaneous_pre_intervals_excluding_zero"] == 0


def test_receipt_preserves_confirmatory_hashes_and_authorized_scope() -> None:
    receipt = json.loads((V4 / "MANUSCRIPT_RECEIPT_v4.json").read_text())
    assert receipt["confirmatory_result_set_altered"] is False
    assert receipt["supplementary_analyses_in_confirmatory_ledger"] is False
    assert receipt["canonical_result_json_sha256"] == _sha256(FROZEN / "FROZEN_RESULTS.json")
    assert receipt["canonical_result_ledger_sha256"] == _sha256(FROZEN / "RESULT_LEDGER.jsonl")
    assert receipt["authorized_new_empirical_analyses"] == [
        "literal common-support six-measure comparison",
        "categorical Q5-Q1 event study with joint pretrend inference",
    ]


def test_primary_interpretation_preserves_both_relative_comparisons() -> None:
    text = (V4 / "YAX_MANUSCRIPT_v4_CLEAN.md").read_text()
    sentence = (
        r"the young employment stock evolved 12\.3% less favorably relative to the "
        r"older-worker stock in Q5 than in Q1"
    )
    assert len(re.findall(sentence, text, flags=re.IGNORECASE)) >= 2
    assert "The estimate can reflect movement in the young stock, the older stock, or both" in text
