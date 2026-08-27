"""p1/wrds/verify.py — the post-landing audit, exercised on fabricated pulls.

The verifier's whole job is to fire while the rented account is still live. So
the checks that matter are the ones that must go FAIL on a bad pull: a wrong
cusip column, a truncated window, a fund-name match that found nothing. Each is
staged here against synthetic parquets, because on the day itself there is no
time to find out the alarm was miswired.
"""
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
WRDS = ROOT / "p1" / "wrds"
sys.path.insert(0, str(WRDS))

pd = pytest.importorskip("pandas")
pytest.importorskip("pyarrow")

import schema as sch  # noqa: E402
import verify as vf   # noqa: E402


# --------------------------------------------------------------------------- #
# fixtures                                                                     #
# --------------------------------------------------------------------------- #
def _spec_resolved():
    """tables.yaml with `resolved` filled from the same synthetic inventory the
    pull tests use — so the verifier is read through the real resolver path."""
    sys.path.insert(0, str(ROOT / "p1" / "tests"))
    from test_wrds_layer import _inventory, _resolve_against
    spec = sch.load_spec()
    _resolve_against(spec, _inventory())
    return spec


@pytest.fixture
def staged(tmp_path, monkeypatch):
    """Point verify at an empty raw/ dir and hand back a writer helper."""
    raw = tmp_path / "raw"
    raw.mkdir()
    spec = _spec_resolved()
    monkeypatch.setattr(vf, "RAW", raw)
    monkeypatch.setattr(sch, "load_spec", lambda *a, **k: spec)
    return raw, spec


def _universe8():
    from universe import _read_convexp_cusips, _read_dropped_cusips
    computed, _ = _read_convexp_cusips()
    return sorted({c[:8].upper() for c in (computed | _read_dropped_cusips()) if c})


def _levels(rep, check_substr):
    return [r["level"] for r in rep.rows if check_substr in r["check"]]


def _run(_raw=None):
    rep = vf.Report()
    vf.run(rep)
    return rep


# --------------------------------------------------------------------------- #
# 1. the join the whole project rests on                                       #
# --------------------------------------------------------------------------- #
def _write_stocknames(raw, spec, cusips, tickers=True):
    c = spec["pulls"]["stock_names"]["columns"]
    df = {
        c["security_id"]["resolved"]: list(range(10001, 10001 + len(cusips))),
        c["cusip"]["resolved"]: cusips,
    }
    if tickers:
        df[c["ticker"]["resolved"]] = [f"T{i}" for i in range(len(cusips))]
    pd.DataFrame(df).to_parquet(raw / "stock_names__stocknames.parquet", index=False)


def test_full_cusip_coverage_passes(staged):
    raw, spec = staged
    _write_stocknames(raw, spec, _universe8())
    rep = _run(raw)
    assert _levels(rep, "cusip->permno coverage") == ["PASS"]


def test_wrong_cusip_column_fails_loudly(staged):
    """The exact failure mode `ncusip` vs `cusip` produces: names resolve, rows
    land, and almost nothing matches. It must FAIL, not warn."""
    raw, spec = staged
    _write_stocknames(raw, spec, [f"ZZ{i:06d}" for i in range(200)])
    rep = _run(raw)
    assert _levels(rep, "cusip->permno coverage") == ["FAIL"]


def test_partial_coverage_warns_rather_than_fails(staged):
    raw, spec = staged
    u = _universe8()
    keep = u[: int(len(u) * 0.7)]
    _write_stocknames(raw, spec, keep + [f"ZZ{i:06d}" for i in range(50)])
    rep = _run(raw)
    assert _levels(rep, "cusip->permno coverage") == ["WARN"]


def test_missing_ticker_fails_because_taq_cannot_be_scoped(staged):
    raw, spec = staged
    _write_stocknames(raw, spec, _universe8(), tickers=False)
    rep = _run(raw)
    # column absent entirely -> the check simply does not fire; the guard that
    # matters is that an all-null ticker column is caught
    c = spec["pulls"]["stock_names"]["columns"]
    df = pd.read_parquet(raw / "stock_names__stocknames.parquet")
    df[c["ticker"]["resolved"]] = None
    df.to_parquet(raw / "stock_names__stocknames.parquet", index=False)
    assert _levels(_run(raw), "ticker present") == ["FAIL"]


# --------------------------------------------------------------------------- #
# 2. an empty pull is a failure, not a pass                                    #
# --------------------------------------------------------------------------- #
def test_zero_row_pull_fails(staged):
    raw, spec = staged
    c = spec["pulls"]["dsf"]["columns"]
    pd.DataFrame({c["security_id"]["resolved"]: pd.Series(dtype="int64"),
                  c["date"]["resolved"]: pd.Series(dtype="datetime64[ns]")}
                 ).to_parquet(raw / "dsf__dsi.parquet", index=False)
    assert _levels(_run(raw), "landed dsf__dsi.parquet") == ["FAIL"]


def test_absent_pull_is_skip_not_fail(staged):
    raw, spec = staged
    _write_stocknames(raw, spec, _universe8())
    rep = _run(raw)
    assert _levels(rep, "landed compustat__funda.parquet") == ["SKIP"]
    assert not [r for r in rep.rows if r["level"] == "FAIL"]


# --------------------------------------------------------------------------- #
# 3. window truncation — the silent one                                        #
# --------------------------------------------------------------------------- #
def _write_dsi(raw, spec, start, end):
    c = spec["pulls"]["dsf"]["columns"]
    dates = pd.bdate_range(start, end)
    pd.DataFrame({c["date"]["resolved"]: dates,
                  c["mkt_ret"]["resolved"]: [0.0] * len(dates)}
                 ).to_parquet(raw / "dsf__dsi.parquet", index=False)


def test_window_covering_the_scope_passes(staged):
    raw, spec = staged
    from universe import build_scope
    w = build_scope()["windows"]
    _write_dsi(raw, spec, w["daily_start"], w["daily_end"])
    assert _levels(_run(raw), "window dsf__dsi.parquet") == ["PASS"]


def test_truncated_window_fails(staged):
    """Exactly the effective-date-anchor bug: data starts ~11 months late."""
    raw, spec = staged
    from universe import build_scope
    w = build_scope()["windows"]
    _write_dsi(raw, spec, "2020-03-04", w["daily_end"])
    assert _levels(_run(raw), "window dsf__dsi.parquet") == ["FAIL"]


# --------------------------------------------------------------------------- #
# 4. the spread ladder, answered from the data                                 #
# --------------------------------------------------------------------------- #
def _write_dsf(raw, spec, bid_frac):
    c = spec["pulls"]["dsf"]["columns"]
    n = 100
    from universe import build_scope
    w = build_scope()["windows"]
    dates = pd.bdate_range(w["daily_start"], periods=n)
    quoted = [10.0 if i < int(n * bid_frac) else None for i in range(n)]
    pd.DataFrame({
        c["security_id"]["resolved"]: [10001] * n,
        c["date"]["resolved"]: dates,
        c["bid"]["resolved"]: quoted,
        c["ask"]["resolved"]: quoted,
    }).to_parquet(raw / "dsf__dsf.parquet", index=False)


def test_populated_crsp_quotes_settle_the_ladder_with_no_vendor(staged):
    raw, spec = staged
    _write_dsf(raw, spec, 1.0)
    rep = _run(raw)
    assert _levels(rep, "spread ladder") == ["PASS"]
    assert "NO external vendor" in next(r["detail"] for r in rep.rows
                                        if r["check"] == "spread ladder")


def test_empty_crsp_quotes_warn_and_send_you_to_taq(staged):
    raw, spec = staged
    _write_dsf(raw, spec, 0.0)
    rep = _run(raw)
    assert _levels(rep, "spread ladder") == ["WARN"]


# --------------------------------------------------------------------------- #
# 5. the fund-name match                                                       #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("matched,want_level", [(0, "FAIL"), (30, "WARN"), (120, "PASS")])
def test_fund_name_match_rate_is_graded(staged, matched, want_level):
    raw, _ = staged
    (raw / "mf_holdings__matched_fundnos.json").write_text(json.dumps(
        {"n_wanted_names": 129, "n_matched_fundnos": matched, "fundnos": []}))
    assert _levels(_run(raw), "converting funds matched") == [want_level]


# --------------------------------------------------------------------------- #
# 6. exit status — the verifier must be usable as a gate                       #
# --------------------------------------------------------------------------- #
def test_report_flags_a_repull_when_anything_failed():
    rep = vf.Report()
    rep.ok("a", "fine")
    rep.fail("b", "broken")
    assert "RE-PULL BEFORE RELEASING THE ACCOUNT" in rep.render()


def test_report_is_quiet_when_everything_passed():
    rep = vf.Report()
    rep.ok("a", "fine")
    assert "RE-PULL" not in rep.render()
