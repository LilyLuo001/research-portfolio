# QC report — P1-T1-events / P1-T13-ant dual-channel outputs

Auditor: seat C (Anthropic in-session lane), 2026-07-17.
Inputs: `ops/l1/out/P1-T1-events{,-B}.json`, `ops/l1/out/P1-T13-ant{,-B}.json`
(main @ 92adddc), spec yamls, `p1/t1_channelA_wip/handoff/worklist.jsonl`,
and the independent Anthropic extraction `p1/t1_channelA_wip/rb_001–038.jsonl`
(batches 1–38 ≈ 40% of corpus, third vendor family) as reference channel.

## Verdict: NOT arb-ready without the mitigations below. Do not run
## T1-arb as a plain machine-diff; do not treat A∩B agreement as truth.

## 1. Coverage & parseability
| | T1-A (deepseek) | T1-B (gemini) | T13-A | T13-B |
|---|---|---|---|---|
| spec items | 1418 | 1418 | 414 | 414 |
| answered+parsed | 1418 ✓ | 1351 | 414 ✓ | 401 |
| missing | 0 | **60** | 0 | **13** |
| unparseable | 0 | 7 | 0 | 0 |
| bogus extra IDs | 0 | **2** (accessions with digits mangled: `0001133125-…` for real `0001193125-…`) | 0 | 0 |

→ B needs a mop-up re-run of 67 T1 IDs + 13 T13 IDs (~5% of corpus, trivial cost).
→ B mangling accession strings means **join on spec ID, never trust B's echoed
`source_accession`** (2 confirmed corruptions; assume more).

## 2. Headline rates
- T1-A: 787 event / 631 no_event / 0 NEED_HUMAN.
- T1-B: 952 event / 401 no_event / 0 NEED_HUMAN.
- Raw verdict agreement: 1089/1358 comparable IDs (80%). Disagreements:
  224 B-event-vs-A-no_event, 38 the other way.

## 3. CRITICAL: correlated false positives — agreement ≠ correctness
3-way check against the Anthropic reference channel (546 overlapping IDs):
- unanimous: 384 (70%).
- **47 IDs where BOTH box channels say event and the reference channel's
  quoted-evidence verdict is no_event.** All 47 adjudicated by reading the
  recorded evidence; every one is an out-of-scope action the spec excludes:
  MF→MF mergers (CLS, Great-West, BlackRock, Calamos, Centre, Columbia,
  Franklin, American Beacon, First Trust/WCM…), ETF→ETF trust adoptions
  (Alpha Architect/Gadsden, Bitwise, Amplify, AXS/Stance, Ionic),
  CEF→ETF (First Trust ETF VIII — spec says FLAG for arb, not event),
  CEF→MF (Brookfield), Class C→A share aging (Fidelity, Calamos).
- That is 47/258 ≈ **18% of A∩B-agreed events are contamination** in the
  audited region. Both cheap workers share the same bias (any "Board approved
  the reorganization" → event) so dual-channel agreement does NOT screen it.
- Sample caveat: batches 1–38 are alphabetical (companies A–G), not random;
  rate may drift either way in H–Z.
- Also: A misses retrospective completed conversions (22 IDs where B + reference
  agree event, A says no_event — e.g. Soundwatch Hedged Equity, converted
  2022-10-24, N-1A retrospective). B-only overcalls (78) exist too but plain
  arb catches those; the correlated-FP class is the one arb cannot see.

## 4. Field-level defects
- **Ticker pollution**: fund NAMES in ticker fields — A: 56 rows, B: 146 rows
  (e.g. `etf_ticker: "Dimensional US Marketwide Value ETF"`; B also packs
  multi-class lists `"MLOAX, MLOCX, …"` into `mutual_fund_ticker`).
  Frozen schema ⇒ normalize to NA unless a real symbol is present.
- **Dates**: B emits prose dates ("March 27, 2026", "fourth quarter of 2026")
  in **825 event rows (~87%)**; A has 35 non-ISO (mostly month/quarter-only
  values that policy says should be NA + note). Arb diff requires
  normalization first or every date is a false mismatch.
- **Intra-channel flake on identical excerpts** (42 dup-excerpt groups):
  A: 10 verdict splits + 3 date splits; B: 5 verdict splits + 18 date splits.
  Same text, different verdicts — direct lower bound on per-item noise.

## 5. Structural spec defect: single-object output drops co-filed conversions
Both L1 spec prompts force one JSON object per filing (输出一行 JSON 对象).
Multi-fund filings therefore lost all but one event in BOTH channels
(0 multi-event answers in either; reference channel has many:
Guinness Atkinson ×2, Mirae/Global X ×2, Goldman 2025 ×4 + 2026 ×2,
FundX ×4, Fidelity Enhanced ×6…). Undercount is systematic, not random.
Reference channel covers batches 1–38; batches 39–90 region needs either the
reference channel finished or a targeted multi-fund re-pass.

## 6. T13-ant
Both channels emitted ONLY `{disclosure_regime, proxy_basket_type}` (or
no_event) — the T1 base fields (fund, dates, tickers) are absent in BOTH,
so T13 outputs cannot support event dating on their own; treat them as an
attribute overlay keyed by accession. Substantive disagreement to arbitrate:
e.g. Putnam transparency-conversion filings (`0001193125-25-15384{1,2}`):
A says no_event, B says daily_full — the filing documents a semi-transparent→
transparent conversion approved 2025-06-27, squarely in T13 scope.

## 7. Fence caveat
"All fences green" = each chunk answered 3 static questions about one
synthetic excerpt (Ridgeline). It certifies liveness/format per chunk, not
extraction accuracy. §3–5 above are all fence-invisible error classes.

## Required mitigations before/at T1-arb
1. B mop-up run: 60+7 T1 IDs, 13 T13 IDs.
2. Arb pipeline: join strictly on spec ID; normalize dates to ISO (else NA);
   strip name-strings from ticker fields (NA).
3. Arb must adjudicate a THIRD class besides A/B splits: **A∩B-agreed events
   whose excerpt does not show an open-end MF → ETF conversion** — use the
   reference channel where it exists (40%), and add an agreed-event stratum
   to the human spot-check gate for the rest (agreement alone is not H-grade
   evidence; ~18% contamination measured in the audited region).
4. Multi-fund recovery pass (or finish reference channel batches 39–90 and
   union its event lists).
5. T1-arb adjudication rules should DOWN-WEIGHT, not trust, confidence fields
   from both channels (self-reported, uncalibrated against the above).
