#!/usr/bin/env python3
"""P1-T2-wrds — holdings pipeline + ConvExp construction. BOX/WRDS-ONLY.

Runs on the WRDS cloud (needs the `wrds` package + owner-injected credentials).
Implements Project_1.md §T2 verbatim:

  ConvExp_{i,e} = Σ_f (converting fund f's pre-conversion share holding of stock i)
                  / (CRSP shares outstanding of i)        [shrout is in THOUSANDS: ×1000]
  wave e        = conversions sharing an effective_date (p1/t2_wrds/waves.csv;
                  DFA 2021-06-11 = anchor)

Output (frozen contract ops/contracts/conv_exposure.yaml):
  conv_exposure.parquet: permno | wave_id | effective_date | conv_exp | n_funds
                         | mcap_decile | pre_etf_ownership
Diagnostic (kill-switch gate 2 input): ConvExp histogram, #stocks ConvExp>=0.5%
and >=1% per wave, DFA-wave share -> p1/t2_wrds/convexp_diagnostics.md

Meta-rule 1: every number here is CODE-ON-REAL-DATA. No holding, shrout, or
mapping is ever hand-filled; a fund that cannot be mapped to a pre-conversion
holdings report is emitted to the NEED_HUMAN list, never imputed.

Run on box:  python p1/t2_wrds/holdings_pipeline.py
             (WRDS creds via ~/.pgpass or WRDS_USER/WRDS_PASS; see README)
"""
import csv
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
WAVES = HERE / "waves.csv"
EVENTS = HERE.parent / "events_merged.csv"
OUT_PARQUET = HERE.parent / "conv_exposure.parquet"
DIAG = HERE / "convexp_diagnostics.md"
NEED_HUMAN = HERE / "unmapped_funds.csv"


def connect():
    try:
        import wrds
    except ImportError:
        sys.exit("NEED_HUMAN: `wrds` package not installed — run on the WRDS cloud node.")
    try:
        return wrds.Connection(wrds_username=os.getenv("WRDS_USER"))
    except Exception as e:  # noqa: BLE001
        sys.exit(f"NEED_HUMAN: WRDS auth failed ({e}). Fix ~/.pgpass / WRDS_USER "
                 "(note: username is case-sensitive; the earlier .pgpass didn't auto-auth).")


# ---- fund identity -> CRSP MF fundno / N-PORT CIK ---------------------------
def map_funds(db, events):
    """Map each converting fund (name / MF ticker / EDGAR accession) to a CRSP MF
    crsp_fundno via MFLINK/ticker, so its holdings can be pulled. Funds absent
    from CRSP MF fall back to their EDGAR N-PORT (CIK from source_accession).
    Returns (mapping, unmapped). Owner/box refines the matcher; unmapped -> file."""
    mapping, unmapped = [], []
    # crsp.fund_hdr / crsp_names carry ticker + fund name; match on MF ticker when
    # present (exact), else fuzzy fund_name within the family, else N-PORT by CIK.
    for e in events:
        mfticker = (e.get("mutual_fund_ticker") or "NA").strip()
        hit = None
        if mfticker not in ("NA", ""):
            q = ("select crsp_fundno, fund_name, ticker from crsp.fund_hdr "
                 f"where ticker = '{mfticker}'")
            df = db.raw_sql(q)
            if len(df):
                hit = int(df.iloc[0]["crsp_fundno"])
        if hit is None:
            unmapped.append(e)            # box: add fuzzy-name + N-PORT fallback here
        else:
            mapping.append({**e, "crsp_fundno": hit})
    return mapping, unmapped


# ---- pre-conversion holdings -> ConvExp ------------------------------------
def convexp_for_wave(db, wave_id, eff_date, funds):
    """Σ_f holding shares / shrout(×1000), per permno, for one wave."""
    fundnos = [f["crsp_fundno"] for f in funds if f.get("crsp_fundno")]
    if not fundnos:
        return []
    inlist = ",".join(str(n) for n in fundnos)
    # last holdings report per fund strictly BEFORE the effective date
    holdings = db.raw_sql(f"""
        with last_rpt as (
          select crsp_fundno, max(report_dt) report_dt
          from crsp.holdings
          where crsp_fundno in ({inlist}) and report_dt < date '{eff_date}'
          group by crsp_fundno)
        select h.crsp_fundno, h.permno, h.nbr_shares
        from crsp.holdings h join last_rpt l
          on h.crsp_fundno = l.crsp_fundno and h.report_dt = l.report_dt
        where h.permno is not null and h.nbr_shares > 0
    """)
    if not len(holdings):
        return []
    # shares outstanding (thousands) at the month-end before eff_date, + mcap decile
    permnos = ",".join(str(int(p)) for p in holdings["permno"].unique())
    shr = db.raw_sql(f"""
        select permno, shrout, prc, date
        from crsp.msf
        where permno in ({permnos})
          and date = (select max(date) from crsp.msf where date < date '{eff_date}')
    """)
    shrout = {int(r.permno): (r.shrout or 0) * 1000.0 for r in shr.itertuples()}  # ×1000 units
    mcap = {int(r.permno): abs((r.prc or 0)) * ((r.shrout or 0) * 1000.0) for r in shr.itertuples()}
    # decile within this cross-section (box may switch to CRSP cap decile breakpoints)
    import numpy as np
    caps = sorted(v for v in mcap.values() if v > 0)
    def decile(c):
        if c <= 0 or not caps:
            return ""
        return int(min(10, 1 + int(10 * (np.searchsorted(caps, c) / len(caps)))))

    agg = {}
    for r in holdings.itertuples():
        p = int(r.permno)
        agg.setdefault(p, [0.0, 0])
        agg[p][0] += float(r.nbr_shares or 0)
        agg[p][1] += 1
    out = []
    for p, (sh, nf) in agg.items():
        so = shrout.get(p, 0.0)
        if so <= 0:
            continue                    # cannot compute exposure without shrout -> skip, not impute
        out.append({"permno": p, "wave_id": wave_id, "effective_date": eff_date,
                    "conv_exp": sh / so, "n_funds": nf, "mcap_decile": decile(mcap.get(p, 0)),
                    "pre_etf_ownership": ""})   # box: fill from 13F/CRSP ETF-holdings join
    return out


def main():
    waves = list(csv.DictReader(WAVES.open()))
    events = list(csv.DictReader(EVENTS.open()))
    ev_by_acc = {}
    for e in events:
        ev_by_acc.setdefault(e["source_accession"], e)

    db = connect()
    mapping, unmapped = map_funds(db, events)
    fundno_by_acc = {m["source_accession"]: m for m in mapping}

    rows = []
    for w in waves:
        accs = w["source_accessions"].split("|")
        funds = [fundno_by_acc[a] for a in accs if a in fundno_by_acc]
        rows += convexp_for_wave(db, w["wave_id"], w["effective_date"], funds)

    import pandas as pd
    df = pd.DataFrame(rows, columns=["permno", "wave_id", "effective_date", "conv_exp",
                                     "n_funds", "mcap_decile", "pre_etf_ownership"])
    df.to_parquet(OUT_PARQUET, index=False)

    if unmapped:
        with NEED_HUMAN.open("w", newline="") as fh:
            wtr = csv.DictWriter(fh, fieldnames=list(unmapped[0].keys()))
            wtr.writeheader(); wtr.writerows(unmapped)

    _diagnostics(df, waves)
    print(f"conv_exposure.parquet: {len(df)} (permno×wave) rows; "
          f"{len(unmapped)} funds unmapped -> {NEED_HUMAN.name}. "
          f"Validate: python ops/runner/contracts.py conv_exposure {OUT_PARQUET}")


def _diagnostics(df, waves):
    import pandas as pd
    anchor = {w["wave_id"] for w in waves if w["is_anchor"] == "1"}
    L = ["# ConvExp diagnostics (kill-switch gate 2 input)\n",
         f"- permno×wave rows: {len(df)}",
         f"- distinct stocks: {df['permno'].nunique() if len(df) else 0}",
         f"- stocks ConvExp >= 0.5%: {(df['conv_exp'] >= 0.005).sum() if len(df) else 0}",
         f"- stocks ConvExp >= 1.0%: {(df['conv_exp'] >= 0.010).sum() if len(df) else 0}"]
    if len(df):
        a = df[df["wave_id"].isin(anchor)]
        L.append(f"- DFA anchor wave: {len(a)} stock-rows, "
                 f"{(a['conv_exp'] >= 0.005).sum()} with ConvExp>=0.5% "
                 f"({100*len(a)/max(1,len(df)):.1f}% of all rows)")
        L.append("\n## ConvExp distribution")
        L.append(df["conv_exp"].describe().to_string())
        L.append("\n## per-wave stocks >=0.5%")
        g = df[df["conv_exp"] >= 0.005].groupby("wave_id").size()
        L.append(g.to_string() if len(g) else "(none)")
    DIAG.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
