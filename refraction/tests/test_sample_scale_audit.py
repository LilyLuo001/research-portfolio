"""Input-contract guard for the sample-scale audit.

The audit's job is to keep amendment v2.2's numbers honest as P1's T1/T2
outputs are revised. That only works if the columns it reads still exist, so
these tests assert the SHAPE of the frozen P1 inputs and the audit's own
derivation logic — never a particular count, which is expected to move.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from refraction import sample_scale_audit as ssa  # noqa: E402

pytestmark = pytest.mark.skipif(
    not ssa.EVENTS.exists(),
    reason="frozen P1 inputs not present in this checkout")


def test_config_reads_the_frozen_thresholds():
    cfg = ssa.load_config()
    # Read from frozen_config, never hardcoded — R3's read-only contract.
    assert cfg["convexp_treated_min"] > 0
    assert cfg["asset_class"] == "equity_US"
    assert cfg["waves_start"] < cfg["waves_end"]


def test_events_input_still_carries_the_columns_the_audit_reads():
    import pandas as pd
    cols = set(pd.read_csv(ssa.EVENTS, nrows=1).columns)
    for c in ("asset_class", "effective_date", "family", "AUM_at_conversion_USD"):
        assert c in cols, "P1 T1 schema changed: %s gone" % c


def test_convexp_input_still_carries_the_columns_the_audit_reads():
    import pandas as pd
    path = next((p for p in ssa.CONVEXP_CANDIDATES if p.exists()), None)
    if path is None:
        pytest.skip("no conv_exposure build present")
    cols = set(pd.read_parquet(path).columns)
    for c in ("cusip", "conv_exp", "wave_id", "effective_date", "pre_etf_ownership"):
        assert c in cols, "P1 T2 schema changed: %s gone" % c


def test_audit_runs_and_derives_its_flags():
    cfg = ssa.load_config()
    ev, cx = ssa.audit_events(cfg), ssa.audit_convexp(cfg)
    assert ev["rows_total"] > 0
    assert ev["equity_US_in_wave_window"] <= ev["equity_US_total"] <= ev["rows_total"]
    if cx["status"] == "OK":
        assert cx["treated_rows"] <= cx["rows_total"]
        assert cx["treated_distinct_waves"] <= cx["distinct_waves"]
        share = cx["largest_wave_share_of_treated"]
        assert share is None or 0 <= share <= 1


def test_stock_key_is_cusip_not_permno():
    # Regression: permno is blank in every row of the free-path build, so
    # keying distinct stocks on it silently reported zero.
    cfg = ssa.load_config()
    cx = ssa.audit_convexp(cfg)
    if cx["status"] != "OK":
        pytest.skip("no conv_exposure build present")
    assert cx["distinct_stocks_cusip"] > 0
    assert "permno_blank_rows" in cx, "permno coverage stays a reported diagnostic"
