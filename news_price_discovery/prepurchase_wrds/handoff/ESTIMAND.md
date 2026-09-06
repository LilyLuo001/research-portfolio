# The timing estimand, preserved

The registered outcome is a **response path**, not a single terminal residual.
This file records what the pilot must show, which horizons the current clock
evidence supports, and what a future planning update would have to specify.
Nothing here is a new research question and nothing here is an intraday claim.

## 1. The estimand

For each event, on a quote clock, the object is the path

```
D(h) = r_ETF(T, T+h) − r_basket(T, T+h),    h ∈ {10s, 30s, 1m, 5m, 15m}
```

where `r_basket` is the weight-weighted return of the **complete** constituent
set at the governing snapshot, and `T` is the release instant. The 15-minute
endpoint is one point on this path. It is not the estimand.

The pilot must display, for every event and every horizon:

1. the ETF return `r_ETF(T, T+h)`;
2. the corresponding **portfolio** return `r_basket(T, T+h)`, built from the
   complete constituent set, not a proxy and not the announcing stock alone;
3. their difference `D(h)`;
4. **quote freshness and coverage** — for each security and horizon: how many
   quote updates occurred, the age of the prevailing quote at each sampling
   instant, the share of the window with no fresh quote, and the share with a
   one-sided or absent quote. A difference computed over stale quotes is an
   artefact of the sampling, not a response, and without this display the two
   cannot be told apart.

For the four micro events, the pilot must additionally identify the **announcing
stock's weighted contribution**, `weightᵢ × rᵢ(T, T+h)`, so the part of the ETF
move mechanically attributable to the announcer is visible separately from the
rest of the basket.

## 2. Reporting is split three ways, and stays split

Results are reported separately for:

- **macro** — the two FOMC events, regular session;
- **premarket micro** — NDAQ 2022-04-20, EMR 2023-02-08;
- **aftermarket micro** — ESS 2022-10-26, GL 2021-07-21.

These three are **not** pooled. Session and news type are completely confounded
in this design: every macro event is in regular hours and every micro event is
outside them. Liquidity, quote frequency, spread, and venue participation all
differ enormously between the regular session and the extended session, so any
macro-versus-micro difference measured here is a difference in *news type and
session together*. Pooling them and calling the result an effect of news type
would be wrong, and no amount of controls inside a six-event sample fixes it.

Stating the confound is not a defect of the pilot — the pilot's job is to
establish whether the measurement can be made at all in each of the three
regimes, which requires exactly this stratification.

## 3. Horizon support is gated by the clock, and 10s/30s are currently unsupported

The achieved announcement-clock resolution is **one minute**. `anntims` is a
minute stamp. The corroborating SEC 8-K acceptance times carry second precision
but time the **filing**, not the newswire release, and they sit 43–44 minutes
away from the I/B/E/S stamp for three of the four earnings events (see
`MANIFEST.md` §2). They confirm the session; they do not pin the instant.

| horizon | supported by current clock evidence? | what would change it |
|---|---|---|
| 10 s | **no** | a wire-level release timestamp at second precision |
| 30 s | **no** | same |
| 1 m | **marginal** — the horizon equals the clock resolution, so `T` may be misplaced by up to a minute | same |
| 5 m | yes | — |
| 15 m | yes | — |

The FOMC statement release time of 14:00:00 ET is a scheduled, published instant
and is better anchored than the earnings clocks. Even so, it is recorded here at
minute precision, and the same gate applies until second-level release evidence
is in hand.

**Consequence.** The 10-second and 30-second evaluations remain in the
registered estimand and are **not** dropped, but they are marked unsupported and
must not be reported as measurements until a wire-level timestamp is obtained
for each event. Obtaining one is a separate, cheap, non-vendor task: the
press-release exhibit (EX-99.1) attached to each 8-K, and the newswire record,
generally carry a dateline. That work has not been done and its outcome is not
assumed here.

A quote product sampled at one second cannot rescue a release time known only to
the minute. Quote resolution and announcement-clock resolution are separate
constraints and the binding one is the announcement clock.

## 4. What a future planning update must specify

The existing MDE80 grid in `REPORT.md` is retained exactly as it is: a
**conditional assumption grid** for a single prespecified endpoint (T to T+15
minutes), driven by an assumed 0.5–10 bps per-event residual SD. It is not a
measurement, and — per correction C7 in `ADDENDUM.md` — its 15-minute numbers
are **not** evidence of power at 10 seconds, nor of power for a
macro-minus-micro contrast.

Any sample-based planning update, once real intraday data exist, must state:

1. **the estimand** — which horizon or which contrast across horizons, named in
   advance;
2. **the surprise normalisation** — the scale, fixed before any response is
   seen, and whether it is comparable across the macro and micro families (a
   rate surprise in basis points and an EPS surprise as a percent of price are
   not on one scale, and no common scale is assumed here);
3. **separate variances for the macro and micro regimes** — not one pooled
   residual SD. The regimes differ in session, liquidity and event count, and
   the daily work already shows different variance behaviour across them;
4. **paired-path dependence** — `D(h)` at successive horizons on one event is
   one path, heavily autocorrelated across `h`; the five horizons are not five
   independent observations;
5. **date and firm dependence** — as in the daily work, resampled by whole date
   jointly across ETFs, since one source event replicated into several ETF rows
   is not several shocks;
6. **horizon multiplicity** — evaluating five horizons and reporting the best is
   specification search; the adjustment or the prespecified primary horizon must
   be named up front.

**More one-second rows do not create more independent announcement shocks.** A
15-minute window sampled at one second yields 900 rows per security, and every
one of them is the same announcement. The number of independent shocks in this
pilot is **six** — two per regime. Any calculation that treats sampled rows as
sample size is wrong by roughly three orders of magnitude, and the
rows-independent column of the existing grid is retained only to size that
overstatement, never as an estimate.

## 5. What the pilot cannot deliver

Six events cannot power a test of the ordering question, and this pilot is not
designed to. It can establish whether:

- quotes exist at the requested times, on the requested dates, in the extended
  session;
- the complete basket can be priced from those quotes at each horizon;
- quote staleness is low enough that `D(h)` is a measurement rather than a
  sampling artefact;
- the announcement clock can be anchored finely enough to place `T`.

If all four hold, the measurement is feasible and a powered design can be
specified. If any fails, the failure is informative and is reported as such. A
null or opposite-sign `D(h)` on six events is neither a technical failure nor
evidence about the research question.
