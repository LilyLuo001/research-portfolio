import json
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent


def test_retained_metadata_counts_and_unknowns():
    subprocess.run([sys.executable, str(HERE / "build_joint_support.py")], check=True)
    result = json.loads((HERE / "STAGED_COUNTS.json").read_text())
    stages = {row["stage"]: row for row in result["stages"]}
    assert stages["candidate_news_records"]["count"] == 32
    assert stages["first_public_clock_certified"]["count"] == 0
    assert stages["candidate_events_with_availability_matched_actual_basket"]["count"] is None
    assert stages["candidate_news_etf_actual_basket_valid_quote_joint_support"]["count"] is None
    assert result["retained_source_metadata"]["archived_holdings_files"] == 149
    assert result["retained_source_metadata"]["nport_record_count_each"].startswith("NOT_INDEPENDENTLY_RECOUNTED")
