# Start here — fixed P1 data order

The sample is decided. Read `PILOT_DATA_ORDER.md`; the machine-readable order is already constructed. Do not run the earlier arbitrary 12-request technical preflight in place of this order.

## Contents
- `securities.csv`: eight named stocks, historical PERMNOs, predecessor-membership locators and limitations.
- `conversion_cohorts.csv`: the two actual conversion packages and distinct effective/operation dates.
- `earnings_events.csv`: exact 32 issuer release dates, evidence URLs, analysis-access status and fixed 16-release budget alternative.
- `core32_requests.csv`: 220 disjoint stock/SPY BBO-1s intervals, exact UTC bounds.
- `core16_budget_reduction_requests.csv`: 115 intervals for the predefined smaller complete base.
- `validation_requests.csv`: fixed XNAS MBP-1 and Arca BBO overlap requests.
- `extra_etf_requests.csv`: optional IWM / post-only DFAC / post-only BSVO.
- `*_event_request_map.csv`: every requested event leg maps to a deduplicated physical request.
- `build_order.py`: reproduces manifests offline (`pandas`, `exchange_calendars`); makes no vendor calls.
- `budget_gate.py`: chooses whole bundles from genuine saved costs; makes no vendor calls or purchases and does not pretend to enforce vendor billing.
- `CODEX_EXECUTE_ORDER.md`: execution instructions and agent/effort assignments.
- `order_summary.json`, `manifest_hashes.json`: measured generated-request counts and artifact hashes.

## Owner launcher

Use only when you actually hold the applicable account/data rights and intend to approve the bounded purchase. The text is an instruction for the owner to send, not an already-issued authorization.

```text
Execute p1_fixed_pilot/CODEX_EXECUTE_ORDER.md and the fixed manifests.

I approve acquisition of the named public historical quotation slices through
my configured Databento account, using no more than $100 of quoted gross usage
and never exceeding $125 total or my actual remaining credits, whichever is
less. No cash top-up, subscription, additional fee agreement or other purchase
is authorized. Verify all exact prices before submitting charged requests.

Use Terra/Medium as executor (retain an existing Sol/Medium coordinator) and
one separate Sol/High acquisition reviewer. The sample, feed, dates, windows
and balanced budget reduction are fixed in the order; do not ask agents to
redesign them. Price and complete the authorized order in the same run.

This explicitly supersedes the earlier vendor METADATA_ONLY instruction for
THIS named purchase. I also approve source/measurement development on the
listed PRE_FOCAL windows; they are not asserted to be globally untreated.
POST_FOCAL windows may be acquired and archived, but their response values and
treatment contrasts remain sealed pending separate analysis approval.

Keep raw data within my licensed environment. Do not copy secrets, access other
protected tables, change the research contract, purchase reference data,
run P1 treatment/power regressions, push or merge.

Return actual files/coverage/receipt and the limited independent review.
The only ordinary remaining procurement unknown should be the actual API
quote/availability; resolve it against these manifests, not by inventing a
price or returning another general preflight request.
```

## Important status

The manifests and date arithmetic were generated and checked locally. No
Databento authentication, live SDK call, charged data request, market-data
quality test or independent agent review was run here. $70/$20/$10 are planned
allocations, not vendor quotes. The exact-price procedure is mandatory.

Core quotations are Nasdaq-venue BBO, not SIP NBBO. The 8-stock/2-wave pilot
is a development sample, not a powered causal study. These limitations are
fixed in the order rather than left for an agent to discover after purchase.
