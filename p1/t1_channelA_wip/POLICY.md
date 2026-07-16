# P1-T1-events channel A — in-session extraction protocol (Anthropic lane)

## Session state
- Task: P1-T1-events (channel A), leased to seat C, branch claude/p1-work-qpqb8j
  (harness-designated; lease commit already on it, pushed).
- Spec: ops/l1/P1-T1-events.yaml (1418 items, 1357 unique excerpts).
- Worklist: scratchpad/worklist.jsonl (hash -> member ids). Reading batches:
  scratchpad/cb_001..cb_090.txt (condensed excerpts).
- Results: scratchpad/res/rb_NNN.jsonl — one line per hash: {"h":..., "v":...}.
- Progress: rb_001..rb_007 done. Continue from cb_008.
- After all 90: run merge.py -> ops/l1/out/P1-T1-events.json (git add -f),
  lineage, decisions.md routing note, commit+push. Task #2/#3 in tracker.

## Frozen extraction rules (manual §T1, from spec — do not drift)
- Every field must be locatable in the excerpt; otherwise "NA". No memory.
- Event = mutual fund → ETF conversion/reorganization (incl. acquisition of a
  MF by an existing ETF). NOT events: MF→MF mergers, ETF→ETF adoptions,
  CEF rights offers, ETFs mentioned as portfolio holdings, acquiring-ETF
  prospectuses with no conversion statement in the excerpt (note tickers in
  _evidence for arb).
- Retrospective statements of completed conversions ARE events (record with
  the stated effective date).
- Fields: fund_name, family, mutual_fund_ticker, etf_ticker, announce_date,
  effective_date, asset_class(equity_US/equity_intl/fixed_income/other),
  AUM_at_conversion_USD, source_accession, source_url (added at fan-out),
  confidence(H/M/L).
- announce_date policy: board-approval date when stated in the excerpt
  (earliest disclosed intent); else the document's own date; else filed date
  (say which in _evidence). effective_date: stated closing/conversion date
  only ("Q3 2021" etc. -> NA + note).
- Missing announce or effective -> confidence M at best (缺一降). Missing
  fund identity or only doc-title inference -> L.
- asset_class only when locatable (bond/muni/high-yield -> fixed_income;
  International/EM -> equity_intl; explicit US equity -> equity_US;
  long-short/multi-asset -> other; else NA). Do not infer geography from
  fund-name conventions alone.
- Multi-fund filings: {"events": [event_obj, ...]} (documented for arb in
  _meta). Single event: bare object. No conversion: {"no_event": true}.
- Every verdict carries _evidence (short quote/paraphrase + what's missing).
- 同一基金日期矛盾 within one filing -> NEED_HUMAN verdict + both quotes.

## Sentinels (answer at assembly, from repo-verified facts)
S1 Dimensional; S2 2025-11; S3 2021-06.

## _meta template (mirrors ops/l1/out/E2-T1-facts.json precedent)
channel: "A — re-routed deepseek→Anthropic L2 session (box L1 lane down since
2026-07-10, no ETA; precedent E2-T1-facts/E2-T9b escalations); cross-vendor
vs channel B (gemini_free) preserved."
