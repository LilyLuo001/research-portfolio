# Module A. Recruitment Opportunities: Volume, Stocks, and Occupational Composition

## Scope and timing

The first empirical module describes where advertised opportunities expand or contract. It separates the volume of advertisements from their occupational composition and from the experience or tasks specified within them. This distinction is central to the broader question of whether technological change reorganizes work and opens different routes into employment. Advertisement counts establish neither the content of that reorganization nor which workers obtain the opportunities.

We reuse previously verified LinkUp Records aggregates. The delivered all-history US Records universe contains **253,210,047 advertisement records**, of which **199,644,730** were first observed from 2016 onward. The reporting series covers **129 months, January 2016–September 2026, and 11 calendar-year entries**. These are not eleven complete years: the delivery ends on **6 September 2026**. Table A1 reports complete-month totals. The available 2026 total is 15,496,940, including partial September; January–August contributes 15,029,705. Neither partial-year total is treated as directly comparable to a complete prior year.

The unit is a US advertisement record, identified using the delivered country classification, not a vacancy, hire, worker, or employment spell. These Records counts are also distinct from the text-processing base and the project's approximately 500-million-record full-delivery target. They are not interchangeable denominators or an estimate of completed semantic coverage.

We use **CREATED as a first-observed posting-time proxy**. Updates and subsequent checks do not generate new first-observed advertisements. This convention does not establish when the currently retained description was written or last revised. Temporal changes are therefore descriptive under this proxy, not automatically effects of AI.

**Table A1. First-observed US advertisements in complete calendar months**

| Year or covered period | Complete months | Advertisement records |
|---|---:|---:|
| 2016 | 12 | 11,280,900 |
| 2017 | 12 | 14,741,748 |
| 2018 | 12 | 15,252,192 |
| 2019 | 12 | 16,742,466 |
| 2020 | 12 | 14,728,302 |
| 2021 | 12 | 24,461,581 |
| 2022 | 12 | 25,082,680 |
| 2023 | 12 | 22,267,905 |
| 2024 | 12 | 20,526,445 |
| 2025 | 12 | 19,063,571 |
| 2026, January–August | 8 | 15,029,705 |

*Source:* Existing annual Records export, reproduced without re-estimation. The final row excludes incomplete September 2026; it is not an annualized count. Coverage is of the delivered Records population, not a claim of complete coverage of all US recruitment.

## Flows, stocks, and the late-2022 comparison

New-advertisement **flow** counts records first observed during a month. Month-end **active stock** applies the existing convention that CREATED is no later than month-end and DELETE_DATE is later than month-end. Missing deletion dates receive two separate treatments: retained as open, or excluded. These conventions expose sensitivity to incomplete lifecycle information rather than establish the true number of unfilled positions.

Direct **exits** require a compatible DELETE_DATE aggregate, which is not available in the reused tables. A residual calculated from flows and stock changes is an accounting diagnostic, not directly observed exits. Advertisement removal would not, by itself, establish that a position was filled.

Table A2 reproduces the existing comparison between two twelve-month windows. These windows differ from the calendar years in Table A1.

**Table A2. Equal-length descriptive windows around late 2022**

| Outcome | December 2021–November 2022 | December 2022–November 2023 | Reported change |
|---|---:|---:|---:|
| First-observed advertisement flow | 25,328,196 | 22,549,332 | -10.97% |
| Mean month-end active stock: missing deletion dates open | 4,180,547.4 | 3,602,666.9 | -13.82% |
| Mean month-end active stock: missing deletion dates excluded | 4,140,658.4 | 3,510,360.6 | — |

*Source:* Previously verified macro run004 comparison. Means and reported changes retain the original definitions; no additional change estimate is computed for the excluded-missing specification. This is not a fitted structural-break test or a causal estimate.

First-observed advertisements are lower in the later window, as is mean active stock under both missing-deletion conventions. The reported declines are 10.97% for flow and 13.82% for the open-missing stock specification. Neither result identifies a decline in successful hiring or employment. Website coverage, employer composition, multi-location advertising, the pandemic and reopening, and broader recruitment conditions remain competing explanations. The late-2022 comparison date is not an exogenous assignment of employer AI adoption.

## Occupational composition: levels and shares

The existing occupational comparison uses major-group codes attached to the delivered snapshot. These codes are not a verified reconstruction of historical occupational classifications. Missing, unmapped, and residual categories are retained; the original run did not locate the official 2019 membership-flag table. Table A3 therefore reports the existing code-based grouping without claiming that taxonomy verification is complete.

**Table A3. Selected occupational major-group counts and share changes**

| Delivered major-group code | Records in 2022 | Records in 2023 | Share change, percentage points |
|---|---:|---:|---:|
| 15 | 1,775,098 | 1,065,189 | -2.293 |
| 11 | 3,112,968 | 2,421,070 | -1.538 |
| 13 | 2,184,822 | 1,624,983 | -1.413 |
| 35 | 1,194,281 | 1,266,375 | +0.926 |
| 53 | 1,458,135 | 1,480,254 | +0.834 |
| 29 | 3,223,379 | 3,035,094 | +0.779 |

*Source:* Previously verified calendar-year occupational summary; selected increases and decreases, not an exhaustive partition. Counts and share changes are reproduced, with share changes rounded to three decimals.

The distinction between levels and composition is substantive. Codes 35 and 53 have higher recorded counts as well as higher shares. Code 29 gains share even though its advertisement count falls from 3,223,379 to 3,035,094. Its relative position improves without an absolute increase in observed advertisements. These patterns cannot establish that technology created new tasks or improved workers' chances of entering those occupations. Occupational recoding and changes in the mix of observed employers also remain relevant.

## Connection to the broader research agenda

These results provide the opportunity side of a five-module design: **A**, opportunity reallocation; **B**, combinations of required experience; **C**, duties and task content; **D**, personnel entry and mobility; and **E**, comparison with computerization. Existing bounded text results remain separate. They do not supply a nationwide entry-level share, which is not estimated here.

The next substantive question is whether changing work combinations open opportunities to people with transferable experience, including experienced cross-industry entrants. One hypothesis is that AI reduces some specialized execution requirements, making adjacent experience more useful. Another is that remaining judgment, verification, and responsibility increase demands for domain-specific experience. Both are hypotheses; neither follows from the aggregate counts. Net advertisement changes do not identify displacement, productivity, or new-task reinstatement effects.

LinkUp requirements and duties can characterize employers' public statements. Revelio, after delivery and verification, can separately characterize prior experience and observed transitions, with entry rates requiring defined risk sets. We do not infer direct advertisement-to-worker matches. Likewise, contemporary software-related advertisements and the years preceding GenAI are not a historical computerization counterfactual. The broader comparison requires compatible historical evidence. This module establishes the descriptive baseline without preselecting an equalizing or exclusionary technological story.
