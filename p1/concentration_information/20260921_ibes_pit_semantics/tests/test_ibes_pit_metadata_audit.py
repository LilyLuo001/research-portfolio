import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[1] / "code"))
from ibes_pit_metadata_audit import audit_frames


def test_synthetic_period_mismatch_ambiguity_delayed_activation_revisions_and_missing_fields():
    config = {"sources": {"detail_candidate": {"quarterly_fpi_codes": ["6"], "candidate_key": ["ticker", "estimator", "analys", "fpedats", "fpi", "measure", "anndats", "anntims", "actdats", "acttims"]}, "actual": {"actual_key": ["ticker", "pends", "measure", "pdicity", "anndats", "anntims", "actdats", "acttims"]}}}
    detail = pd.DataFrame([{"ticker":"A","estimator":"E","analys":"1","fpedats":"2023-03-31","fpi":"6","pdicity":"QTR","measure":"EPS","anndats":"2023-02-01","anntims":"10:00:00","actdats":"2024-01-02","acttims":"09:00:00"}, {"ticker":"A","estimator":"E","analys":"1","fpedats":"2023-03-31","fpi":"6","pdicity":"QTR","measure":"EPS","anndats":"2023-02-01","anntims":"10:00:00","actdats":"2024-01-02","acttims":"09:00:00"}, {"ticker":"B","estimator":"E2","analys":"2","fpedats":"2023-06-30","fpi":"6","pdicity":"QTR","measure":"EPS","anndats":None,"anntims":None,"actdats":"bad","acttims":None}])
    actual = pd.DataFrame([{"ticker":"A","pends":"2023-03-31","pdicity":"QTR","measure":"EPS","anndats":"2023-04-01","anntims":"09:00:00","actdats":"2023-04-01","acttims":"10:00:00"}, {"ticker":"A","pends":"2023-03-31","pdicity":"QTR","measure":"EPS","anndats":"2023-04-02","anntims":"09:00:00","actdats":"2023-04-01","acttims":"10:00:00"}])
    out = audit_frames(detail, actual, config)
    assert out["detail_candidate"]["records_in_candidate_duplicate_key_groups"] == 2
    assert out["detail_candidate"]["activation_vs_announcement_date_order"]["activation_after_announcement_date"] == 2
    assert out["actual"]["activation_vs_announcement_date_order"]["same_date_activation_after_announcement_raw_time"] == 1
    assert out["actual"]["activation_vs_announcement_date_order"]["activation_before_announcement_date"] == 1
    assert out["period_identity_match"]["detail_period_identity_ambiguous_actual_records"] == 2
    assert out["period_identity_match"]["detail_period_identity_unmatched_records"] == 1


def test_null_identity_or_period_never_cross_matches_and_detail_missing_pdicity_is_recorded():
    config = {"sources": {"detail_candidate": {"quarterly_fpi_codes": ["6"], "candidate_key": ["ticker", "estimator", "analys", "fpedats", "fpi", "measure", "anndats", "anntims", "actdats", "acttims"]}, "actual": {"actual_key": ["ticker", "pends", "measure", "pdicity", "anndats", "anntims", "actdats", "acttims"]}}}
    detail = pd.DataFrame([{"ticker":None,"estimator":"E","analys":"1","fpedats":None,"fpi":"6","measure":"EPS","anndats":"2023-01-01","anntims":"x","actdats":"2023-01-01","acttims":"x"}])
    actual = pd.DataFrame([{"ticker":None,"pends":None,"pdicity":"QTR","measure":"EPS","anndats":"2023-01-01","anntims":None,"actdats":"2023-01-01","acttims":None}])
    out = audit_frames(detail, actual, config)
    assert out["detail_candidate"]["projected_rows"] == 1
    assert "pdicity" not in out["detail_candidate"]["categories_before_filter"]
    assert out["period_identity_match"]["detail_period_identity_unmatchable_missing_identity_or_period_records"] == 1
