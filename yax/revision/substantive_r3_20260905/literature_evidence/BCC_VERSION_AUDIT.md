# Brynjolfsson–Chandar–Chen version and estimand audit

**Audit date:** 2026-09-05
**Status vocabulary:** `VERIFIED` means located in a primary source; `INFERENCE` means a conclusion drawn from verified facts; `UNRESOLVED` means the primary materials inspected do not establish the fact.

## Source identity

| Item | Finding | Status | Primary locator |
|---|---|---|---|
| Work | Erik Brynjolfsson, Bharat Chandar, and Ruyu Chen, *Canaries in the Coal Mine? Six Facts about the Recent Employment Effects of Artificial Intelligence* | VERIFIED | [Stanford Digital Economy Lab publication page](https://digitaleconomy.stanford.edu/publication/canaries-in-the-coal-mine-six-facts-about-the-recent-employment-effects-of-artificial-intelligence/) |
| Version inspected | August 2026 revision, dated August 12, 2026; it updates the August 2025 circulation | VERIFIED | [Official August 2026 PDF](https://digitaleconomy.stanford.edu/app/uploads/2026/08/Canaries_August2026.pdf), title page and note 1 |
| Data endpoint | June 2026 | VERIFIED | Official PDF, abstract and §1.1 |
| File integrity | PDF size 3,390,516 bytes; SHA-256 `c8d2e5c4ccc0de7ef977c191c144726d6073e164b33f30397fcb0090165d2bdf` | VERIFIED | Locally downloaded official PDF; hash recorded during this audit |

This is the version that must be named whenever YAX discusses the current BCC results. Statements based on the August 2025 circulation must be labeled historical and must not be attributed to the August 2026 version without rechecking.

## Data, population, classification, and treatment

| Dimension | August 2026 BCC construction | Status and locator |
|---|---|---|
| Source | ADP administrative payroll records, not public CPS microdata | VERIFIED, PDF §1.1 |
| Main balanced panel | Firms observed monthly January 2021–June 2026, 3.5–5 million employees per month | VERIFIED, PDF §1.1, p. 6 |
| Extended balanced panel | Firms observed January 2018–June 2026 | VERIFIED, PDF §1.1, p. 6 |
| Person/job restrictions | Full-time workers under age 70 with positive earnings | VERIFIED, PDF §1.1, p. 6 |
| Employment unit | Worker–firm match; the paper uses both “employment” and “headcount” for that unit | VERIFIED, PDF §1.1, p. 6 |
| Occupation assignment | ADP standardized job titles mapped to 2010 SOC; about 30% of titles are missing, with missing codes filled where possible from the worker's most recent or next nonmissing occupation | VERIFIED, PDF §1.1, p. 6 |
| Primary exposure | Eloundou et al. GPT-4 beta task-exposure rating | VERIFIED, PDF §1.2, p. 7 |
| Exposure vintage conversion | Eloundou's 8-digit 2018 SOC values are collapsed to 6-digit and crosswalked to ADP's 2010 SOC using the BLS 2010–2018 crosswalk | VERIFIED, PDF §1.2, p. 7 |
| Quintile assignment algorithm | The PDF names exposure quintiles but does not state a complete cutoff/tie/weight algorithm in the text inspected | UNRESOLVED |

### Important grouping-rule discrepancy

The official [Canaries Dashboard](https://digitaleconomy.stanford.edu/project/indicators/canaries-dashboard/) says occupations are given equal weight when exposure groups are formed. It also reports that its most-exposed 20 percent of occupations represented 38.3 percent of November 2022 employment, which is consistent with cuts over occupations rather than employment-weighted quintiles. In contrast, BCC's occupation-level outcome regressions are explicitly **employment weighted**.

These are different operations:

1. **Group formation:** determining which occupations enter Q1–Q5.
2. **Regression weighting:** weighting occupation-level changes after groups have been formed.

The August 2026 PDF does not establish that employment weights form the quintile cutoffs. Therefore:

- an employment-weighted quantile construction must **not** be labeled “BCC-exact”;
- a dashboard-rule implementation may be labeled “equal-occupation-weighted cuts following the official dashboard description,” but it is still not proof of identical BCC paper membership;
- exact concordance requires author code/data or a published membership list. Appendix Tables A.2–A.6 list only the largest occupations in each quintile and are insufficient to recover all assignments.

The author's public [CPS Tracker repository](https://github.com/chandarb/CPS_tracker) uses unweighted occupation-level `pandas.qcut` in its public notebook (quartiles in that tracker). This is corroborating implementation evidence, not proof of the paper's quintile algorithm.

## Headline descriptive result versus regression estimand

The August 2026 paper contains several noninterchangeable quantities.

| Quantity | Exact object | Result or unit | Locator |
|---|---|---|---|
| Indexed stock paths | Aggregate worker–firm-match employment within age × exposure groups, normalized to November 2022 | Among ages 22–25, Q4–Q5 together fell about 11% while Q1–Q3 grew about 10% through June 2026 | Abstract; Figure 3 and text, pp. 10–11 |
| “Kept pace” shortfall | Young high-exposure employment relative to the growth of less-exposed same-age employment | 19% as of June 2026 | Abstract and §2.3 |
| Occupation long difference | Percent change in employment in each occupation, November 2022–June 2026, regressed separately by age group on Q2–Q5 indicators with Q1 omitted | Age 22–25 Q5 coefficient is approximately −0.179 without controls in the primary 2018-balanced sample | Table 1, pp. 13–14 |
| Dynamic occupation regression | Q5 relative to Q1 as the long-difference endpoint rolls forward; November 2022 base | Employment-weighted; occupation-clustered intervals | Figure 4, p. 15 |
| ACS comparison | Q5–Q1 employment growth, 2022–2024, ages 22–25 | −0.022, CI [−0.055, 0.011] for all employed; −0.019, CI [−0.059, 0.020] for full-time civilian wage-and-salary workers | §5 and Table H.1, pp. 28 and 130 |

The 19% “kept pace” number is not the Table 1 regression coefficient and is not a hiring-rate estimate. Any bridge must align age bands, contrast, endpoints, population, unit, and outcome before comparing magnitudes.

## Controls and interpretation

Table 1 is an employment-weighted occupation-level long-difference regression. The paper adds occupational interest-rate exposure, 2017 ACS college share, work-from-home measures, and teleworkability; the first three enter as quintile indicators and teleworkability is binary (Table 1 notes, pp. 13–14). These controls define conditional descriptive comparisons. They do not turn the design into a causal natural experiment.

BCC explicitly warns about pretrends in its hiring/separation discussion and describes the employment relationships as equilibrium quantities. YAX should describe both papers as descriptive exposure comparisons unless a separately validated causal design is implemented.

## Stocks, hires, and separations

BCC first studies employment **stocks**. Its flow exercise then defines:

- hiring as new worker–firm matches in an age × exposure cell over the prior year;
- separation as the analogous worker–firm matches leaving the firm;
- each annual count divided by the cell's headcount one year earlier;
- rates measured January over January on the extended balanced firm panel.

The exact definition appears in Figure B.7, p. 66; main interpretation is in §2.4, p. 16. BCC reports that the post-2022 divergence is associated with reduced hiring rather than increased separation.

These employer-match flows are not identical to CPS flows from nonemployment into employment. Employer hires can include job-to-job moves; CPS longitudinal transitions have different risk sets, linking attrition, time horizons, and occupation availability. A stock–flow calibration therefore needs an explicit accounting model for nonemployment entry/exit, job-to-job/occupation switching, and aging into and out of ages 22–25. Without those pieces, a numerical calibration would be manufactured.

## Existing public-data comparisons and novelty consequence

The August 2026 paper already contains:

- monthly CPS employment paths for three occupations and for age × exposure quintiles through June 2026 (Online Appendix Figures H.1–H.4, pp. 123–126);
- annual ACS occupation and age/exposure analyses through 2024 (Figures H.5–H.8, pp. 127–129);
- ACS versus ADP Q5–Q1 estimates and sector decompositions (Tables H.1–H.3, pp. 130–131);
- an explicit statement that multiple prior analyses had used CPS to study AI and entry-level work (§H, p. 122).

Therefore YAX cannot safely claim to be the first public-CPS test, the first young-worker CPS exposure analysis, or the first public-data comparison with BCC. Its defensible contribution is narrower: an exact, auditable sensitivity analysis of a specified CPS estimand across exposure architectures, mapping/support constructions, and occupational conditioning restrictions.

## Required bridge labels

Until exact membership is verified, every BCC bridge output should carry all of the following fields:

1. `bcc_version = 2026-08-12`;
2. source population and outcome unit;
3. age band;
4. start and end month/year;
5. contrast (`Q5-Q1` or `Q4-Q5 versus Q1-Q3`);
6. exposure measure and SOC direction;
7. group-cut rule, tie rule, and weighting base;
8. membership-concordance status;
9. regression weight;
10. controls and inference procedure.

If fields 6–8 cannot be verified, label the result an **approximate BCC-style bridge**, not a replication.
