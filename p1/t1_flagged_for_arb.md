# P1-T1 — deepseek v2-A items flagged for third-model (qwen) arbitration

Primary channel = deepseek v2-A (accepted, 1418/1418, 97.2% agreement with the
reference channel on the 45% overlap). This file lists the verdicts that are
**contested or unverifiable**, to be re-run by an independent model (qwen,
alibaba family). Runnable subset: `ops/l1/P1-T1-events-arb-qwen.yaml` (140 items).
A flag does NOT mean deepseek is wrong — several are cases where deepseek is
right and the reference channel erred (noted inline).

## Tier A — 41 evidence-backed / schema / self-risk flags (must arbitrate)

| accession | deepseek | reason | flag(s) | note |
|---|---|---|---|---|
| 0000894189-25-003724 | event | EVENT | EVENT_NO_ETF_QUOTE | event but evidence omits ETF/exchange wording |
| 0000894189-25-010747 | event | EVENT | LOW_CONF | deepseek self-rated confidence L |
| 0000930413-22-001188 | event | EVENT | REF_DISAGREE | contested; ref: N-14/A pre-effective amendment 2 (2022-06-21): same AXS/Collaborative  |
| 0000930413-22-001217 | event | EVENT | REF_DISAGREE | contested; ref: 497 (2022-06-21): five Collaborative Investment Series Trust Target Fu |
| 0000930413-25-002048 | event | EVENT | B_DISAGREE+EVENT_NO_ETF_QUOTE | event but evidence omits ETF/exchange wording |
| 0000945908-25-000554 | no_event | MENTION | REF_DISAGREE | ds MISSED? ref=event; ref: 497 supplement (prospectus dated 2024-11-29, filed 2025-09-18): Boar |
| 0001032423-20-000089 | no_event | MENTION | MISSING_EVIDENCE | no_event with empty evidence — reason unverifiable |
| 0001032423-20-000105 | no_event | MF_TO_MF | MISSING_EVIDENCE | no_event with empty evidence — reason unverifiable |
| 0001081400-22-000747 | no_event | MF_TO_MF | MISSING_EVIDENCE | no_event with empty evidence — reason unverifiable |
| 0001104659-25-034754 | event | EVENT | EVENT_NO_ETF_QUOTE | event but evidence omits ETF/exchange wording |
| 0001133228-24-010291 | no_event | MF_TO_MF | REF_DISAGREE | ds MISSED? ref=event; ref: Fidelity Merrimack Street Trust N-14 filed 2024-11-15 (doc title: Fi |
| 0001133228-24-011315 | event | EVENT | REF_DISAGREE | ds likely RIGHT (evidence quotes ETF acquirer); ref: American Beacon Select Funds N-14 2024-12- |
| 0001133228-25-000086 | no_event | MENTION | REF_DISAGREE+MISSING_EVIDENCE | ds MISSED? ref=event; ref: Fidelity Merrimack Street Trust N-14 filed 2025-01-03 (information s |
| 0001193125-20-268564 | no_event | MENTION | MISSING_EVIDENCE | no_event with empty evidence — reason unverifiable |
| 0001193125-20-289030 | no_event | MENTION | MISSING_EVIDENCE | no_event with empty evidence — reason unverifiable |
| 0001193125-21-174908 | event | EVENT | EVENT_NO_ETF_QUOTE | event but evidence omits ETF/exchange wording |
| 0001193125-24-176766 | no_event | ETF_TO_ETF | MISSING_EVIDENCE | no_event with empty evidence — reason unverifiable |
| 0001193125-24-182734 | no_event | MF_TO_MF | MISSING_EVIDENCE | no_event with empty evidence — reason unverifiable |
| 0001193125-24-182763 | no_event | MF_TO_MF | MISSING_EVIDENCE | no_event with empty evidence — reason unverifiable |
| 0001193125-26-235541 | event | EVENT | B_DISAGREE |  |
| 0001213900-25-067869 | no_event | MENTION | MISSING_EVIDENCE | no_event with empty evidence — reason unverifiable |
| 0001213900-25-120167 | no_event | ETF_TO_ETF | B_DISAGREE |  |
| 0001398344-21-003295 | no_event | MENTION | REF_DISAGREE | ds MISSED? ref=event; ref:  |
| 0001398344-23-012799 | event | EVENT | LOW_CONF | deepseek self-rated confidence L |
| 0001398344-23-018006 | no_event | MENTION | MISSING_EVIDENCE | no_event with empty evidence — reason unverifiable |
| 0001398344-25-013501 | event | EVENT | EVENT_NO_ETF_QUOTE | event but evidence omits ETF/exchange wording |
| 0001445546-24-004217 | event | EVENT | REF_DISAGREE | ds likely RIGHT (evidence quotes ETF acquirer); ref: First Trust Series Fund N-14 2024-06-07: W |
| 0001445546-24-005389 | no_event | MF_TO_MF | B_DISAGREE |  |
| 0001445546-25-007210 | event | EVENT | REF_DISAGREE | ds likely RIGHT (evidence quotes ETF acquirer); ref: First Trust Series Fund N-14 2025-10-31: V |
| 0001445546-25-007214 | event | EVENT | REF_DISAGREE | ds likely RIGHT (evidence quotes ETF acquirer); ref: First Trust Series Fund N-14 2025-10-31: V |
| 0001615774-19-004946 | event | EVENT | REF_DISAGREE | ds likely RIGHT (evidence quotes ETF acquirer); ref: Amplify ETF Trust N-14 2019-03-29: YieldSh |
| 0001615774-19-008515 | event | EVENT | REF_DISAGREE | ds likely RIGHT (evidence quotes ETF acquirer); ref: Amplify N-14/A 2019-05-28: same ETF-to-ETF |
| 0001615774-19-009307 | no_event | ETF_TO_ETF | B_DISAGREE |  |
| 0001680359-24-000315 | event | EVENT | REF_DISAGREE | ds likely RIGHT (evidence quotes ETF acquirer); ref: FT ETF Trust N-14 2024-09-12: 'Like the Ta |
| 0001829126-22-020405 | no_event | MENTION | REF_DISAGREE | ds MISSED? ref=event; ref: 497 2022-12-20: Alpha Architect Tail Risk ETF prospectus naming the  |
| 0001829126-23-001258 | no_event | MENTION | REF_DISAGREE | ds MISSED? ref=event; ref: 497 2023-02-01 (Alpha Architect Tail Risk ETF prospectus XBRL): Arin |
| 0001829126-23-001991 | no_event | MENTION | REF_DISAGREE | ds MISSED? ref=event; ref: 497 2023-03-13 (EA Bridgeway Omni Small-Cap Value ETF prospectus XBR |
| 0001829126-23-004882 | event | EVENT | REF_DISAGREE | ds likely RIGHT (evidence quotes ETF acquirer); ref: 497 2023-07-25: Highland/iBoxx Senior Loan |
| 0001999371-24-001777 | no_event | ETF_TO_ETF | MISSING_EVIDENCE | no_event with empty evidence — reason unverifiable |
| 0001999371-24-004206 | no_event | ETF_TO_ETF | MISSING_EVIDENCE | no_event with empty evidence — reason unverifiable |
| 0001999371-25-004112 | no_event | MENTION | REF_DISAGREE | ds MISSED? ref=event; ref: ETF Opportunities Trust N-14 filed 2025-04-10: mutual fund Target Fu |

## Tier B — ETF_TO_ETF category, corpus-wide (52; ~55% un-refereed)

deepseek's false-positive events cluster in the ETF-to-ETF boundary (Amplify/YieldShares, BondBloxx/SNLN, AXS/Collaborative, Ionic). The reference channel only covers 45% of the corpus, so ALL items deepseek coded ETF_TO_ETF are sent to qwen to catch same-type errors in the unchecked region. IDs:

`0000894189-19-006990 0000894189-19-007612 0000894189-19-007720 0000894189-19-007867 0000894189-21-005518 0000894189-21-006707 0000930413-22-000901 0001104659-26-008053 0001104659-26-027691 0001104659-26-033932 0001104659-26-054947 0001133228-25-000515 0001133228-25-002526 0001137439-24-001447 0001193125-20-196617 0001193125-24-176766 0001193125-24-218946 0001213900-20-019602 0001213900-20-025036 0001213900-25-035595 0001213900-25-052868 0001213900-25-053228 0001213900-25-053772 0001213900-25-065732 0001213900-25-066942 0001213900-25-067779 0001213900-25-120167 0001213900-26-006220 0001387131-23-007855 0001387131-23-009286 0001387131-23-009317 0001398344-21-024040 0001398344-22-001559 0001398344-22-002411 0001398344-22-007367 0001398344-22-010009 0001398344-23-014326 0001398344-23-015067 0001398344-26-003172 0001445546-20-005466 0001445546-21-000348 0001445546-21-000625 0001592900-25-000039 0001592900-25-000325 0001615774-19-009307 0001829126-23-004305 0001999371-24-001777 0001999371-24-004206 0001999371-24-004858 0001999371-24-007206 0001999371-24-010468 0001999371-24-012550`

## Tier C — CEF category, corpus-wide (52)

CEF→ETF is a spec 'FLAG for arb' class regardless (closed-end funds are out of the MF→ETF scope but arbitrage-relevant); confirming deepseek's CEF calls costs little. IDs:

`0000897101-19-000123 0000897101-19-000358 0000897101-19-000892 0001104659-19-054429 0001104659-21-037747 0001104659-21-051409 0001104659-23-065529 0001104659-23-076994 0001104659-23-077626 0001104659-24-090454 0001104659-24-104212 0001104659-24-105255 0001133228-19-000825 0001133228-20-000839 0001193125-19-069154 0001193125-19-069158 0001193125-19-069161 0001193125-19-211791 0001193125-19-211809 0001193125-19-317752 0001193125-20-061055 0001193125-20-061057 0001193125-20-069925 0001193125-20-100197 0001193125-20-243917 0001193125-20-272941 0001193125-20-272942 0001193125-20-278576 0001193125-20-289933 0001193125-21-207753 0001193125-21-236413 0001193125-22-069424 0001193125-23-138361 0001193125-23-169149 0001193125-23-169994 0001193125-24-013179 0001193125-24-045882 0001193125-24-047599 0001398344-25-004999 0001445546-20-003122 0001445546-23-004116 0001445546-23-005258 0001445546-23-005463 0001445546-23-005580 0001445546-24-008115 0001445546-25-001268 0001445546-25-001315 0001445546-26-000293 0001445546-26-002743 0001445546-26-002801 0001999371-25-001924 0001999371-26-011653`

## Coverage caveat (read before trusting the un-flagged 1278)

The reference channel checks only 45% of the corpus. For the un-refereed 55%, confidence in deepseek rests on (a) the 97.2% agreement observed on the overlap and (b) deepseek's internal schema consistency. Tiers B/C extend independent checking to the two error-prone categories, but MENTION (195) and MF_TO_MF (385) verdicts in the un-refereed region are NOT individually arbitrated here. If you want full assurance, run qwen on the whole 1418 instead of this 140-item subset — cost is still trivial (~¥15). This file is the minimal high-yield set per your 'flag the suspect ones' ask.

## After qwen runs

Merge `ops/l1/out/P1-T1-events-arb-qwen.json` and diff each verdict against deepseek v2-A. Three outcomes per item: (1) qwen agrees with deepseek → resolve, keep deepseek; (2) qwen agrees with the reference channel against deepseek → flip; (3) all three differ → human gate. Seat C will run that diff on request.
