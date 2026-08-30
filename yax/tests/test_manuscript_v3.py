from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
V3 = ROOT / "yax" / "manuscript" / "v3"
FROZEN = ROOT / "yax" / "analysis" / "outcomes" / "frozen_v11_corrected_run"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_clean_manuscript_has_no_internal_artifacts() -> None:
    text = (V3 / "YAX_MANUSCRIPT_v3_CLEAN.md").read_text()
    assert "<!-- prov:" not in text
    assert not re.search(r"\[Table[^]]*\]\(", text)
    assert ".csv" not in text.lower()
    assert not re.search(r"\bYAX\b", text)
    assert "repository" not in text.lower()


def test_clean_and_auditable_differ_only_by_provenance() -> None:
    clean = (V3 / "YAX_MANUSCRIPT_v3_CLEAN.md").read_text()
    audit = (V3 / "YAX_MANUSCRIPT_v3_AUDITABLE.md").read_text()
    stripped = re.sub(r"[ \t]*<!--\s*prov:[^>]+-->", "", audit)
    assert clean == stripped


def test_v3_required_deliverables_exist() -> None:
    required = [
        "YAX_MANUSCRIPT_v3_CLEAN.md",
        "YAX_MANUSCRIPT_v3_AUDITABLE.md",
        "YAX_V3_SUPPLEMENTARY_APPENDIX.md",
        "YAX_V3_REFEREE_RESPONSE_MATRIX.md",
        "YAX_REFEREE_REDTEAM_v3.md",
        "MANUSCRIPT_RECEIPT_v3.json",
        "figures/figure2_support_bridge.png",
        "figures/figure3_dynamics_and_pretrends.png",
        "tables/table3c_continuous_vs_headline_support.md",
        "tables/table6b_remote_interaction.md",
        "tables/table7_joint_pretrend.md",
    ]
    assert all((V3 / rel).is_file() for rel in required)


def test_supplementary_tables_are_labelled() -> None:
    for stem in [
        "table2c_validator_source_split",
        "table3c_continuous_vs_headline_support",
        "table6b_remote_interaction",
        "table7_joint_pretrend",
    ]:
        text = (V3 / "tables" / f"{stem}.md").read_text()
        assert "POST-OUTCOME SUPPLEMENTARY" in text
        assert "NOT PART OF CONFIRMATORY YAX v1.1" in text


def test_receipt_preserves_confirmatory_hashes() -> None:
    receipt = json.loads((V3 / "MANUSCRIPT_RECEIPT_v3.json").read_text())
    assert receipt["confirmatory_result_set_altered"] is False
    assert receipt["supplementary_analyses_in_confirmatory_ledger"] is False
    assert receipt["canonical_result_json_sha256"] == _sha256(FROZEN / "FROZEN_RESULTS.json")
    assert receipt["canonical_result_ledger_sha256"] == _sha256(FROZEN / "RESULT_LEDGER.jsonl")
