# P1 — the event count, resolved

_Seat C. **Rev 2, 2026-08-27** — the owner-gate recheck pool is adjudicated and
closed; the register is rebuilt. Every number recomputed in-container from
committed files, with the reproduction command given. Nothing from memory._

## The answer

**172 conversions with a verified effective date, across 96 waves.**

```bash
python p1/t1_arb/resolve_recheck.py   # verify adjudications, emit the overlay
python p1/t1_arb/assemble.py          # rebuild events_merged.csv
python p1/t2_wrds/build_waves.py      # rebuild the wave registry
```

| | rev 1 (2026-08-19) | **rev 2 (now)** |
|---|---:|---:|
| unique conversion groups | 237 | **264** |
| → dated, in `events_merged.csv` | 131 | **172** |
| → distinct waves | 78 | **96** |
| → equity_US | 36 | **46** |
| → equity_intl | 25 | **31** |
| → fixed_income (excluded by design) | 36 | 51 |
| → other | 9 | 10 |
| → `asset_class` blank | 25 | 34 |
| held back (no ISO effective date) | 92 | **73** |
| confidence H / M / L | 77 / 53 / 1 | **106 / 65 / 1** |

Of the 172: **139 already have a complete +120 trading-day post-window**; 11 are
future-dated. Effective dates run 2021-03-26 → 2026-11-20; announcements
2020-05-01 → 2026-07-08. Contract check: `PASS [events_merged] 172 rows, 13 cols`.

**"200+" is now the wrong number in both directions.** The corpus found 264
conversion groups; the *study register* holds 172. The plan's §2 figure of "累计
203 起" carries no source locator and includes fixed income, so it should not be
cited — our own count is better evidenced and larger.

---

## What was wrong, and what fixed it

`assemble.py` silently dropped every event record whose `_spotcheck.disposition`
was `recheck`, `defer` or `not_event`. The 2026-07-18 owner gate had assigned one
of those to **111 records across 69 fund groups — but only 4 were `not_event`.**
The rest were parked with reasons that all asked one question:

> the excerpt proves a reorganization **into** an ETF, but does it prove the
> **target** was an open-end mutual fund, rather than a closed-end fund or
> another ETF?

That question turned out to be answerable from evidence this repo already
carried. `p1/t1_channelA_wip/handoff/cb_*.txt` holds **3.6 MB of condensed filing
excerpts covering all 1,418 accessions** — every gated record had one. It never
needed `sec.gov`, which is EGRESS_BLOCKED here (re-verified today by curl → 403
at the proxy, by the agent-proxy status endpoint, and by WebFetch — not taken on
a prior session's word).

### The adjudication

`p1/t1_arb/recheck_resolution.json` records one verdict per fund group against a
stated evidentiary standard, each citing a verbatim quote:

| | promote if the excerpt… |
|---|---|
| **S1** | states the target is a mutual fund / open-end management investment company |
| **S2** | names two or more retail share classes **of the target** (a CEF and an ETF have none) |
| **S3** | is a supplement to the target's own Summary/statutory Prospectus — Form N-1A disclosure, which only an open-end fund files |
| **S4** | directs holders to exchange into another mutual fund of the same complex |
| **D1** | *reject* — the acquirer offers multiple share classes, so the destination is a mutual fund (MF→MF) |
| **D2** | *reject* — the target is itself described as an ETF (ETF→ETF) |

Anything else stays **unresolved**: not promoted, not deleted, visible in the
register with its reason. Meta-rule 4.

| verdict | fund groups | records |
|---|---:|---:|
| **event** (released) | **50** | **85** |
| unresolved | 16 | 20 |
| not_event (confirmed rejection) | 3 | 6 |

### Why this is not just an assertion

`resolve_recheck.py` re-reads **every quote out of the cited accession's
committed excerpt and refuses to emit anything if one is missing** — character
for character, folding only typography (curly quotes, non-breaking spaces). A
verdict resting on text that is not there is exactly the hallucination case
meta-rule 1 exists for, and a quote nobody re-checks is indistinguishable from a
quote from memory. The check runs in CI, and a test deliberately doctors a quote
to prove the guard bites.

### The rejections are as informative as the promotions

The three `not_event` groups were all one 2021 filing (Litman Gregory Funds
Trust), and reading it confirmed the gate rather than overturning it:

- **iM Dolan McEniry Corporate Bond Fund** — the *acquirer* offers "Institutional
  Class Shares and Investor Class Shares", so the destination is a mutual fund.
  MF→MF, not a conversion. The gate had flagged it for the right reason.
- **iM DBi Managed Futures Strategy ETF / iM DBi Hedge Strategy ETF** — "The
  Target Managed Futures Strategy ETF and Target Hedge Strategy ETF and their
  corresponding Acquiring Funds are exchange-traded fund[s]". ETF→ETF.

### The 16 unresolved groups, and the one pattern behind them

Almost all are N-14s **filed by the acquiring ETF trust**, whose excerpt window
carries the boilerplate "What are the differences between an ETF and a mutual
fund?" comparison table but never states what the target is. That table appears
in these filings regardless and is not evidence about any particular target.

Baron (FinTech, Technology, Financials), Lazard (4), Harding Loevner, JPMorgan
National Municipal Income, William Blair Emerging Markets Debt, Fort Pitt
Capital, Morgan Stanley Mortgage Securities Trust, OTG Latin America (×2),
Locorr. Two have a second defect worth naming: **Lazard US High Yield ETF** and
**Locorr Investment Trust** have an acquiring-ETF name and a *trust* name
respectively in the `fund_name` field — there is no converting fund to key on, so
they could not be promoted even if the conversion is real.

**Each needs one full N-14 read.** That is the entire remaining backlog on the
event count, and it is 16 documents.

---

## Three integrity problems this surfaced

### 1. wave_id was renumbering silently — fixed

`build_waves.py` assigned `W001…` by rank over sorted effective dates. Adding 19
waves, several of them early, would have moved **36 existing wave_ids** — and
`conv_exposure_free.parquet` carries `wave_id` per cell, so every one of those
cells would have been re-pointed at the wrong wave with nothing raised.

Assignment is now **append-only**: any `(effective_date → wave_id)` binding
already in `waves.csv` is frozen and reused; new dates take ids after the current
max. Verified: **0 existing bindings moved**, DFA is still W002, 19 new ids
assigned. A test inserts a synthetic event dated before every existing one and
asserts nothing renumbers.

### 2. One wave date moved, and 7 ConvExp cells are stale

**Pabrai Wagons Fund**'s closing date moved 2026-02-06 → 2026-02-09, because
releasing its gated records brought in a later-filed accession stating the new
date, and the frozen policy is that the latest-filed filing wins. Its old wave
date is retired. **7 non-treated ConvExp cells now carry a stale wave binding;
zero treated cells are affected.** A test pins both numbers.

### 3. The classification backlog is no longer harmless

Rev 1 recorded that **zero** treated cells sat in a wave containing an
unclassified fund, which made the DFA finding independent of the `asset_class`
backlog. That is no longer literally true. Releasing **Thrivent Mid Cap Value
Fund** (no `asset_class`) into wave W065 (2025-11-14), which already carried one
treated cell (BELFB, ConvExp 1.30%), puts **exactly 1 treated cell** at stake.

One cell cannot move a 389-stock scenario or the 92.8% concentration. But the
claim "the backlog cannot move anything" has to stop being made, and the test now
pins the number at 1 rather than asserting zero.

---

## What did NOT change, and why

**The treated-stock numbers still describe the 131-event build:**

| ConvExp ≥ 0.5% | stocks | waves |
|---|---:|---:|
| ALL (as built) | 389 | 10 |
| excl DFA (W002) | 36 | 9 |
| **W002 share** | **361 / 389 = 92.8%** | |

`conv_exposure_free.parquet` is built by `p1/t2_free/build_nport_convexp.py`,
which fetches N-PORT holdings from SEC endpoints. Blocked here, and the local
cache is empty and gitignored (box-local). **So the 41 newly released conversions
have no ConvExp cells yet, and the treated counts above cannot be refreshed in
this container.** Rebuilding it is a box task, and it is now the single highest-value
one for P1: 10 of the 41 new conversions are equity_US, and the exclude-DFA arm
currently stands at 36 stocks against a power floor of 33.

Until that rebuild runs, **quote 172 conversions / 96 waves for the event
register, and 389 stocks / 10 waves / 92.8% for the treated sample, and say they
are measured at different vintages.** They are not yet the same build.

---

## Reproduce the whole thing

```bash
python p1/t1_arb/recheck_dossier.py       # evidence dossier from the excerpts
python p1/t1_arb/resolve_recheck.py       # verify every quote, emit the overlay
python p1/t1_arb/assemble.py              # -> events_merged.csv (172)
python p1/t2_wrds/build_waves.py          # -> waves.csv (96), append-only ids
python p1/t1_reconcile/sample_scenarios.py
python p1/wrds/universe.py --write
python -m pytest p1/tests/test_recheck_resolution.py -q
```

`p1/t1_arb/arb_report.md` now carries a permanent **Owner-gate pool** section
listing every still-excluded record with its gate reason and its adjudication, so
the pool can never go silent again. Released + still-excluded must sum to the
full pool, and a test enforces it.

## Honest limits

- **16 fund groups remain unresolved**, needing one full N-14 read each. They are
  named above. Until then the register is a floor.
- `asset_class` is blank on **34 of 172 (19.8%)**, so "46 equity_US" is a floor too.
- The adjudication is **one model reading committed text** — a third channel over
  the two cheap ones, which is what the QC report's mitigation #3 asked for, but
  not an independent dual-channel pass. Every call is quote-backed and re-verified
  mechanically; none is a majority vote.
- No post-v2 contamination rate has been measured. The v2 re-run cleared 46/47
  known decoys and reached 97.2% agreement with the reference channel, so the
  register should be far cleaner than the 18% measured on v1 — but that is a
  reason not to quote a number, not a licence to quote the old one.
