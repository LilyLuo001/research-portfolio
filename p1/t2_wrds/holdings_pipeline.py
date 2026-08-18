#!/usr/bin/env python3
"""P1-T2-wrds — holdings pipeline + ConvExp construction. BOX/WRDS-ONLY.

Implements Project_1.md §T2 verbatim:

  ConvExp_{i,e} = Σ_f (converting fund f's pre-conversion share holding of stock i)
                  / (CRSP shares outstanding of i)      [shrout is in THOUSANDS: ×1000]
  wave e        = conversions sharing an effective_date (p1/t2_wrds/waves.csv;
                  DFA 2021-06-11 = anchor)

Output (frozen contract ops/contracts/conv_exposure.yaml):
  conv_exposure.parquet: permno | wave_id | effective_date | conv_exp | n_funds
                         | mcap_decile | pre_etf_ownership
Side outputs: unmapped_funds.csv (NEED_HUMAN), convexp_diagnostics.md,
  conv_exposure.parquet.lineage.json, query_manifest.json (see DATA POLICY).

Meta-rule 1: every number here is CODE-ON-REAL-DATA. No holding, shrout, or
mapping is ever hand-filled; a fund that cannot be mapped to a pre-conversion
holdings report is emitted to the NEED_HUMAN list, never imputed.

TWO THINGS TO READ BEFORE RUNNING
---------------------------------
1. **The schema below is UNVERIFIED.** Every CRSP table and column name lives in
   the SCHEMA dict, and not one of them has been confirmed against a live WRDS
   account — this file was written before access was delivered, and guessing
   schema from memory is exactly what meta-rule 1 forbids. Run
   `python p1/t2_wrds/coverage_census.py --introspect` first; it prints the real
   tables/columns and tells you which SCHEMA entries to correct. Correcting them
   is a one-place edit, by construction.
2. **Data policy**: p1/t2_wrds/README.md. Raw rows never enter git; this script
   writes a query-locator manifest instead, which is the WRDS analogue of an
   EDGAR accession.

Testability: every query is built by a pure function and every database call goes
through an injected object exposing `.raw_sql(sql) -> DataFrame`. p1/tests/ drives
the whole pipeline with a fake, so this file is exercised with zero credentials —
it cannot be run from a Claude Code session (wrds speaks PostgreSQL on 9737).

Run on box:  python p1/t2_wrds/holdings_pipeline.py
             (WRDS creds via ~/.pgpass or WRDS_USER/WRDS_PASS; see README)
"""
import argparse
import csv
import hashlib
import json
import os
import pathlib
import sys
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WAVES = HERE / "waves.csv"
# Wave MEMBERSHIP (which fund converted in which wave) lives in waves_members.csv,
# not waves.csv. An earlier revision read waves.csv["source_accessions"], a column
# that only ever existed in the merge-corrupted build_waves scaffold's 7-col
# output; against the canonical 4-col waves.csv that is a KeyError. The free
# pipeline (build_nport_convexp.py) already keys off members for the same reason.
MEMBERS = HERE / "waves_members.csv"
EVENTS = HERE.parent / "events_merged.csv"
OUT_PARQUET = HERE.parent / "conv_exposure.parquet"
DIAG = HERE / "convexp_diagnostics.md"
NEED_HUMAN = HERE / "unmapped_funds.csv"
QUERY_MANIFEST = HERE / "query_manifest.json"

CONTRACT_COLUMNS = ["permno", "wave_id", "effective_date", "conv_exp",
                    "n_funds", "mcap_decile", "pre_etf_ownership"]

# --------------------------------------------------------------------------- #
# SCHEMA — every CRSP identifier this pipeline depends on, in ONE place.
# STATUS: UNVERIFIED (no live WRDS account existed when this was written).
# Verify with coverage_census.py --introspect, then correct here and nowhere else.
# --------------------------------------------------------------------------- #
SCHEMA = {
    "fund_header": {"table": "crsp.fund_hdr",
                    "fundno": "crsp_fundno", "name": "fund_name", "ticker": "ticker"},
    "holdings": {"table": "crsp.holdings",
                 "fundno": "crsp_fundno", "permno": "permno",
                 "shares": "nbr_shares", "report_date": "report_dt"},
    "monthly_stock": {"table": "crsp.msf",
                      "permno": "permno", "date": "date",
                      "shrout": "shrout", "price": "prc"},
}
SHROUT_UNITS_PER_SHARE = 1000.0   # CRSP shrout is in THOUSANDS of shares
SHROUT_LOOKBACK_MONTHS = 6        # see as_of_shrout(): tolerate a stale-but-real obs
TREATED_LINE = 0.005              # 0.5%, the P1 convention (also the Gate-2 line)


def _q(value):
    """Single-quote a SQL literal, escaping embedded quotes.

    Values come from our own CSVs, so this is about correctness (a ticker or fund
    name containing an apostrophe must not break the query), not about defending
    against an attacker. If the installed `wrds` client exposes parameter binding,
    prefer it — that is a box-side improvement, flagged in the README.
    """
    return "'" + str(value).replace("'", "''") + "'"


def _inlist(values):
    return ", ".join(_q(v) if isinstance(v, str) else str(int(v)) for v in values)


# --------------------------------------------------------------------------- #
# connection                                                                   #
# --------------------------------------------------------------------------- #
def connect():
    try:
        import wrds
    except ImportError:
        sys.exit("NEED_HUMAN: `wrds` package not installed — run on the box or "
                 "WRDS Cloud. This cannot run in a Claude Code session: the "
                 "client speaks PostgreSQL on port 9737, not HTTPS.")
    try:
        return wrds.Connection(wrds_username=os.getenv("WRDS_USER"))
    except Exception as e:  # noqa: BLE001
        sys.exit(f"NEED_HUMAN: WRDS auth failed ({e}). Fix ~/.pgpass / WRDS_USER "
                 "(note: username is case-sensitive; the earlier .pgpass didn't "
                 "auto-auth).")


class Recorder:
    """Wraps the connection so every query is logged as a locator, never as rows.

    The manifest it accumulates — statement, row count, digest — is what gets
    committed in place of the data (README, DATA POLICY).
    """

    def __init__(self, db):
        self.db = db
        self.queries = []

    def raw_sql(self, sql, label=""):
        df = self.db.raw_sql(sql)
        self.queries.append({
            "label": label,
            "sql": " ".join(sql.split()),
            "rows": int(len(df)),
            "sql_sha256": hashlib.sha256(" ".join(sql.split()).encode()).hexdigest()[:16],
            "at": datetime.now(timezone.utc).isoformat(),
        })
        return df


# --------------------------------------------------------------------------- #
# query builders — pure functions, unit-tested without a database              #
# --------------------------------------------------------------------------- #
def sql_funds_by_ticker(tickers):
    s = SCHEMA["fund_header"]
    return (f"select {s['fundno']}, {s['name']}, {s['ticker']} "
            f"from {s['table']} where {s['ticker']} in ({_inlist(sorted(tickers))})")


def sql_last_holdings_before(fundnos, eff_date):
    """Each fund's LAST holdings report strictly before the wave's effective date.

    'Strictly before' is the lookahead ban in SQL form: a report filed on or after
    the conversion can reflect the ETF wrapper, which is the thing being measured.
    """
    h = SCHEMA["holdings"]
    return (f"with last_rpt as ("
            f" select {h['fundno']}, max({h['report_date']}) as {h['report_date']}"
            f" from {h['table']}"
            f" where {h['fundno']} in ({_inlist(fundnos)})"
            f" and {h['report_date']} < date {_q(eff_date)}"
            f" group by {h['fundno']})"
            f" select h.{h['fundno']}, h.{h['permno']}, h.{h['shares']}, h.{h['report_date']}"
            f" from {h['table']} h join last_rpt l"
            f" on h.{h['fundno']} = l.{h['fundno']} and h.{h['report_date']} = l.{h['report_date']}"
            f" where h.{h['permno']} is not null and h.{h['shares']} > 0")


def sql_shrout_asof(permnos, eff_date, lookback_months=SHROUT_LOOKBACK_MONTHS):
    """Most recent monthly observation PER PERMNO before the effective date.

    The scaffold this replaces pinned one global month-end and joined on equality,
    so any stock without a row on exactly that date — newly listed, delisted,
    halted, or simply not in that month's file — silently lost its denominator and
    dropped out. That is the same failure that cost the free path ~5,600 cells,
    and it is worth avoiding twice.
    """
    m = SCHEMA["monthly_stock"]
    return (f"select distinct on ({m['permno']}) {m['permno']}, {m['shrout']}, "
            f"{m['price']}, {m['date']} "
            f"from {m['table']} "
            f"where {m['permno']} in ({_inlist(permnos)}) "
            f"and {m['date']} < date {_q(eff_date)} "
            f"and {m['date']} >= date {_q(eff_date)} - interval '{int(lookback_months)} months' "
            f"order by {m['permno']}, {m['date']} desc")


# --------------------------------------------------------------------------- #
# fund identity -> CRSP fundno                                                 #
# --------------------------------------------------------------------------- #
def map_funds(db, events):
    """Map converting funds to crsp_fundno by exact MF ticker, in ONE query.

    Deliberately conservative: only an exact ticker match maps a fund. Everything
    else — no ticker in events_merged, or a ticker CRSP does not carry — goes to
    NEED_HUMAN with a reason, because a fuzzy name match that silently pairs the
    wrong fund would corrupt ConvExp invisibly.

    The layer this does NOT implement is the MFLINK / name-match fallback, which
    needs a live account to design against. coverage_census.py measures how much
    it would be worth before anyone builds it.
    """
    tickers = sorted({(e.get("mutual_fund_ticker") or "").strip()
                      for e in events} - {"", "NA"})
    by_ticker = {}
    if tickers:
        df = db.raw_sql(sql_funds_by_ticker(tickers), label="fund_header_by_ticker")
        tcol, fcol = SCHEMA["fund_header"]["ticker"], SCHEMA["fund_header"]["fundno"]
        for r in df.itertuples():
            by_ticker.setdefault(str(getattr(r, tcol)).strip().upper(),
                                 int(getattr(r, fcol)))

    mapping, unmapped = [], []
    for e in events:
        t = (e.get("mutual_fund_ticker") or "").strip().upper()
        if t in ("", "NA"):
            unmapped.append({**e, "unmapped_reason": "no_mutual_fund_ticker_in_events"})
        elif t not in by_ticker:
            unmapped.append({**e, "unmapped_reason": "ticker_not_in_crsp_fund_header"})
        else:
            mapping.append({**e, "fundno": by_ticker[t]})
    return mapping, unmapped


# --------------------------------------------------------------------------- #
# ConvExp                                                                      #
# --------------------------------------------------------------------------- #
def decile_ranks(mcaps):
    """1..10 by market cap within the wave's cross-section; None if unpriced.

    Within-wave ranking, not CRSP universe breakpoints — a documented
    simplification, not an accident. Switching to NYSE breakpoints is a box-side
    change once the universe tables are verified.
    """
    caps = sorted(c for c in mcaps.values() if c and c > 0)
    out = {}
    for permno, c in mcaps.items():
        if not c or c <= 0 or not caps:
            out[permno] = None
            continue
        rank = sum(1 for x in caps if x <= c)          # 1..len(caps)
        out[permno] = min(10, max(1, int((rank - 1) * 10 // len(caps)) + 1))
    return out


def convexp_for_wave(db, wave_id, eff_date, funds):
    """Σ_f shares held / shares outstanding, per permno, for one wave."""
    fundnos = sorted({f["fundno"] for f in funds if f.get("fundno")})
    if not fundnos:
        return [], []

    h = SCHEMA["holdings"]
    holdings = db.raw_sql(sql_last_holdings_before(fundnos, eff_date),
                          label=f"holdings::{wave_id}")
    if not len(holdings):
        return [], [{"wave_id": wave_id, "reason": "no_pre_conversion_holdings"}]

    agg = {}
    for r in holdings.itertuples():
        p = int(getattr(r, h["permno"]))
        cell = agg.setdefault(p, {"shares": 0.0, "funds": set()})
        cell["shares"] += float(getattr(r, h["shares"]) or 0)
        cell["funds"].add(int(getattr(r, h["fundno"])))

    m = SCHEMA["monthly_stock"]
    shr = db.raw_sql(sql_shrout_asof(sorted(agg), eff_date), label=f"shrout::{wave_id}")
    shrout, mcap = {}, {}
    for r in shr.itertuples():
        p = int(getattr(r, m["permno"]))
        so = float(getattr(r, m["shrout"]) or 0) * SHROUT_UNITS_PER_SHARE
        shrout[p] = so
        px = getattr(r, m["price"], None)
        # CRSP encodes a bid/ask average as a NEGATIVE price; magnitude is the datum.
        mcap[p] = abs(float(px)) * so if px not in (None, "") and so > 0 else None

    deciles = decile_ranks(mcap)
    rows, dropped = [], []
    for p in sorted(agg):
        so = shrout.get(p, 0.0)
        if so <= 0:
            # No denominator -> no exposure. Recorded, never imputed (meta-rule 1),
            # and carrying the numerator so the drop can be costed later — the
            # lesson from the free path's dropped cells.
            dropped.append({"wave_id": wave_id, "permno": p,
                            "reason": "no_shrout_in_lookback_window",
                            "shares_held": agg[p]["shares"],
                            "n_funds": len(agg[p]["funds"])})
            continue
        rows.append({"permno": p, "wave_id": wave_id, "effective_date": eff_date,
                     "conv_exp": agg[p]["shares"] / so,
                     "n_funds": len(agg[p]["funds"]),
                     "mcap_decile": deciles.get(p),
                     # NOT the same quantity as the converting funds' ownership:
                     # total pre-conversion ETF ownership needs a 13F/ETF-holdings
                     # join that has no verified source yet. Left null rather than
                     # aliased to conv_exp, which would look like data.
                     "pre_etf_ownership": None})
    return rows, dropped


def main():
    if not MEMBERS.exists():
        sys.exit(f"NEED_HUMAN: missing {MEMBERS} — run p1/t2_wrds/build_waves.py first.")
    waves = list(csv.DictReader(WAVES.open()))
    members = list(csv.DictReader(MEMBERS.open()))
    events = list(csv.DictReader(EVENTS.open()))
# --------------------------------------------------------------------------- #
# outputs                                                                      #
# --------------------------------------------------------------------------- #
def build_frame(rows):
    import pandas as pd
    df = pd.DataFrame(rows, columns=CONTRACT_COLUMNS)
    if len(df):
        df["permno"] = df["permno"].astype("Int64")
        df["n_funds"] = df["n_funds"].astype("Int64")
        df["mcap_decile"] = df["mcap_decile"].astype("Int64")
        df["conv_exp"] = df["conv_exp"].astype(float)
        df["pre_etf_ownership"] = df["pre_etf_ownership"].astype("Float64")
    return df


def write_query_manifest(recorder, path=QUERY_MANIFEST):
    """Locators, not rows — see README, DATA POLICY."""
    path.write_text(json.dumps({
        "note": "Query locators for the WRDS pull. Row-level licensed data is "
                "never committed; these statements let an auditor with their own "
                "subscription reproduce the identical extract.",
        "schema_status": "SEE SCHEMA dict in holdings_pipeline.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "queries": recorder.queries,
    }, indent=2) + "\n")


def write_unmapped(unmapped, path=NEED_HUMAN):
    """Always written, even when empty — an absent file is ambiguous."""
    fields = sorted({k for r in unmapped for k in r}) or ["unmapped_reason"]
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(unmapped)


def diagnostics(df, waves, unmapped, dropped, path=DIAG):
    anchor = {w["wave_id"] for w in waves if str(w.get("is_anchor")) == "1"}
    n = len(df)
    L = ["# ConvExp diagnostics (kill-switch gate 2 input)", "",
         f"generated: {datetime.now(timezone.utc).isoformat()}", "",
         f"- permno×wave rows: **{n}**",
         f"- distinct stocks: **{df['permno'].nunique() if n else 0}**",
         f"- stocks ConvExp ≥ 0.5%: **{int((df['conv_exp'] >= TREATED_LINE).sum()) if n else 0}**",
         f"- stocks ConvExp ≥ 1.0%: **{int((df['conv_exp'] >= 0.01).sum()) if n else 0}**",
         f"- funds unmapped (NEED_HUMAN): **{len(unmapped)}**",
         f"- cells dropped for a missing denominator: **{len(dropped)}**", ""]
    if n:
        a = df[df["wave_id"].isin(anchor)]
        L += [f"- DFA anchor wave: {len(a)} stock-rows, "
              f"{int((a['conv_exp'] >= TREATED_LINE).sum())} with ConvExp≥0.5% "
              f"({100 * len(a) / max(1, n):.1f}% of all rows)", "",
              "## ConvExp distribution", "", "```",
              df["conv_exp"].describe().to_string(), "```", "",
              "## stocks ≥0.5% per wave", "", "```"]
        g = df[df["conv_exp"] >= TREATED_LINE].groupby("wave_id").size()
        L += [g.to_string() if len(g) else "(none)", "```"]
    path.write_text("\n".join(L) + "\n")

    # wave_id -> the converting funds in it, via each member's source_accession
    accs_by_wave = {}
    for m in members:
        accs_by_wave.setdefault(m["wave_id"], []).append(m["source_accession"])

    rows = []
    for w in waves:
        accs = accs_by_wave.get(w["wave_id"], [])
        funds = [fundno_by_acc[a] for a in accs if a in fundno_by_acc]
        rows += convexp_for_wave(db, w["wave_id"], w["effective_date"], funds)

# --------------------------------------------------------------------------- #
def run(db, waves, events):
    """The whole pipeline against an injected connection. Returns (df, ...)."""
    rec = db if isinstance(db, Recorder) else Recorder(db)
    mapping, unmapped = map_funds(rec, events)
    by_acc = {m["source_accession"]: m for m in mapping}

    rows, dropped = [], []
    for w in waves:
        accs = (w.get("source_accessions") or "").split("|")
        funds = [by_acc[a] for a in accs if a in by_acc]
        r, d = convexp_for_wave(rec, w["wave_id"], w["effective_date"], funds)
        rows += r
        dropped += d
    return build_frame(rows), unmapped, dropped, rec


def main(argv=None):
    ap = argparse.ArgumentParser(description="P1-T2 WRDS ConvExp build")
    ap.parse_args(argv)
    if not WAVES.exists():
        sys.exit(f"NEED_HUMAN: run build_waves.py first (missing {WAVES})")

    waves = list(csv.DictReader(WAVES.open()))
    events = list(csv.DictReader(EVENTS.open()))
    df, unmapped, dropped, rec = run(connect(), waves, events)

    df.to_parquet(OUT_PARQUET, index=False)
    write_unmapped(unmapped)
    write_query_manifest(rec)
    diagnostics(df, waves, unmapped, dropped)
    sys.path.insert(0, str(ROOT / "ops" / "runner"))
    from lineage import write_lineage
    write_lineage(str(OUT_PARQUET), [str(WAVES), str(EVENTS)],
                  extra={"source": "WRDS/CRSP (licensed; rows not committed)",
                         "query_manifest": str(QUERY_MANIFEST),
                         "schema_status": "verify SCHEMA against a live account"})

    print(f"conv_exposure.parquet: {len(df)} (permno×wave) rows; "
          f"{len(unmapped)} funds unmapped -> {NEED_HUMAN.name}; "
          f"{len(dropped)} cells without a denominator. "
          f"Validate: python ops/runner/contracts.py conv_exposure {OUT_PARQUET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
