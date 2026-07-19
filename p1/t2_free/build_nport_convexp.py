#!/usr/bin/env python3
"""P1-T2 FREE path — ConvExp from EDGAR N-PORT + OpenFIGI + XBRL. BOX (needs net).

Replaces the WRDS/CRSP holdings pipeline with 100%-free, provenance-clean public
sources (meta-rule 1 satisfied: every number carries an EDGAR/OpenFIGI locator):

  fund holdings           -> SEC EDGAR NPORT-P (each converting fund's last monthly
                             holdings filing before its effective_date)
  CUSIP -> ticker         -> N-PORT's own identifiers, else OpenFIGI (free)
  ticker -> stock CIK     -> SEC company_tickers.json
  shares outstanding      -> SEC XBRL companyconcept dei:EntityCommonStockSharesOutstanding
  ConvExp_{i,e}           -> Σ_f (fund f's share holding of i) / shares_outstanding_i

Keyed on public CUSIP (no free CRSP permno). Output conforms to
ops/contracts/conv_exposure_free.yaml; a cusip<->ticker<->cik crosswalk lets a
later CRSP merge recover permno. Every raw pull is cached immutable under
p1/t2_free/cache/ so re-runs are free and auditable.

Run on box (internet + a polite SEC User-Agent required):
  export SEC_UA="Boston University research <your-email>"      # SEC requires a UA
  python p1/t2_free/build_nport_convexp.py

Inputs already in repo: p1/events_merged.csv, p1/t2_wrds/waves.csv,
p1/t1_arb/id_meta.json (trust CIK per accession).
"""
import csv
import json
import os
import pathlib
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
P1 = HERE.parent
EVENTS = P1 / "events_merged.csv"
WAVES = P1 / "t2_wrds" / "waves.csv"
IDMETA = P1 / "t1_arb" / "id_meta.json"
CACHE = HERE / "cache"
OUT = P1 / "conv_exposure_free.parquet"
XWALK = HERE / "cusip_ticker_cik_crosswalk.csv"
DIAG = HERE / "convexp_free_diagnostics.md"
NEED_FUND = HERE / "unresolved_funds.csv"
NEED_STOCK = HERE / "unresolved_stocks.csv"

UA = os.getenv("SEC_UA", "research-agent contact@example.com")
SEC = "https://data.sec.gov"
ARCH = "https://www.sec.gov/Archives/edgar/data"
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CIKRE = re.compile(r"CIK\s*0*([0-9]{1,10})", re.I)


def _get(url, kind="json", tries=4):
    import requests
    CACHE.mkdir(exist_ok=True)
    key = re.sub(r"[^A-Za-z0-9]+", "_", url)[-180:]
    cp = CACHE / (key + ("." + kind if kind != "raw" else ".bin"))
    if cp.exists():
        return json.loads(cp.read_text()) if kind == "json" else cp.read_text(errors="ignore")
    for i in range(tries):
        try:
            r = requests.get(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"}, timeout=45)
            if r.status_code == 200:
                cp.write_text(r.text)
                return r.json() if kind == "json" else r.text
            if r.status_code in (403, 404):
                return None
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1.5 * (i + 1))     # SEC fair-use: <=10 req/s; back off on error
    return None


def _post_openfigi(cusips):
    """CUSIP -> ticker via OpenFIGI (free; add OPENFIGI_KEY for higher limits)."""
    import requests
    out, key = {}, os.getenv("OPENFIGI_KEY")
    hdr = {"Content-Type": "application/json"}
    if key:
        hdr["X-OPENFIGI-APIKEY"] = key
    uniq = [c for c in sorted(set(cusips)) if c]
    for i in range(0, len(uniq), 10):          # 10/req unauth, 100/req with key
        batch = uniq[i:i + (100 if key else 10)]
        body = [{"idType": "ID_CUSIP", "idValue": c} for c in batch]
        try:
            r = requests.post("https://api.openfigi.com/v3/mapping", headers=hdr,
                              json=body, timeout=45)
            if r.status_code == 200:
                for c, res in zip(batch, r.json()):
                    d = (res or {}).get("data") or []
                    if d:
                        out[c] = d[0].get("ticker")
            time.sleep(0.3 if key else 3.0)
        except Exception:  # noqa: BLE001
            time.sleep(3.0)
    return out


# ---- Stage A: fund -> (trust_cik, series_id) --------------------------------
def resolve_funds(events, idmeta):
    mf_map = _get("https://www.sec.gov/files/company_tickers_mf.json") or {}
    by_ticker = {}
    # company_tickers_mf.json shape: {"fields":[...], "data":[[cik, seriesId, classId, symbol],...]}
    rows = mf_map.get("data", []) if isinstance(mf_map, dict) else []
    for row in rows:
        try:
            cik, series, klass, sym = row
            by_ticker[str(sym).upper()] = (int(cik), str(series))
        except Exception:  # noqa: BLE001
            continue
    resolved, unresolved = [], []
    for e in events:
        tkr = (e.get("mutual_fund_ticker") or "NA").strip().upper()
        m = idmeta.get(e["source_accession"], {})
        trust = CIKRE.search(m.get("company", "") or "")
        trust_cik = int(trust.group(1)) if trust else None
        if tkr in by_ticker:
            cik, series = by_ticker[tkr]
            resolved.append({**e, "trust_cik": cik, "series_id": series})
        elif trust_cik:
            # no ticker: fall back to the trust CIK; series matched by name at N-PORT time
            resolved.append({**e, "trust_cik": trust_cik, "series_id": ""})
        else:
            unresolved.append(e)
    return resolved, unresolved


# ---- Stage B/C: latest pre-conversion N-PORT holdings -----------------------
def nport_holdings(fund):
    """Return list of {cusip,name,ticker,shares,val} equity holdings from the fund's
    last NPORT-P before effective_date. Series filtered when series_id known."""
    cik10 = f"{fund['trust_cik']:010d}"
    sub = _get(f"{SEC}/submissions/CIK{cik10}.json")
    if not sub:
        return None, "no submissions"
    recent = sub.get("filings", {}).get("recent", {})
    forms = recent.get("form", []); accs = recent.get("accessionNumber", [])
    dates = recent.get("reportDate", []) or recent.get("filingDate", [])
    eff = fund["effective_date"]
    cands = [(dates[i], accs[i]) for i in range(len(forms))
             if forms[i].startswith("NPORT-P") and dates[i] and dates[i] < eff]
    if not cands:
        return None, "no NPORT-P before effective_date"
    _, acc = max(cands)                       # latest report period before conversion
    accnd = acc.replace("-", "")
    xml = _get(f"{ARCH}/{fund['trust_cik']}/{accnd}/primary_doc.xml", kind="raw")
    if not xml:
        return None, f"NPORT xml not fetched ({acc})"
    return parse_nport(xml, fund.get("series_id", "")), acc


def parse_nport(xml, series_id):
    """Minimal N-PORT holdings parse (namespace-agnostic regex over <invstOrSec>)."""
    out = []
    for blk in re.findall(r"<invstOrSec\b.*?</invstOrSec>", xml, re.S):
        def g(tag):
            m = re.search(rf"<(?:\w+:)?{tag}\b[^>]*>(.*?)</(?:\w+:)?{tag}>", blk, re.S)
            return (m.group(1).strip() if m else "")
        assetcat = g("assetCat")
        if assetcat and assetcat.upper() not in ("EC", "COMMON", "EQUITY-COMMON"):
            continue                          # equities only
        cusip = g("cusip")
        m = re.search(r'<(?:\w+:)?identifiers>(.*?)</(?:\w+:)?identifiers>', blk, re.S)
        ident = m.group(1) if m else ""
        tk = re.search(r'ticker[^>]*value="([^"]+)"', ident) or re.search(r"<ticker>([^<]+)</ticker>", ident)
        ticker = tk.group(1).strip() if tk else ""
        shares = g("balance")
        units = g("units")
        if units and units.upper() not in ("NS", "SHARES"):
            continue                          # share-denominated positions only
        try:
            sh = float(shares)
        except ValueError:
            continue
        if sh <= 0 or not (cusip or ticker):
            continue
        out.append({"cusip": cusip.upper(), "name": g("name"), "ticker": ticker.upper(),
                    "shares": sh, "val": g("valUSD")})
    return out


# ---- Stage E: shares outstanding via XBRL -----------------------------------
def shares_outstanding(stock_cik, eff):
    j = _get(f"{SEC}/api/xbrl/companyconcept/CIK{int(stock_cik):010d}"
             f"/dei/EntityCommonStockSharesOutstanding.json")
    if not j:
        return None
    best = None
    for u in j.get("units", {}).get("shares", []):
        end = u.get("end", "")
        if end and end <= eff and (best is None or end > best[0]):
            best = (end, u.get("val"))
    return float(best[1]) if best and best[1] else None


def main():
    if UA.endswith("example.com"):
        print("WARN: set SEC_UA to a real contact — SEC throttles anonymous UAs.", file=sys.stderr)
    events = list(csv.DictReader(EVENTS.open()))
    waves = {w["source_accessions"]: w for w in csv.DictReader(WAVES.open())}
    # map accession -> wave_id
    acc2wave = {}
    for w in csv.DictReader(WAVES.open()):
        for a in w["source_accessions"].split("|"):
            acc2wave[a] = (w["wave_id"], w["effective_date"])
    idmeta = json.loads(IDMETA.read_text())
    ticker2cik = _ticker_cik_map()

    resolved, unresolved_funds = resolve_funds(
        [e for e in events if ISO.match(e.get("effective_date", ""))], idmeta)

    # gather holdings per fund
    holdings, no_hold = [], []
    for f in resolved:
        wv = acc2wave.get(f["source_accession"])
        if not wv:
            continue
        f["wave_id"], f["effective_date"] = wv
        h, note = nport_holdings(f)
        if not h:
            no_hold.append({**f, "note": note}); continue
        for row in h:
            holdings.append({**row, "wave_id": f["wave_id"], "effective_date": f["effective_date"]})

    # resolve stock identity (ticker + cik) and shares outstanding
    cusip_need = [h["cusip"] for h in holdings if not h["ticker"] and h["cusip"]]
    figi = _post_openfigi(cusip_need) if cusip_need else {}
    xwalk, need_stock = {}, []
    convexp = {}     # (cusip, wave_id) -> {shares_sum, n_funds, eff, ticker, cik, so}
    for h in holdings:
        cusip = h["cusip"]; tkr = h["ticker"] or figi.get(cusip, "")
        cik = ticker2cik.get(tkr.upper()) if tkr else None
        xwalk[cusip] = (tkr, cik or "")
        key = (cusip, h["wave_id"])
        d = convexp.setdefault(key, {"shares": 0.0, "n_funds": 0, "eff": h["effective_date"],
                                     "ticker": tkr, "cik": cik})
        d["shares"] += h["shares"]; d["n_funds"] += 1

    rows = []
    so_cache = {}
    for (cusip, wave_id), d in convexp.items():
        cik = d["cik"]
        so = None
        if cik:
            so = so_cache.get((cik, d["eff"]))
            if so is None:
                so = shares_outstanding(cik, d["eff"]); so_cache[(cik, d["eff"])] = so
        if not so or so <= 0:
            need_stock.append({"cusip": cusip, "ticker": d["ticker"], "wave_id": wave_id,
                               "reason": "no shares_outstanding" if cik else "no stock CIK"})
            continue
        rows.append({"stock_cusip": cusip, "ticker": d["ticker"], "stock_cik": cik,
                     "wave_id": wave_id, "effective_date": d["eff"],
                     "conv_exp": d["shares"] / so, "n_funds": d["n_funds"],
                     "mcap_decile": "", "pre_etf_ownership": ""})

    _write(rows, xwalk, unresolved_funds, no_hold, need_stock, waves)


def _ticker_cik_map():
    j = _get("https://www.sec.gov/files/company_tickers.json") or {}
    out = {}
    for _, v in (j.items() if isinstance(j, dict) else []):
        try:
            out[str(v["ticker"]).upper()] = int(v["cik_str"])
        except Exception:  # noqa: BLE001
            continue
    return out


def _write(rows, xwalk, unresolved_funds, no_hold, need_stock, waves):
    import pandas as pd
    # market-cap decile within the full cross-section (needs a price; approx from
    # XBRL is out of scope here -> leave decile blank, box may add a free price join)
    df = pd.DataFrame(rows, columns=["stock_cusip", "ticker", "stock_cik", "wave_id",
                                     "effective_date", "conv_exp", "n_funds",
                                     "mcap_decile", "pre_etf_ownership"])
    df.to_parquet(OUT, index=False)
    with XWALK.open("w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["cusip", "ticker", "stock_cik"])
        for c, (t, k) in sorted(xwalk.items()):
            w.writerow([c, t, k])
    for path, data in [(NEED_FUND, unresolved_funds + no_hold), (NEED_STOCK, need_stock)]:
        if data:
            keys = sorted({k for d in data for k in d})
            with path.open("w", newline="") as fh:
                wr = csv.DictWriter(fh, fieldnames=keys); wr.writeheader(); wr.writerows(data)
    # diagnostics (kill-switch gate 2)
    L = ["# ConvExp (FREE / EDGAR path) diagnostics\n",
         f"- (cusip×wave) rows: {len(df)}",
         f"- distinct stocks: {df['stock_cusip'].nunique() if len(df) else 0}",
         f"- stocks ConvExp>=0.5%: {(df['conv_exp']>=0.005).sum() if len(df) else 0}",
         f"- stocks ConvExp>=1.0%: {(df['conv_exp']>=0.010).sum() if len(df) else 0}",
         f"- unresolved funds / no-holdings: {len(unresolved_funds)+len(no_hold)}",
         f"- stocks dropped (no shares-out / CIK): {len(need_stock)}"]
    if len(df):
        anchor = {w["wave_id"] for w in csv.DictReader(WAVES.open()) if w["is_anchor"] == "1"}
        a = df[df["wave_id"].isin(anchor)]
        L.append(f"- DFA anchor wave rows: {len(a)}, >=0.5%: {(a['conv_exp']>=0.005).sum()}")
        L.append("\n## ConvExp distribution\n" + df["conv_exp"].describe().to_string())
    DIAG.write_text("\n".join(L) + "\n")
    print(f"conv_exposure_free.parquet: {len(df)} rows | xwalk {len(xwalk)} cusips | "
          f"unresolved funds {len(unresolved_funds)+len(no_hold)}, dropped stocks {len(need_stock)}. "
          f"Validate: python ops/runner/contracts.py conv_exposure_free {OUT}")


if __name__ == "__main__":
    main()
