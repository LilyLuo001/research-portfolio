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
        "crsp.fund_hdr":    ["crsp_fundno", "ticker"],
        "crsp.portnomap":   ["crsp_fundno", "crsp_portno"],
        "crsp.stocknames":  ["permno", "ncusip", "namedt", "nameendt"],
        "crsp.msf":         ["permno", "date", "prc", "shrout"],
        "crsp.dsf":         ["permno", "date", "ret", "prc", "vol", "openprc"],
        "crsp.dsi":         ["date", "vwretd"],
        "wrdsapps.taq_iid": ["sym_root", "date", "ehalfspd", "price_impact"],
        "ibes.statsum_epsus": ["ticker", "meanest", "stdev", "numest"],
        "ibes.act_epsus":     ["ticker", "anndats", "value"],
        "ibes.idsum":         ["ticker", "cusip"],
    })


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
@pytest.mark.parametrize("pull", ["stock_names", "mf_holdings", "taq_iid", "ibes"])
def test_queries_build_against_a_confirmed_inventory(spec, pull):
    import pull as pl
    pytest.importorskip("pandas")
    r = _resolve_against(spec, _inventory())
    if not r.ready(pull):
        pytest.skip(f"{pull} not fully resolvable from the synthetic inventory")
    from universe import build_scope
    qs = pl.build_queries(pull, r, build_scope())
    assert qs
    for sql in qs.values():
        assert sql.lower().startswith("select ")
        assert "None" not in sql, "an unresolved name leaked into SQL"


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
    assert s["waves"]["n_waves"] == 78
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
