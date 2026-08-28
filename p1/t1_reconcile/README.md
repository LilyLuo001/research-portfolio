# P1-B1 — event-set reconciliation

_Seat C, 2026-08-19. Offline; no WRDS, no network. Every number regenerates from
`sample_scenarios.py`, which reads only committed files._

Answers the roadmap's V-4 (event completeness) and puts numbers under V-1 (the
DFA question) and V-6 (the international sleeve).

---

## 1. The headline: the two robustness cuts compound

| Dose tier | Scenario | Stocks | Waves | Powered (≥33)? |
|---|---|---:|---:|:--|
| ≥0.5% | ALL (as built) | 389 | 10 | ✅ |
| ≥0.5% | Option A — drop pure-intl waves | 381 | 6 | ✅ |
| ≥0.5% | A-strict — drop any intl-touching | 373 | 5 | ✅ |
| ≥0.5% | **excl DFA (W002)** | **36** | 9 | ✅ *(3 above)* |
| ≥0.5% | **excl DFA + Option A** | **28** | 5 | ❌ |
| ≥0.5% | **excl DFA + A-strict** | **20** | 4 | ❌ |
| ≥1% | ALL (as built) | 24 | 9 | ❌ |
| ≥1% | Option A | 21 | 6 | ❌ |
| ≥1% | A-strict | 16 | 5 | ❌ |
| ≥1% | excl DFA | 16 | 8 | ❌ |
| ≥1% | excl DFA + Option A | 13 | 5 | ❌ |
| ≥1% | excl DFA + A-strict | 8 | 4 | ❌ |

Two things that were not visible before:

**(a) The ≥1% dose tier is underpowered as built.** 24 treated stocks against a
floor of 33 — *before* any robustness cut. §8 item 4 makes dose tiers
(continuous / binary / tercile) a robustness axis, so the ≥1% tier cannot carry a
robustness claim on its own. It should be reported as descriptive, or the tier
line moved.

**(b) V-1 and V-6 compound.** Excluding DFA alone leaves 36 stocks — three above
the floor. Add Option A and it is 28; add A-strict and it is 20. **The
international-sleeve decision is not independent of the DFA decision**, and the
two were being considered separately. Four of the ten treated waves (W003, W020,
W043, W075) are international-only, and they sit almost entirely in the non-DFA
remainder — which is exactly the part the exclude-DFA robustness check relies on.

Recommendation for V-6, given this: **Option A, not A-strict.** A-strict costs
another 8 stocks in the arm that can least afford them, in exchange for a
purity that the DFA anchor wave (`no_intl`) does not need.

## 2. Completeness against the published count

Trade reporting puts conversions at **203 over five years, 60 in 2025**, with the
200 mark crossed in May 2026
([VettaFi](https://www.advisorperspectives.com/commentaries/2026/05/29/cross-200-mutual-fund-etf-conversions),
[ETFdb](https://etfdb.com/fixed-income-content-hub/mutual-fund-etf-conversions-cross-200/)).
P1 has **131 events across 86 accessions**.

The gap is not mysterious — **P1's own T1 QC report already diagnosed it, and both
defects are still OPEN**:

- **§5 structural undercount.** Both L1 extraction prompts forced one JSON object
  per filing (输出一行 JSON 对象), so multi-fund filings lost all but one event in
  *both* channels. The QC report calls the undercount "systematic, not random".
  The mop-up partially repaired this — 24 accessions now carry >1 event, one
  carries 6 — but the QC's own worked examples are still short: **Goldman is 1 row
  where the reference channel found 2025 ×4 + 2026 ×2.**
- **§3 correlated contamination, ~18%.** In the audited region, 47 of 258
  A∩B-agreed events are CEF→ETF, CEF→MF or share-class aging misread as
  conversions. Both cheap workers share the bias, so **dual-channel agreement does
  not screen it** — this is the one error class arbitration cannot see.

The QC also notes the reference channel covers batches 1–38 (families A–G) only.
Splitting the committed event set on that line: **72 events in the audited region,
59 in the unaudited H–Z region** where neither the multi-fund re-pass nor the
contamination audit has run.

**Net:** 131 is simultaneously an undercount (multi-fund collapse, unaudited
region) and an overcount (~18% contamination). These do not cancel — they are
different rows. Both need the box.

## 3. The classification backlog — and why it does not rescue the DFA problem

**25 of 131 events (19.1%) have no `asset_class`**, across 15 accessions. That is
the field defining the equity_US analysis universe, so the "36 equity_US" figure
is a floor, not a count. By fund name many look like US equity (Fidelity
Disruptive ×7, Baron FinTech/Technology, BBH Large/Mid Cap, Scharf, Pabrai
Wagons, AB Equity Income), but **naming them from the fund title is exactly what
meta-rule 1 forbids** — the class must come from the filing's investment objective
with a locator. All 15 accessions carry a `source_url` in
`p1/edgar_filings/manifest.csv`, so this is a clean extraction task; it needs
egress this container does not have (`www.sec.gov` is EGRESS_BLOCKED — verified
today by both curl and WebFetch).

Runbook: `classify_asset_class-BOX.md`.

**Important negative result:** all 131 events reached the wave build, and **zero
treated cells at either dose tier sit in a wave containing an unclassified fund.**

```
treated cells at stake from the classification backlog: {'>=0.5%': 0, '>=1%': 0}
```

So finishing the classification **cannot** change any row of the scenario table.
It matters for the sample-definition prose and for any equity_US filter applied
downstream — but it is not an escape hatch from the DFA concentration. V-1 has to
be decided on the numbers as they stand.

## 4. What this changes

| Decision | Before | After this reconciliation |
|---|---|---|
| V-1 DFA | "92.8% concentrated" | unchanged, and now known to be *robust* to the classification backlog |
| V-6 intl sleeve | looked independent | **compounds with V-1**; Option A recommended over A-strict |
| Dose tiers | assumed all powered | **≥1% is underpowered as built** (24 < 33) |
| V-4 completeness | "never reconciled" | reconciled: two OPEN QC defects + a 59-event unaudited region |

## 5. Files

| Path | What |
|---|---|
| `sample_scenarios.py` | regenerates the table from committed files |
| `sample_scenarios.csv` | the table, committed |
| `classify_asset_class-BOX.md` | runbook for the 15-accession extraction |
