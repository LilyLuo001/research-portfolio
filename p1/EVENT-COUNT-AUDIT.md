# P1 — is the event count really "200+"?

_Seat C, 2026-08-27. Owner asked to double-check the sample size before booking
WRDS. Every number below was recomputed in-container from committed files today;
the reproduction command is given for each. Nothing from memory (meta-rule 1)._

## Short answer

**"200+ conversions" is defensible as a count of conversions our EDGAR corpus
found. It is badly wrong as a description of the sample that identifies the
paper.** Those are two different numbers separated by a factor of twenty-four:

| | count | what it is |
|---|---:|---|
| Conversion groups found in our corpus | **237** | unique conversions across 1,419 screened filings |
| → carry a verbatim ISO effective date | **131** | `events_merged.csv`, the study key |
| → distinct effective dates (waves) | **78** | `t2_wrds/waves_members.csv` |
| → waves that yield any ConvExp cell | **49** | 29 waves map to zero US-listed holdings |
| → **waves that yield ≥1 treated stock** | **10** | ConvExp ≥ 0.5% |
| → **distinct treated stocks** | **389** | of which **361 (92.8%) are one wave** |

The plan's own §2 already says the honest version of this — *"美股权益类转换的
AUM 高度集中于 DFA 2021-06 … 不是均匀交错的教科书 staggered DiD"* — so this is a
confirmation of a known risk, not a new one. What is new is that the funnel is
now measured end to end rather than asserted.

---

## Where "203" comes from, and why it should not be cited as-is

`docs/基金转换实验_博士研究计划.md` §2 states: *"2025:60 起、31 家公司;累计 203
起、~2600 亿美元(含固收)"*. Searched the whole doc set: **that figure appears
once and carries no source locator** — no URL, no accession, no page. Under
meta-rule 1 it is a narrative number, not a usable one. It also explicitly
includes fixed income (含固收), which the design excludes.

Our own corpus independently found **237 conversion groups**, which is *above*
203. So the industry-scale claim is not in doubt. It is the wrong number to put
in an abstract, because the paper does not run on 237 conversions.

---

## The full funnel, with reproduction commands

```
python p1/t1_arb/assemble.py          # deterministic; reproduces events_merged.csv byte-identically
```
Verified today: re-running `assemble.py` reproduces the committed
`events_merged.csv` and `arb_report.md` with **zero diff**. The pipeline is
reproducible; the counts below are not estimates.

```
1,419  filings screened (conversion-candidate corpus, EDGAR N-14/497/N-1A)
  652  filings judged "event"
1,197  event records (filing × fund)
  111  ── EXCLUDED by the owner gate as recheck/defer/not_event   ← see next section
1,086  event-filings entering assembly
  237  unique conversion groups (filings collapsed per conversion)
   ├── 131  fund_name + verbatim ISO effective_date  →  events_merged.csv
   ├──  92  held back, no ISO effective date (34 carry approximate timing)
   └──  14  dropped as cross-trust duplicates of a merged row
```

### Of the 131 in `events_merged.csv`

| asset_class | n |
|---|---:|
| equity_US | 36 |
| fixed_income | 36 | ← excluded by design (§4 剔除固收) |
| equity_intl | 25 |
| **blank** | **25** | ← 19.1% unclassified; "36 equity_US" is a floor |
| other | 9 |

Confidence: 77 H / 53 M / 1 L. 118 of the 131 have a complete +120 trading-day
post-window as of today; 4 are future-dated.

### Of the 78 waves, only 10 produce treated stocks

```
python p1/t1_reconcile/sample_scenarios.py
```

| wave | treated stocks (ConvExp ≥ 0.5%) |
|---|---:|
| **W002** (2021-06-11, DFA ×4) | **361** |
| W019 | 12 |
| W064 | 8 |
| W008 | 6 |
| W075, W020 | 3 each |
| W007 | 2 |
| W003, W043, W065 | 1 each |

**361 / 389 = 92.8%.** The nine non-DFA waves contribute 36 stocks between them,
against a simulated power floor of 33 (`t2a_power_results.json`). Four of those
nine are international-only sleeves.

---

## The finding that actually matters: 111 events are parked, not rejected

`assemble.py` silently drops any event record whose `_spotcheck.disposition` is
`recheck`, `defer` or `not_event`. The owner gate of 2026-07-18 assigned one of
those to **111 event records — 66 distinct funds**. Only 4 were judged
`not_event`. **99 are `recheck`: not rejected, just never re-examined.**

```
python3 -c "import json;f=json.load(open('p1/t1_events_final.json'));..."   # see below
```

The exclusion reasons are almost all one class:

| reason | n |
|---|---:|
| target / acquired-fund type unproven (7 phrasings) | 66 |
| acquirer-ETF only; target type unproven | 19 |
| source filed after the gate date (2026-07-28 > gate 2026-07-18) | 8 |
| genuinely out of scope (ETF→ETF, no reorg language) | 5 |

Every one of the first three groups says the same thing: *the excerpt window
proves a reorganization **into** an ETF, but does not prove the **target** was an
open-end mutual fund rather than a closed-end fund or another ETF.* That is
answerable by reading the full N-14 — one document per fund. It is not a
judgment call, and it is not a data purchase.

### What is at stake in that pool

Excluding the 9 funds already represented in `events_merged.csv`:

- **57 new distinct funds**, **43 with a verbatim ISO effective date**
- across **26 potential new effective dates** (new waves)
- **15 of those 26 dates already have a complete +120 trading-day post-window**
- asset class of the 43: 15 fixed_income (irrelevant), **6 equity_US**,
  **9 equity_intl**, 9 unclassified, 4 other

The 15 equity ones, named:

| fund | family | effective | class |
|---|---|---|---|
| Goldman Sachs Enhanced U.S. Equity Fund | Goldman Sachs Trust | 2025-11-13 | equity_US |
| Goldman Sachs Focused Value Fund | Goldman Sachs Trust | 2025-11-13 | equity_US |
| Goldman Sachs Strategic Growth Fund | Goldman Sachs Trust | 2025-11-13 | equity_US |
| Goldman Sachs Technology Opportunities Fund | Goldman Sachs Trust | 2025-12-04 | equity_US |
| Columbia Integrated Large Cap Value Fund | Columbia Funds Series Trust II | 2026-03-16 | equity_US |
| Nomura Smid Cap Core Fund | Ivy Funds | 2026-11-06 | equity_US |
| abrdn China A Share Equity Fund | abrdn Funds | 2025-10-17 | equity_intl |
| abrdn Focused Emerging Markets ex-China Fund | abrdn Funds | 2025-10-17 | equity_intl |
| Lazard Emerging Markets Opportunities Portfolio | Lazard Active ETF Trust | 2025-10-24 | equity_intl |
| Lazard International Dynamic Equity Portfolio | Lazard Funds | 2025-04-30 | equity_intl |
| Emerging Markets Portfolio | Sanford C. Bernstein Fund, Inc. | 2026-01-23 | equity_intl |
| Hartford Climate Opportunities Fund | The Hartford Mutual Funds, Inc. | 2026-10-16 | equity_intl |
| Hartford International Equity Fund | The Hartford Mutual Funds, Inc. | 2026-10-23 | equity_intl |
| American Beacon Ninety One International Franchise Fund | American Beacon Select Funds | 2026-01-09 | equity_intl |
| OTG Latin America Fund | ETF Opportunities Trust | 2025-07-11 | equity_intl |

This corrects one line in the current roadmap. `ROADMAP-2026-08-19.md` §L-3 says
the §5 multi-fund undercount is still OPEN and cites Goldman as "still 1 row where
the reference channel found 2025 ×4 + 2026 ×2". **The extraction is not the
problem any more.** All six Goldman conversions are present in
`t1_events_final.json`, correctly multi-fund, with dates and asset classes — the
v2 prompt fixed §5 as its addendum claimed. They are missing from
`events_merged.csv` because the owner gate parked them at `recheck`, and nobody
came back. That is a different, cheaper, and more tractable defect than the one
the roadmap records.

### Reproduce the pool

```bash
python3 - <<'PY'
import json, pandas as pd, re
f = json.load(open('p1/t1_events_final.json'))
em = pd.read_csv('p1/events_merged.csv', dtype=str)
ISO = re.compile(r'^\d{4}-\d{2}-\d{2}$'); merged = set(em.fund_name)
rows = []
for fid, v in f.items():
    if fid == '_meta' or v.get('no_event') or v.get('NEED_HUMAN'):
        continue
    for e in (v.get('events') or [v]):
        sc = e.get('_spotcheck')
        if sc and sc.get('disposition') in ('not_event', 'recheck', 'defer'):
            rows.append(dict(fund=e.get('fund_name'), fam=e.get('family'),
                             eff=e.get('effective_date'), ac=e.get('asset_class'),
                             disp=sc['disposition'], reason=sc.get('reason'), acc=fid))
d = pd.DataFrame(rows)
new = d[~d.fund.isin(merged)]
print(len(d), 'records |', d.fund.nunique(), 'funds |', new.fund.nunique(), 'new')
print(new[new.eff.astype(str).str.match(ISO)].drop_duplicates('fund')
        .ac.fillna('NA').value_counts())
PY
```

---

## What this means for the WRDS purchase

**Nothing.** None of the above changes the table list or the pull scope, and none
of it is fixable with WRDS. The recheck pool needs `sec.gov` (EGRESS_BLOCKED in
this container — verified, not assumed) and the asset_class backlog needs the
same. Buy the tables as listed in `p1/wrds/TABLE-REQUEST.md`.

Two things it *does* change:

1. **The pull universe should be built to accommodate the recheck pool later.**
   `stock_names` is a CUSIP→PERMNO map over our endogenous universe; if 43 new
   conversions land afterwards, their holdings introduce CUSIPs the map does not
   cover, and re-pulling means re-renting. Mitigation is cheap and is applied in
   `p1/wrds/universe.py`: the pull covers the dropped-denominator cells too
   (6,747 CUSIPs, not 2,241), which already over-covers by ~3×.

2. **The abstract's sample sentence should be written from the funnel, not the
   headline.** Something like: *"237 mutual-fund-to-ETF conversions filed with the
   SEC between 2020 and 2026, of which 131 carry a verified effective date and 10
   waves produce stock-level treatment intensity above 0.5%, covering 389 US
   equities"* — with the DFA concentration stated in the same paragraph, per
   decision V-1.

## Honest limits of this audit

- The 92 held-back conversions and the 111 gated records overlap partially; both
  pools are documented separately and neither is silently dropped, but a single
  reconciled "master conversion register" does not exist yet. `held_back.json`
  on disk is a **stale snapshot (109 rows)** predating the date-recovery overlay;
  the live number from `assemble.py` is 92. It should be regenerated or deleted —
  a downstream consumer reading it today gets the wrong set.
- The ~18% correlated-contamination rate in `t1_qc_report.md` §3 was measured on
  the **v1** extraction. The v2 re-run cleared 46/47 known decoys and reached
  97.2% agreement with the reference channel. The current 131 should be far
  cleaner than 18% contaminated, but **no post-v2 contamination rate has been
  measured**, so no number should be quoted for it.
- `asset_class` is blank on 25 of 131 (19.1%), so every asset-class split above
  is a floor, not a count.
