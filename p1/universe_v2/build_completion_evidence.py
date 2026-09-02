"""Decide completion for every structural MF->ETF pair on the strongest evidence.

No single form type is allowed to decide the outcome, and completion is decided
separately from dating. Conflating the two was the earlier mistake: a pair whose
closing is beyond doubt but whose exact day is only bracketed to a year was being
thrown into the same bucket as a pair with no evidence at all.

DID IT COMPLETE -- first channel that speaks wins, strongest first:

  A_explicit   a filing on either side of the deal names the transaction and
               states the day it closed
  B_terminated the predecessor's registrant filed an N-CEN TERMINATED_ORGANIZATION
               record for this series
  B_ceased     the predecessor stopped appearing in its registrant's N-CEN at its
               own fiscal-year-end anniversary, i.e. the registrant stopped
               reporting a fund it would otherwise have had to report
  B_elapsed    the successor is reporting in N-CEN and the proposed close has passed

WHEN -- independently, best available precision:

  exact_day          the stated closing day
  month_only         the N-CEN termination month
  exact_day_proposed the proposed closing day, once elapsed
  window_only        bracketed between two N-CEN periods, up to a year wide

A window_only event is counted as completed but is only assigned to a calendar
year when the whole bracket falls inside one. Otherwise its year is 'ambiguous',
because assigning it would mean inventing a date the filings do not support.

A missing predecessor N-CEN TERMINATED_ORGANIZATION record is explicitly *not*
sufficient to force unresolved, because that record is registrant-reported and
its absence carries little information -- the B_ceased channel is what covers it.
"""
import difflib
import functools
import html
import re
import sys

import pandas as pd

from paths import CACHE as HERE  # data lives outside the repo; see paths.py
CUTOFF = pd.Timestamp("2026-08-29")
WINDOW_DAYS = 540
SIM = 0.90

STOP = {"fund", "funds", "the", "portfolio", "portfolios", "trust", "inc", "etf",
        "incorporated", "company", "co", "lp", "llc", "series", "class", "shares",
        "exchange", "traded", "of", "a", "and", "predecessor", "mutual", "i", "ii"}
TAGS = re.compile(r"(?is)<(script|style|head)[^>]*>.*?</\1>")


def flat(s):
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", str(s or "").lower()).split())


def namespans(ctx):
    """Candidate fund names in the text, as every word-suffix ending at a head noun.

    A single regex cannot do this: it commits to the earliest start that can reach
    the head noun rather than the start that makes a real fund name. Emitting all
    suffixes and letting the similarity test pick lets the right boundary win.
    """
    out = []
    for m in re.finditer(r"\b(?:ETFs?|Funds?|Portfolios?)\b", ctx):
        head = ctx[max(0, m.start() - 90):m.start()].split()
        for k in range(1, min(len(head), 10) + 1):
            out.append(" ".join(head[-k:] + [m.group(0)]))
    return out


def names_match(ctx, *targets):
    """Does the text name any of these funds, allowing for wording drift?"""
    cands = namespans(ctx)
    if not cands:
        return False
    flats = [flat(c) for c in cands]
    for t in targets:
        want = flat(t)
        if not want:
            continue
        if max(difflib.SequenceMatcher(None, c, want).ratio() for c in flats) >= SIM:
            return True
    return False


@functools.lru_cache(maxsize=4096)
def doc_text(acc):
    for d in ("escalation", "sup497"):
        p = HERE / d / f"{acc}.html"
        if p.exists():
            raw = TAGS.sub(" ", p.read_bytes().decode("utf8", "ignore"))
            raw = re.sub(r"(?s)<[^>]+>", " ", raw)
            return re.sub(r"\s+", " ", html.unescape(html.unescape(raw)))
    return ""


def attribute(ev, comp, sub):
    """Tie each completion statement to the event whose funds it names.

    A trust files for every series it runs, so a statement is only this event's if
    the surrounding sentence names one of this pair's two funds. Token-subset tests
    failed here -- sibling funds of the same trust are supersets of each other
    ("Eaton Vance Short Duration Municipal Income ETF" contains every token of the
    non-municipal fund) -- so the comparison is symmetric similarity.

    Where the sentence refers to the counterparty generically ("the reorganization
    of the Predecessor Fund, which occurred on July 9, 2021") no name is in reach.
    Those are recovered by looking at the whole document, but only when the
    document's filer has exactly one candidate event in the window, so there is no
    sibling for it to be confused with.
    """
    doc = comp.merge(sub[["acc", "cik", "filed"]].drop_duplicates("acc"),
                     on="acc", how="left")
    by_cik = {c: g for c, g in doc.groupby("cik")}

    # how many of our events could a given filer's document be describing?
    n_events = {}
    for r in ev.itertuples(index=False):
        for cik in {r.pre_cik, r.post_cik}:
            if pd.notna(cik):
                n_events[int(cik)] = n_events.get(int(cik), 0) + 1

    out = []
    for r in ev.itertuples(index=False):
        lo = pd.to_datetime(r.n14_first_filed)
        hi = pd.to_datetime(r.n14_last_filed) + pd.Timedelta(days=WINDOW_DAYS)
        best = None
        for cik in {r.pre_cik, r.post_cik}:
            if pd.isna(cik):
                continue
            g = by_cik.get(int(cik))
            if g is None:
                continue
            sole = n_events.get(int(cik), 0) == 1
            for x in g.itertuples(index=False):
                # a closing cannot precede the proxy that proposed it, and a filing
                # often recites an unrelated reorganization from years back
                if not (pd.notna(lo) and lo <= x.close_date <= hi):
                    continue
                how = None
                if names_match(str(x.context), r.pre_series_name, r.post_series_name):
                    how = "named_in_sentence"
                elif sole and names_match(doc_text(x.acc), r.pre_series_name,
                                          r.post_series_name):
                    how = "named_in_document_sole_event"
                if how is None:
                    continue
                if best is None or x.close_date < best[0]:
                    best = (x.close_date, x.acc, x.pattern, str(x.context)[:300], how)
        out.append(best if best is not None else (None,) * 5)
    return out


def load_completions():
    frames = []
    for f in ("sup497_completions.csv", "escalation_completions.csv"):
        p = HERE / f
        if p.exists():
            d = pd.read_csv(p)
            d["close_date"] = pd.to_datetime(d.close_date, errors="coerce")
            frames.append(d[d.close_date.notna()])
    if not frames:
        return pd.DataFrame(columns=["acc", "close_date", "pattern", "context"])
    return pd.concat(frames, ignore_index=True)


def main():
    ev = pd.read_csv(HERE / "ncen_cease_signal.csv")
    ev["proposed_close"] = pd.to_datetime(ev.proposed_close, errors="coerce")
    ev["term_month"] = pd.to_datetime(ev.ncen_termination_month, errors="coerce")
    ev["cease_lo"] = pd.to_datetime(ev.cease_window_lo, errors="coerce")
    ev["cease_hi"] = pd.to_datetime(ev.cease_window_hi, errors="coerce")
    # The corpus-wide sweep needs the submissions index to map a document to its
    # filer, and the document cache to read it. Both are bulk artefacts that live
    # outside version control, so its output is persisted: re-tiering must not
    # require re-fetching tens of thousands of filings.
    src = HERE / "submissions_flat.parquet"
    cache = HERE / "attributed_completions.csv"
    comp = load_completions()
    if src.exists() and len(comp):
        sub = pd.read_parquet(src)
        sub["filed"] = pd.to_datetime(sub.filed, errors="coerce")
        got = attribute(ev, comp, sub)
        for i, c in enumerate(["a_close_date", "a_accession", "a_pattern",
                               "a_context", "a_how"]):
            ev[c] = [g[i] for g in got]
        ev[["pre_series_id", "a_close_date", "a_accession", "a_pattern", "a_how"]] \
            .dropna(subset=["a_close_date"]).to_csv(cache, index=False)
    else:
        a = pd.read_csv(cache).drop_duplicates("pre_series_id") \
              .set_index("pre_series_id")
        for c in ["a_close_date", "a_accession", "a_pattern", "a_how"]:
            ev[c] = ev.pre_series_id.map(a[c])
        ev["a_context"] = None
        print(f"[corpus sweep read from {cache.name}; bulk caches absent]")
    ev["a_close_date"] = pd.to_datetime(ev.a_close_date, errors="coerce")

    # The per-event escalation searched one pair at a time and required the
    # sentence to name that pair's own funds, so its hits are attributed more
    # tightly than the corpus-wide sweep and take precedence over it.
    esc = HERE / "escalation_resolved.csv"
    if esc.exists():
        e = pd.read_csv(esc)
        if len(e):
            e["close_date"] = pd.to_datetime(e.close_date, errors="coerce")
            e = e.drop_duplicates("pre_series_id").set_index("pre_series_id")
            hit = ev.pre_series_id.map(e.close_date)
            ev["a_accession"] = ev.a_accession.mask(hit.notna(),
                                                    ev.pre_series_id.map(e.acc))
            ev["a_pattern"] = ev.a_pattern.mask(hit.notna(),
                                                ev.pre_series_id.map(e.pattern))
            ev["a_context"] = ev.a_context.mask(hit.notna(),
                                                ev.pre_series_id.map(e.context))
            ev["a_how"] = ev.a_how.mask(hit.notna(), "per_event_escalation")
            ev["a_close_date"] = hit.fillna(ev.a_close_date)

    # Days recovered by the bracketed per-event search. These carry the tightest
    # attribution of any channel: the sentence must name this pair's own funds,
    # and the day must fall inside a bracket drawn from independent evidence --
    # the registrant's own termination month, or the window between two N-CEN
    # periods -- so two channels have to agree before a day is accepted.
    rec = HERE / "recovered_verified_dates.csv"
    if rec.exists():
        v = pd.read_csv(rec)
        if len(v):
            v["verified_day"] = pd.to_datetime(v.verified_day, errors="coerce")
            v = v.drop_duplicates("pre_series_id").set_index("pre_series_id")
            hit = ev.pre_series_id.map(v.verified_day)
            for col, s in (("a_accession", v.acc), ("a_pattern", v.pattern),
                           ("a_context", v.context)):
                ev[col] = ev[col].mask(hit.notna(), ev.pre_series_id.map(s))
            ev["a_how"] = ev.a_how.mask(hit.notna(), "bracketed_recovery")
            ev["a_close_date"] = hit.fillna(ev.a_close_date)

    tier, why, eff, prec, src, yr = [], [], [], [], [], []
    for r in ev.itertuples(index=False):
        # A stated day is attributed by name similarity; a TERMINATED_ORGANIZATION
        # record is the registrant speaking about this exact series. Where they
        # disagree by more than a quarter the statement has almost certainly been
        # matched to a later, separate transaction, so the direct record wins and
        # the disagreement is recorded rather than silently resolved.
        conflict = (pd.notna(r.a_close_date) and pd.notna(r.term_month)
                    and abs((r.a_close_date - r.term_month).days) > 100)
        # A termination predating its own proposal is a stale registrant record for
        # some earlier event, not this transaction.
        coherent = pd.notna(r.term_month) and (
            pd.isna(r.n14_first_filed)
            or r.term_month >= pd.to_datetime(r.n14_first_filed) - pd.Timedelta(days=90))
        elapsed = (pd.notna(r.proposed_close) and r.proposed_close <= CUTOFF
                   and bool(r.post_active_in_ncen))
        ceased = bool(r.pre_ceased_at_anniversary)

        if pd.notna(r.a_close_date) and not conflict:
            t, w = "A_explicit_completion", f"explicit completion statement ({r.a_pattern}, {r.a_how})"
        elif coherent:
            t, w = "B_structural_completion", "ncen predecessor termination record" + (
                " (stated date conflicted, discarded)" if conflict else "")
        elif ceased:
            t, w = "B_structural_completion", "predecessor absent from its own ncen anniversary filing"
        elif elapsed:
            t, w = "B_structural_completion", "successor active in ncen + proposed close elapsed"
        elif pd.notna(r.proposed_close) and r.proposed_close > CUTOFF:
            t, w = "announced_future", "proposed close is after the execution cutoff"
        elif r.completion_tier in ("proposed_future", "cancelled_or_not_completed"):
            # fall back to the structural classification rather than discarding it:
            # a pair whose only N-14 was filed days ago is awaiting its close, not
            # missing evidence
            t = ("announced_future" if r.completion_tier == "proposed_future"
                 else "cancelled_or_not_completed")
            w = f"carried forward: {r.completion_evidence}"
        else:
            t, w = "unresolved", "no completion evidence in any channel"

        # dating is decided separately, at the best precision any channel supports
        if t.startswith(("A_", "B_")):
            if pd.notna(r.a_close_date) and not conflict:
                d, p = r.a_close_date.strftime("%Y-%m-%d"), "verified_exact_day"
                y = r.a_close_date.year
            elif coherent:
                d, p, y = r.term_month.strftime("%Y-%m"), "month_only", r.term_month.year
            elif elapsed:
                # A day, but the day the proxy PROPOSED. Completion is established
                # -- the successor reports in N-CEN and the proposed day has passed
                # -- but no filing states that it closed on that day, and
                # reorganizations slip. This is not a verified date, and it must
                # not enter wave construction.
                d, p = r.proposed_close.strftime("%Y-%m-%d"), "proposed_exact_day_only"
                y = r.proposed_close.year
            else:
                d = (f"{r.cease_lo:%Y-%m-%d}..{r.cease_hi:%Y-%m-%d}"
                     if pd.notna(r.cease_lo) and pd.notna(r.cease_hi) else None)
                # a bracket that stays inside one calendar year does pin the year,
                # so it is not the same object as one that straddles a boundary
                if bool(r.cease_window_same_year):
                    p, y = "year_only", r.cease_lo.year
                else:
                    p, y = "bounded_window", None
        else:
            d, p, y = None, "unknown", None

        tier.append(t); why.append(w); eff.append(d); prec.append(p)
        yr.append(y)
        src.append(r.a_accession if p == "verified_exact_day" else
                   r.effective_date_accession if p == "month_only" else None)

    ev["final_tier"] = tier
    ev["final_evidence"] = why
    ev["final_effective_date"] = eff
    ev["final_precision"] = prec
    ev["final_year"] = yr
    ev["final_source_accession"] = src
    # The verified day and the proposed day are different claims and get
    # different columns, so that no downstream consumer can reach for a date
    # without choosing which kind it is willing to accept. Wave construction
    # reads final_verified_day and nothing else.
    ev["final_verified_day"] = ev.final_effective_date.where(
        ev.final_precision == "verified_exact_day")
    ev["final_proposed_day"] = pd.to_datetime(
        ev.proposed_close, errors="coerce").dt.strftime("%Y-%m-%d")

    # The date columns a downstream consumer needs in order to accept or refuse a
    # date without re-deriving anything. verified_effective_date is populated only
    # where a filing states the day: a proposed day, a meeting day and an N-CEN
    # termination month all leave it empty, by construction rather than by
    # convention, so nothing can silently promote one of them into a wave.
    isv = ev.final_precision == "verified_exact_day"
    subs = HERE / "submissions_flat.parquet"
    form = (pd.read_parquet(subs, columns=["acc", "form"])
            .drop_duplicates("acc").set_index("acc").form
            if subs.exists() else None)
    ev["verified_effective_date"] = ev.final_verified_day
    ev["verified_date_source_accession"] = ev.a_accession.where(isv)
    ev["verified_date_source_form"] = (
        ev.a_accession.map(form).where(isv) if form is not None else None)
    ev["verified_date_evidence"] = (
        ev.a_pattern.fillna("") + " / " + ev.a_how.fillna("")).where(isv)
    ev["date_precision"] = ev.final_precision
    assert not (ev.verified_effective_date.notna() & ~isv).any()

    ev.to_csv(HERE / "events_master_v2_stage3.csv", index=False)

    print(f"completion statements parsed : {len(comp):,d}")
    print(f"  attributed to an event     : {int(ev.a_close_date.notna().sum()):,d}")
    if ev.a_how.notna().any():
        print(ev.a_how.value_counts().to_string())
    print("\nFINAL COMPLETION TIERS")
    print(ev.final_tier.value_counts().to_string())
    print("\nDATE PRECISION")
    print(ev.final_precision.value_counts().to_string())
    done = ev[ev.final_tier.str.startswith(("A_", "B_"))]
    print(f"\ncompleted conversions        : {len(done):,d}")
    print("\nVERIFIED PREDECESSOR MFs BY YEAR")
    print(done.final_year.value_counts().sort_index().to_string())
    amb = int(done.final_year.isna().sum())
    print(f"year ambiguous (window spans a year boundary) : {amb}")
    print(f"\nthrough 2024-12-31 : {int((done.final_year <= 2024).sum())}   vs Fed 125")
    return 0


if __name__ == "__main__":
    sys.exit(main())
