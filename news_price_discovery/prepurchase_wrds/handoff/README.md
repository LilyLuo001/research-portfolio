# Bounded quote-and-weight validation handoff

The seven-section WRDS pre-purchase exercise is accepted here as a versioned
feasibility result and was **not rerun**. This directory is an *export of
existing evidence plus a six-event acquisition specification*. It contains no
new intraday result, no vendor contact, and no purchase.

The research question is unchanged: **do ETFs or their underlying portfolios
incorporate news first, and how does that ordering differ between monetary
announcements and firm earnings?**

---

## Status

```
READY_TO_REQUEST_SPECIFIC_SAMPLE
```

**Reason.** The six-event manifest is complete and deduplicated — 532
securities, 24 dates, 8,604 security-days, 645,300 quote-minutes. Every event's
release clock was validated *individually* against a primary source, not
extrapolated from the twelve 2023 controls. Weights are documented with their
provenance, their staleness, and their missing mass. Nothing further can be
learned about product suitability from data already in hand; the next question
is one only a provider can answer, and asking it costs nothing.

**Two bounds are named, not hidden:**

1. **XLF carries 2.56–3.21% unmapped constituent mass** in every snapshot
   governing a selected event. The complete basket is therefore complete up to
   that residual, which propagates into the basket return as a bound.
2. **The announcement clock is minute-resolution.** `anntims` is a minute
   stamp; SEC acceptance times are second-precise but time the *filing*, not
   the wire, and sit 43–44 minutes from the I/B/E/S stamp for three of the four
   earnings events. The 10-second and 30-second horizons stay in the registered
   estimand but are **marked unsupported** until a wire-level timestamp is
   obtained. A one-second quote product does not fix this.

Neither bound blocks the request. Both would block a claim about intraday
ordering, and no such claim is made here.

The other two verdicts were considered and rejected:
`BLOCKED_NAMED_QUOTE_OR_WEIGHT_INPUT` would require a specific input that is
missing and unobtainable — none is; the weight gap is quantified and the clock
gap has a known, cheap, non-vendor remedy.
`PRODUCT_UNSUITABLE_FOR_REQUESTED_MEASUREMENT` would require evidence that a
product cannot serve the measurement — no product has been evaluated, because
no vendor has been contacted.

---

## Contents

| file | what it is |
|---|---|
| `REPORT.md` | the original seven-section report, unaltered |
| `RESULTS_FULL.txt` | the full stage logs behind it, unaltered — **see restrictions** |
| `figures/fig1_delay.png` | delay-measure distribution |
| `figures/fig2_response.png` | response-path figure |
| `figures/fig3_spread.png` | decile spread |
| `figures/fig4_precision.png` | precision / MDE grid |
| `ADDENDUM.md` | definitions table, restored clipped numbers, count reconciliation, corrections E1–E2 and C1–C7 |
| `SELECTION_RULE.md` | the six-event selection rule, **committed before the selection program existed** (`30dc8e6` precedes `6d6d56b`) |
| `MANIFEST.md` | the six events, clock evidence, weight evidence, quote windows, file inventory |
| `ESTIMAND.md` | the response-path estimand, horizon gating, three-way reporting split |
| `REQUEST_UNSENT.md` | the drafted, **unsent** vendor specification and quotation request |
| `s8_six_events.csv` | the six selected events with keys and ranks |
| `s8_coverage.csv` | weight provenance and coverage, per event-ETF |
| `s8_corp_actions.csv` | corporate-action flags within ±5 sessions |
| `s8_windows_summary.csv` | quote-window totals |
| `s8_constituent_counts.csv` | constituent count and summed weight per event-ETF |

Reproduced by `src/s8_01_select_six.py` and `src/s8_02_evidence.py`. The
selection is deterministic — a salted SHA-256 tie-breaker, no seed, no
sampling — so rerunning must yield the identical six keys and ranks.

---

## Sharing restrictions

**Read this before putting anything here in a shared or public location.**

A file's presence in this directory is **not** a determination that its content
is safe for redistribution. The determinations actually made are:

**`RESULTS_FULL.txt` — restricted. Do not redistribute publicly as-is.**
Lines 445–449 carry a firm-level diagnostic block ("the extreme names") that
discloses CRSP firm-date price levels for named securities — e.g. Chesapeake
Energy, PERMNO 78877, 2020-02-26, pre-event price $0.48. These are individual
licensed data points, not aggregates. Redact that block, or share the file only
within the licensed environment.

**Held back entirely — not in this repository.** These are per-security
licensed extracts and stay under `$PPW_WORK/out` on SCC:

- `s8_constituents.parquet` — actual holdings and weights, per fund per date
- `s8_windows.parquet` — the per-security quote-window manifest

Sending either to a vendor is itself a disclosure of licensed holdings and
requires a licence determination first. `REQUEST_UNSENT.md` §5.1 sets out a
disclosure ladder; the recommended rung transmits **counts and window structure
only**, with no constituent names, and is sufficient to answer every
product-suitability question.

**Cleared for sharing.** `REPORT.md`, the four figures, all five CSVs, and the
five markdown documents in this directory. These are aggregates, event-level
records, and public-source clock evidence.

---

## What this handoff does not do

- It does not make an intraday leadership claim. Six events could not support
  one, and this pilot is not designed to.
- It does not claim vendor confirmation of anything. No vendor was contacted.
- It does not assume a free sample, trial credit, institutional licence,
  current price, or historical coverage.
- It does not change any number in `REPORT.md`. `ADDENDUM.md` corrects one
  transcription error (E1) and narrows seven interpretations (C1–C7); the
  underlying estimates are untouched.
- It has not been pushed to any remote.

## The next step

After explicit access or purchase approval — which has not been given — the
next data-dependent step is **measurement validation on the six-event sample**,
not full-history acquisition. What that pilot must display, and what it cannot
deliver, is in `ESTIMAND.md`.
