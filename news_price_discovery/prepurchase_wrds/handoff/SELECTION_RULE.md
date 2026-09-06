# Frozen selection rule — six measurement-validation events

**Registered 2026-09-06, before any selection code was executed and before any
new intraday outcome was examined.** This file is committed on its own, ahead of
the commit that contains the selection program and its output, so that the
ordering is verifiable in the git history rather than asserted here.

## What this rule is for

To pick six events on which to test whether the *measurement* can be built at
all: whether an announcement clock can be pinned to a real first-public-release
source, whether the session was open, whether the complete constituent set and
its historical weights can be assembled, and whether a quote path exists over
the required windows. Six events cannot power a test of the research question
and this rule is not designed to. A null or opposite-sign result on these six
would not be a technical failure of the measurement.

## Candidate pool

Only the already-registered, already-seeded acquisition candidates from the
completed feasibility exercise:

- `out/s5_batch_fomc.parquet` — 12 FOMC events, stratified by year, seeded draw
- `out/s5_batch_earnings.parquet` — 60 earnings events, 31 strata, seeded draw

No new draw is taken from the 11,313-event registry. No event outside these two
files is eligible. Enlarging the pool after seeing anything is prohibited.

## Outcome-independence, enforced in code

Before any filter or sort is applied, the selection program **deletes** the
following columns from the in-memory candidate frames and asserts they are
absent. Selection therefore cannot condition on them even by accident:

| dropped from | columns |
|---|---|
| earnings candidates | `src_ret`, `contribution_bps`, `surprise_scaled`, `date` |
| FOMC candidates | `MP1`–`MP6`, `FF1`–`FF6`, `ED1`–`ED8`, `OIS1Y`, `OIS2Y`, `UST3M`–`UST30Y`, `TIPS5Y`–`TIPS30Y`, `SP500`, `SPFUT`, `DXY`, `EURUSD`, `USDJPY` |

`src_ret` and `contribution_bps` are realised outcomes. `surprise_scaled` and
the rate-surprise columns are the treatment, not an outcome, but selecting on
their magnitude would still be selecting on signal strength, so they are
dropped as well. The equity and FX columns of the USMPD are announcement-window
market responses and are dropped for the same reason.

Nothing about daily tracking quality, regression coefficients, decile
membership, or realised return enters the rule.

## Eligibility filters (structural and pre-event only)

**FOMC events** must satisfy all of:

1. present in `s5_batch_fomc.parquet`;
2. `Unscheduled == 0` — a scheduled meeting, so the release clock is the
   published statement time rather than an ad-hoc action;
3. `date_time` populated — a statement clock is recorded in the source file;
4. the announcement date is a NYSE trading day with a full session, and the
   statement time falls inside regular trading hours, so the historical
   market/feed was operating at the release.

**Earnings events** must satisfy all of:

5. present in `s5_batch_earnings.parquet`;
6. `session` is exactly `BMO` or `AMC` — `UNKNOWN` and non-trading-day
   classifications are ineligible, because an unresolved clock cannot anchor a
   measurement-validation window;
7. `eff_before_event` is true — the holdings snapshot was *demonstrably
   available* before the event, not merely economically dated before it. This
   is a weight-provenance requirement, not an outcome;
8. `report_age_days <= 120` — the registered report-age rule, unchanged;
9. `prc_pre >= 5.00` — the registered minimum price, unchanged;
10. `reaction_date_session` is a NYSE trading day, and the release does not fall
    on a weekend or an exchange holiday. A Saturday release routed to Monday is
    not an immediate release-time response and is ineligible here.

## Deterministic tie-breaker

The draw is **deterministic, not random**. There is no seed and no sampling
step, so there is no non-degenerate selection probability to report: every
eligible candidate has selection probability 0 or 1 under the rule, fixed at the
moment this file was written. What is reported instead is the tie-breaker, in
full, so the result can be recomputed by anyone.

Each eligible candidate receives a rank string

```
rank = sha256( SALT + "|" + key ).hexdigest()

SALT      = "ppw-handoff-20260906-six-event-validation"
key_fomc  = "FOMC|" + Date.strftime("%Y-%m-%d")
key_earn  = "EARN|" + str(permno) + "|" + fpedats.strftime("%Y-%m-%d") + "|" + etf
```

Candidates are sorted ascending by `rank` (ties broken by `key`, which is
unique, so no tie survives). The salt is an arbitrary fixed string chosen before
any rank was computed; it exists to keep the ordering from coinciding with
identifier order, which would over-select low PERMNOs and early dates.

## Greedy acceptance with diversity constraints

Walking the eligible candidates in ascending `rank` order, accept a candidate
into its category if and only if it does not violate a constraint already
satisfied by an accepted one:

- **FOMC (need 2):** the two events must fall in different calendar years.
- **BMO earnings (need 2):** different `permno`, and different calendar years.
- **AMC earnings (need 2):** different `permno`, and different calendar years.
- **Across all four earnings events:** `permno` distinct — no firm appears
  twice in the manifest.

If a duplicate `(permno, fpedats)` appears under more than one ETF, the row
with the lexicographically smallest `etf` is kept before ranking, so one event
maps to exactly one ETF and its one complete basket.

## If a category cannot be filled

If fewer than two candidates in any category survive the eligibility filters,
the shortfall is reported by name — the category, the count found, and the
filter that removed the rest. The gap is **not** backfilled from another
category, not filled by relaxing a filter, and not filled by reaching outside
the registered pool. A five-event or four-event manifest with a named missing
category is the correct output in that case.

## What may not be done after this point

No re-running of the rule with a different salt, a different constraint set, or
a different pool. If the rule is executed and the result is unwelcome, the
result stands and the objection is recorded as text. Any change to this file
after its commit is a new rule and must be labelled as one, with the original
retained.
