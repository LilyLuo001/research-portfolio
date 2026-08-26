# Novelty gate: CPS young-worker × occupational AI exposure

Search date: 2026-08-25. This is a search-bounded assessment, not a universal proof of absence. Sources searched included author/institution pages, working papers/PDFs, and public replication repositories. Search concepts included combinations of `CPS`, `Current Population Survey`, `young workers`, `22-25`, `early career`, `AI exposure`, `occupation`, `employment`, `hiring`, `post ChatGPT`, `remote work`, `crosswalk`, and the named authors/projects below.

## Bottom line

The broad claim that a nationally representative CPS study has not examined young workers by occupational AI exposure after ChatGPT is false. At least three public U.S. CPS analyses already occupy that space:

1. Atkinson and Yamco (Dallas Fed, 2026) plot employment shares and labor-market flows for ages 20-24 versus 25-55 by occupational AI-exposure group through September 2025.
2. Massenkoff and McCrory (Anthropic, 2026) estimate post-ChatGPT differences in unemployment and CPS job starts, including a 22-25 high-exposure analysis and an older-worker comparison.
3. Emanuel, Harrington, and Pallais (2025/2026 version) estimate a CPS triple-difference in unemployment for young versus older workers in remotable occupations and fully interact occupational generative-AI exposure with young and post indicators as a control.

The exact narrow stock-employment specification proposed here—occupation-month weighted employment for ages 22-25 relative to older workers, interacted with continuous occupational exposure and post-ChatGPT, with explicit coefficient sensitivity to alternative SOC/Census crosswalks—was not found in the sources reviewed. That is a narrower, search-bounded absence. It is not enough by itself for a strong novelty claim because the Dallas Fed analysis is very close descriptively, Anthropic is very close on CPS hiring, and Tucker (Census QWI) already estimates an industry-state analogue with a formal young-versus-prime-age triple difference.

The crosswalk-coefficient-sensitivity angle appears less crowded. EIG explicitly compares two crosswalk constructions and selects one, while Yale adopts EIG's method; I did not find a paper that re-estimates the same young-employment coefficient under alternative crosswalks and reports coefficient/inference instability. This too is search-bounded and should be presented as a robustness contribution, not as a new labor-market question.

## Comparison matrix

| Study | Data and dates | Outcomes | Ages | AI exposure × age × post? | Crosswalk / measure sensitivity | Remote-work treatment | Relevance to proposed chapter |
|---|---|---|---|---|---|---|---|
| Brynjolfsson, Chandar & Chen, *Canaries* (rev. Aug. 2026) | Proprietary ADP payroll, through Jun. 2026 | Employment headcount, hiring, separations, base compensation | 22-25 versus experienced groups | **Yes**, core design; firm-time event studies and exposure groups | Revised page says results hold across alternative AI measures; public crosswalk sensitivity not documented | Revised page says results persist controlling for remote work and excluding computer occupations | Target result/benchmark, but not CPS |
| Eckhardt & Goldschlag / EIG, *AI and Jobs* (Aug. 2025) | IPUMS CPS monthly Jan. 2015-Jun. 2025; ASEC/ORG supplements | Unemployment; 12-month labor-force exit; occupation switching; switching to lower exposure; industry employment; young/recent-graduate unemployment | Young/recent graduate figure (notes indicate 22-27); not a young-vs-old employment-stock design | **Partial/no**: exposed-vs-less-exposed young unemployment is shown, but no formal young × exposure × post employment-stock coefficient found | Five exposure measures. Explicitly compares two SOC-to-Census crosswalk approaches, chooses occupation-to-occupation Approach 1, and reports outcomes across measures; does not report outcome coefficients across crosswalk approaches | None found | Crowds generic “robust across exposure measures” and crosswalk construction novelty |
| EIG, *AI and Young-adult Jobs: The Real Mystery* (2026 repo) | IPUMS CPS 2015-present | Employment, unemployment, LFPR moving averages | 22-25, 26+, all; college/noncollege; school enrollment variant | **No AI exposure or occupation interaction** | None | None | Age-outcome benchmark only; does not answer occupational-exposure question |
| Yale Budget Lab tracker/update (through Dec. 2025) | CPS; occupational mix, employment and unemployment tracking | Occupational dissimilarity; exposure shares; unemployment duration; employment/wages in later SDID work | Recent grads 20-24 vs 25-34 in mix; 16-34 unemployment appendix; unreported 22-27 attempt | **No exact 22-25 triple interaction**; later SDID compares exposed occupations, not young-vs-old | Multiple measures harmonized to SOC 2018; 867 any-score/710 all-score occupations; follows EIG crosswalk; later results robust PCA vs Eloundou | Discusses remote-work confounding but does not separately identify it | Crowds generic CPS exposure/employment robustness; explicitly warns CPS is underpowered for 22-27 occupation-quarter cells |
| Atkinson & Yamco, Dallas Fed (Jan. 2026) | Public CPS, long preperiod; results through Sep. 2025 | Employment share; employment-to-unemployment; unemployed job finding; entrant job finding | **20-24 vs 25-55** | **Descriptive equivalent is present**: six age × exposure cells over time; not a formal coefficient in the article | Eloundou exposure, fixed 2024 employment-weighted tertiles; no alternative crosswalk/measure sensitivity documented | None | Very close to proposed CPS employment chapter; later months plus formal inference alone is incremental |
| Massenkoff & McCrory, Anthropic (Mar. 2026) | CPS rotating panel, pre-2016 through report date; occupation matched with EIG crosswalk | Unemployment; new-job starts/job finding | **22-25**, with older-than-25 comparison | **Yes for hiring/job starts in substance**: post-ChatGPT DiD by high vs zero exposure for 22-25; states no such decline for older workers. Not the same employment-stock triple-difference | New observed-exposure measure plus construction sensitivity; uses EIG occupation crosswalk; not a broad multi-index coefficient audit | None | Already finds a roughly 14% relative drop in young job finding into exposed occupations; directly crowds a CPS hiring contribution |
| Emanuel, Harrington & Pallais, *Power of Proximity* (Nov. 2025 PDF) | Fortune 500 tech firm plus IPUMS CPS 2017-2019 vs 2022-2024 | Firm feedback/code quality/hiring; CPS unemployment | CPS college graduates 22-64; young <29 vs older | **Yes, but AI is a control**: CPS remote-work triple difference; additional controls fully interact occupational generative-AI exposure with young and post | One Schubert GenAI measure; no crosswalk audit | **Primary contribution**: Dingel-Neiman remote feasibility; estimated remote work explains 64% of young-college-grad unemployment increase | Directly occupies AI-vs-remote confounding for young CPS unemployment, though not employment stocks |
| Iscenko & Curto Millet, *Looking for the Ladder* (Jan. 2026) | Proprietary Lightcast, Sep. 2019-Aug. 2025, 767 6-digit SOCs | Total and junior/intermediate/senior job postings | Posting seniority, not worker ages | AI exposure × junior × time descriptively; no CPS | Eloundou GPT-4 beta; advocates multiple measures but primary analysis uses one | No direct remote test; focuses monetary policy, cyclicality, and pre-ChatGPT timing | Establishes major alternative explanation and narrow-age cohort-aging critique |
| Humlum & Vestergaard (Apr. 2025) | Denmark adoption surveys late 2023/2024 linked to admin employer-employee monthly records; 11 exposed occupations | Earnings, hours, occupational switching, job/workplace effects | Early-career heterogeneity; no U.S. 22-25 design | Adoption/policy DiD, not occupation exposure × U.S. age × post | Eleven selected occupations; not a multi-index crosswalk exercise | No | Important precise-null external evidence; not direct CPS novelty conflict |
| Tucker, Census CES 26-27 (Apr. 2026) | Public QWI detailed industry × state × quarter, through 2025Q2; ACS occupation-industry bridge | Employment, hires, separations, earnings, job gains/losses, replacement/backfill hires | **22-24 vs 25-54** | **Yes**, formal period × most-exposed quintile × age-group analogue at industry-state level | Eloundou GPT-4 beta crosswalked occupation→ACS industry→QWI NAICS; information loss documented; no multi-index coefficient audit | ACS work-at-home relationship examined; authors say firm-linked remote/AI data needed | The closest formal public-data analogue; materially narrows novelty of a CPS version |
| Mask, *Same Occupations, Different Clocks* (July 2026) | CPS 2012-mid-2026 | Entry hourly/annual pay, hours, net employment | Labor-market entrants (exact age definition not available in accessible abstract/summary) | AI and remote exposures dated to separate shocks; reports unstable AI net-employment estimate | Full paper needed to verify crosswalk variants; abstract says exposure fixed using pre-pandemic occupation mixes | **Central design**: remote shock vs later AI shock | Directly crowds the “opposite clocks separate remote from AI for CPS entrants” contribution |

## Exact-estimand determination

### Already present

- CPS young-worker outcomes by occupational AI exposure after ChatGPT: **yes** (Dallas Fed; Anthropic; EIG young exposed-unemployment chart).
- CPS young-versus-older labor outcomes with occupation-level AI exposure included in a post design: **yes in substance**, and literally as a fully interacted control in Emanuel-Harrington-Pallais.
- Formal public-data young-versus-older × AI exposure × post employment/hiring design: **yes at industry-state level** in Tucker's QWI paper.
- CPS design separating remote-work and AI timing for entrants: **yes** in Mask (2026).

### Not found in this search

- A published/public study whose primary outcome is the exact CPS occupation-month **stock employment ratio** for ages 22-25 versus older workers and whose focal coefficient is continuous occupational AI exposure × young × post.
- A published outcome-level audit that holds this exact coefficient fixed while varying SOC/Census crosswalk algorithms and reports the resulting coefficient/inference sensitivity.

The defensible novelty sentence is therefore:

> In a search of public papers, institutional reports, and replication repositories completed on 2026-08-25, we found several CPS studies of young workers in AI-exposed occupations, but did not find one that combines the exact occupation-month young-versus-older employment-stock estimand with a pre-specified coefficient-level audit across alternative occupational crosswalks. This is a narrow robustness and replication extension, not a new substantive question.

## Decision implication

The “estimand is absent” gate does **not** pass in its broad form. It passes only in the narrow exact-specification form. A viable chapter cannot rest on the sentence “no nationally representative CPS study has looked at young employment in AI-exposed occupations.” It must instead show that one or more of the following changes what the literature can conclude:

1. The CPS confidence interval meaningfully excludes either zero or the ADP-sized benchmark on a comparable scale.
2. The post-2025 extension changes the estimate or exclusion conclusion under a pre-specified test—not merely its significance stars.
3. Alternative defensible crosswalks materially change the exact coefficient/inference on a common-support sample.
4. The design resolves a specific discrepancy among ADP, Dallas Fed, Anthropic, Yale, EHP, Mask, and QWI rather than simply reproducing their descriptive pattern.

If none holds, the project is a useful replication/audit but not a distinct chapter contribution.

## Primary sources

- Stanford Digital Economy Lab, revised *Canaries*: https://digitaleconomy.stanford.edu/publication/canaries-in-the-coal-mine-six-facts-about-the-recent-employment-effects-of-artificial-intelligence/
- EIG report PDF: https://eig.org/wp-content/uploads/2025/08/EIG-AI-and-Jobs.pdf
- EIG replication: https://github.com/EIG-Research/AI-unemployment
- EIG young-adult CPS repo: https://github.com/EIG-Research/EIG-ai-unemp-she-wrote
- Yale Dec. 2025 CPS update: https://budgetlab.yale.edu/sites/default/files/page_to_pdf/1334/publication_1334.pdf
- Yale May 2026 SDID analysis: https://budgetlab.yale.edu/research/what-we-do-and-dont-know-about-how-ai-affecting-labor-market
- Yale exposure/crosswalk report: https://budgetlab.yale.edu/research/labor-market-ai-exposure-what-do-we-know
- Dallas Fed CPS analysis: https://www.dallasfed.org/research/economics/2026/0106
- Anthropic labor-market report: https://www.anthropic.com/research/labor-market-impacts
- Emanuel-Harrington-Pallais PDF: https://pallais.scholars.harvard.edu/sites/g/files/omnuum5926/files/2025-11/Power%20of%20Proximity%20to%20Coworkers%20November%202025.pdf
- Iscenko-Curto Millet PDF: https://eig.org/wp-content/uploads/2026/01/TAWP-Iscenko-Millet.pdf
- Humlum-Vestergaard PDF: https://bfi.uchicago.edu/wp-content/uploads/2025/04/BFI_WP_2025-56.pdf
- Tucker QWI PDF: https://www2.census.gov/library/working-papers/2026/adrm/ces/CES-WP-26-27.pdf
- Mask SSRN landing/delivery: https://papers.ssrn.com/sol3/Delivery.cfm/7075479.pdf?abstractid=7075479&mirid=1
