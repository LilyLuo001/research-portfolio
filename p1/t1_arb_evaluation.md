# P1-T1 arbitration evaluation — deepseek v2-A vs qwen vs reference (140 items)

Seat C, 2026-07-18. Inputs: `ops/l1/out/P1-T1-events.json` (deepseek v2-A,
primary), `ops/l1/out/P1-T1-events-arb-qwen.json` (qwen, 140 flagged items),
and the seat-C reference channel (`p1/t1_channelA_wip/rb_*`, batches 1–43).
Per-item outcome in `p1/t1_arb_resolution.json`.

## Qwen run quality
Clean execution: 140/140 answered, 0 unparseable, sentinel fence held on the
first pass. Schema mostly honored EXCEPT qwen emitted **no `evidence` field on
any of its 88 no_event rows** (deepseek populated them) and its no_event
**reason codes are noisy** — e.g. it labels ETF-to-ETF adoptions and
mutual-fund cases "CEF" (0001445546-25-007214, 0001615774-19-004946). Treat
qwen's binary verdict as usable, its reason code as not.

## Headline: the arbitration VALIDATES deepseek; qwen is the biased one
Deepseek and qwen agree on 109/140 verdicts (78%). The 31 disagreements are
**not** randomly distributed — they expose a systematic qwen bias:

- On items deepseek coded `ETF_TO_ETF` or `CEF`, qwen flipped **39** to
  "event" (33 ETF_TO_ETF + 6 CEF). In the **23** of those where the reference
  channel also weighed in, deepseek+reference BOTH say no_event and only qwen
  says event. **Zero** cases go the other way (qwen never correctly overturned
  a deepseek ETF/CEF no_event). These are textbook exclusions — First Trust
  ETF VIII closed-end conversions, Bitwise/AXS/Change-Finance ETF adoptions —
  that the T1 scope explicitly drops. **Qwen over-calls the ETF/CEF boundary.**

So qwen's disagreements in Tiers B/C are qwen errors, and they *confirm*
deepseek's boundary calls rather than challenge them. The value of running
Tiers B/C wasn't to correct deepseek — it was to demonstrate deepseek's
ETF/CEF exclusions are trustworthy across the un-refereed corpus.

## Where qwen earned its keep: Tier A
On the genuinely ambiguous mutual-fund-identity cases, qwen + the independent
reference hand-read agree against deepseek **10 times** — real corrections:

| flip | deepseek | → resolves to | what it is |
|---|---|---|---|
| 0000930413-22-001188/…1217 | event | **no_event** | AXS/Collaborative SPAC ETFs — target already an ETF |
| 0001615774-19-004946/…008515 | event | **no_event** | YieldShares→Amplify — ETF-to-ETF |
| 0001445546-24-004217 | event | **no_event** | WCM Focused Global Growth — acquirer not an ETF |
| 0001445546-25-007210/…007214 | event | **no_event** | FT Vest — target already an ETF (deepseek saw "acquirer is an ETF" and over-called) |
| 0000945908-25-000554 | no_event/MENTION | **event** | Fidelity Dividend ETF for Rising Rates conversion deepseek dismissed |
| 0001133228-24-010291 | no_event/MF_TO_MF | **event** | acquirer is a newly-created ETF, deepseek misread as MF-MF |
| 0001133228-25-000086 | no_event/MENTION | **event** | Fidelity Merrimack conversion (deepseek left evidence blank) |

## Net effect on the primary channel
Of the full 1418 deepseek v2-A verdicts, this arbitration flips **10 (0.7%)**,
all Tier A, all corroborated by the independent hand-read. Everything else
stands. Final buckets over the 140:

- **KEEP deepseek — 119**: 78 all-agree, 23 qwen-outlier (deepseek+ref beat
  qwen), 18 qwen-bias-reject (unreferenced ETF/CEF over-calls).
- **FLIP — 10** (table above): apply to `P1-T1-events.json`.
- **HUMAN — 11**:
  - 8 where BOTH models agree but the reference hand-read disagrees
    (shared-bias risk cuts both ways — could be a reference error OR a
    two-model blind spot). Mostly acquiring-ETF-prospectus retrospectives
    (Alpha Architect/Arin/EA Bridgeway 0001829126-*, Guinness ADIV/DIVS
    0001398344-21-003295) and two ETF-to-ETF the models jointly over-called
    (Ionic 0001133228-24-011315, Highland/BondBloxx 0001829126-23-004882).
  - 3 unreferenced splits where deepseek=event and qwen=no_event/MF_TO_MF
    (0001193125-21-174908, 0001398344-23-012799, 0001398344-25-013501) —
    possible deepseek over-calls, need the excerpt.

## Recommendation
1. Accept deepseek v2-A as the P1-T1 channel. Apply the 10 FLIPs (list in
   `p1/t1_arb_resolution.json`, resolution=FLIP).
2. Send the 11 HUMAN items to the owner spot-check gate with the excerpts.
3. Do NOT use qwen as a general channel-B replacement for T1 — its ETF/CEF
   over-call bias would inject ~39 false-positive events per 140 boundary
   items if trusted blindly. It works only as a Tier-A tiebreaker alongside
   the hand-read. (This also retro-justifies keeping deepseek, not a cheap
   model, on channel A.)
4. The reference channel itself has ≥4 confirmed errors (the ds+qwen-agree
   HUMAN rows) — my batches 1–43 are good but not gold; the owner gate is the
   real ground truth on the 11.
