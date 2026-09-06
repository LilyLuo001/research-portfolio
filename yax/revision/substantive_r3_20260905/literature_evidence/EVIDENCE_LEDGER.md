# Literature and official-documentation evidence ledger

**Created:** 2026-09-05
**Purpose:** factual foundation for the substantive R3 revision. This ledger records only claims checked against primary or official sources. It is not a substitute for the empirical results ledger.

## Status rules

- **VERIFIED:** directly supported by the linked primary source at the stated locator.
- **INFERENCE:** a bounded conclusion drawn from one or more verified facts; the reasoning is stated.
- **UNRESOLVED:** the inspected primary material does not establish the claim.
- **SEARCH RESULT:** a result of a dated, declared search protocol; not proof of universal absence.

## Load-bearing findings

| ID | Topic | Finding | Status | Source/locator | Revision consequence |
|---|---|---|---|---|---|
| BCC-01 | Version | The current BCC paper is the August 12, 2026 revision with data through June 2026. | VERIFIED | [Official PDF](https://digitaleconomy.stanford.edu/app/uploads/2026/08/Canaries_August2026.pdf), title page, abstract, note 1 | Cite/version-date every comparison. |
| BCC-02 | Population | BCC's main outcome is full-time, positive-earnings worker–firm-match employment in a balanced ADP firm panel, not national CPS employment. | VERIFIED | BCC PDF §1.1, p. 6 | Do not compare magnitudes without population/unit alignment. |
| BCC-03 | Headline | BCC's 19% shortfall is a “kept pace” comparison; its primary no-control age-22–25 Q5 occupation-regression coefficient is about −0.179. | VERIFIED | Abstract; §2.3; Table 1, pp. 13–14 | Never treat 19% as the regression coefficient or hiring-rate estimate. |
| BCC-04 | Flows | BCC also studies employer-match hires and separations, with 12-month counts divided by prior-year cell headcount. | VERIFIED | §2.4, p. 16; Figure B.7, p. 66 | CPS nonemployment entry is not the same flow. |
| BCC-05 | Public data | The August 2026 BCC appendix already reports monthly CPS age/exposure paths through June 2026 and ACS comparisons through 2024. | VERIFIED | Appendix §H, Figures H.1–H.8, Tables H.1–H.3, pp. 122–131 | Remove broad public-CPS/young-worker priority claims. |
| BCC-06 | Grouping | The official dashboard says occupations receive equal weight when exposure groups are formed, but the PDF's occupation outcome regressions are employment weighted. The PDF does not fully specify the cutoff/tie algorithm. | VERIFIED + UNRESOLVED | [Official dashboard](https://digitaleconomy.stanford.edu/project/indicators/canaries-dashboard/); BCC Tables 1–2 notes | Separate cut weights from regression weights; do not call employment-weighted cuts BCC-exact. |
| CPS-25A | Jan. 2025 | Updated controls add about 2.871m to population and 2.000m to employment when applied to the Dec. 2024 sample; official earlier months were not revised. | VERIFIED | [BLS 2025 adjustment memo](https://www.bls.gov/cps/methods/population-controls/population-control-adjustments-2025.pdf) | Treat Jan. 2025 as a level-series discontinuity. |
| CPS-25B | Jan. 2025 | BLS experimental factors cover major aggregates, not YAX age × occupation cells. | VERIFIED | [BLS experimental series](https://www.bls.gov/cps/methods/population-controls/experimental-series-accounting-for-january-2025-population-control-effects.htm) | Do not mechanically rescale subgroup cells. |
| CPS-SD | Shutdown | October 2025 CPS was not collected; November had delayed/extended collection, modified weighting, roughly 50% overlap, and a 64.0% response rate. | VERIFIED | [BLS shutdown impact page](https://www.bls.gov/cps/methods/2025-federal-government-shutdown-impact-cps.htm) | Preserve calendar gap; run month-exclusion sensitivity; do not interpolate. |
| CPS-26A | Jan. 2026 | January 2026 estimates and PUMF were reissued on March 6, 2026 with Vintage 2025 controls. | VERIFIED | [BLS revision notice](https://www.bls.gov/cps/notices/2026/population-control-revision-2026.htm) | Verify extract contains revised January file/weights. |
| CPS-26B | Jan. 2026 | Applied to Dec. 2025, the new controls reduce employment by about 1.432m and EPOP by 0.5 pp; prior official months were not revised. | VERIFIED | [BLS adjustment memo](https://www.bls.gov/web/empsit/cps-pop-control-adjustments.pdf) | Treat Dec.–Jan. level change as noncomparable. |
| IPUMS-01 | Extract vintage | IPUMS processed revised Jan. 2026 weights on Apr. 10, 2026, revised IDs/links on Jul. 13 and Aug. 14, 2026, and an April 2025 weight correction in June 2025. | VERIFIED | [IPUMS CPS revisions](https://cps.ipums.org/cps-action/revisions) | Record extract date/DDI/hash; refresh or bound affected stock/flow analyses. |
| RR-01 | Trend method | Rambachan–Roth requires a joint event-study coefficient vector, full covariance, reference-period ordering, post functional, and declared restriction grid. | VERIFIED | [ReStud article](https://doi.org/10.1093/restud/rdad018); [`HonestDiD`](https://github.com/asheshrambachan/HonestDiD) | A static coefficient/SE alone is not a valid input. |
| EXP-W | Webb | Webb measures patent–task textual exposure separately for software, robots, and AI. | VERIFIED | [Author PDF](https://www.michaelwebb.co/webb_ai.pdf) | Do not call it realized adoption. |
| EXP-E | Eloundou | Published measures are alpha = E1, beta = E1 + 0.5E2, and zeta = E1 + E2 under a ≥50% time-saving rubric at constant quality. | VERIFIED | [arXiv](https://arxiv.org/abs/2303.10130); [Science](https://doi.org/10.1126/science.adj0998) | Distinguish repo `gamma` column name from published zeta notation. |
| EXP-F | Felten | AIOE maps ten AI application areas to 52 O*NET abilities and is standardized across occupations without employment weighting. | VERIFIED | [SMJ/DOI](https://doi.org/10.1002/smj.3286) | Do not interpret it as automation direction or GenAI adoption. |
| NOV-01 | Novelty | Targeted searches of the declared ten journals did not locate the exact combined YAX design, but QJE and BCC contain closely relevant young-worker/public-data analyses. | SEARCH RESULT | `TEN_JOURNAL_SEARCH_SCOPE.md` | Use narrow affirmative contribution language; no broad “first.” |

## High-value unresolved facts

| ID | Unresolved fact | Why unresolved | What would resolve it |
|---|---|---|---|
| BCC-U1 | Complete BCC quintile cutoff and tie algorithm | The August 2026 PDF names quintiles but does not state all mechanics; dashboard documentation is not a complete membership file. | Author code/data or complete published occupation-to-quintile assignment. |
| BCC-U2 | Exact occupation-membership concordance between YAX and BCC | ADP internal mappings and complete group memberships are unavailable in the inspected public materials. | Author-supplied assignment, or a bridge explicitly labeled approximate. |
| CPS-U1 | Exact impact of population-control changes on YAX age × occupation cells | BLS publishes aggregate and selected series, not detailed counterfactual factors. | A Census/BLS micro-level reweighting bridge or revised historical microdata that agencies have not published. |
| NOV-U1 | Universal absence of an exact prior paper | Targeted publisher searches cannot prove absence. | A registered systematic search with databases, backward/forward citation searches, dual screening, and later updates; even then phrase cautiously. |

## Prohibited inference upgrades

The following moves are not licensed by the verified evidence:

- “BCC estimates a 19% hiring decline.”
- “YAX replicates BCC” when grouping membership, population, unit, and endpoint are not exact.
- “Employment-weighted quintiles are BCC's published quintiles.”
- “CPS cannot adjudicate because it is noisy” merely because BCC's monthly figure is volatile.
- “Aggregate BLS population-control factors correct age × occupation cells.”
- “November 2025 national unemployment design effects apply to YAX cells.”
- “AIOE/Eloundou/Webb measure actual AI adoption.”
- “Teleworkability is computerization.”
- “No detectable pretrend validates parallel trends.”
- “Rambachan–Roth can be run on one static coefficient and standard error.”
- “No previous public-CPS young-worker study exists.”

## Companion files

- `BCC_VERSION_AUDIT.md`: full version, estimand, bridge, and novelty audit.
- `CPS_DOCUMENTATION_AUDIT.md`: official CPS/IPUMS chronology and analysis implications.
- `METHODS_CONSTRUCT_AUDIT.md`: Rambachan–Roth and exposure definitions.
- `TEN_JOURNAL_SEARCH_SCOPE.md`: declared search scope, closest works, and safe claim.
- `MANUSCRIPT_SAFE_STATEMENTS.md`: pasteable, bounded prose.
- `citation_evidence_ledger.csv`: machine-readable locator table.
