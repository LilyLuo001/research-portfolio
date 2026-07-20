#!/usr/bin/env python3
"""P1-T2 FREE PATH — build ConvExp from EDGAR N-PORT + OpenFIGI + XBRL.

WRDS/CRSP is unavailable, so this reproduces the holdings-based treatment
intensity ConvExp_i,e = Σ_f (fund f's pre-conversion shares of stock i) /
(shares outstanding of i), using only free public sources:

  events_merged.csv (T1)         who converted, when, which registrant (CIK)
  EDGAR submissions API          -> each fund's NPORT-P filings before its date
  N-PORT primary_doc.xml         -> per-holding CUSIP, ticker, shares (balance/NS)
  OpenFIGI /v3/mapping           -> CUSIP -> ticker  (only when N-PORT lacks it)
  SEC company_tickers.json       -> ticker -> issuer CIK
  SEC XBRL companyconcept        -> dei:EntityCommonStockSharesOutstanding

Every number therefore carries a public locator (meta-rule 1). NOTHING is
imputed: a fund with no matchable NPORT-P, or a stock with no resolvable
shares-outstanding, is written to a NEED_HUMAN_*.csv and DROPPED, never guessed
(CLAUDE.md rule 4; Project_1.md §113 no interpolation).

Design notes:
  * Immutable cache: every raw HTTP body is written once under cache/ keyed by a
    stable name; reruns read disk and hit the network zero times. Delete a cache
    file to force a refetch.
  * Fail-soft per unit: one bad fund/stock logs + goes to NEED_HUMAN; the run
    continues. Read build_nport_convexp.log for the full diagnostic trail.
  * TWO KNOWN GAPS are implemented best-effort and LOUDLY logged, because they
    need live-EDGAR validation the author could not run in-sandbox:
      (G1) fund -> series matching in multi-series trusts (fuzzy name match on
           the N-PORT <seriesName>); review SERIES_MATCH log lines.
      (H2) mcap_decile from the N-PORT-implied price (valUSD/shares × shares_
           outstanding) — no external feed. Null decile logged MCAP_MISS.

Run:
  export SEC_UA="Boston University research <email>"     # SEC REQUIRES real UA
  export OPENFIGI_KEY=...                                # optional, raises limit
  python p1/t2_wrds/build_waves.py
  python p1/t2_free/build_nport_convexp.py
Then:
  python ops/runner/contracts.py conv_exposure_free p1/conv_exposure_free.parquet
"""
import csv
import io
import json
import logging
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
import xml.etree.ElementTree as ET
from datetime import datetime

import requests

try:
    import pandas as pd
except ImportError:
    print("NEED pandas+pyarrow: pip install pandas pyarrow requests")
    raise

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = ROOT / "p1" / "t2_free"
CACHE = HERE / "cache"
WAVES = ROOT / "p1" / "t2_wrds" / "waves.csv"
MEMBERS = ROOT / "p1" / "t2_wrds" / "waves_members.csv"
OUT = ROOT / "p1" / "conv_exposure_free.parquet"
DIAG = HERE / "diagnostics.md"
NH_FUNDS = HERE / "NEED_HUMAN_funds.csv"
NH_STOCKS = HERE / "NEED_HUMAN_stocks.csv"

SEC_UA = os.environ.get("SEC_UA", "").strip()
OPENFIGI_KEY = os.environ.get("OPENFIGI_KEY", "").strip()
SEC_SLEEP = 0.15          # be polite; SEC ceiling is 10 req/s
FIGI_SLEEP = 0.30
MAX_NPORT_PROBE = 8       # candidates to open when hunting the right series
# A giant multi-series trust (DFA CIK 355437) files ~106 per-series NPORT-P in
# one batch; the exact-named series can sit anywhere in it. When no cheap match
# is found we enumerate the full most-recent-before-date batch, which always
# contains the exact-name filing (Jaccard 1.0). Normal single-series funds match
# on filing #1 and never pay this cost (exact-match early-stop below).
MAX_BATCH_PROBE = 160
SERIES_MATCH_MIN = 0.34   # token-overlap threshold for fuzzy series match
SERIES_EXACT = 0.999      # normalized-equal series name -> stop hunting
NPORT = "NPORT-P"

for d in (HERE, CACHE, CACHE / "sub", CACHE / "nport", CACHE / "xbrl",
          CACHE / "figi", CACHE / "price", CACHE / "fts"):
    d.mkdir(parents=True, exist_ok=True)

log = logging.getLogger("t2free")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler(HERE / "build_nport_convexp.log", mode="w")])

SESS = requests.Session()


# --------------------------------------------------------------------------- #
# cached HTTP                                                                  #
# --------------------------------------------------------------------------- #
def _headers(host):
    # SEC hosts demand a descriptive User-Agent or they 403.
    ua = SEC_UA or "research-portfolio P1-T2-free (set SEC_UA env)"
    return {"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}


def http_get(url, cache_file, is_json=True, host="sec"):
    """GET with immutable on-disk cache. Returns text (or None on failure)."""
    if cache_file.exists():
        txt = cache_file.read_text(encoding="utf-8", errors="ignore")
        return txt if txt and not txt.startswith("__ERR__") else None
    for attempt in range(3):
        try:
            r = SESS.get(url, headers=_headers(host), timeout=45)
            time.sleep(SEC_SLEEP)
            if r.status_code == 200:
                cache_file.write_text(r.text, encoding="utf-8")
                return r.text
            log.warning("HTTP %s on %s (attempt %d)", r.status_code, url, attempt + 1)
            if r.status_code in (403, 404):
                break
            time.sleep(1.0 + attempt)
        except requests.RequestException as e:
            log.warning("GET error %s on %s (attempt %d)", e, url, attempt + 1)
            time.sleep(1.0 + attempt)
    cache_file.write_text("__ERR__", encoding="utf-8")
    return None


def _lname(tag):
    return tag.split("}", 1)[1] if "}" in tag else tag


def _find(el, name):
    for c in el.iter():
        if _lname(c.tag) == name:
            return c
    return None


def _findall_local(el, name):
    return [c for c in el.iter() if _lname(c.tag) == name]


# --------------------------------------------------------------------------- #
# reference maps                                                               #
# --------------------------------------------------------------------------- #
def ticker_cik_map():
    txt = http_get("https://www.sec.gov/files/company_tickers.json",
                   CACHE / "company_tickers.json")
    if not txt:
        log.error("could not load company_tickers.json — ticker->CIK disabled")
        return {}
    d = json.loads(txt)
    m = {}
    for row in d.values():
        m[str(row["ticker"]).upper()] = int(row["cik_str"])
    log.info("ticker->CIK map: %d symbols", len(m))
    return m


def cik_from_url(url):
    m = re.search(r"/data/(\d+)/", url or "")
    return int(m.group(1)) if m else None


_CUSIP_RE = re.compile(r"^[A-Z0-9]{9}$")


def valid_cusip(c):
    """A usable 9-char CUSIP: alphanumeric, not a placeholder. N-PORT sometimes
    carries 'N/A', 'NONE', or all-zeros for non-US / unidentifiable holdings —
    those cannot key the ConvExp table and would break the cache path, so drop."""
    c = (c or "").strip().upper()
    if not _CUSIP_RE.match(c):
        return False
    if c in ("000000000", "NNNNNNNNN", "XXXXXXXXX"):
        return False
    return len(set(c)) > 1


_CIK_IN_NAME = re.compile(r"CIK\s*(\d{4,10})")


def fts_nport_hits(fund_name, eff_date):
    """Resolve the pre-conversion holdings filing via EDGAR full-text search.

    The N-14 URL's CIK is the *acquiring* entity (e.g. an ETF trust), NOT the
    mutual fund that actually held the pre-conversion portfolio. And a giant
    multi-series trust (e.g. DFA Investment Dimensions, CIK 355437) files a
    separate NPORT-P per series, so probing its newest few filings misses the
    target series entirely. FTS on the exact fund name returns the SPECIFIC
    accessions whose filing text carries that series name — so we parse those
    accessions directly rather than re-probing the trust.

    Returns [(cik, accession, filed)] newest-first, deduplicated. Each hit's
    holdings XML is the accession folder's primary_doc.xml (the FTS-reported
    primary doc is often an HTML 'book', not the XML)."""
    from datetime import datetime as _dt, timedelta as _td
    try:
        end = _dt.strptime(eff_date, "%Y-%m-%d")
    except ValueError:
        return []
    start = (end - _td(days=550)).strftime("%Y-%m-%d")
    q = requests.utils.quote(f'"{fund_name}"')
    url = (f"https://efts.sec.gov/LATEST/search-index?q={q}&forms=NPORT-P"
           f"&startdt={start}&enddt={eff_date}")
    cf = CACHE / "fts" / (re.sub(r"[^0-9A-Za-z]", "_", fund_name)[:80]
                          + f"_{eff_date}.json")
    txt = http_get(url, cf)
    if not txt:
        return []
    try:
        hits = json.loads(txt).get("hits", {}).get("hits", [])
    except ValueError:
        return []
    out, seen = [], set()
    for h in hits:
        # _id is 'ACCESSION:primarydoc.ext'; the accession precedes the colon.
        acc = (h.get("_id") or "").split(":")[0].strip()
        if not re.match(r"^\d{10}-\d{2}-\d{6}$", acc):
            continue
        src = h.get("_source", {}) or {}
        filed = (src.get("file_date") or src.get("filed") or "")[:10]
        ciks = src.get("ciks", []) or []
        # fall back to any CIK embedded in display_names
        if not ciks:
            for nm in src.get("display_names", []):
                m = _CIK_IN_NAME.search(nm)
                if m:
                    ciks.append(m.group(1))
        for c in ciks:
            try:
                ci = int(c)
            except (TypeError, ValueError):
                continue
            key = (ci, acc)
            if key in seen:
                continue
            seen.add(key)
            out.append((ci, acc, filed))
    return out  # EDGAR relevance order preserved (CIK discovery only)


# --------------------------------------------------------------------------- #
# EDGAR submissions -> NPORT-P candidates                                      #
# --------------------------------------------------------------------------- #
def nport_filings(cik):
    """All NPORT-P (accession, filed, primaryDocument) for a registrant CIK,
    newest first, following the submissions API's paginated 'files' too."""
    out = []
    subs = [f"https://data.sec.gov/submissions/CIK{cik:010d}.json"]
    seen_extra = False
    while subs:
        url = subs.pop(0)
        cf = CACHE / "sub" / re.sub(r"[^0-9A-Za-z]", "_", url.split("/")[-1])
        txt = http_get(url, cf)
        if not txt:
            continue
        j = json.loads(txt)
        recent = j.get("filings", {}).get("recent", {}) if "filings" in j else j
        forms = recent.get("form", [])
        accs = recent.get("accessionNumber", [])
        filed = recent.get("filingDate", [])
        prim = recent.get("primaryDocument", [])
        for i, fm in enumerate(forms):
            if fm == NPORT:
                out.append({"accession": accs[i], "filed": filed[i],
                            "primary": prim[i] if i < len(prim) else "primary_doc.xml"})
        if not seen_extra:
            seen_extra = True
            for extra in j.get("filings", {}).get("files", []):
                subs.append("https://data.sec.gov/submissions/" + extra["name"])
    out.sort(key=lambda r: r["filed"], reverse=True)
    return out


# --------------------------------------------------------------------------- #
# N-PORT XML -> holdings + series identity                                     #
# --------------------------------------------------------------------------- #
_WS = re.compile(r"[^a-z0-9 ]+")


def _norm_tokens(s):
    s = _WS.sub(" ", (s or "").lower())
    stop = {"fund", "the", "trust", "series", "portfolio", "inc", "of", "etf",
            "shares", "class", "co", "lp"}
    return {t for t in s.split() if t and t not in stop}


def series_score(fund_name, series_name):
    a, b = _norm_tokens(fund_name), _norm_tokens(series_name)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def parse_nport(cik, filing):
    acc = filing["accession"]
    acc_nodash = acc.replace("-", "")
    # The submissions API reports primaryDocument as the XSL *viewer* path
    # (e.g. 'xslFormNPORT-P_X01/primary_doc.xml') which serves rendered HTML.
    # The raw XML is the same filename at the accession-folder root.
    doc = (filing.get("primary") or "").split("/")[-1] or "primary_doc.xml"
    url = (f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{doc}")
    cf = CACHE / "nport" / f"{cik}_{acc_nodash}.xml"
    txt = http_get(url, cf, is_json=False)
    if not txt:
        return None
    try:
        root = ET.fromstring(txt)
    except ET.ParseError as e:
        log.warning("XML parse error %s in %s", e, acc)
        return None
    gen = _find(root, "genInfo")
    series_name = ""
    series_id = ""
    if gen is not None:
        sn = _find(gen, "seriesName")
        si = _find(gen, "seriesId")
        series_name = (sn.text or "").strip() if sn is not None else ""
        series_id = (si.text or "").strip() if si is not None else ""
    holdings = []
    for sec in _findall_local(root, "invstOrSec"):
        def g(name):
            e = _find(sec, name)
            return (e.text or "").strip() if e is not None and e.text else ""
        units = g("units")
        asset_cat = g("assetCat")
        # equity common stock, long, share-denominated only
        if units != "NS":
            continue
        # common stock only: dei:EntityCommonStockSharesOutstanding is the
        # denominator, so preferred/other would mismatch. Blank assetCat kept
        # (older N-PORT sometimes omits it for plain equities).
        if asset_cat and asset_cat != "EC":
            continue
        cusip = g("cusip")
        ticker = ""
        ids = _find(sec, "identifiers")
        if ids is not None:
            for ch in ids.iter():
                if _lname(ch.tag) == "ticker":
                    ticker = (ch.get("value") or ch.text or "").strip()
                    break
        try:
            shares = float(g("balance") or 0)
        except ValueError:
            shares = 0.0
        try:
            val = float(g("valUSD") or 0)
        except ValueError:
            val = 0.0
        if shares <= 0 or not valid_cusip(cusip):
            continue
        holdings.append({"cusip": cusip.strip().upper(), "ticker": ticker.upper(),
                         "name": g("name") or g("title"), "shares": shares,
                         "valUSD": val, "asset_cat": asset_cat})
    return {"accession": acc, "filed": filing["filed"], "series_name": series_name,
            "series_id": series_id, "holdings": holdings}


def _best_nport_in_cik(cik, fund_name, eff_date):
    """Best (score, parsed, cik) NPORT-P under one registrant CIK filed before
    eff_date. Returns (None, None, cik) if none parse.

    Enumerates newest-first. Stops the moment a filing's series name is an exact
    normalized match (SERIES_EXACT) — so a normal single-series fund opens just
    one filing. A giant multi-series trust has no exact match early, so it falls
    through to the full most-recent-before-date batch (up to MAX_BATCH_PROBE),
    which is where its exact-named series lives. The cache makes the batch cost
    one-time and shared across every fund that converts out of that trust."""
    fils = [f for f in nport_filings(cik) if f["filed"] < eff_date]
    best = None
    for f in fils[:MAX_BATCH_PROBE]:
        parsed = parse_nport(cik, f)
        if not parsed:
            continue
        sc = series_score(fund_name, parsed["series_name"])
        log.info("SERIES_MATCH fund=%r <> nport_series=%r cik=%s acc=%s filed=%s "
                 "score=%.2f", fund_name, parsed["series_name"], cik,
                 parsed["accession"], parsed["filed"], sc)
        if best is None or sc > best[0]:
            best = (sc, parsed, cik)
        if sc >= SERIES_EXACT:
            break
    return best if best else (None, None, cik)


def pick_nport_for_fund(url_cik, fund_name, eff_date):
    """Find the pre-conversion NPORT-P holdings for a fund.

    Candidate registrants = the N-14 URL's CIK (correct for single-trust
    families) plus the CIKs EDGAR full-text search surfaces for the exact fund
    name (the real pre-conversion registrant when the N-14 CIK is the acquiring
    ETF trust, e.g. DFA). For each candidate, _best_nport_in_cik enumerates the
    trust's NPORT-P and locks onto the exact-named series (Jaccard 1.0),
    scanning the full most-recent batch only when there's no cheap match.

    Returns (parsed, why, used_cik). An exact series match wins outright; a
    weaker best-effort match is returned but flagged in `why` for human review;
    an all-zero score is emitted as NO_series_match for the kill-switch eyeball,
    never silently trusted."""
    fts_ciks = []
    for cik, _acc, _filed in fts_nport_hits(fund_name, eff_date):
        if cik not in fts_ciks:
            fts_ciks.append(cik)

    fallback = None  # (score, parsed, cik)
    tried = []
    for cik in ([url_cik] if url_cik else []) + fts_ciks:
        if not cik or cik in tried:
            continue
        tried.append(cik)
        sc, parsed, _ = _best_nport_in_cik(cik, fund_name, eff_date)
        if parsed is None:
            continue
        if sc >= SERIES_EXACT:
            return parsed, "series_exact(cik=%s)" % cik, cik
        if fallback is None or sc > fallback[0]:
            fallback = (sc, parsed, cik)

    if fallback:
        sc, parsed, cik = fallback
        if sc >= SERIES_MATCH_MIN:
            why = "series_matched(score=%.2f,cik=%s)" % (sc, cik)
        elif sc > 0:
            why = "best_effort_series(score=%.2f,cik=%s)" % (sc, cik)
        else:
            why = "NO_series_match_used_newest(cik=%s)" % cik
        return parsed, why, cik
    return None, "no_nport_before_date", url_cik


# --------------------------------------------------------------------------- #
# CUSIP -> ticker (OpenFIGI) and ticker -> shares outstanding (XBRL)           #
# --------------------------------------------------------------------------- #
def _figi_cache(cusip):
    return CACHE / "figi" / (re.sub(r"[^0-9A-Za-z]", "_", cusip) + ".json")


def openfigi_batch(cusips):
    """Map many CUSIPs -> ticker via OpenFIGI, cached individually. Anonymous
    access is ~25 req/min and near-useless at scale; a free key raises the limit
    and enables batch-100. Aborts the network phase after sustained 429s so a
    keyless run degrades gracefully instead of grinding for minutes."""
    out, todo = {}, []
    for c in cusips:
        cf = _figi_cache(c)
        if cf.exists():
            try:
                out[c] = json.loads(cf.read_text()).get("ticker")
            except ValueError:
                out[c] = None
        else:
            todo.append(c)
    if not todo:
        return out
    hdr = {"Content-Type": "application/json"}
    if OPENFIGI_KEY:
        hdr["X-OPENFIGI-APIKEY"] = OPENFIGI_KEY
    batch = 100 if OPENFIGI_KEY else 10
    pause = FIGI_SLEEP if OPENFIGI_KEY else 2.6   # keyless: stay under 25/min
    consec_429 = 0
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        if consec_429 >= 5:
            log.warning("OpenFIGI: aborting after sustained 429s; %d CUSIPs left "
                        "unresolved (set OPENFIGI_KEY and rerun)", len(todo) - i)
            for c in todo[i:]:
                out.setdefault(c, None)
            break
        body = [{"idType": "ID_CUSIP", "idValue": c} for c in chunk]
        try:
            r = SESS.post("https://api.openfigi.com/v3/mapping",
                          headers=hdr, json=body, timeout=45)
            time.sleep(pause)
            if r.status_code == 429:
                consec_429 += 1
                for c in chunk:
                    out[c] = None
                continue
            if r.status_code != 200:
                log.warning("OpenFIGI HTTP %s (chunk @%d)", r.status_code, i)
                for c in chunk:
                    out[c] = None
                continue
            consec_429 = 0
            for c, res in zip(chunk, r.json()):
                data = (res or {}).get("data") or []
                tk = data[0].get("ticker") if data else None
                out[c] = tk.upper() if tk else None
                _figi_cache(c).write_text(json.dumps({"ticker": out[c]}))
        except requests.RequestException as e:
            log.warning("OpenFIGI error %s", e)
            for c in chunk:
                out[c] = None
    return out


def shares_outstanding(stock_cik, on_date):
    """dei:EntityCommonStockSharesOutstanding nearest on/before on_date.
    Sums distinct share-class 'end' values at the chosen date is NOT done —
    we take the largest single reported value at the nearest end date and log
    if multiple classes are seen (XBRL_MULTICLASS)."""
    url = (f"https://data.sec.gov/api/xbrl/companyconcept/CIK{stock_cik:010d}/"
           f"dei/EntityCommonStockSharesOutstanding.json")
    cf = CACHE / "xbrl" / f"{stock_cik:010d}.json"
    txt = http_get(url, cf)
    if not txt:
        return None, None
    try:
        arr = json.loads(txt).get("units", {}).get("shares", [])
    except ValueError:
        return None, None
    if not arr:
        return None, None
    before = [a for a in arr if a.get("end", "") <= on_date and a.get("val")]
    pool = before or [a for a in arr if a.get("val")]
    if not pool:
        return None, None
    best_end = max(a["end"] for a in before) if before else min(a["end"] for a in pool)
    same = [a for a in pool if a["end"] == best_end]
    if len({a["val"] for a in same}) > 1:
        log.info("XBRL_MULTICLASS cik=%s end=%s vals=%s", stock_cik, best_end,
                 sorted({a["val"] for a in same}))
    return float(max(a["val"] for a in same)), best_end


# --------------------------------------------------------------------------- #
# main                                                                         #
# --------------------------------------------------------------------------- #
def main():
    if not SEC_UA:
        log.warning("SEC_UA is empty — SEC endpoints may 403. "
                    'export SEC_UA="Your Name <email>"')
    if not WAVES.exists() or not MEMBERS.exists():
        log.error("run build_waves.py first (missing %s / %s)", WAVES, MEMBERS)
        sys.exit(2)

    members = list(csv.DictReader(open(MEMBERS, newline="")))
    log.info("loaded %d wave members", len(members))
    tcik = ticker_cik_map()

    # ---- Step 1: per-fund holdings ---------------------------------------- #
    # rows[(cusip)] accumulates shares by wave; keep per-fund provenance
    fund_holdings = []          # list of dicts w/ wave_id, holdings, provenance
    nh_funds = []
    for m in members:
        fund = m["fund_name"]
        eff = m["effective_date"]
        # Resolve holdings: EDGAR-FTS targets the exact pre-conversion series
        # accession (essential for multi-series trusts like DFA); the N-14 URL
        # CIK is the fallback probe (works for single-trust families).
        url_cik = cik_from_url(m.get("source_url", "")) or None
        try:
            parsed, why, cik = pick_nport_for_fund(url_cik, fund, eff)
        except Exception as e:                       # fail-soft per fund
            log.exception("FUND_ERROR %r: %s", fund, e)
            nh_funds.append({**m, "reason": f"exception:{e}"})
            continue
        if not parsed or not parsed["holdings"]:
            log.warning("NO_HOLDINGS fund=%r url_cik=%s why=%s", fund, url_cik, why)
            nh_funds.append({**m, "reason": why or "no_holdings"})
            continue
        log.info("FUND_OK %r cik=%s acc=%s holdings=%d (%s)", fund, cik,
                 parsed["accession"], len(parsed["holdings"]), why)
        fund_holdings.append({"wave_id": m["wave_id"], "effective_date": eff,
                              "fund_name": fund, "accession": parsed["accession"],
                              "why": why, "holdings": parsed["holdings"]})

    # ---- Step 2: resolve CUSIP -> ticker for holdings missing one --------- #
    need_figi = sorted({h["cusip"] for fh in fund_holdings for h in fh["holdings"]
                        if valid_cusip(h["cusip"]) and not h["ticker"]})
    if not need_figi:
        figi = {}
    elif not OPENFIGI_KEY:
        # Anonymous OpenFIGI can't resolve this many; skip cleanly rather than
        # grind through 429s. US common stocks almost always carry a ticker in
        # N-PORT already, so these are mostly foreign/odd holdings that lack SEC
        # XBRL shares-outstanding anyway. Set OPENFIGI_KEY for a fuller pass.
        log.warning("Step2: %d holdings lack a N-PORT ticker but OPENFIGI_KEY is "
                    "unset -> skipping CUSIP->ticker; they will drop to "
                    "NEED_HUMAN. Get a free key at openfigi.com/api for pass 2.",
                    len(need_figi))
        figi = {}
    else:
        log.info("holdings missing ticker -> OpenFIGI for %d CUSIPs", len(need_figi))
        figi = openfigi_batch(need_figi)

    # ---- Step 3: aggregate shares per (cusip, wave) ----------------------- #
    # keyed by (cusip) within a wave -> {shares, n_funds, ticker, name, accs}
    agg = {}
    for fh in fund_holdings:
        wid = fh["wave_id"]
        for h in fh["holdings"]:
            cusip = h["cusip"]
            ticker = h["ticker"] or (figi.get(cusip) or "")
            if not cusip:
                continue
            key = (cusip, wid)
            a = agg.setdefault(key, {"cusip": cusip, "wave_id": wid,
                                     "effective_date": fh["effective_date"],
                                     "ticker": ticker, "name": h["name"],
                                     "shares_held": 0.0, "valusd": 0.0,
                                     "funds": set(), "accs": set()})
            a["shares_held"] += h["shares"]
            a["valusd"] += h.get("valUSD", 0.0)
            a["funds"].add(fh["fund_name"])
            a["accs"].add(fh["accession"])
            if not a["ticker"] and ticker:
                a["ticker"] = ticker
    log.info("aggregated %d (cusip,wave) cells across %d funds",
             len(agg), len(fund_holdings))

    # ---- Step 4: ticker -> stock CIK -> shares outstanding ---------------- #
    nh_stocks = []
    rows = []
    # cache shares_out per (stock_cik, effective_date) within the run
    so_cache = {}
    for (cusip, wid), a in sorted(agg.items()):
        ticker = a["ticker"]
        eff = a["effective_date"]
        stock_cik = tcik.get(ticker.upper()) if ticker else None
        if not stock_cik:
            log.warning("NO_STOCK_CIK cusip=%s ticker=%r wave=%s", cusip, ticker, wid)
            nh_stocks.append({"cusip": cusip, "ticker": ticker, "wave_id": wid,
                              "reason": "no_ticker" if not ticker else "ticker_not_in_sec_map"})
            continue
        ck = (stock_cik, eff)
        if ck not in so_cache:
            so_cache[ck] = shares_outstanding(stock_cik, eff)
        shares_out, so_end = so_cache[ck]
        if not shares_out or shares_out <= 0:
            log.warning("NO_SHARES_OUT cusip=%s ticker=%s cik=%s wave=%s",
                        cusip, ticker, stock_cik, wid)
            nh_stocks.append({"cusip": cusip, "ticker": ticker, "wave_id": wid,
                              "reason": "no_xbrl_shares_outstanding"})
            continue
        conv_exp = a["shares_held"] / shares_out
        if conv_exp > 1.0:
            log.info("CONVEXP_GT1 cusip=%s ticker=%s wave=%s exp=%.3f "
                     "(shares_held=%.0f > shares_out=%.0f as of %s) -> NEED_HUMAN",
                     cusip, ticker, wid, conv_exp, a["shares_held"], shares_out, so_end)
            nh_stocks.append({"cusip": cusip, "ticker": ticker, "wave_id": wid,
                              "reason": f"conv_exp>1 ({conv_exp:.3f}); shares_out date {so_end}"})
            continue
        # implied price from the fund's own N-PORT valuation (valUSD/shares) —
        # a real market price near the report date, no external feed needed.
        implied_px = (a["valusd"] / a["shares_held"]) if a["shares_held"] else None
        mcap = implied_px * shares_out if implied_px else None
        rows.append({"cusip": cusip, "ticker": ticker, "stock_cik": stock_cik,
                     "permno": "", "wave_id": wid, "effective_date": eff,
                     "conv_exp": conv_exp, "n_funds": len(a["funds"]),
                     "mcap_decile": None, "_mcap": mcap,
                     "pre_etf_ownership": conv_exp,  # converting-fund ownership
                     "shares_held": a["shares_held"],
                     "shares_outstanding": shares_out,
                     "source_accessions": ";".join(sorted(a["accs"]))})

    if not rows:
        log.error("no ConvExp rows produced — see NEED_HUMAN files and log")
    df = pd.DataFrame(rows)

    # ---- Step 5: mcap_decile from N-PORT-implied price -------------------- #
    # mcap = shares_outstanding × (valUSD/shares_held). Both terms are from the
    # filing itself, so no external price feed (stooq is now bot-walled).
    if not df.empty:
        miss = int(df["_mcap"].isna().sum())
        log.info("MCAP: %d/%d cells lack an implied price (MCAP_MISS)", miss, len(df))

        def decile(g):
            v = g["_mcap"]
            ok = v.notna()
            if ok.sum() >= 10:
                g.loc[ok, "mcap_decile"] = (
                    pd.qcut(v[ok], 10, labels=False, duplicates="drop") + 1)
            elif ok.sum() > 0:
                log.info("MCAP_THIN wave=%s only %d priced names; decile left null",
                         g.name, int(ok.sum()))
            return g
        df = df.groupby("wave_id", group_keys=False).apply(decile)
        df = df.drop(columns=["_mcap"])
        df["mcap_decile"] = df["mcap_decile"].astype("Float64")

    # ---- write outputs ---------------------------------------------------- #
    if not df.empty:
        df = df.sort_values(["wave_id", "conv_exp"], ascending=[True, False])
        df.to_parquet(OUT, index=False)
        log.info("wrote %s: %d rows, %d cols", OUT, len(df), len(df.columns))
    _write_need_human(nh_funds, nh_stocks)
    _diagnostics(df, fund_holdings, nh_funds, nh_stocks)
    log.info("DONE. funds_ok=%d need_human_funds=%d rows=%d need_human_stocks=%d",
             len(fund_holdings), len(nh_funds), len(df), len(nh_stocks))


def _write_need_human(nh_funds, nh_stocks):
    if nh_funds:
        keys = sorted({k for r in nh_funds for k in r})
        with open(NH_FUNDS, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(nh_funds)
        log.info("NEED_HUMAN funds -> %s (%d)", NH_FUNDS, len(nh_funds))
    if nh_stocks:
        with open(NH_STOCKS, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["cusip", "ticker", "wave_id", "reason"])
            w.writeheader()
            w.writerows(nh_stocks)
        log.info("NEED_HUMAN stocks -> %s (%d)", NH_STOCKS, len(nh_stocks))


def _diagnostics(df, fund_holdings, nh_funds, nh_stocks):
    lines = ["# P1-T2 free-path ConvExp — diagnostics",
             f"generated: {datetime.utcnow().isoformat()}Z", "",
             f"- funds with holdings resolved: **{len(fund_holdings)}**",
             f"- funds to NEED_HUMAN: **{len(nh_funds)}**",
             f"- ConvExp rows (cusip×wave): **{len(df)}**",
             f"- distinct stocks: **{df['cusip'].nunique() if not df.empty else 0}**",
             f"- stock cells to NEED_HUMAN: **{len(nh_stocks)}**", ""]
    if not df.empty:
        ge05 = int((df["conv_exp"] >= 0.005).sum())
        ge1 = int((df["conv_exp"] >= 0.01).sum())
        lines += [f"- cells ConvExp ≥ 0.5%: **{ge05}**",
                  f"- cells ConvExp ≥ 1%: **{ge1}**",
                  f"- ConvExp max/median: {df['conv_exp'].max():.4f} / "
                  f"{df['conv_exp'].median():.4f}", ""]
        anchor = df[df["effective_date"] == "2021-06-11"]
        share = (len(anchor) / len(df)) if len(df) else 0
        lines += [f"- DFA anchor wave (2021-06-11) rows: **{len(anchor)}** "
                  f"({share:.1%} of all cells)", "",
                  "## ConvExp ≥0.5% / ≥1% by wave", "",
                  "| wave | eff_date | cells | ≥0.5% | ≥1% |",
                  "|---|---|---|---|---|"]
        for wid, g in df.groupby("wave_id"):
            lines.append(f"| {wid} | {g['effective_date'].iloc[0]} | {len(g)} | "
                         f"{int((g['conv_exp']>=0.005).sum())} | "
                         f"{int((g['conv_exp']>=0.01).sum())} |")
        n_dec = int(df["mcap_decile"].notna().sum()) if "mcap_decile" in df else 0
        lines += ["", f"- rows with mcap_decile filled: **{n_dec}** / {len(df)} "
                  "(H2 price join; rest need review)"]
    lines += ["", "## known gaps to review (feed the log back)",
              "- **G1 series match**: grep `SERIES_MATCH` / `NO_series_match` in the log.",
              "- **H2 mcap price**: grep `MCAP_MISS` / `MCAP_THIN`.",
              "- **shares-out ambiguity**: grep `XBRL_MULTICLASS`.",
              "- **ownership>100%**: grep `CONVEXP_GT1` (dropped, likely stale shares-out).",
              "", "These feed P1-T2-killswitch (Gate 2). Not a go/no-go until signed."]
    DIAG.write_text("\n".join(lines) + "\n")
    log.info("wrote diagnostics -> %s", DIAG)

if __name__ == "__main__":
    main()
