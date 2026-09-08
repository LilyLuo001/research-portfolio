# Review of the Gate 1 assignment-and-support audit

**Reviewed:** `FINAL_DECISION.md` and the manual-transfer review package for the Gate 1 execution
(`index-reweighting-gate1/`), execution date 8 September 2026.
**Reviewer basis:** the decision memo and the package narrative. **I did not inspect the artifacts
themselves** — no CSV, no `logs/gate1_summary.json`, no `src/`, no test output. Every count below is
quoted from the memo or the package, not verified against the committed tables. Where I say a number
"is not reported," I mean it does not appear in those two documents; it may exist in the artifacts.
**Verdict on the deliverable: accept REVISE.** The audit is honest, well-instrumented work that
declined several available opportunities to manufacture a favourable result. What follows is about
how to make the *output* decision-grade, since in its current form it establishes that a gap exists
without establishing whether closing the gap would help.

---

## 1. What the output establishes

Read strictly, the package supports four claims and no more:

1. **The local archive does not contain the treatment.** No Select Sector constituent membership; one
   Nasdaq-100 name match in index metadata with zero constituent rows. Holdings, daily prices and
   MIDAS are present and audited; none of them is an index assignment.
2. **Rule regimes are documented; assignments are not.** 21 registry rows (10 grade-A rule-source,
   7 B, 4 unresolved) against **34 grade-B dose rows and zero complete grade-A vectors**.
3. **Binding events exist but are few and clustered.** 30 confirmed-binding rows in 17 event-date
   groups; 175 confirmed nonbinding; 575 uncertain; 1 separately-recorded non-capping intervention.
4. **Calendar overlap is nonempty and dependent.** 63 eligible primary-scope FOMC meetings;
   37/70/86 binding-group–meeting pairs at 20/40/60 trading days, over 24/36/39 distinct meetings.
   **Zero validated `comparison_id`.**

Everything else in the package is coverage bookkeeping or an explicit abstention.

---

## 2. What the audit did well

These are worth naming because they are the properties that make the rest of the output trustworthy,
and because two of them are reusable elsewhere in the portfolio.

**Non-manufacture under pressure.** Zero grade-A vectors is reported as zero. `NOT_COMPUTED` appears
where a statistic would have required inputs that do not exist. The 30 rounded Technology rows are
never renormalised into a purported full-index vector. An audit that wanted to look productive had
several easy outs here and took none of them.

**Three grade dimensions kept orthogonal.** `rule_source_grade` (evidence for a rule statement),
assignment grade (observability of a dose), and event-classification grade are separate, and the
package explicitly forbids transferring one into another. This is the correct decomposition and it is
the reason the "10 grade-A rule rows / 0 grade-A assignments" pair is legible rather than confusing.
It should become house convention.

**Bounding a rule regime from third-party contemporaneous documents.** When the provider's change log
was silent on when Nasdaq-100 capping moved from security-line to issuer level, the audit used SEC
424(b)(2) filings dated November 2019, March 2020 and July 2020 to bracket the transition to 2020 Q2
and left the exact date unresolved rather than interpolating. That is the best single piece of
institutional work in the package. The technique — using a third party's contemporaneous description
of a rule to date a regime the rule-owner did not document — generalises, and is worth writing into
the evidence contract as a named pattern.

**Interference recorded rather than absorbed.** The 17 July 2023 Trade Desk–for–Activision
replacement is a separate intervention linked as interference to the 24 July special rebalance, not
attributed to it and not counted as a cap treatment. Correct, and the kind of thing that quietly
contaminates event studies when it is not done.

**Counting units held apart.** 785 rows → 104 groups → 17 binding groups, with the row/group
distinction enforced in the narrative rather than only in a schema. Similarly, 11,745 support rows
are explicitly disclaimed as not a sample size.

**Reproducibility scaffolding with an honest ceiling.** Hash-pinned inputs, 64 tests, a contract
validator, stale-summary rejection, redaction hygiene — and a stated limitation that validator
success establishes internal consistency and output hygiene, "not the truth of every institutional
claim or a legal redistribution opinion." The caveat is as valuable as the validator.

---

## 3. Weaknesses in the output

Ordered by how much each one costs the decision.

### W1. The headline is mis-ranked

The memo leads with assignment observability. The finding that actually binds is one paragraph
further down: **every one of the 785 comparison-audit rows lacks a validated `comparison_id`.**

These are different kinds of failure. An input gap is closed by retrieval. A missing comparison is
closed by design work, and no assignment file supplies one. Because the memo foregrounds the
retrievable gap, the "smallest next retrieval" reads as the primary act and the design freeze as a
parallel chore — when the dependency runs the other way (see W7).

**Fix:** lead the decision memo with the comparison finding, and state the assignment gap as what
must be resolved *once the comparison names which portfolios need doses*.

### W2. Support diagnostics were gated on grade A when only some of them needed to be

The package declines to compute residualised dose information shares, matrix rank, collinearity and
leverage without complete vectors. **That gating is correct** — those objects are dose-weighted and
computing them on partial vectors would manufacture precision, exactly as the memo says.

But the same prohibition was extended to a different object that does not need doses: **the count of
binding event groups surviving leave-one-out.** Removing the September 2024 transition, Technology,
or the dominant issuer from a set of 17 groups requires only the classification layer, which is
committed. The distinction is between a *dose-weighted leverage statistic* and a *group count*, and
the output currently treats them as one prohibition.

The consequence is that the package cannot answer the question its own verdict raises: would a
successful retrieval leave enough independent groups to matter? A reader is told the design has no
support diagnostics and cannot tell whether that is a temporary or terminal condition.

**Fix:** add a dose-free `binding_group_support.csv` — binding groups after each omission, plus the
distribution of rows per binding group.

### W3. The 575 uncertain rows are counted but not diagnosed

73% of the ledger is `uncertain`. The memo treats this as one undifferentiated gap. It is at least
four:

- no contemporaneous methodology version located for that date;
- methodology known, trigger inputs unavailable;
- trigger inputs available but rounding straddles the threshold;
- regime applicability itself unresolved.

Those have very different resolution costs and very different implied yields. The proposed retrieval
covers three 2024 Select Sector episodes — but nothing in the output says what fraction of the 575 that
pathway would resolve. It could be most of them or almost none, and the memo cannot distinguish those
worlds.

**Fix:** `uncertain_reason_breakdown.csv`, with an explicit column for whether the proposed retrieval
addresses that reason.

### W4. The binding base rate is derivable and not stated

Among *classified* rows the binding rate is 30/(30+175) ≈ **15%**. This is the most decision-relevant
derived number available from the current output and it does not appear. It bounds what full
resolution of the 575 could plausibly yield.

It also needs its own caveat, which is why stating it matters: classified rows are not a random sample
of the ledger. Events get documented partly *because* they were dramatic, so 15% is plausibly an
overestimate of the binding rate among the unclassified. That caveat is exactly the kind of reasoning
the package handles well elsewhere and omits here.

### W5. The row-to-group ratio is reported but not interpreted

30 rows over 17 groups is ≈1.8 rows per group. If the September 2024 transition carries roughly one
row per affected sector, the remaining ~16 groups average close to one row each — that is, the binding
events are mostly *single-sector*.

That has a direct design consequence the memo never draws: it is good for independence across dates
and bad for cross-sectional dose variation *within* a date, which determines whether a within-date,
cross-stock estimator is available at all or whether the design must lean entirely on across-date
variation. The group-size histogram is one line of code and changes which estimator is on the table.

### W6. "Holdings" is treated as one object class

The audit inspected CRSP holdings-report snapshots: 1,133 fund-report dates, 12 funds, 8 years —
roughly quarterly. The memo's conclusion ("snapshots, not daily holdings histories") is right but
under-stated. The sharper form closes the route permanently:

> Snapshot frequency is approximately equal to rebalance frequency, so these snapshots cannot bracket
> a rebalance under any coverage improvement.

That is a structural exclusion, not a coverage complaint, and it belongs in `remaining_input_gaps.csv`
as such — otherwise a later reader will re-litigate it as a data-quality issue.

Separately: issuer-published daily holdings files are a **different object** from CRSP holdings
snapshots, and the package's evidence tables do not appear to distinguish them. Whatever the eventual
verdict on that route, the gap row should name which object class it refers to, or the exclusion above
will be read as covering both.

### W7. The "smallest next retrieval" is neither smallest nor scopeable yet

The retrieval spec lists every field one could want for three episodes. But the memo also, correctly,
requires that one comparison be frozen before outcomes — and the retrieval spec itself contains the
clause "plus any other Select Sector portfolio strictly required for the predeclared comparison."

That clause is undefined until the comparison exists. So the request as written cannot actually be
filed at minimum scope; it can only be filed at maximum scope. The dependency is backwards.

Freezing the comparison — treatment object, counterfactual portfolio, assignment and inference units,
mechanical identical-price-path benchmark, anticipation interval, shared-stock interference rule,
strongest falsification — requires **no data at all**. It is a writing task, and it is the output that
makes the retrieval minimal and its success falsifiable. It belongs in this round's deliverables, not
the next round's parallel track.

### W8. Counting units are inconsistent across the two documents

The package snapshot reports "49 resolved unique intervention dates" and "785 distinct
`basket_assignment_id` values"; the memo narrates "104 event-date groups" and "17 groups confirmed
binding." These may all be correct under different filters, but the package instructs a reviewer to
treat `gate1_summary.json` as controlling while the memo narrates a different denominator. A reviewer
cannot reconcile them from the documents alone.

**Fix:** one reconciliation table — count name, definition, filter applied, value, and which document
reports it.

### W9. Anticipation coverage is thin and its consequence is not drawn

Only **74 of 11,745** support rows carry valid stage dates for the anticipation calculation; 8,572 are
missing or invalid. The memo reports this as a data-quality fact.

Its consequence is larger than that. The announcement-versus-effective-date decomposition is the main
defence against confounding a weight reassignment with the rebalancing flow it induces — the confound
the whole design must survive. That decomposition is currently supported on well under 1% of rows.
This should be stated as a first-order constraint on the eventual design, alongside the comparison
gap, rather than sitting in a coverage paragraph.

### W10. Two figures rest on a single source chain

The ~12% one-way turnover and the 21 July implementation close both trace to provider documents in the
same chain. The package is otherwise strict about evidence provenance; these should carry an explicit
single-source flag, since both are load-bearing for how the July 2023 episode is characterised.

---

## 4. Additions that would make the deliverable decision-grade

All five are computable from committed artifacts or from prose. None requires new retrieval.

| # | Addition | Answers |
|---|---|---|
| 1 | `binding_group_support.csv` — binding groups surviving omission of the September 2024 transition, Technology, the dominant issuer, and each index family; plus rows-per-group distribution | Whether a successful retrieval leaves usable independent support (W2, W5) |
| 2 | `uncertain_reason_breakdown.csv` — the 575 by resolution mechanism, flagged for whether the proposed retrieval addresses each | What the retrieval would actually yield (W3) |
| 3 | Binding base rate among classified rows, with the documentation-selection caveat | Upper bound on the yield from resolving the 575 (W4) |
| 4 | A frozen comparison specification, prose only | Scopes the retrieval; converts it from maximal to minimal (W1, W7) |
| 5 | Counting-unit reconciliation table | Makes the two documents mutually checkable (W8) |

Item 4 is the one that changes the shape of the project. The other four change whether the next
decision can be made on evidence.

---

## 5. On the verdict

**REVISE is the right label.** The audit did not find that the mechanism is absent; it found that the
treatment is unobservable in the audited sources and that no comparison has been specified. Neither is
falsification.

What is missing is that the verdict is not yet *conditional in a checkable way*. As written, it says:
retrieve assignment files, then freeze a comparison, then decide. With items 1–4 above, it can instead
say: here are the pass/fail thresholds — surviving binding groups, issuer and sector spread, the
fraction of uncertain rows the retrieval resolves — and here is the frozen comparison the retrieval is
scoped to serve. Those thresholds are checkable before any new data arrives, which is the property a
gate is supposed to have.

The memo's own closing sentence is right and should be promoted: the earliest evidence that should
trigger reconsideration is not an outcome coefficient. It is a complete, source-vintaged vector that
reconciles under the contemporaneous rule, repeated on a second routine episode, against a frozen
comparison whose identifying variation survives the mechanical and dependence audits. The additions
above are what let you know, in advance, whether that evidence would be worth having.

---

*Companion to `IndexConcentration_Referee_Report_2026-09-08.md`. This review assesses the Gate 1
deliverable as a work product; it does not re-open the upstream design questions, which are treated in
that report.*
