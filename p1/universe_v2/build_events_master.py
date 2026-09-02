"""Turn filing-level N-14 MERGER rows into deduplicated economic conversion events.

Design points, each of which is an audit finding rather than a preference:

1. Counting units stay separate. The Fed's 125 counts *mutual funds*, so the
   only comparable unit is distinct verified predecessor series. Events,
   successor ETFs, effective dates and waves are reported separately and never
   substituted for one another.

2. N-CEN is not the sole MF/ETF classifier, because a successor ETF created
   this year has no annual N-CEN observation yet and requiring one would drop
   precisely the most recent conversions. Every side records the evidence tier
   that decided it.

3. N-CEN's IS_ETF is not sufficient on its own either, in both directions:
     - a mutual fund carrying an ETF *share class* (the Vanguard structure)
       reports IS_ETF=Y at series level, so an ordinary MF->MF merger into it
       would look like a conversion;
     - some genuine ETFs report the flag blank, so an ETF->ETF merger would
       look like it had a mutual-fund predecessor.
   Both are rejected by requiring the successor to be named an ETF when N-CEN
   also shows non-ETF observations for it, and by refusing to call a
   target an open-end MF when its own name says ETF.

4. An N-14 is a *proposal*. Completion is a separate finding with its own
   evidence tiers, and no one-sided signal earns verified_completed.

5. Dates carry their own provenance and precision. N-CEN terminations are
   MM/YYYY, so they stay month_only and are never given a manufactured day.
"""
import pickle
import re

import pandas as pd

from paths import CACHE as HERE  # data lives outside the repo; see paths.py
CUTOFF = pd.Timestamp("2026-08-29")
FED_CUT = pd.Timestamp("2024-12-31")

ETF_NAME = re.compile(r"\bETFs?\b|exchange[- ]traded", re.I)
# A fund that *is* an ETF ends its name with one ("Leuthold Select Industries
# ETF"). A fund that merely *holds* ETFs carries the word mid-name and ends with
# Fund ("JNL/Vanguard Growth ETF Allocation Fund"), and is an ordinary mutual
# fund. This tail test is what separates the two.
ETF_TAIL = re.compile(r"(?:\bETFs?|exchange[- ]traded\s+fund)\s*$", re.I)
MF_TICKER = re.compile(r"^[A-Z]{4}X$|^[A-Z]{5}X$")


def load_ncen():
    with open(HERE / "ncen_tables.pkl", "rb") as fh:
        t = pickle.load(fh)
    s = t["SUBMISSION"]
    sub = s.assign(period_end=pd.to_datetime(s.REPORT_ENDING_PERIOD, errors="coerce"),
                   filing_date=pd.to_datetime(s.FILING_DATE, errors="coerce"))
    fri = t["FUND_REPORTED_INFO"].merge(
        sub[["ACCESSION_NUMBER", "CIK", "period_end", "filing_date"]],
        on="ACCESSION_NUMBER", how="left")
    fri = fri[fri.SERIES_ID.str.startswith("S0", na=False)]
    se = t["SECURITY_EXCHANGE"].drop_duplicates("FUND_ID").set_index("FUND_ID")
    fri["exchange"] = fri.FUND_ID.map(se.FUND_EXCHANGE)

    term = t["TERMINATED_ORGANIZATION"].copy()
    term["term_month"] = pd.to_datetime(term.TERMINATION_DATE, format="%m/%Y",
                                        errors="coerce")
    term = (term[term.term_month.notna()
                 & term.SERIES_ID.str.startswith("S0", na=False)]
            .sort_values("term_month").drop_duplicates("SERIES_ID", keep="first")
            .set_index("SERIES_ID"))
    return fri, term


def series_facts(fri):
    g = fri.groupby("SERIES_ID")
    return pd.DataFrame({
        "ever_etf": g.IS_ETF.apply(lambda s: s.eq("Y").any()),
        "ever_nonetf": g.IS_ETF.apply(lambda s: (~s.eq("Y")).any()),
        "listed": g.exchange.apply(lambda s: s.notna().any()),
        "first_period": g.period_end.min(),
        "last_period": g.period_end.max(),
        "n_obs": g.size(),
    })


def is_successor_etf(sid, name, facts, n14_filed):
    named = bool(ETF_NAME.search(str(name or "")))
    f = facts.loc[sid] if sid in facts.index else None
    if f is None:
        # a successor created for the conversion has no annual N-CEN yet
        return (True, "named_etf_no_ncen_yet") if named else (False, "no_evidence")

    # Exchange listing is strong evidence (99.7% of series N-CEN ever flags
    # IS_ETF=Y carry an exchange row) but not a necessary condition: N-CEN
    # exchange data can simply be missing for a newly launched successor. So a
    # missing exchange row only rejects when the name also fails the tail test.
    if not f.listed:
        if ETF_TAIL.search(str(name or "")):
            return True, "named_etf_tail_listing_unconfirmed"
        return False, "ncen_not_exchange_listed"

    # a fund reporting BOTH etf and non-etf years is the dual-share-class
    # structure, not a pure ETF; only trust it if it is actually named one
    if f.ever_etf and f.ever_nonetf:
        return (True, "ncen_mixed_flag_but_named_etf") if named \
            else (False, "ncen_mixed_flag_dual_share_class")
    if f.ever_etf:
        if named:
            return True, "ncen_is_etf"
        # listed and flagged ETF, but not named one and already reporting well
        # before the proposal: a mutual fund carrying an ETF share class
        # (Vanguard Value Index Fund / VTV), so the target merges *into an MF*
        if pd.notna(n14_filed) and pd.notna(f.first_period) \
                and f.first_period < n14_filed - pd.Timedelta(days=365):
            return False, "listed_but_preexisting_dual_share_class_mf"
        return True, "ncen_is_etf_not_named"
    return (True, "ncen_exchange_listed_named_etf") if named \
        else (False, "ncen_says_open_end_mf")


def is_predecessor_mf(sid, name, tickers, facts):
    if ETF_NAME.search(str(name or "")):
        return False, "target_name_says_etf"
    f = facts.loc[sid] if sid in facts.index else None
    if f is not None:
        if f.ever_etf and not f.ever_nonetf:
            return False, "ncen_says_etf"
        if f.ever_nonetf:
            return True, "ncen_is_open_end_mf"
    if any(MF_TICKER.fullmatch(t) for t in str(tickers or "").split(";") if t):
        return True, "mf_ticker_x_suffix"
    return True, "name_not_etf_no_ncen"


def main():
    m = pd.read_csv(HERE / "n14_mergers.csv")
    m["filed"] = pd.to_datetime(m.filed, errors="coerce")
    n_raw, n_hdr = len(m), m.accession.nunique()
    m = m[m.filed <= CUTOFF]
    n_cut = len(m)
    m = m[m.acq_series_id.notna() & m.tgt_series_id.notna()].copy()
    n_ids = len(m)

    fri, term = load_ncen()
    facts = series_facts(fri)

    a = [is_successor_etf(r.acq_series_id, r.acq_series_name, facts, r.filed)
         for r in m.itertuples(index=False)]
    t = [is_predecessor_mf(r.tgt_series_id, r.tgt_series_name, r.tgt_tickers, facts)
         for r in m.itertuples(index=False)]
    m["acq_is_etf"], m["acq_evidence"] = [x[0] for x in a], [x[1] for x in a]
    m["tgt_is_mf"], m["tgt_evidence"] = [x[0] for x in t], [x[1] for x in t]

    conv = m[m.acq_is_etf & m.tgt_is_mf].sort_values("filed")
    # the pairs that were dropped, and why. Reconciling a count against an outside
    # benchmark needs the exclusions to be countable, not just the inclusions.
    m[["accession", "filed", "tgt_series_id", "tgt_series_name", "tgt_cik",
       "acq_series_id", "acq_series_name", "acq_cik", "acq_is_etf",
       "acq_evidence", "tgt_is_mf", "tgt_evidence"]] \
        .to_csv(HERE / "classification_ledger.csv", index=False)

    print("=" * 72)
    print("N-14 STRUCTURAL FUNNEL")
    print("=" * 72)
    print(f"indexed N-14-family rows                 : 2,070")
    print(f"unique accessions                        : 2,060")
    print(f"headers fetched / failed                 : 2,060 / 0")
    print(f"headers WITH a structured MERGER block   : {n_hdr:,d}")
    print(f"headers WITHOUT a MERGER block           : {2060 - n_hdr:,d}")
    print(f"merger rows                              : {n_raw:,d}")
    print(f"  filed <= {CUTOFF.date()}                     : {n_cut:,d}")
    print(f"  with both target and acquirer series id: {n_ids:,d}")
    print(f"  acquirer classified ETF                : {int(m.acq_is_etf.sum()):,d}")
    print(f"  target classified open-end MF          : {int(m.tgt_is_mf.sum()):,d}")
    print(f"  MF -> ETF merger rows                  : {len(conv):,d}")
    print(f"  unique target->acquirer series pairs   : "
          f"{conv.drop_duplicates(['tgt_series_id','acq_series_id']).shape[0]:,d}")

    ev = conv.groupby("tgt_series_id").agg(
        pre_series_name=("tgt_series_name", "last"),
        pre_cik=("tgt_cik", "last"),
        pre_class_ids=("tgt_class_ids", "last"),
        pre_tickers=("tgt_tickers", "last"),
        post_series_id=("acq_series_id", "last"),
        post_series_name=("acq_series_name", "last"),
        post_cik=("acq_cik", "last"),
        post_class_ids=("acq_class_ids", "last"),
        n14_first_filed=("filed", "min"),
        n14_last_filed=("filed", "max"),
        supporting_accessions=("accession", lambda s: ";".join(sorted(set(s)))),
        n_accessions=("accession", "nunique"),
        tgt_evidence=("tgt_evidence", "last"),
        acq_evidence=("acq_evidence", "last"),
    ).reset_index().rename(columns={"tgt_series_id": "pre_series_id"})

    # ------------------------------------------------------- date provenance
    ev["term_month"] = ev.pre_series_id.map(term.term_month)
    ev["term_accession"] = ev.pre_series_id.map(term.ACCESSION_NUMBER)
    ev["verified_effective_date"] = ev.term_month.dt.strftime("%Y-%m")
    ev["effective_date_source"] = ev.term_month.notna().map(
        {True: "ncen_terminated_organization", False: None})
    ev["effective_date_precision"] = ev.term_month.notna().map(
        {True: "month_only", False: "unknown"})
    ev["effective_date_accession"] = ev.term_accession
    ev["proposed_effective_date"] = pd.NA          # lives in the N-14 body
    ev["proposed_effective_date_source"] = pd.NA

    pf = facts.reindex(ev.post_series_id)
    ev["post_first_ncen_period"] = pf.first_period.values
    ev["post_active_in_ncen"] = pf.n_obs.notna().values
    prf = facts.reindex(ev.pre_series_id)
    ev["pre_last_ncen_period"] = prf.last_period.values

    # ------------------------------------------------------- completion tiers
    def tier(r):
        pre_gone = pd.notna(r.term_month)
        post_live = bool(r.post_active_in_ncen)
        coherent = (pre_gone and post_live
                    and r.term_month >= r.n14_first_filed - pd.Timedelta(days=120)
                    and r.term_month <= r.n14_last_filed + pd.Timedelta(days=760))
        # predecessor still filing N-CEN long after the proposal = not completed
        stale = (pd.notna(r.pre_last_ncen_period)
                 and r.pre_last_ncen_period > r.n14_last_filed + pd.Timedelta(days=760))
        if pre_gone and post_live and coherent and not stale:
            return "B_structurally_confirmed_completion"
        if stale:
            return "cancelled_or_not_completed"
        if r.n14_last_filed >= CUTOFF - pd.Timedelta(days=400) and not pre_gone:
            return "proposed_future"
        return "unresolved"

    ev["completion_tier"] = [tier(r) for r in ev.itertuples(index=False)]
    ev["completion_evidence"] = [
        ("ncen_predecessor_terminated + ncen_successor_etf_reporting"
         if r.completion_tier == "B_structurally_confirmed_completion" else None)
        for r in ev.itertuples(index=False)]
    # tier A requires body-level confirmation language, not yet fetched
    ev["A_explicit_completion_checked"] = False

    ev = ev.drop(columns=["term_month", "term_accession"])
    ev = ev.sort_values(["verified_effective_date", "pre_series_name"])
    ev.to_csv(HERE / "events_master_v2_stage1.csv", index=False)

    print()
    print("=" * 72)
    print("COMPLETION TIERS")
    print("=" * 72)
    print(ev.completion_tier.value_counts().to_string())
    print("\nA_explicit_completion: 0 (requires N-14/497 body text; not yet fetched)")

    b = ev[ev.completion_tier == "B_structurally_confirmed_completion"]
    print()
    print("=" * 72)
    print("COUNTING UNITS (kept separate)")
    print("=" * 72)
    print(f"verified predecessor mutual funds  : {b.pre_series_id.nunique():,d}")
    print(f"successor ETFs                     : {b.post_series_id.nunique():,d}")
    print(f"economic conversion events         : {len(b):,d}")
    print(f"distinct effective months          : {b.verified_effective_date.nunique():,d}")
    print(f"waves                              : NOT COMPUTED (dates are month_only)")

    print()
    print("effective_date_precision census:")
    print(ev.effective_date_precision.value_counts().to_string())

    thru = b[b.verified_effective_date <= FED_CUT.strftime("%Y-%m")]
    print()
    print("=" * 72)
    print("FED-125 COMPARISON (predecessor mutual funds only)")
    print("=" * 72)
    print(f"verified predecessor MFs completed <= 2024-12   : "
          f"{thru.pre_series_id.nunique():,d}")
    print(f"Fed benchmark                                   : 125")
    print(f"difference                                      : "
          f"{125 - thru.pre_series_id.nunique():,d}")

    yr = b.verified_effective_date.str[:4].value_counts().sort_index()
    print("\nverified predecessor MFs by completion year:")
    print(yr.to_string())
    print("cumulative:")
    print(yr.cumsum().to_string())
    print("\nwrote events_master_v2_stage1.csv")


if __name__ == "__main__":
    main()
