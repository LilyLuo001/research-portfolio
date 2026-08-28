"""The (sponsor, stock) dependence measure, and the guard on the claim it replaces.

Plan §15.3.0 once said sponsor resampling covered 94.9% of the relevant
dependence. That number came from 20/389 TREATED stocks, while the stacked
sample is mostly controls and controls are reused across waves heavily. These
tests pin both halves of the correction: the measure behaves, and the deleted
claim cannot reappear in the plan without someone deleting a test.
"""
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "p1" / "t5_spec" / "measure_dependence.py"
sys.path.insert(0, str(SCRIPT.parent))

import measure_dependence as md  # noqa: E402

PLAN = ROOT / "docs" / "基金转换实验_博士研究计划.md"


def test_selftest_passes():
    r = subprocess.run([sys.executable, str(SCRIPT), "--selftest"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr


def test_treated_only_reuse_understates_the_sample():
    """The exact failure mode of the deleted claim, in four rows.

    Every treated stock sits under one sponsor, so a treated-only audit reports
    zero uncovered dependence — while half the estimation rows are controls
    reused across two sponsors.
    """
    rows = [
        {"stock": "A", "sponsor": "S1", "wave": "W1", "treated": True},
        {"stock": "B", "sponsor": "S2", "wave": "W2", "treated": True},
        {"stock": "C", "sponsor": "S1", "wave": "W1", "treated": False},
        {"stock": "C", "sponsor": "S2", "wave": "W2", "treated": False},
    ]
    p = md.dependence_profile(rows)
    assert p["treated"]["cross_sponsor_row_share"] == 0.0
    assert p["all"]["cross_sponsor_row_share"] == 0.5
    assert p["stocks_nest_in_sponsors"] is False


def test_row_share_not_stock_share_is_the_headline_number():
    """One heavily reused stock among many singletons: the two shares differ, and
    the row share is the one a standard error is about."""
    rows = [{"stock": f"S{i}", "sponsor": "S1", "wave": "W1", "treated": False}
            for i in range(9)]
    rows += [{"stock": "X", "sponsor": s, "wave": w, "treated": False}
             for s, w in [("S1", "W1"), ("S2", "W2"), ("S3", "W3")]]
    p = md.dependence_profile(rows)["all"]
    assert p["cross_sponsor_stocks"] == 1
    assert p["cross_sponsor_stock_share"] == pytest.approx(0.1)
    assert p["cross_sponsor_row_share"] == pytest.approx(0.25)
    assert p["max_sponsors_per_stock"] == 3


def test_empty_sample_reports_none_not_zero():
    """A zero here would read as 'no dependence'; there is simply no sample."""
    p = md.dependence_profile([])
    assert p["all"]["cross_sponsor_row_share"] is None
    assert p["verdict"] == "empty sample"


def test_blocked_without_a_sample_and_refuses_to_sniff_columns(tmp_path):
    r = subprocess.run([sys.executable, str(SCRIPT)],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 2 and "BLOCKED" in r.stdout
    assert "crosswalk" in r.stdout                    # names the other blocker

    f = tmp_path / "sample.csv"
    f.write_text("permno,sponsor,wave_id,treated\n1,S1,W1,1\n")
    r = subprocess.run([sys.executable, str(SCRIPT), "--sample", str(f)],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode != 0 and "NEED_HUMAN" in (r.stdout + r.stderr)


def test_end_to_end_on_a_csv(tmp_path):
    f = tmp_path / "sample.csv"
    f.write_text("permno,sponsor,wave_id,treated\n"
                 "10,S1,W1,1\n20,S2,W2,1\n30,S1,W1,0\n30,S2,W2,0\n")
    out = tmp_path / "dependence_profile.json"
    r = subprocess.run(
        [sys.executable, "-c",
         f"import sys; sys.path.insert(0, {str(SCRIPT.parent)!r});"
         f"import pathlib, measure_dependence as m;"
         f"m.OUT = pathlib.Path({str(out)!r});"
         f"sys.argv = ['x', '--sample', {str(f)!r}, '--stock-col', 'permno',"
         f"'--sponsor-col', 'sponsor', '--wave-col', 'wave_id',"
         f"'--treated-col', 'treated']; m.main()"],
        capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    import json
    prof = json.loads(out.read_text())
    assert prof["all"]["cross_sponsor_row_share"] == 0.5
    assert prof["source"]["stock_col"] == "permno"


# --------------------------------------------------------------------------- #
# the claim must stay deleted                                                  #
# --------------------------------------------------------------------------- #
def test_plan_carries_no_unmeasured_coverage_percentage():
    """94.9% (and its complement 5.1% as a coverage bound) may not be asserted
    until measure_dependence.py has run on the final sample. The strings may
    appear inside the v2.1d note that explains the deletion; they may not appear
    as a live claim."""
    lines = PLAN.read_text().splitlines()
    for i, line in enumerate(lines):
        if "94.9" not in line:
            continue
        near = "\n".join(lines[max(0, i - 8):i + 8])
        assert "v2.1d 删除" in near, (
            "94.9% appears in the plan outside the deletion note: " + line)
    # the deletion note itself must be present, so the history is not lost
    assert any("v2.1d 删除" in l for l in lines)


def test_plan_does_not_present_first_sponsor_only_as_the_inference_fix():
    """first-sponsor-only is a SAMPLE change; it cannot supply standard errors
    for the rows it keeps. It survives as a de-duplication robustness test."""
    text = PLAN.read_text()
    assert "降级为去重稳健性检验" in text
    m = re.search(r"headline 推断 = (.{0,160})", text, re.S)
    assert m and "multiway" in m.group(1), m.group(1) if m else "no headline rule"
