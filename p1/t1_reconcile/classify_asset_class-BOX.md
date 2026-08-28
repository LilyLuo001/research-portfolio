# BOX RUNBOOK — classify the 25 unclassified events

_Needs egress to `www.sec.gov`, which the seat-C container does not have
(verified 2026-08-19: curl → `CONNECT tunnel failed, 403`; WebFetch →
`EGRESS_BLOCKED`). Everything else is prepared._

## What and why

`p1/events_merged.csv` has **25 events (19.1%) with a blank `asset_class`**, across
**15 accessions**. `asset_class` is the field that defines the equity_US analysis
universe, so until it is filled the "36 equity_US events" figure is a floor rather
than a count.

**This does not change any sample scenario** — `sample_scenarios.py` shows zero
treated cells at either dose tier sit in a wave containing an unclassified fund.
It matters for the sample-definition prose and for any downstream equity_US
filter, not for the DFA decision.

## The one rule

**Do not classify from the fund name.** Meta-rule 1: the class comes from the
filing's investment objective / principal strategy, with a verbatim quote and a
locator. "Fidelity Disruptive Technology Fund" *looks* like equity_US; that is a
guess, not evidence, and guesses are what this pipeline exists to prevent.

If the filing does not state it clearly enough to classify, leave
`asset_class_FILL` blank and write why in `evidence_quote_FILL`. A blank is a
legitimate output. `NEED_HUMAN` is a legitimate output. A guess is not.

## Input

`p1/t1_reconcile/asset_class_TODO.csv` — 25 rows, pre-joined to the manifest, every
row carrying a working `source_url`:

| column | filled by |
|---|---|
| `fund_name`, `family`, `effective_date` | already present |
| `source_accession`, `source_url` | already present — the locator |
| `asset_class_FILL` | **you** — one of `equity_US` / `equity_intl` / `fixed_income` / `other` |
| `evidence_quote_FILL` | **you** — the verbatim sentence the class is read from |
| `evidence_page_FILL` | **you** — page or section anchor within the filing |

## Classification rule (frozen — `docs/Project_1.md` §90)

| class | test |
|---|---|
| `equity_US` | principal strategy is US equity securities |
| `equity_intl` | principal strategy is non-US / global / international equity |
| `fixed_income` | principal strategy is debt securities |
| `other` | allocation, fund-of-funds, multi-asset, or none of the above |

Funds-of-funds (the FundX Upgrader family, Touchstone Dynamic Allocation) are
`other` even when the underlying holdings are equity — the fund's own strategy is
the test, and their N-PORT holdings are fund shares, not stocks.

## Run

```bash
# with egress:
#  1. fetch each distinct source_url (15 of them)
#  2. locate the "Investment Objective" / "Principal Investment Strategies" section
#  3. fill the three _FILL columns, one row per fund named in the filing
#  4. save as p1/t1_reconcile/asset_class_FILLED.csv

# then merge back and verify nothing else moved:
python p1/t1_reconcile/apply_asset_class.py p1/t1_reconcile/asset_class_FILLED.csv
python p1/t1_reconcile/sample_scenarios.py       # must print identical numbers
python -m pytest p1/tests -q
```

`sample_scenarios.py` printing **identical** numbers afterwards is the check that
the merge touched only the blank field — the classification is expected to change
nothing in the scenario table, and if it does, something else moved and the merge
is wrong.

## Note for whoever runs this

Ten of the 15 accessions cover more than one fund (the Fidelity Disruptive filing
alone covers seven). That is the same multi-fund structure behind the §5
undercount in the T1 QC report — while you have these filings open, it is cheap to
also check whether the filing names funds that are **absent** from
`events_merged.csv` entirely. If it does, record them; do not add them here. That
belongs to the separate multi-fund re-pass, which is still OPEN.
