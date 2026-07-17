# P1-T1 re-run prompt v2 — failure-driven revision of the L1 extraction rules

Owner-run on the box (deepseek lane + gemini lane). Written by seat C from
the QC evidence in `p1/t1_qc_report.md`. The v1 rule block
(`T1_RULES` in `p1/make_extraction_specs.py`) is replaced by `T1_RULES_V2`
below; everything else in the pipeline (condensing, chunking, sentinels,
fences) stays as-is.

## 1. Why the v1 answers went wrong — failure taxonomy, each mapped to a fix

| # | Failure (measured) | Root cause in the v1 prompt | Fix in v2 |
|---|---|---|---|
| F1 | **Correlated false positives** (~18% of A∩B-agreed events): MF→MF mergers, ETF→ETF trust adoptions, CEF→ETF/MF, Class C→A share aging all coded as events, by BOTH workers | "转换事件" never defined. Any filing with "Board approved the reorganization of X into Y" pattern-matches. The workers never had to check WHAT X and Y are | Mandatory 2-step TARGET/ACQUIRER classification before any verdict + explicit decoy list with verbatim no_event outputs |
| F2 | **Multi-fund undercount** (both channels, 0 multi-event answers on a corpus with many 2–6-fund filings) | "输出一行 JSON 对象" — the schema literally forbids a second event | Output is ALWAYS `{"events":[...]}`; instruction to enumerate every Target Fund row in the filing's fund table |
| F3 | Missed retrospective conversions (deepseek, ~22 IDs: Soundwatch, FundX SAI, Matrix…) | Rules define announce/effective dates for *upcoming* deals only; nothing says a completed conversion counts | Explicit retrospective rule with its own example |
| F4 | Prose/vague dates (gemini 87% of rows: "March 27, 2026", "fourth quarter of 2026") | No output format stated for dates | `YYYY-MM-DD` only; month/quarter/prose → `"NA"` + raw text into `evidence`; `date_basis` field says which date was used |
| F5 | Fund names & multi-class lists in ticker fields (A 56, B 146 rows) | No format stated for tickers | Ticker = 2–6 uppercase chars or `"NA"`, never a name; multi-class → NA + list in `evidence` |
| F6 | Dropped IDs (60) and re-typed/mangled accession keys (2) | Nothing tells the worker to echo IDs verbatim or that the answer-map must be complete | Copy-the-id-verbatim rule + count self-check before emitting |
| F7 | Unparseable nested-JSON strings (7) | v1 asks for a JSON object per item inside a JSON map → double-encoding ambiguity | Answer value is a plain JSON object, never a string |
| F8 | Spurious NEED_HUMAN across filings (pre-fence gemini void) | "同一基金日期矛盾" didn't say *within this one filing* | Restated: contradiction must be two quotes from THIS filing's excerpt |
| F9 | Same-excerpt verdict flips (A 10, B 5 duplicate-group splits) | No deterministic decision procedure; borderline judgment re-rolled per chunk | The步骤-based procedure in v2 makes the verdict mechanical; temperature stays 0 |

## 2. Drop-in replacement rule block — `T1_RULES_V2`

Paste into `p1/make_extraction_specs.py` replacing `T1_RULES`, regenerate
specs, re-run. (Bilingual anchors kept where the manual is Chinese; the
operative text is English for cross-vendor parity.)

```
T1_RULES_V2 = """【规则 v2 (manual §T1 + QC修订). Follow the STEPS in order for THIS filing's excerpt.

STEP 1 — Identify every reorganization/conversion described. For each one name:
  TARGET = the entity whose shareholders receive new shares (acquired/converted fund)
  ACQUIRER = the entity that survives (acquiring/successor fund)
STEP 2 — Classify both, quoting the excerpt:
  TARGET must be an OPEN-END MUTUAL FUND (multi-class shares, bought/redeemed at NAV).
  ACQUIRER must be an ETF (exchange-traded fund / "will operate as an exchange-traded
  fund" / listed on an exchange).
STEP 3 — Verdict:
  EVENT only if TARGET=open-end mutual fund AND ACQUIRER=ETF. This includes:
   (a) shell-ETF conversions and cross-trust reorganizations into a new ETF;
   (b) acquisition of a mutual fund by an EXISTING ETF;
   (c) RETROSPECTIVE statements of completed conversions ("the ETF is the successor
       to the X Fund as a result of a reorganization on <date>") — record the event
       with effective_date = the stated completion date.
  NOT events — output {"no_event": true, "reason": "<code>"} with code:
   MF_TO_MF   mutual fund merged into another MUTUAL FUND (acquirer not an ETF)
   ETF_TO_ETF target is itself an ETF (trust adoption/re-domiciliation/rebrand)
   CEF        target is a closed-end fund (incl. CEF→ETF: code CEF, add "flag":"CEF_to_ETF")
   INTERVAL   acquirer is an interval fund or other non-ETF structure
   SHARECLASS share-class conversion/aging (e.g. Class C→A), fund rename, no reorganization
   MENTION    ETFs appear only as portfolio holdings/risk language/ordinary prospectus text
  If the excerpt truly shows no reorganization at all, use code MENTION.

OUTPUT — one JSON value per item id. Copy the item id EXACTLY as printed after 文件:
(character-for-character; never re-type digits). Value is a PLAIN JSON object (never a
quoted/escaped string):
  {"events": [ {one object PER TARGET FUND named in the filing — enumerate ALL rows of
   the Target/Acquiring fund table, a 4-fund filing yields 4 objects}, ... ]}
  or the no_event object above.
Each event object:
  fund_name        target mutual fund's full name (from excerpt)
  family           fund family/trust (from excerpt)
  mutual_fund_ticker / etf_ticker
                   a single 2-6 char UPPERCASE symbol from the excerpt, else "NA".
                   NEVER a fund name. Multiple class tickers → "NA" and list them in evidence.
  announce_date    YYYY-MM-DD only. Board-approval date if stated; else the document's own
                   date; else the filed date. Vague ("May 2020","Q4 2026") → "NA".
  date_basis       "board" | "document" | "filed" | "NA"
  effective_date   YYYY-MM-DD only; the stated closing/completion date. Vague → "NA".
  asset_class      equity_US / equity_intl / fixed_income / other — ONLY if locatable in the
                   excerpt (bond/muni/high-yield/MBS→fixed_income; International/EM/Asia→
                   equity_intl; explicit US equity→equity_US; managed-futures/multi-asset/
                   long-short→other). Name alone insufficient → "NA".
  AUM_at_conversion_USD  number from excerpt or "NA"
  source_accession copy from the 文件 line
  confidence       H = fund identity + (announce or effective) with explicit basis;
                   M = identity clear, dates partly missing/document-dated;
                   L = identity inferred from title only
  evidence         ≤25-word quote fragment supporting the verdict (for events: the words
                   showing the acquirer is an ETF; for no_event: the words showing why not)
NEED_HUMAN only when TWO date statements INSIDE THIS ONE EXCERPT contradict for the same
fund: {"NEED_HUMAN": true, "quotes": ["...", "..."]}. Different filings never contradict.
Never fill any field from memory — excerpt-locatable or "NA".

SELF-CHECK before emitting (do this, don't print it): every input item id appears exactly
once in your answer map (count them); every event object quotes ETF-acquirer evidence;
every date matches ^\\d{4}-\\d{2}-\\d{2}$ or is "NA"; no ticker field contains a space.】"""
```

For **T13** (`T13_RULES_V2`): same scaffold with STEP 2 replaced by
"the filing concerns a SEMI-TRANSPARENT actively managed ETF (launch,
operation under an exemptive order, or a transparency-regime change)", the
event object extended with `disclosure_regime` ("daily_full"/"semi_transparent",
the regime AFTER the described change) and `proxy_basket_type` (the excerpt's
own term, normalized to lowercase_underscore: e.g. "proxy_portfolio",
"portfolio_reference_basket", "activeshares", "nyse_ams"; else "NA") — and a
note that a semi-transparent→transparent conversion IS an event (record both
the old and new regime in evidence), not a no_event.

## 3. Run instructions (box)

```bash
# 1. update the rule blocks
#    edit p1/make_extraction_specs.py: replace T1_RULES/T13_RULES with the V2 blocks
# 2. regenerate all four specs (same worklists, same sentinels ride along)
python p1/make_extraction_specs.py
# 3. archive v1 outputs for the three-way record, then clear
cd ops/l1/out && for f in P1-T1-events P1-T1-events-B P1-T13-ant P1-T13-ant-B; do
  mv $f.json $f.v1.json; done && cd -
# 4. re-run both lanes (deepseek ~¥15, gemini ~¥18–25 at paid-key prices)
python ops/runner/l1_driver.py --live
# 5. verify + push (finals must be git add -f'd — .gitignore eats them otherwise)
python ops/l1/merge_mopup.py P1-T1-events   2>/dev/null || true   # coverage check prints gaps
git add -f ops/l1/out/P1-T1-events*.json ops/l1/out/P1-T13-ant*.json
git commit -m "P1 T1/T13 v2-prompt re-run, both channels" && git push
```

Re-run scope: FULL re-run of both channels is recommended (cost is trivial
and v2 changes the schema, so mixing v1/v2 rows inside one channel would
complicate the arb). Keep the v1 outputs as `.v1.json` — three verdicts per
filing (v1-A, v1-B, v2-A, v2-B + reference channel) make the arb's
adjudication strictly stronger.

Acceptance checks after the run (seat C will re-audit): coverage 1418/1418 +
414/414; zero string-encoded values; every date ISO or NA; no ticker with a
space; multi-fund filings (Guinness 2020-09-22, Goldman 2025-06-20,
JPMorgan 2022-01-19, FundX, Mirae) each yield ≥2 event rows; the 47
known-decoy filings in qc report §3 each yield no_event with the right
reason code.
