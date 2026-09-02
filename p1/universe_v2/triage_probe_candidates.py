"""Read what actually happened to each fund the N-CEN probe flagged.

The probe finds a shape, not an event. A non-ETF series stopping while a
similarly named ETF starts is what a conversion looks like, but it is also what a
liquidation next to an unrelated launch looks like, and liquidation is the modal
way a small fund leaves N-CEN. The shape cannot separate those; the registrant's
own filings can.

Two structural checks run first because they settle cases without reading
anything. A predecessor whose registrant files POS AMI is a master fund in a
master-feeder pair, not a retail fund: its "disappearance" beside a same-named
ETF is the feeder ETF going standalone, and the two have shared a fiscal year end
all along, which is why they show a zero-day gap. And an ETF that was already
reporting before the fund's last period cannot have been created by that fund --
it can still have acquired it, so this is recorded rather than used to reject.

Then the documents. A fund that liquidates says so, in a supplement announcing a
plan of liquidation. A fund that reorganizes says that instead, and names what it
reorganized into. The first pass at this matched any sentence containing
"convert" or "exchange-traded fund", which fires on convertible-securities risk
language and on "ETFs in which the Fund invests" -- boilerplate present in every
prospectus. So a hit now requires a transaction template, and the sentence must
name this fund, using the same similarity test the rest of the pipeline uses.

The verdict matters for a specific claim. None of these series appears anywhere
in the N-14 merger ledger, so if one of them did convert, it converted without a
filer-declared N-14 MERGER block -- precisely the failure mode the LEGACY_GOLD
recall check is blind to, and the reason the unexplained Fed residual cannot be
reported as zero discovery miss.
"""
import json
import re
import sys

import pandas as pd

import fetchlib
from build_completion_evidence import names_match
from paths import CACHE, ESCALATION, SUBMISSIONS

READ = {"497", "497K", "N-14", "N-14/A", "DEF 14A", "DEFS14A", "N-8F"}

# Adjudications made by reading the cited document, where the automated verdict
# was wrong or absent. Each is a fund the pattern flagged and a person resolved;
# the accession is the locator, so the claim can be rechecked without rerunning.
# All three "reorganization" hits are boilerplate describing an EARLIER, unrelated
# transaction -- the sentence is real, but it is not about a move to an ETF.
ADJUDICATED = {
    "S000055179": ("not_a_conversion", "0000930413-25-000224",
                   "performance-history boilerplate about the 2016 Virtus Insight "
                   "Trust reorganization, not a move to the ETF"),
    "S000010974": ("not_a_conversion", "0000908186-22-000008",
                   "match is XBRL cover-page tagging, not prose; the pair is an "
                   "American Century fund named like an unrelated Putnam ETF"),
    "S000061547": ("liquidated", "0001387131-20-002498",
                   "360 Funds Trust board approved a Plan of Liquidation, "
                   "supplement dated 2020-03-04"),
    "S000061545": ("liquidated", "0001580642-20-002219",
                   "board resolved the fund cease operations; all shares redeemed "
                   "on or about 2020-06-19"),
    "S000061544": ("liquidated", "0001580642-20-002219",
                   "same supplement as S000061545"),
    "S000001920": ("not_a_conversion", "0000813383-19-000029",
                   "the reorganization described is of the SUB-ADVISER (NIMNA into "
                   "NIM), not of the fund"),
    "S000065576": ("not_a_conversion", "0001104659-20-105946",
                   "nearest supplement naming the fund is a portfolio-manager "
                   "change; the N-14 in the window is the unrelated Schroder Core "
                   "Bond transaction"),
}
MAX_DOCS = 40
BEFORE, AFTER = pd.Timedelta(days=400), pd.Timedelta(days=400)

# a transaction, not a risk factor: each names an act done to the fund itself
CONV = re.compile(r"(?i)("
                  r"plan of reorganization"
                  r"|(?:will|to|shall) be reorganized into"
                  r"|reorganiz\w+ (?:of|into) the [\w .,'&-]{0,60}(?:ETF|Fund|Portfolio)"
                  r"|convert(?:ed|ing|s)?(?: the [\w .,'&-]{0,50})? (?:in)?to an "
                  r"(?:actively[ -]managed )?exchange[ -]traded fund"
                  r"|conversion of the [\w .,'&-]{0,60}(?:Fund|Portfolio)"
                  r"|transfer(?:red|ring)? (?:substantially )?all of its assets"
                  r"|acquired by the [\w .,'&-]{0,60}ETF"
                  r")")
# a board closing a fund rarely uses the word "liquidation" in the operative
# sentence: the Trend Aggregation supplement says the funds "cease operations"
# and that shares will be "automatically redeemed", and nothing else
LIQ = re.compile(r"(?i)(plan of liquidation|will be liquidated"
                 r"|liquidat\w+ and dissolv\w+|liquidation of the fund"
                 r"|cease operations|begin liquidating its portfolio"
                 r"|redeem all outstanding shares|automatically redeemed"
                 r"|will be closed and (?:its|their) (?:assets|shares))")
TAGS = re.compile(r"(?is)<(script|style|head)[^>]*>.*?</\1>")
SENT = re.compile(r"(?<=[.;])\s+")


def text(path):
    with open(path, "rb") as fh:
        raw = TAGS.sub(" ", fh.read().decode("utf8", "ignore"))
    import html
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(html.unescape(raw)))


def history(cik):
    p = fetchlib.get(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json",
                     SUBMISSIONS / f"CIK{int(cik):010d}.json",
                     kind="edgar_submissions")
    if not p:
        return pd.DataFrame()
    try:
        j = json.load(open(p))
    except Exception:
        return pd.DataFrame()
    blocks = [j.get("filings", {}).get("recent", {})]
    for extra in j.get("filings", {}).get("files", []):
        q = fetchlib.get(f"https://data.sec.gov/submissions/{extra['name']}",
                         SUBMISSIONS / extra["name"], kind="edgar_submissions_page")
        if q:
            try:
                blocks.append(json.load(open(q)))
            except Exception:
                pass
    out = [pd.DataFrame({k: b.get(k, []) for k in
                         ["form", "filingDate", "accessionNumber", "primaryDocument"]})
           for b in blocks if b.get("accessionNumber")]
    if not out:
        return pd.DataFrame()
    h = pd.concat(out, ignore_index=True)
    h["filingDate"] = pd.to_datetime(h.filingDate, errors="coerce")
    return h


def statement(t, name, other):
    """The first transaction sentence whose neighbourhood names this fund.

    Attribution cannot be done on the sentence alone. A supplement names the fund
    in its heading and then says "the Fund" for the rest of the page, so the
    operative sentence carries no name at all. Widening to the surrounding
    passage is what makes those readable, while still refusing a statement that
    sits in a thirty-fund prospectus far from any mention of this one.
    """
    for m in re.finditer(r"[^.;]{0,900}[.;]", t):
        s = m.group(0)
        c, l = CONV.search(s), LIQ.search(s)
        if not (c or l):
            continue
        ctx = t[max(0, m.start() - 1500):m.end() + 500]
        if not names_match(ctx, name, other):
            continue
        return ("reorganization" if c else "liquidation"), s.strip()[:420]
    return None, ""


def main():
    s = pd.read_csv(CACHE / "discovery_probe_shortlist.csv")
    s["mf_last_ncen"] = pd.to_datetime(s.mf_last_ncen)
    s["etf_first_ncen"] = pd.to_datetime(s.etf_first_ncen)
    mfs = s.sort_values("name_sim", ascending=False).drop_duplicates("mf_series_id")
    print(f"predecessors to read: {len(mfs)}", flush=True)

    rows = []
    for n, r in enumerate(mfs.itertuples(index=False), 1):
        h = history(r.cik)
        forms = set(h.form) if len(h) else set()
        # A master fund registers under the 1940 Act only and amends by POS AMI;
        # it never registers a public offering, so it never files 485BPOS. Using
        # POS AMI alone flags retail trusts that happen to host one master series.
        master = "POS AMI" in forms and not any(
            str(f).startswith("485") for f in forms)
        win = h[(h.filingDate >= r.mf_last_ncen - BEFORE)
                & (h.filingDate <= r.mf_last_ncen + AFTER)] if len(h) else pd.DataFrame()
        n14 = sorted({f for f in win.form if str(f).startswith("N-14")}) if len(win) else []

        verdict, acc, snip, nread = "no_statement_found", "", "", 0
        if master:
            verdict = "master_feeder_not_a_conversion"
        else:
            docs = win[win.form.isin(READ)] if len(win) else pd.DataFrame()
            if len(docs):
                docs = docs.assign(d=(docs.filingDate - r.mf_last_ncen).abs()) \
                    .sort_values("d").head(MAX_DOCS)
            nread = len(docs)
            for x in docs.itertuples(index=False):
                url = (f"https://www.sec.gov/Archives/edgar/data/{int(r.cik)}/"
                       f"{x.accessionNumber.replace('-', '')}/{x.primaryDocument}")
                p = fetchlib.get(url, ESCALATION / f"{x.accessionNumber}.html",
                                 accession=x.accessionNumber, kind="probe_triage_doc")
                if p is None:
                    continue
                kind, sn = statement(text(p), r.mf_name, r.etf_name)
                if kind == "reorganization":
                    verdict, acc, snip = "reorganization_language", x.accessionNumber, sn
                    break
                if kind == "liquidation" and verdict == "no_statement_found":
                    verdict, acc, snip = "liquidation_language", x.accessionNumber, sn

        adj, adj_acc, adj_note = ADJUDICATED.get(
            r.mf_series_id,
            ("not_a_conversion", "", "master-feeder structure, not a reorganization")
            if master else
            ("liquidated", acc, "filing-stated closure") if verdict == "liquidation_language"
            else ("unadjudicated", "", "terminated; no closure or reorganization "
                  "statement located in the predecessor's own filings"))

        rows.append({"mf_series_id": r.mf_series_id, "mf_name": r.mf_name,
                     "mf_cik": r.cik, "mf_last_ncen": r.mf_last_ncen.date(),
                     "etf_series_id": r.etf_series_id, "etf_name": r.etf_name,
                     "name_sim": round(r.name_sim, 3),
                     "etf_predates_mf_death": bool(r.etf_first_ncen < r.mf_last_ncen),
                     "master_feeder": master,
                     "n14_forms_in_window": ";".join(n14),
                     "verdict": verdict, "acc": acc, "statement": snip,
                     "docs_read": nread, "adjudication": adj,
                     "adjudication_acc": adj_acc, "adjudication_note": adj_note})
        print(f"  [{n}/{len(mfs)}] {str(r.mf_name)[:38]:<38} {verdict:<32} "
              f"n14={';'.join(n14) or '-'}", flush=True)

    d = pd.DataFrame(rows)
    out = CACHE / "discovery_probe_triage.csv"
    d.to_csv(out, index=False)
    fetchlib.record(out, kind="derived", parser="triage_probe_candidates.py")

    print("\n" + "=" * 74)
    print("PROBE TRIAGE")
    print("=" * 74)
    print("  automated pattern verdict")
    print("  " + d.verdict.value_counts().to_string().replace("\n", "\n  "))
    print("\n  adjudication (pattern verdicts read and confirmed or overturned)")
    print("  " + d.adjudication.value_counts().to_string().replace("\n", "\n  "))
    print(f"\n  ETF already reporting before the fund's last period : "
          f"{int(d.etf_predates_mf_death.sum())}")
    print(f"  predecessors with an N-14 in the window             : "
          f"{int((d.n14_forms_in_window != '').sum())}")

    conv = int((d.adjudication == "is_a_conversion").sum())
    print("\n" + "-" * 74)
    print(f"  CONVERSIONS DEMONSTRATED BY THIS PROBE : {conv}")
    print(f"  UNADJUDICATED                          : "
          f"{int((d.adjudication == 'unadjudicated').sum())}")
    print("\n  The unadjudicated funds all carry a registrant-reported N-CEN")
    print("  termination, so they did end; what they ended into was not located")
    print("  in their own filings. None is shown to be a conversion, and none is")
    print("  shown not to be, which is why DISCOVERY_COMPLETENESS stays OPEN.")
    print(f"\n  written: {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
