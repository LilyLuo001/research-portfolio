#!/usr/bin/env python3
"""p1/wrds/verify.py — audit the landed pulls BEFORE the account is released.

Runs entirely offline against `p1/wrds/raw/`. It exists because of an asymmetry
specific to a rented window: a bad pull is cheap to fix while the account is
live and expensive afterwards. Discovering a 12% CUSIP->PERMNO match rate the
day after handing the account back means renting it again.

So this asks the questions whose answers change what you do in the next ten
minutes, not the questions a downstream analysis will ask later:

  1. Did every expected part land, and with how many rows?
  2. Does `stock_names` actually cover our universe? (the whole project's join)
  3. Do the daily/monthly files span the window `pull_scope.json` asked for?
  4. Are `crsp.dsf`'s bid/ask populated?  -> settles the spread ladder from the
     data itself, and decides whether any external vendor is needed at all
  5. Did the fund-name match find the converting funds, or almost none of them?
  6. Do IBES and Compustat reach the stocks we care about?

Every check prints PASS / WARN / FAIL and a one-line reason. FAIL means re-pull
now. WARN means write it down; it may be a real data limit rather than a mistake.

  python p1/wrds/verify.py            # audit whatever has landed
  python p1/wrds/verify.py --json     # machine-readable, for the lineage record
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = ROOT / "p1" / "wrds"
RAW = HERE / "raw"
SCOPE = HERE / "pull_scope.json"

sys.path.insert(0, str(HERE))

# part file -> (pull, why it matters if absent)
EXPECTED = {
    "stock_names__stocknames.parquet": ("stock_names", "CUSIP->PERMNO; nothing joins without it"),
    "mf_holdings__fund_header.parquet": ("mf_holdings", "fund identity for the name match"),
    "mf_holdings__portno_map.parquet": ("mf_holdings", "portno<->fundno crosswalk"),
    "mf_holdings__holdings.parquet": ("mf_holdings", "CRSP-identifier ConvExp"),
    "msf__msf.parquet": ("msf", "ConvExp denominator, mcap deciles"),
    "dsf__dsf.parquet": ("dsf", "every spine-two outcome"),
    "dsf__dsi.parquet": ("dsf", "market-model benchmark"),
    "dsf__dsedelist.parquet": ("dsf", "delisting returns inside the CAR window"),
    "taq_iid__taq_iid.parquet": ("taq_iid", "spine four spread/price impact"),
    "ccm_link__ccm_link.parquet": ("ccm_link", "gvkey<->permno"),
    "compustat__fundq.parquet": ("compustat", "earnings decomposition, FERC"),
    "compustat__funda.parquet": ("compustat", "book equity for the control match"),
    "ibes__identifiers.parquet": ("ibes", "IBES ticker<->historical CUSIP"),
    "ibes__summary.parquet": ("ibes", "consensus, dispersion, coverage"),
    "ibes__actuals.parquet": ("ibes", "actual EPS + announcement date"),
}

# A match rate below this is a mistake, not a data limit.
MATCH_FLOOR_FAIL = 0.50
MATCH_FLOOR_WARN = 0.80


class Report:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, level: str, check: str, detail: str) -> None:
        self.rows.append({"level": level, "check": check, "detail": detail})

    def __getattr__(self, name):
        if name in ("ok", "warn", "fail", "skip"):
            level = {"ok": "PASS", "warn": "WARN", "fail": "FAIL", "skip": "SKIP"}[name]
            return lambda check, detail: self.add(level, check, detail)
        raise AttributeError(name)

    def render(self) -> str:
        w = max((len(r["check"]) for r in self.rows), default=10)
        out = [f"{r['level']:5s} {r['check']:{w}s}  {r['detail']}" for r in self.rows]
        n = {lv: sum(1 for r in self.rows if r["level"] == lv)
             for lv in ("PASS", "WARN", "FAIL", "SKIP")}
        out += ["", f"{n['PASS']} pass, {n['WARN']} warn, {n['FAIL']} fail, "
                    f"{n['SKIP']} not landed"]
        if n["FAIL"]:
            out += ["", "*** RE-PULL BEFORE RELEASING THE ACCOUNT ***"]
        elif n["SKIP"]:
            out += ["", "Some pulls have not landed yet — re-run after they do."]
        return "\n".join(out)


def _resolved(spec, pull, kind, logical):
    return (spec["pulls"].get(pull, {}).get(kind, {}).get(logical, {}) or {}).get("resolved")


def _read(part):
    import pandas as pd
    return pd.read_parquet(RAW / part)


def run(rep: Report) -> None:
    import pandas as pd
    from schema import load_spec
    from universe import _read_convexp_cusips, _read_dropped_cusips

    spec = load_spec()
    scope = json.loads(SCOPE.read_text()) if SCOPE.exists() else {}
    win = scope.get("windows", {})

    # ---- 1. presence ------------------------------------------------------
    landed = set()
    for part, (pull, why) in EXPECTED.items():
        if (RAW / part).exists():
            landed.add(part)
            try:
                n = len(_read(part))
            except Exception as e:                                # noqa: BLE001
                rep.fail(f"read {part}", f"landed but unreadable: {e}")
                continue
            (rep.fail if n == 0 else rep.ok)(
                f"landed {part}", f"{n:,} rows" if n else "ZERO rows — the query "
                f"matched nothing ({why})")
        else:
            rep.skip(f"landed {part}", f"not pulled yet — {why}")

    # ---- 2. the join the whole project rests on ---------------------------
    if "stock_names__stocknames.parquet" in landed:
        sn = _read("stock_names__stocknames.parquet")
        ccol = _resolved(spec, "stock_names", "columns", "cusip")
        pcol = _resolved(spec, "stock_names", "columns", "security_id")
        tcol = _resolved(spec, "stock_names", "columns", "ticker")
        computed, _ = _read_convexp_cusips()
        universe8 = {c[:8].upper() for c in (computed | _read_dropped_cusips()) if c}
        if ccol and ccol in sn.columns:
            got = {str(v).upper()[:8] for v in sn[ccol].dropna().unique()}
            rate = len(universe8 & got) / max(len(universe8), 1)
            lvl = (rep.fail if rate < MATCH_FLOOR_FAIL
                   else rep.warn if rate < MATCH_FLOOR_WARN else rep.ok)
            lvl("cusip->permno coverage",
                f"{len(universe8 & got):,}/{len(universe8):,} of our CUSIPs found "
                f"({rate:.1%}). Below {MATCH_FLOOR_FAIL:.0%} means the wrong cusip "
                f"column (ncusip vs cusip) or a truncation mismatch.")
        else:
            rep.fail("cusip->permno coverage", f"cusip column '{ccol}' not on the file")
        if pcol and pcol in sn.columns:
            rep.ok("permno recovered", f"{sn[pcol].nunique():,} distinct permnos")
        if tcol and tcol in sn.columns:
            n = sn[tcol].notna().sum()
            (rep.ok if n else rep.fail)(
                "ticker present", f"{n:,} non-null — needed to scope TAQ-IID")

    # ---- 3. window coverage ----------------------------------------------
    for part, (lo_key, hi_key, pull, logical) in {
        "dsf__dsf.parquet": ("daily_start", "daily_end", "dsf", "date"),
        "msf__msf.parquet": ("monthly_start", "monthly_end", "msf", "date"),
        "dsf__dsi.parquet": ("daily_start", "daily_end", "dsf", "date"),
    }.items():
        if part not in landed:
            continue
        df, dcol = _read(part), _resolved(spec, pull, "columns", logical)
        if not dcol or dcol not in df.columns:
            rep.warn(f"window {part}", f"date column '{dcol}' not on the file")
            continue
        d = pd.to_datetime(df[dcol], errors="coerce").dropna()
        lo, hi = win.get(lo_key), win.get(hi_key)
        got_lo, got_hi = d.min().date().isoformat(), d.max().date().isoformat()
        short = (lo and got_lo > lo) or (hi and got_hi < hi)
        # a few days at each edge are holidays/weekends, not a truncation
        bad = lo and (pd.Timestamp(got_lo) - pd.Timestamp(lo)).days > 7
        (rep.fail if bad else rep.warn if short else rep.ok)(
            f"window {part}", f"{got_lo} .. {got_hi} (asked {lo} .. {hi})")

    # ---- 4. the spread ladder, settled from the data ----------------------
    if "dsf__dsf.parquet" in landed:
        dsf = _read("dsf__dsf.parquet")
        bid = _resolved(spec, "dsf", "columns", "bid")
        ask = _resolved(spec, "dsf", "columns", "ask")
        if bid in dsf.columns and ask in dsf.columns:
            both = dsf[[bid, ask]].notna().all(axis=1).mean()
            if both >= 0.80:
                rep.ok("spread ladder",
                       f"CRSP bid/ask populated on {both:.1%} of stock-days — "
                       "spine four's quoted spread needs NO external vendor. "
                       "Record this against tables.yaml taq_iid.spread_ladder.")
            elif both > 0:
                rep.warn("spread ladder",
                         f"CRSP bid/ask populated on only {both:.1%} of stock-days — "
                         "usable as a cross-check, not as the primary measure.")
            else:
                rep.warn("spread ladder",
                         "CRSP bid/ask are entirely null — the spread must come "
                         "from TAQ-IID or an external vendor.")
        else:
            rep.warn("spread ladder", "bid/ask columns were not resolved or not selected")

    # ---- 5. did the fund-name match actually find the converting funds? ---
    m = RAW / "mf_holdings__matched_fundnos.json"
    if m.exists():
        info = json.loads(m.read_text())
        got, want = info["n_matched_fundnos"], info["n_wanted_names"]
        rate = got / max(want, 1)
        (rep.fail if rate < 0.20 else rep.warn if rate < 0.60 else rep.ok)(
            "converting funds matched",
            f"{got}/{want} fund names matched a CRSP fundno ({rate:.0%}). "
            "A partial match silently drops treated funds from ConvExp — read "
            "raw/mf_holdings__matched_fundnos.json before trusting it.")
    elif "mf_holdings__holdings.parquet" in landed:
        rep.warn("converting funds matched", "holdings landed but no match record exists")

    # ---- 6. do the fundamentals/IBES reach our stocks? --------------------
    if {"ccm_link__ccm_link.parquet", "stock_names__stocknames.parquet"} <= landed:
        cl = _read("ccm_link__ccm_link.parquet")
        sn = _read("stock_names__stocknames.parquet")
        pcol = _resolved(spec, "stock_names", "columns", "security_id")
        lcol = _resolved(spec, "ccm_link", "columns", "link_permno")
        if pcol in sn.columns and lcol in cl.columns:
            ours = set(pd.to_numeric(sn[pcol], errors="coerce").dropna().astype(int))
            hit = set(pd.to_numeric(cl[lcol], errors="coerce").dropna().astype(int))
            rate = len(ours & hit) / max(len(ours), 1)
            (rep.warn if rate < MATCH_FLOOR_WARN else rep.ok)(
                "ccm link coverage",
                f"{len(ours & hit):,}/{len(ours):,} permnos have a gvkey ({rate:.1%}). "
                "Non-operating securities (funds, trusts, ADRs) legitimately lack "
                "one, so a shortfall here is not automatically an error.")

    for part, pull, logical, label in [
        ("ibes__summary.parquet", "ibes", "cusip", "ibes summary coverage"),
        ("ibes__actuals.parquet", "ibes", "cusip", "ibes actuals coverage"),
    ]:
        if part not in landed:
            continue
        df = _read(part)
        col = _resolved(spec, pull, "columns", logical)
        if not col or col not in df.columns:
            rep.warn(label, f"cusip column '{col}' not on the file")
            continue
        computed, _ = _read_convexp_cusips()
        universe8 = {c[:8].upper() for c in (computed | _read_dropped_cusips()) if c}
        got = {str(v).upper()[:8] for v in df[col].dropna().unique()}
        rate = len(universe8 & got) / max(len(universe8), 1)
        rep.warn(label, f"{rate:.1%} of our CUSIPs appear. IBES covers analyst-"
                        "followed names only, and 84% of this panel is deciles 1-5 "
                        "— a low rate here is a SAMPLE FACT to report, not a bug.") \
            if rate < MATCH_FLOOR_WARN else rep.ok(label, f"{rate:.1%} of our CUSIPs appear")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    a = ap.parse_args()
    try:
        import pandas  # noqa: F401
    except ImportError:
        sys.exit("NEED pandas: pip install pandas pyarrow")
    rep = Report()
    if not RAW.exists() or not any(RAW.glob("*.parquet")):
        print(f"nothing landed in {RAW.relative_to(ROOT)} yet — run the pulls first.")
        return
    run(rep)
    if a.json:
        print(json.dumps(rep.rows, indent=2))
    else:
        print(rep.render())
    if any(r["level"] == "FAIL" for r in rep.rows):
        sys.exit(1)


if __name__ == "__main__":
    main()
