#!/usr/bin/env python3
"""p1/wrds/pull.py — the five WRDS pulls, written offline, executed in one sprint.

ops/briefs/WRDS-access-assessment.md's recommendation: pre-write everything, then
borrow an account for one concentrated window (~3-5 days instead of 3-6 weeks
on/off) and run pure execution. This is that pre-written half. It needs no
network to develop or test; it needs a connection only for `discover` and `pull`.

Subcommands
  status     what is resolved, what is missing, what still needs a human (offline)
  discover   read the server's OWN table/column inventory -> discovered_schema.json
  resolve    match tables.yaml's logical fields to that inventory; anything
             ambiguous is reported NEED_HUMAN rather than picked
  pull       run one or all pulls; refuses on any unconfirmed name

Why the ceremony: meta-rule 1. A WRDS column name written from memory does not
raise, it returns a different number. Nothing here builds SQL from a name that
has not been seen in the live inventory — see p1/wrds/schema.py.

Raw landing: every pull writes an immutable parquet under p1/wrds/raw/ plus a
lineage JSON, and refuses to overwrite an existing file (pass --force only if
you mean to discard a landed pull).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = ROOT / "p1" / "wrds"
RAW = HERE / "raw"

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "ops" / "runner"))
from schema import DISCOVERED, Inventory, Resolver, SchemaRefusal, format_status  # noqa: E402

CUSIP_OK = re.compile(r"^[A-Z0-9]{6,9}$")
TICKER_OK = re.compile(r"^[A-Z0-9.\-]{1,10}$")
# Order is load-bearing, and every dependency below is enforced by a refusal in
# the query builder rather than by convention:
#   stock_names  -> permnos + tickers for msf/dsf/taq_iid, and fundno matching
#   ccm_link     -> gvkeys for compustat
# Anything unscoped here is not "a bit bigger", it is the whole CRSP/Compustat
# universe: comp.funda alone is every North American company since 1950.
PULL_ORDER = ["stock_names", "mf_holdings", "msf", "dsf", "taq_iid", "ccm_link",
              "compustat", "ibes"]


# --------------------------------------------------------------------------- #
# connection                                                                   #
# --------------------------------------------------------------------------- #
def connect():
    try:
        import wrds
    except ImportError:
        sys.exit("NEED_HUMAN: the `wrds` package is not installed. This subcommand "
                 "only runs on a connected node (WRDS cloud or the box). "
                 "`status` works offline.")
    import os
    try:
        return wrds.Connection(wrds_username=os.getenv("WRDS_USER"))
    except Exception as e:  # noqa: BLE001
        sys.exit(f"NEED_HUMAN: WRDS auth failed ({e}). Check ~/.pgpass or WRDS_USER "
                 "(the username is case-sensitive).")


# --------------------------------------------------------------------------- #
# discover — the server tells us its schema; we never tell it ours             #
# --------------------------------------------------------------------------- #
def cmd_discover(args) -> None:
    spec = Resolver().spec
    db = connect()
    tables: dict[str, list[str]] = {}
    for lib in spec["libraries"]:
        try:
            names = db.list_tables(library=lib)
        except Exception as e:  # noqa: BLE001
            print(f"  {lib}: NOT AVAILABLE ({e}) — skipping", file=sys.stderr)
            continue
        print(f"  {lib}: {len(names)} tables")
        for t in names:
            full = f"{lib}.{t}"
            try:
                desc = db.describe_table(library=lib, table=t)
                tables[full] = [str(c) for c in desc["name"].tolist()]
            except Exception as e:  # noqa: BLE001
                print(f"    {full}: describe failed ({e})", file=sys.stderr)
    payload = {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(),
        "libraries": spec["libraries"],
        "note": "Read off the live server. This is the ONLY authority on names.",
        "tables": tables,
    }
    DISCOVERED.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"\nwrote {DISCOVERED.relative_to(ROOT)}: {len(tables)} tables described.")
    print("next: python p1/wrds/pull.py resolve")


# --------------------------------------------------------------------------- #
# resolve — match logical fields to real names, refuse to guess                #
# --------------------------------------------------------------------------- #
def _resolve_one(candidates, present) -> tuple[str | None, str]:
    """Exactly one candidate present -> resolved. Zero or many -> NEED_HUMAN.

    Deliberately not clever. A 'best match' heuristic here would reintroduce
    precisely the guessing this module exists to prevent.
    """
    hits = [c for c in (candidates or []) if c in present]
    if len(hits) == 1:
        return hits[0], "unique candidate confirmed in inventory"
    if not hits:
        return None, "no candidate exists on the server — owner must supply the real name"
    return None, f"ambiguous: {hits} all exist — owner must pick"


def cmd_resolve(args) -> None:
    import yaml
    r = Resolver()
    if r.inv.empty:
        sys.exit(f"NEED_HUMAN: {DISCOVERED.relative_to(ROOT)} is missing. Run "
                 "`python p1/wrds/pull.py discover` on a connected node first.")
    spec = r.spec
    all_tables = set(r.inv.tables)
    unresolved: list[str] = []

    for pull, cfg in spec["pulls"].items():
        for logical, entry in cfg.get("tables", {}).items():
            if entry.get("resolved"):
                continue
            name, why = _resolve_one(entry.get("candidates"), all_tables)
            entry["resolved"] = name
            if not name:
                unresolved.append(f"{pull}.table.{logical}: {why} "
                                  f"(want: {' '.join(str(entry.get('want','')).split())})")
        # columns are confirmed against THIS pull's resolved tables only
        cols_present: set[str] = set()
        for e in cfg.get("tables", {}).values():
            if e.get("resolved"):
                cols_present |= set(r.inv.tables.get(e["resolved"], []))
        for logical, entry in cfg.get("columns", {}).items():
            if entry.get("resolved"):
                continue
            name, why = _resolve_one(entry.get("candidates"), cols_present)
            entry["resolved"] = name
            if not name:
                unresolved.append(f"{pull}.column.{logical}: {why} "
                                  f"(want: {' '.join(str(entry.get('want','')).split())})")

    if not args.dry_run:
        (HERE / "tables.yaml").write_text(yaml.safe_dump(spec, sort_keys=False,
                                                         allow_unicode=True))
        print(f"updated {(HERE / 'tables.yaml').relative_to(ROOT)}")
    print(f"\n{len(unresolved)} field(s) still need a human:")
    for u in unresolved:
        print(f"  NEED_HUMAN {u}")
    if unresolved:
        print("\nSettle these at the WRDS web query tool and paste the real names into\n"
              "tables.yaml's `resolved:` fields. Do not fill them from memory.")


# --------------------------------------------------------------------------- #
# pull — build SQL only from confirmed names                                   #
# --------------------------------------------------------------------------- #
def _cusip_list(cusips) -> str:
    """Inline a CUSIP list, validating each. WRDS's raw_sql takes params, but the
    lists here are thousands long; validating against a strict pattern and
    inlining is safer than trusting a driver to bind 6,747 params efficiently."""
    clean = sorted({c.strip().upper() for c in cusips if c and CUSIP_OK.match(c.strip().upper())})
    if not clean:
        raise SchemaRefusal("refusing to run: empty CUSIP universe")
    return ",".join(f"'{c}'" for c in clean)


def _landed(part_file: str, need: str) -> "object":
    """Read an already-landed raw parquet, or refuse with the command to run.

    Pull order is not a convention here, it is a scoping dependency: the universe
    is endogenous (whatever the converting funds held), so nothing downstream can
    be bounded until the identifier pulls have actually come back.
    """
    import pandas as pd
    src = RAW / part_file
    if not src.exists():
        try:
            shown = src.relative_to(ROOT)
        except ValueError:          # RAW redirected (tests) — show the full path
            shown = src
        raise SchemaRefusal(
            f"PULL ORDER: {need}\n"
            f"  missing: {shown}\n"
            f"  run the pull that produces it first, then re-run this one.\n"
            f"  (Unscoped, this query would fetch the whole server-side table.)")
    return pd.read_parquet(src)


def _landed_tickers(resolver: Resolver) -> list[str]:
    """Trading symbols for our universe, from the landed stock_names pull.

    TAQ-IID is keyed on the trading SYMBOL, not permno, so this is the only way
    to bound the spread pull. Symbols are reused across time and across issuers,
    so this over-covers; the date filter and a post-hoc permno join do the rest.
    """
    df = _landed("stock_names__stocknames.parquet",
                 "taq_iid is symbol-keyed and needs stock_names' ticker column.")
    tcol = resolver.spec["pulls"]["stock_names"]["columns"]["ticker"]["resolved"]
    if not tcol or tcol not in df.columns:
        raise SchemaRefusal(
            "stock_names landed without a resolved `ticker` column, so taq_iid "
            "cannot be scoped. Resolve stock_names.ticker and re-pull stock_names "
            "(--force), or skip taq_iid — do NOT pull it unscoped.")
    out = sorted({str(v).strip().upper() for v in df[tcol].dropna().unique()
                  if TICKER_OK.match(str(v).strip().upper())})
    if not out:
        raise SchemaRefusal("stock_names landed but yielded ZERO usable tickers.")
    return out


def _landed_gvkeys(resolver: Resolver) -> list[str]:
    """Compustat gvkeys for our permnos, from the landed ccm_link pull.

    Deliberately does NOT apply the linktype/linkprim filter: that filter belongs
    to the merge, where a wrong code silently duplicates firm-quarters, and it is
    flagged NEED_HUMAN on the ccm_link pull. Here we only want a superset to
    bound the fundamentals pull, so a loose match is the safe direction.
    """
    df = _landed("ccm_link__ccm_link.parquet",
                 "compustat must be scoped to our gvkeys, which come from ccm_link.")
    gcol = resolver.spec["pulls"]["ccm_link"]["columns"]["gvkey"]["resolved"]
    pcol = resolver.spec["pulls"]["ccm_link"]["columns"]["link_permno"]["resolved"]
    ours = set(_landed_permnos(resolver))
    hit = df[df[pcol].astype("Int64").isin(ours)]
    keys = sorted({str(v).strip() for v in hit[gcol].dropna().unique() if str(v).strip()})
    if not keys:
        raise SchemaRefusal(
            "ccm_link landed but matched ZERO of our permnos. Check the permno "
            "column (CCM carries lpermno and upermno) before pulling Compustat.")
    return keys


def _landed_fundnos(resolver: Resolver) -> list[int]:
    """CRSP fund numbers for the CONVERTING funds, matched by name offline.

    crsp.holdings is every fund's every position every quarter. Scoping it by our
    STOCK universe would still return every fund that happens to hold those
    stocks, which is most of the industry — the scope that matters is the ~237
    converting funds. Matching is on normalised fund name because
    events_merged.csv carries a real mutual-fund ticker on almost none of its
    rows (8 distinct tickers across 131 events).

    Deliberately loose: a false positive costs a few extra rows, a false negative
    silently loses a treated fund. The match set is written alongside the pull so
    it can be audited rather than trusted.
    """
    import csv as _csv
    import re as _re
    df = _landed("mf_holdings__fund_header.parquet",
                 "crsp.holdings must be scoped to the converting funds, whose "
                 "fundnos come from the fund_header pull.")
    cfg = resolver.spec["pulls"]["mf_holdings"]["columns"]
    idcol, namecol = cfg["fund_id"]["resolved"], cfg["fund_name"]["resolved"]

    def norm(s):
        s = _re.sub(r"[^a-z0-9 ]", " ", str(s).lower())
        s = _re.sub(r"\b(the|fund|funds|portfolio|inc|lp|llc|ltd|co|trust|series|"
                    r"class|shares?|etf|of|company)\b", " ", s)
        return _re.sub(r"\s+", " ", s).strip()

    with open(ROOT / "p1" / "events_merged.csv", newline="") as f:
        wanted = {norm(r["fund_name"]) for r in _csv.DictReader(f) if r.get("fund_name")}
    wanted.discard("")
    hit = df[df[namecol].map(lambda v: norm(v) in wanted)]
    nos = sorted({int(v) for v in hit[idcol].dropna().unique()})
    if not nos:
        raise SchemaRefusal(
            f"fund_header landed ({len(df):,} rows) but NONE of the {len(wanted)} "
            "converting fund names matched. Do not fall back to an unscoped "
            "holdings pull — inspect the name column first.")
    (RAW / "mf_holdings__matched_fundnos.json").write_text(
        json.dumps({"n_wanted_names": len(wanted), "n_matched_fundnos": len(nos),
                    "fundnos": nos}, indent=2) + "\n")
    return nos


def _landed_permnos(resolver: Resolver) -> list[int]:
    """Our permno universe, from the ALREADY-LANDED stock_names pull.

    This is why pull order matters. The universe is endogenous — it is whatever
    the converting funds held — so msf/dsf cannot be scoped until CUSIP->PERMNO
    has actually been fetched. Unscoped, the daily pull is the entire CRSP
    universe over six years (the 5-10GB case ops/briefs/WRDS-access-assessment.md
    warns against) instead of ~1-3GB.
    """
    import pandas as pd
    from universe import build_scope as _bs   # noqa: F401  (kept for symmetry)
    src = RAW / "stock_names__stocknames.parquet"
    if not src.exists():
        raise SchemaRefusal(
            "PULL ORDER: msf/dsf must be scoped to our permnos, which come from the\n"
            "  stock_names pull. Run `pull.py pull --pull stock_names` first, then\n"
            "  re-run this. (Unscoped, this would fetch the whole CRSP universe.)")
    df = pd.read_parquet(src)
    pcol = resolver.spec["pulls"]["stock_names"]["columns"]["security_id"]["resolved"]
    ccol = resolver.spec["pulls"]["stock_names"]["columns"]["cusip"]["resolved"]
    want = _universe_cusips()
    hit = df[df[ccol].astype(str).str.upper().str[:8].isin({c[:8] for c in want})]
    permnos = sorted({int(v) for v in hit[pcol].dropna().unique()})
    if not permnos:
        raise SchemaRefusal("stock_names landed but matched ZERO of our CUSIPs — check "
                            "the cusip column (CRSP carries a historical 8-char ncusip "
                            "as well as a current cusip) before pulling anything large.")
    return permnos


def _universe_cusips() -> set[str]:
    from universe import _read_convexp_cusips, _read_dropped_cusips
    computed, _ = _read_convexp_cusips()
    return {c.strip().upper() for c in (computed | _read_dropped_cusips()) if c}


def _int_list(values) -> str:
    return ",".join(str(int(v)) for v in values)


def build_queries(pull: str, resolver: Resolver, scope: dict) -> dict[str, str]:
    """The SQL for one pull. Every identifier comes through the resolver, so an
    unconfirmed name raises SchemaRefusal here rather than returning bad data."""
    R = resolver
    win = scope["windows"]

    if pull == "stock_names":
        t = R.table(pull, "stocknames")
        c = R.column(pull, "cusip", of_table=t)
        # scoped to our endogenous universe — CRSP's cusip fields are 8-char, so
        # match on the first 8 of the 9-char CUSIPs the N-PORT path carries
        return {"stocknames": (
            f"select {R.column(pull,'security_id',of_table=t)}, {c}, "
            f"{R.column(pull,'ticker',of_table=t)}, "
            f"{R.column(pull,'name_start',of_table=t)}, "
            f"{R.column(pull,'name_end',of_table=t)} from {t} "
            f"where substr({c}, 1, 8) in ({_cusip_list(_universe_cusips())})")}

    if pull == "msf":
        t = R.table(pull, "monthly_stock")
        d = R.column(pull, "date", of_table=t)
        sid = R.column(pull, "security_id", of_table=t)
        return {"msf": (
            f"select {sid}, {d}, "
            f"{R.column(pull,'price',of_table=t)}, "
            f"{R.column(pull,'ret',of_table=t)}, "
            f"{R.column(pull,'shares_out',of_table=t)} from {t} "
            f"where {d} between date '{win['monthly_start']}' "
            f"and date '{win['monthly_end']}' "
            f"and {sid} in ({_int_list(_landed_permnos(R))})")}

    if pull == "dsf":
        t = R.table(pull, "daily_stock")
        d = R.column(pull, "date", of_table=t)
        sid = R.column(pull, "security_id", of_table=t)
        idx = R.table(pull, "daily_index")
        dl = R.table(pull, "delisting_daily")
        permnos = _int_list(_landed_permnos(R))
        dld = R.column(pull, "delist_date", of_table=dl)
        return {
            # bid/ask ride along at zero marginal cost and decide the spread
            # ladder: if they are populated, spine four's quoted spread needs no
            # external vendor at all (tables.yaml taq_iid.spread_ladder).
            "dsf": (f"select {sid}, {d}, "
                    f"{R.column(pull,'ret',of_table=t)}, "
                    f"{R.column(pull,'price',of_table=t)}, "
                    f"{R.column(pull,'volume',of_table=t)}, "
                    f"{R.column(pull,'open_price',of_table=t)}, "
                    f"{R.column(pull,'bid',of_table=t)}, "
                    f"{R.column(pull,'ask',of_table=t)}, "
                    f"{R.column(pull,'bid_low',of_table=t)}, "
                    f"{R.column(pull,'ask_high',of_table=t)} from {t} "
                    f"where {d} between date '{win['daily_start']}' "
                    f"and date '{win['daily_end']}' "
                    f"and {sid} in ({permnos})"),
            "dsi": (f"select {R.column(pull,'date',of_table=idx)}, "
                    f"{R.column(pull,'mkt_ret',of_table=idx)} from {idx} "
                    f"where {R.column(pull,'date',of_table=idx)} between "
                    f"date '{win['daily_start']}' and date '{win['daily_end']}'"),
            # a delisting inside [0,+120] truncates the CAR path. Omitting this
            # does not raise, it just biases spine two — the main evidence.
            "dsedelist": (
                f"select {R.column(pull,'security_id',of_table=dl)}, {dld}, "
                f"{R.column(pull,'delist_ret',of_table=dl)}, "
                f"{R.column(pull,'delist_code',of_table=dl)} from {dl} "
                f"where {dld} between date '{win['daily_start']}' "
                f"and date '{win['daily_end']}' "
                f"and {R.column(pull,'security_id',of_table=dl)} in ({permnos})"),
        }

    if pull == "mf_holdings":
        t = R.table(pull, "holdings")
        h = R.table(pull, "fund_header")
        pm = R.table(pull, "portno_map")
        rd = R.column(pull, "report_date", of_table=t)
        # holdings are used for PRE-conversion exposure only (plan §5: 强度用转换前
        # 最后一期持仓, fixed, never revised) — so the window ends at the last
        # effective date and starts a year before the first announcement.
        hold_lo = win["daily_start"]
        hold_hi = scope["waves"]["last_effective_date"]
        return {
            "fund_header": (f"select {R.column(pull,'fund_id',of_table=h)}, "
                            f"{R.column(pull,'fund_name',of_table=h)}, "
                            f"{R.column(pull,'fund_ticker',of_table=h)} from {h}"),
            # small reference crosswalk; `select *` is deliberate — we want every
            # column, and the TABLE name still goes through the resolver gate
            "portno_map": f"select * from {pm}",
            "holdings": (f"select {R.column(pull,'fund_id',of_table=t)}, {rd}, "
                         f"{R.column(pull,'security_id',of_table=t)}, "
                         f"{R.column(pull,'shares_held',of_table=t)} from {t} "
                         f"where {rd} between date '{hold_lo}' and date '{hold_hi}' "
                         f"and {R.column(pull,'fund_id',of_table=t)} in "
                         f"({_int_list(_landed_fundnos(R))})"),
        }

    if pull == "taq_iid":
        t = R.table(pull, "intraday_indicators")
        d = R.column(pull, "date", of_table=t)
        sid = R.column(pull, "security_id", of_table=t)
        # This product is symbol-keyed on some vintages and permno-keyed on
        # others; scope by whichever one discovery actually resolved. Unscoped it
        # is every listed US name every day — the pull that eats the window.
        if sid.lower() in ("permno", "lpermno"):
            where_id = f"{sid} in ({_int_list(_landed_permnos(R))})"
        else:
            syms = ",".join(f"'{s}'" for s in _landed_tickers(R))
            where_id = f"upper({sid}) in ({syms})"
        return {"taq_iid": (
            f"select {sid}, {d}, "
            f"{R.column(pull,'eff_spread',of_table=t)}, "
            f"{R.column(pull,'price_impact',of_table=t)} from {t} "
            f"where {d} between date '{win['daily_start']}' "
            f"and date '{win['daily_end']}' and {where_id}")}

    if pull == "ccm_link":
        t = R.table(pull, "ccm_link")
        lp = R.column(pull, "link_permno", of_table=t)
        # No linktype/linkprim filter here on purpose: that filter belongs to the
        # merge (tables.yaml ccm_link.link_filter is NEED_HUMAN), and applying it
        # at pull time would discard the rows needed to audit the choice.
        return {"ccm_link": (
            f"select {R.column(pull,'gvkey',of_table=t)}, {lp}, "
            f"{R.column(pull,'link_start',of_table=t)}, "
            f"{R.column(pull,'link_end',of_table=t)}, "
            f"{R.column(pull,'link_type',of_table=t)}, "
            f"{R.column(pull,'link_prim',of_table=t)} from {t} "
            f"where {lp} in ({_int_list(_landed_permnos(R))})")}

    if pull == "compustat":
        q, a = R.table(pull, "fundq"), R.table(pull, "funda")
        gv = ",".join(f"'{g}'" for g in _landed_gvkeys(R))
        dq = R.column(pull, "datadate", of_table=q)
        da = R.column(pull, "datadate", of_table=a)
        lo, hi = win["fundamentals_start"], win["fundamentals_end"]
        return {
            "fundq": (f"select {R.column(pull,'gvkey',of_table=q)}, {dq}, "
                      f"{R.column(pull,'rdq',of_table=q)}, "
                      f"{R.column(pull,'eps_q',of_table=q)} from {q} "
                      f"where {dq} between date '{lo}' and date '{hi}' "
                      f"and {R.column(pull,'gvkey',of_table=q)} in ({gv})"),
            # annual is for the CONTROL MATCH (§107 book-to-market), not for DGTW
            "funda": (f"select {R.column(pull,'gvkey',of_table=a)}, {da}, "
                      f"{R.column(pull,'book_equity',of_table=a)}, "
                      f"{R.column(pull,'shares_annual',of_table=a)}, "
                      f"{R.column(pull,'price_fiscal',of_table=a)} from {a} "
                      f"where {da} between date '{lo}' and date '{hi}' "
                      f"and {R.column(pull,'gvkey',of_table=a)} in ({gv})"),
        }

    if pull == "ibes":
        s, a = R.table(pull, "summary"), R.table(pull, "actuals")
        i = R.table(pull, "identifiers")
        cus = _cusip_list({c[:8] for c in _universe_cusips()})
        lo, hi = win["fundamentals_start"], win["fundamentals_end"]
        sp = R.column(pull, "stat_period", of_table=s)
        ad = R.column(pull, "anndate", of_table=a)
        # Both IBES files carry cusip, so neither needs idsum to be landed first —
        # idsum is pulled for the MAPPING HISTORY, which a point-in-time cusip on
        # a statsum row is not.
        return {
            # `select *` is deliberate: idsum is the mapping HISTORY and every
            # column of it is wanted. The table name still goes through the gate.
            "identifiers": (f"select * from {i} where substr("
                            f"{R.column(pull,'cusip',of_table=i)}, 1, 8) in ({cus})"),
            "summary": (f"select {R.column(pull,'security_id',of_table=s)}, "
                        f"{R.column(pull,'cusip',of_table=s)}, {sp}, "
                        f"{R.column(pull,'fp_end',of_table=s)}, "
                        f"{R.column(pull,'fp_index',of_table=s)}, "
                        f"{R.column(pull,'consensus',of_table=s)}, "
                        f"{R.column(pull,'dispersion',of_table=s)}, "
                        f"{R.column(pull,'n_analysts',of_table=s)} from {s} "
                        f"where {sp} between date '{lo}' and date '{hi}' "
                        f"and substr({R.column(pull,'cusip',of_table=s)}, 1, 8) "
                        f"in ({cus})"),
            "actuals": (f"select {R.column(pull,'security_id',of_table=a)}, "
                        f"{R.column(pull,'cusip',of_table=a)}, {ad}, "
                        f"{R.column(pull,'period_end',of_table=a)}, "
                        f"{R.column(pull,'actual',of_table=a)} from {a} "
                        f"where {ad} between date '{lo}' and date '{hi}' "
                        f"and substr({R.column(pull,'cusip',of_table=a)}, 1, 8) "
                        f"in ({cus})"),
        }

    raise SchemaRefusal(f"unknown pull '{pull}' (known: {', '.join(PULL_ORDER)})")


def cmd_pull(args) -> None:
    from universe import build_scope
    from lineage import write_lineage

    resolver = Resolver()
    scope = build_scope()
    targets = [args.pull] if args.pull else PULL_ORDER
    RAW.mkdir(parents=True, exist_ok=True)

    blocked = [p for p in targets if not resolver.ready(p)]
    if blocked:
        print("REFUSING — these pulls have unconfirmed names:\n")
        print(format_status(resolver))
        sys.exit(f"\nblocked: {', '.join(blocked)}. Run discover + resolve first.")

    for p in targets:
        outstanding = resolver.outstanding_asserts(p)
        if outstanding and not args.accept_open_questions:
            print(f"\nNEED_HUMAN before '{p}' is usable (data will pull, but the "
                  "SEMANTICS are unsettled):")
            for k, v in outstanding.items():
                print(f"  {k}: {' '.join(v.split())}")
            print("  These are conventions/units that discovery cannot answer. Re-run "
                  "with --accept-open-questions to land the raw data anyway and settle "
                  "them before any number is computed from it.")
            continue
        queries = build_queries(p, resolver, scope)
        if args.dry_run:
            print(f"\n--- {p} ---")
            for name, sql in queries.items():
                print(f"[{name}]\n{sql}\n")
            continue
        db = connect()
        for name, sql in queries.items():
            out = RAW / f"{p}__{name}.parquet"
            if out.exists() and not args.force:
                print(f"  {out.name}: already landed, skipping (--force to replace)")
                continue
            print(f"  {out.name}: running...")
            df = db.raw_sql(sql)
            df.to_parquet(out, index=False)
            write_lineage(out, [], extra={"wrds_query": sql, "rows": int(len(df)),
                                          "pull": p, "part": name})
            print(f"  {out.name}: {len(df):,} rows")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("discover")
    r = sub.add_parser("resolve"); r.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("pull")
    p.add_argument("--pull", choices=PULL_ORDER)
    p.add_argument("--dry-run", action="store_true", help="print SQL, connect to nothing")
    p.add_argument("--force", action="store_true", help="replace an already-landed file")
    p.add_argument("--accept-open-questions", action="store_true",
                   help="land raw data whose units/conventions are still NEED_HUMAN")
    a = ap.parse_args()

    if a.cmd == "status":
        print(format_status(Resolver()))
    elif a.cmd == "discover":
        cmd_discover(a)
    elif a.cmd == "resolve":
        cmd_resolve(a)
    elif a.cmd == "pull":
        cmd_pull(a)


if __name__ == "__main__":
    main()
