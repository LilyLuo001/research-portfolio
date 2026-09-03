"""p1/wrds — offline guards. No `wrds` package, no network, no credentials.

The whole point of this layer is that a WRDS table/column name written from
memory does not raise, it silently returns a different number (CLAUDE.md
meta-rule 1). So the tests that matter are the REFUSALS: unresolved names,
stale names, and pulls attempted out of order must all fail loudly rather than
produce SQL. The happy path is exercised against a synthetic inventory so the
sprint is not the first time these queries are built.
"""
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
WRDS = ROOT / "p1" / "wrds"
sys.path.insert(0, str(WRDS))
sys.path.insert(0, str(ROOT / "ops" / "runner"))

import schema as sch  # noqa: E402


# --------------------------------------------------------------------------- #
# fixtures                                                                     #
# --------------------------------------------------------------------------- #
@pytest.fixture
def spec():
    return sch.load_spec()


def _inventory():
    """A synthetic server inventory. Names here are TEST FIXTURES, not claims
    about WRDS — they exist to prove the plumbing, and every one of them is
    deliberately confirmed through the same code path a real one would be."""
    return sch.Inventory(tables={
        "crsp.holdings":    ["crsp_fundno", "report_dt", "permno", "nbr_shares"],
        "crsp.fund_hdr":    ["crsp_fundno", "ticker", "fund_name"],
        "crsp.portnomap":   ["crsp_fundno", "crsp_portno"],
        "crsp.stocknames":  ["permno", "ncusip", "ticker", "namedt", "nameendt"],
        "crsp.msf":         ["permno", "date", "prc", "ret", "shrout",
                     "cfacshr", "cfacpr"],
        "crsp.dsf":         ["permno", "date", "ret", "prc", "vol", "openprc",
                             "bid", "ask", "bidlo", "askhi",
                             # daily share/price factors + raw shares: Gate 0
                             # joins CFACSHR on the N-PORT repPdDate, and the
                             # monthly file is not known to be precise enough
                             # for every one of those dates (v2.1d).
                             "cfacshr", "cfacpr", "shrout",
                             # PRICE return: the spine-zero beta series, both
                             # legs (D-T3-29). `ret` stays for the daily spines.
                             "retx",
                             # preferred ex-distribution flag for the OpenGap
                             # screen (D-T3-31); optional in the spec
                             "distcd"],
        "crsp.dsi":         ["date", "vwretd"],
        "crsp.dsedelist":   ["permno", "dlstdt", "dlret", "dlstcd"],
        "crsp.ccmxpf_lnkhdr": ["gvkey", "lpermno", "linkdt", "linkenddt",
                               "linktype", "linkprim"],
        "comp.fundq":       ["gvkey", "datadate", "rdq", "epspxq"],
        "comp.funda":       ["gvkey", "datadate", "ceq", "csho", "prcc_f"],
        "wrdsapps.taq_iid": ["sym_root", "date", "ehalfspd", "price_impact"],
        "ibes.statsum_epsus": ["ticker", "cusip", "statpers", "fpedats", "fpi",
                               "meanest", "stdev", "numest"],
        "ibes.act_epsus":     ["ticker", "cusip", "anndats", "pends", "value"],
        "ibes.idsum":         ["ticker", "cusip"],
    })


# Which already-landed raw parquet each pull needs before its SQL can be scoped.
# Mirrors PULL_ORDER's dependency edges; used to fake the landed files offline.
LANDED_DEPS = {
    "msf":        ["stock_names__stocknames.parquet"],
    "dsf":        ["stock_names__stocknames.parquet"],
    "taq_iid":    ["stock_names__stocknames.parquet"],
    "ccm_link":   ["stock_names__stocknames.parquet"],
    "mf_holdings": ["mf_holdings__fund_header.parquet"],
    "compustat":  ["stock_names__stocknames.parquet", "ccm_link__ccm_link.parquet"],
}


def _fake_landings(spec, raw_dir):
    """Write the minimal upstream parquets a downstream pull needs to be scoped.

    Values are fabricated on purpose — the point is to prove the SQL BUILDS and
    is bounded, not to check any number. Real scoping happens on the box.
    """
    import pandas as pd
    import csv as _csv
    sn = spec["pulls"]["stock_names"]["columns"]
    pd.DataFrame({
        sn["security_id"]["resolved"]: [10001, 10002, 10003],
        sn["cusip"]["resolved"]: ["03783310", "88160R10", "45920010"],
        sn["ticker"]["resolved"]: ["AAPL", "TSLA", "IBM"],
    }).to_parquet(raw_dir / "stock_names__stocknames.parquet", index=False)

    cl = spec["pulls"]["ccm_link"]["columns"]
    pd.DataFrame({
        cl["gvkey"]["resolved"]: ["001690", "184996", "006066"],
        cl["link_permno"]["resolved"]: [10001, 10002, 10003],
    }).to_parquet(raw_dir / "ccm_link__ccm_link.parquet", index=False)

    # fund_header must contain names that actually match events_merged.csv, or
    # _landed_fundnos refuses — which is the behaviour a separate test asserts
    with open(ROOT / "p1" / "events_merged.csv", newline="") as f:
        names = [r["fund_name"] for r in _csv.DictReader(f)][:5]
    mh = spec["pulls"]["mf_holdings"]["columns"]
    pd.DataFrame({
        mh["fund_id"]["resolved"]: list(range(1, len(names) + 1)),
        mh["fund_name"]["resolved"]: names,
        mh["fund_ticker"]["resolved"]: ["AAA"] * len(names),
    }).to_parquet(raw_dir / "mf_holdings__fund_header.parquet", index=False)


def _resolve_against(spec, inv):
    """Run the same unique-candidate rule cmd_resolve uses."""
    import pull as pl
    all_tables = set(inv.tables)
    for pull, cfg in spec["pulls"].items():
        for entry in cfg.get("tables", {}).values():
            entry["resolved"] = pl._resolve_one(entry.get("candidates"), all_tables)[0]
        cols = set()
        for e in cfg.get("tables", {}).values():
            if e.get("resolved"):
                cols |= set(inv.tables.get(e["resolved"], []))
        for entry in cfg.get("columns", {}).values():
            entry["resolved"] = pl._resolve_one(entry.get("candidates"), cols)[0]
    return sch.Resolver(spec=spec, inventory=inv)


# --------------------------------------------------------------------------- #
# 1. the shipped config must be inert — nothing resolved, nothing usable       #
# --------------------------------------------------------------------------- #
def test_shipped_config_resolves_nothing(spec):
    """tables.yaml must ship with every `resolved` null. A committed non-null
    value would be a name nobody confirmed against a server."""
    for pull, cfg in spec["pulls"].items():
        for kind in ("tables", "columns"):
            for logical, entry in cfg.get(kind, {}).items():
                assert entry["resolved"] is None, \
                    f"{pull}.{kind}.{logical} ships pre-resolved — unconfirmed name"


def test_status_offline_reports_everything_blocked(spec):
    r = sch.Resolver(spec=spec, inventory=sch.Inventory())
    for pull in spec["pulls"]:
        assert not r.ready(pull)
    text = sch.format_status(r)
    assert "MISSING" in text and "BLOCKED" in text


def test_unresolved_table_refuses_with_guidance(spec):
    r = sch.Resolver(spec=spec, inventory=_inventory())
    with pytest.raises(sch.SchemaRefusal) as e:
        r.table("dsf", "daily_stock")
    msg = str(e.value)
    assert "NEED_HUMAN" in msg and "discover" in msg


def test_stale_name_refuses_loudly(spec):
    """The hallucination case: a plausible name that does not exist."""
    spec["pulls"]["dsf"]["tables"]["daily_stock"]["resolved"] = "crsp.daily_stock_file"
    r = sch.Resolver(spec=spec, inventory=_inventory())
    with pytest.raises(sch.SchemaRefusal) as e:
        r.table("dsf", "daily_stock")
    assert "STALE SCHEMA" in str(e.value)


def test_resolved_but_no_inventory_still_refuses(spec):
    """A resolved name with nothing to confirm it against is not usable."""
    spec["pulls"]["msf"]["tables"]["monthly_stock"]["resolved"] = "crsp.msf"
    r = sch.Resolver(spec=spec, inventory=sch.Inventory())
    with pytest.raises(sch.SchemaRefusal):
        r.table("msf", "monthly_stock")


# --------------------------------------------------------------------------- #
# 2. the resolver refuses to pick when candidates are ambiguous or absent      #
# --------------------------------------------------------------------------- #
def test_resolve_one_semantics():
    import pull as pl
    assert pl._resolve_one(["a", "b"], {"a"})[0] == "a"
    assert pl._resolve_one(["a", "b"], {"a", "b"})[0] is None      # ambiguous
    assert pl._resolve_one(["a"], set())[0] is None                # absent
    assert "ambiguous" in pl._resolve_one(["a", "b"], {"a", "b"})[1]


# --------------------------------------------------------------------------- #
# 3. happy path — queries build, and only from confirmed names                 #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("pull", ["stock_names", "mf_holdings", "msf", "dsf",
                                  "taq_iid", "ccm_link", "compustat", "ibes"])
def test_queries_build_against_a_confirmed_inventory(spec, pull, monkeypatch, tmp_path):
    """Every pull, no skips.

    This used to skip a pull whose names the synthetic inventory did not cover,
    which meant tables added to tables.yaml (delisting, Compustat, the CCM link)
    were silently never exercised — a green suite that proved nothing about them.
    The rental window is the wrong place to discover a query does not build.
    """
    import pull as pl
    pytest.importorskip("pandas")
    r = _resolve_against(spec, _inventory())
    assert r.ready(pull), (
        f"{pull} is not resolvable from the synthetic inventory: "
        f"{r.status()[pull]['unresolved'] + r.status()[pull]['stale']}")
    monkeypatch.setattr(pl, "RAW", tmp_path)
    _fake_landings(spec, tmp_path)
    from universe import build_scope
    qs = pl.build_queries(pull, r, build_scope())
    assert qs
    for name, sql in qs.items():
        assert sql.lower().startswith("select "), name
        assert "None" not in sql, f"an unresolved name leaked into {pull}.{name}"


@pytest.mark.parametrize("pull", ["mf_holdings", "msf", "dsf", "taq_iid",
                                  "ccm_link", "compustat", "ibes"])
def test_every_large_pull_is_bounded(spec, pull, monkeypatch, tmp_path):
    """No pull may be an unbounded table scan.

    comp.funda unscoped is every North American company since 1950; crsp.holdings
    unscoped is every fund's every position every quarter; taq_iid unscoped is
    every listed US name every day. Each of those alone would consume a one-day
    rental. `ibes.idsum` and `crsp.portnomap` are the two deliberate exceptions:
    small reference crosswalks wanted whole (idsum is still cusip-filtered).
    """
    import pull as pl
    pytest.importorskip("pandas")
    r = _resolve_against(spec, _inventory())
    monkeypatch.setattr(pl, "RAW", tmp_path)
    _fake_landings(spec, tmp_path)
    from universe import build_scope
    for name, sql in pl.build_queries(pull, r, build_scope()).items():
        if name in ("portno_map", "fund_header"):
            continue
        assert " where " in sql.lower(), f"{pull}.{name} has no WHERE clause at all"
        bounded = (" in (" in sql.lower()) or (" between " in sql.lower())
        assert bounded, f"{pull}.{name} is not bounded by an id list or a date range"


def test_holdings_refuses_when_no_converting_fund_name_matches(spec, monkeypatch,
                                                               tmp_path):
    """A zero-match fund_header must refuse, never silently pull every fund."""
    import pandas as pd
    import pull as pl
    pytest.importorskip("pandas")
    r = _resolve_against(spec, _inventory())
    monkeypatch.setattr(pl, "RAW", tmp_path)
    mh = spec["pulls"]["mf_holdings"]["columns"]
    pd.DataFrame({
        mh["fund_id"]["resolved"]: [1, 2],
        mh["fund_name"]["resolved"]: ["Not A Real Converting Fund", "Neither Is This"],
        mh["fund_ticker"]["resolved"]: ["AAA", "BBB"],
    }).to_parquet(tmp_path / "mf_holdings__fund_header.parquet", index=False)
    from universe import build_scope
    with pytest.raises(sch.SchemaRefusal) as e:
        pl.build_queries("mf_holdings", r, build_scope())
    assert "NONE" in str(e.value)


@pytest.mark.parametrize("pull,missing", [
    ("compustat", "ccm_link__ccm_link.parquet"),
    ("taq_iid", "stock_names__stocknames.parquet"),
    ("mf_holdings", "mf_holdings__fund_header.parquet"),
])
def test_pull_order_is_enforced_by_refusal_not_by_convention(spec, pull, missing,
                                                             monkeypatch, tmp_path):
    import pull as pl
    pytest.importorskip("pandas")
    r = _resolve_against(spec, _inventory())
    monkeypatch.setattr(pl, "RAW", tmp_path)     # nothing landed
    from universe import build_scope
    with pytest.raises(sch.SchemaRefusal) as e:
        pl.build_queries(pull, r, build_scope())
    assert "PULL ORDER" in str(e.value)


def test_daily_pull_refuses_before_stock_names_has_landed(spec, monkeypatch, tmp_path):
    """Pull order is load-bearing: unscoped, dsf is the whole CRSP universe."""
    import pull as pl
    pytest.importorskip("pandas")
    r = _resolve_against(spec, _inventory())
    monkeypatch.setattr(pl, "RAW", tmp_path)          # nothing landed
    from universe import build_scope
    with pytest.raises(sch.SchemaRefusal) as e:
        pl.build_queries("dsf", r, build_scope())
    assert "PULL ORDER" in str(e.value)


def test_cusip_list_rejects_junk_and_refuses_empty():
    import pull as pl
    out = pl._cusip_list(["037833100", "bad!", "88160R101", ""])
    assert "'037833100'" in out and "bad" not in out
    with pytest.raises(sch.SchemaRefusal):
        pl._cusip_list(["!!!", ""])


# --------------------------------------------------------------------------- #
# 4. the offline scope derivation — real numbers from committed artifacts      #
# --------------------------------------------------------------------------- #
def test_scope_is_derivable_offline_and_covers_dropped_cells():
    pytest.importorskip("pandas")
    from universe import build_scope
    s = build_scope()
    u = s["universe"]
    # dropped cells lost a denominator, not a holding — they must be in the pull
    assert u["cusips_dropped_for_missing_denominator"] > 0
    assert u["cusips_total_to_map"] > u["cusips_with_convexp"]
    # derived, not hard-coded: the register grows when gated events are released
    # (78 -> 96 on 2026-08-27), and a literal here just breaks on every such change
    import csv as _csv
    with open(ROOT / "p1" / "t2_wrds" / "waves_members.csv", newline="") as fh:
        n_waves = len({r["effective_date"] for r in _csv.DictReader(fh)})
    assert s["waves"]["n_waves"] == n_waves
    assert s["waves"]["first_effective_date"] == "2021-03-26"
    # the daily window may not run past today
    import datetime as dt
    assert s["windows"]["daily_end"] <= dt.date.today().isoformat()
    assert s["windows"]["daily_start"] < s["waves"]["first_effective_date"]


def test_daily_window_starts_before_the_earliest_ANNOUNCEMENT_not_the_earliest_effective():
    """The event study anchors t=0 on the announcement date (plan §6 threat T2).

    Anchoring the pull on the earliest EFFECTIVE date instead truncates the
    market-model estimation window for the earliest events — silently, because a
    short window does not raise, it just returns a different beta. The earliest
    announcement leads the earliest effective date by ~11 months here, so the
    two anchors are far enough apart for this to be a real regression guard.
    """
    pytest.importorskip("pandas")
    import datetime as dt
    from universe import build_scope, PRE_TRADING_DAYS, TRADING_TO_CALENDAR
    s = build_scope()
    first_ann = s["waves"]["first_announce_date"]
    assert first_ann < s["waves"]["first_effective_date"], \
        "fixture assumption: the earliest announcement precedes the earliest effective date"
    need = (dt.date.fromisoformat(first_ann)
            - dt.timedelta(days=int(PRE_TRADING_DAYS * TRADING_TO_CALENDAR)))
    assert s["windows"]["daily_start"] <= need.isoformat(), (
        f"daily_start {s['windows']['daily_start']} does not reach back a full "
        f"estimation window before the first announcement {first_ann}")


def test_fundamentals_window_reaches_further_back_than_prices():
    """SUE needs an 8-quarter lookback and annual book equity lags by up to ~2y."""
    pytest.importorskip("pandas")
    from universe import build_scope
    w = build_scope()["windows"]
    assert w["fundamentals_start"] < w["daily_start"]
    assert w["fundamentals_lookback_years"] >= 2


def test_future_dated_waves_are_flagged_not_silently_pulled():
    pytest.importorskip("pandas")
    import datetime as dt
    from universe import build_scope
    s = build_scope()
    for d in s["waves"]["future_dated_waves"]:
        assert dt.date.fromisoformat(d) > dt.date.today()


# --------------------------------------------------------------------------- #
# 5. semantic questions discovery cannot answer stay open                      #
# --------------------------------------------------------------------------- #
def test_unit_and_convention_questions_survive_resolution(spec):
    """Listing columns never tells you whether shrout is in thousands."""
    r = _resolve_against(spec, _inventory())
    assert "shares_out_units" in r.outstanding_asserts("msf")
    assert "sue_convention" in r.outstanding_asserts("ibes")
    assert "spread_definition" in r.outstanding_asserts("taq_iid")


def test_discovered_schema_is_not_committed():
    """It is a machine-read artifact of one connected session, not source."""
    assert not (WRDS / "discovered_schema.json").exists(), \
        "discovered_schema.json should be produced on the box, not committed blind"
