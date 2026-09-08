# Independent execution-audit corrections — 2026-09-08

Separate agents reviewed the local-data layer (Stage A), institutional rule/event and assignment layer (Stages B/C), and FOMC/calendar-intersection layer (Stage E). These were internal execution-quality audits. They are not a Claude or Opus referee report, and no external-model endorsement is claimed.

## Stage A: licensed archive audit

The audit reran on BU SCC and its focused tests passed. Review corrections:

- removed raw target metadata from the public evidence JSON;
- removed a low-entropy target-identifier fingerprint rather than treating hashing as anonymization;
- added a regression test rejecting both prohibited fields;
- changed each fund-year locator to the actual contributing source file(s), instead of all same-year candidates;
- separated screening coverage from assignment fitness;
- separated fund-header intervals from portfolio-map intervals; and
- computed interval-catalog maxima from the end-date field.

Remaining limitation: the manifest/hard-coded-table search did not resolve constituent rows for the target Nasdaq-100 metadata key and did not identify a target Select Sector membership series. This is scoped to the searched archive objects; it is not a claim that such data do not exist elsewhere. ETF holdings remain screening proxies, not assignments.

## Stages B/C: rules, events, and assignment evidence

The first institutional build did not pass independent review. The final builders and tests incorporate these corrections:

- replaced an incorrect 2018 issuer-level Nasdaq-100 backcast with security-level regimes through 2020 Q1, an explicitly unresolved 2020 Q2 transition, and issuer/company-level regimes only when contemporaneous evidence supports them;
- left unsupported pre-May-2026 routine Nasdaq announcement dates blank;
- corrected Nasdaq publisher attribution on rule rows;
- rolled third-Friday June 2026 implementation closes back from the Juneteenth holiday to June 18;
- added the independently announced July 17, 2023 Trade Desk-for-Activision replacement as a separate `confirmed_other_intervention`, linked it to the July 24 special reweighting as interference, and did not count it as another capping treatment;
- added event-to-rule evidence keys and verified that each event resolves to an applicable regime;
- separated rule-source, event-classification, and assignment-observability grades; and
- retained selected rounded values as incomplete assignment grade B, never as a complete vector.

Remaining limitation: no historical full precision assignment/pro-forma vector or complete contemporaneous rule input package was recovered for any pilot. Therefore no exact-dose replay, design rank, leverage, information-effective support, or assignment-based power calculation is justified.

## Stage E: FOMC calendar and support intersections

The final independent Stage E audit reproduced the generated tables and all resolved signed trading-session distances and overlap indicators. Corrections made before that audit:

- added four omitted notation-vote records and kept all notation votes ineligible for the scheduled-common-news sample;
- separated policy-statement availability from meeting/package labels;
- made calendar source IDs/URLs and per-row FOMC evidence keys resolve exactly;
- fixed anticipation overlap to test interval intersection rather than a single endpoint;
- left unknown anticipation and next-intervention indicators blank with explicit statuses;
- propagated event binding, evidence-grade, rule, comparison, and interference context into support rows;
- split support roles for confirmed binding, confirmed nonbinding, uncertain, outside-regime, and other-intervention contexts;
- separated all dated event groups, confirmed interventions, confirmed capping events, and undated groups in interference counts;
- prohibited announcement/reference-date fallback as a canonical intervention date;
- used an official NYSE rule filing for the Juneteenth calendar transition and treated a mutable current trading-days page as nonhistorical support; and
- treated the public USMPD workbook as metadata/schema screening only, without importing factors or row-level event classifications.

Remaining limitation: the calendar intersection establishes descriptive opportunities, not independent treatment variation, a valid macro-news instrument, or power. Shared intervention groups, issuers, baskets, and meetings remain dependent.

## Closure standard

The controlling final state is the deterministic rebuild plus `logs/gate1_summary.json`, the full test suite, and `src/validate_gate1.py`. Any discrepancy in a copied prose count should be resolved in favor of the same-commit machine summary and then corrected, not averaged.
