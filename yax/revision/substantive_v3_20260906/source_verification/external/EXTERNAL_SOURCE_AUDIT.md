# External Source Verification Audit

Date accessed: 2026-09-06  
Requirements covered: B01, B02, B05, B07, B09, F07  
Scope: official or primary-source verification only

## Bottom line

The targeted verification closes several factual questions but does **not** close every V3 requirement. In particular, the exact BCC occupation-to-quintile membership remains unavailable in the public artifacts inspected, the currently valid ACS extension ends in 2024, and the full ten-journal search remains **incomplete**.

The machine-readable record is [`source_claim_matrix.json`](source_claim_matrix.json). It distinguishes fixed paper versions from mutable data endpoints, states the exact claim each source supports, and records limitations rather than promoting partial checks to passes.

## Requirement status

| Requirement | Status | Verified result |
|---|---|---|
| B01 | Verified with estimand corrections | BCC's 19% headline, its ADP long-difference coefficient, and its ACS comparison are three different quantities. They are not interchangeable literature benchmarks. |
| B02 | Open | The paper, dashboard, and three inspected ZIP downloads do not provide an exhaustive SOC-code-to-quintile membership artifact. A public reconstruction is not exact BCC membership. |
| B05 | Feasible through 2024 only | Official 2024 one-year PUMS is public. Census had not released a verified 2025 one-year product as of this audit. Standard 2020 one-year estimates do not exist and the experimental 2020 estimates must not be spliced into the series. |
| B07 | Partially verified | BTOS is public at aggregate business cells but lacks worker age and occupation. Detailed RPS occupation adoption is now public as pooled post-period sheets, but those sheets are not an occupation-by-quarter panel and expose no sampling intervals in the inspected interface. |
| B09 | Targeted corrections complete; broad search incomplete | Named publisher records were verified and prior citation premises corrected. The prescribed full ten-journal novelty search and reproducible query ledger have not been completed. |
| F07 | Official variable verified; input blocked | `EARNWEEK2` is available through current monthly samples and harmonizes the April 2023 privacy transition, but it is absent from all four authorized YAX extract DDIs. A new extract is required. |

## Corrections that should govern the revision

### 1. BCC benchmark alignment

The August 2026 BCC paper supports all of the following, but they answer different questions:

- The **19%** figure is a descriptive relative shortfall: employment for ages 22–25 in the top two exposure quintiles fell about 11% while the bottom three grew about 10% from November 2022 to June 2026.
- ADP Table 1 estimates **−0.179 (SE 0.036)** for Q5 relative to Q1 in an occupation-level, employment-weighted long-difference regression using a firm panel balanced since January 2018.
- ACS Appendix Table H.1 estimates **−0.022, 95% CI [−0.055, 0.011]**, for the Q5−Q1 change from 2022 to 2024 among all employed ages 22–25. The full-time civilian wage-and-salary estimate is **−0.019 [−0.059, 0.020]**.

The manuscript should compare YAX only with a benchmark whose age group, outcome stock, exposure contrast, dates, weighting, and scale are explicitly aligned. The landing-page 19% should not be used as if it were the coefficient from Table 1 or Appendix H.1.

BCC forms occupation-equal quintiles using Eloundou et al.'s GPT-4 beta measure and a 2010-to-2018 SOC crosswalk. Its fixed paper ends in June 2026. The dashboard ZIPs inspected here identify a July 2026 endpoint and a 2026-08-12 vintage; they are mutable `latest` endpoints and are pinned in the JSON matrix by SHA-256.

### 2. Exact BCC membership is not publicly verified

The paper lists only the top 50 occupation names in each quintile. The dashboard downloads contain aggregate date-by-quintile, age-by-quintile, or composition data. None of those inspected artifacts supplies the exhaustive SOC-code membership needed for exact membership replication.

Therefore:

- do not label an independently constructed membership list as “exact BCC membership”;
- label it a reconstruction from the public exposure file and stated rules;
- preserve crosswalk, aggregation, tie-breaking, and quintile-cut decisions;
- leave B02 open unless an exact primary artifact is later obtained.

No author contact was authorized for this audit.

### 3. ACS extension boundaries

The defensible one-year ACS extension currently ends in **2024**. As of 2026-09-06, Census said the 2025 one-year release date was still being determined. The 2024 PUMS release and API are public.

The extension should:

- use one-year with one-year products;
- omit 2020 rather than using its limited experimental estimates;
- use person weights and the 80 successive-difference replicate weights for confidence intervals;
- report sensitivity to weighting or use rate-based outcomes because the 2024 population controls incorporate a sizable migration-related revision;
- avoid claiming that annual 2022 data isolate the late-November 2022 ChatGPT launch.

Overlapping five-year PUMS are not an acceptable substitute for a missing annual observation.

### 4. BTOS is an ecological business-adoption measure

BTOS is a **Census Bureau** experimental survey, not a BLS product. Public downloads provide national, industry, size, state, state-by-sector, and related aggregate cells. They do not provide a worker-age-by-occupation treatment.

Any BTOS linkage to CPS is therefore ecological and descriptive unless a separate identification strategy is supplied. Cell-level sampling uncertainty should be retained; BTOS uses a ten-group delete-a-group jackknife, and its standard errors do not cover systematic nonsampling bias.

There is also a binding series break: starting November 17, 2025, the core AI wording expanded from use in producing goods or services to use in any business function. Census treats the revised wording as a new series beginning with the December 4, 2025 release. The two definitions must not be silently spliced.

### 5. Detailed RPS occupation adoption now exists, with limits

The author-maintained RPS page links public occupation and task workbooks. The occupation workbook pools four waves—August 2025, November 2025, February 2026, and May 2026—and exposes detailed 2018 SOC/Census occupation tabs. Cells with fewer than 20 pooled observations are suppressed.

This corrects the premise that only SOC2 adoption is publicly available. But it does not create pre-2022 observations or detailed occupation-by-quarter adoption. The displayed workbook supplies pooled point estimates and counts, not standard errors or confidence intervals. A binary export was not captured in this environment, and the task workbook still contains an unresolved exact-O*NET-release placeholder.

Accordingly, these data can support descriptive exposure validation or mechanism checks. They should not be described as a causal treatment series or used for inference without verified variance/replication materials.

### 6. EARNWEEK2 is available, but not in the authorized extracts

The official IPUMS CPS page confirms that `EARNWEEK2` is the rounded weekly-earnings variable designed to harmonize the April 2023 privacy transition. IPUMS applies the newer rounding rules backward and across rotation groups during the phase-in; dynamic topcoding changes across April 2023–March 2024 and April 2024 onward. Researchers must use `EARNWT`, and the Basic Monthly universe is the outgoing-rotation wage-and-salary sample rather than all employed respondents.

The verified YAX source inventory separately records that `EARNWEEK2` is absent from the DDIs for authorized extracts 9, 10, 11, and 12. Extracts 9 and 11 contain the older `EARNWEEK` plus `EARNWT`. Thus the existing March 2023 endpoint is an **extract-content blocker**, not survey unavailability.

F07 needs a new minimal authorized extract containing `EARNWEEK2`, `EARNWT`, `MISH`, and the existing sample and identification fields. Until that extract is obtained and hashed, the extension is blocked. When it is run, the revision must document its rounding/topcode compatibility rule rather than silently splice fields.

### 7. Literature premises corrected

- Bick, Blandin, and Deming's *The Rapid Adoption of Generative AI* is a published **Management Science** article as of January 20, 2026, not merely a 2025 working paper.
- Bick, Blandin, Deming, and Schumacher's *What Work Does Generative AI Do?* is NBER Working Paper 35677, issued August 2026, and is distinct from the earlier article.
- Autor and Thompson's *Expertise* is a relevant 2025 **JEEA** article. Any prior journal-search row saying that no close JEEA article was found is false and must be corrected.
- Deming and Noray's 2020 QJE article supports life-cycle motivation around skill obsolescence, not post-2022 AI causal attribution.
- Hampole et al.'s paper uses a firm-occupation-time exposure design. This audit did not locate a verified public, occupation-only score artifact, so it must not be listed as an available plug-in measure without one.

## Still unresolved

1. Exact exhaustive BCC SOC-code-to-quintile membership.
2. Release of 2025 ACS one-year PUMS.
3. A locally captured and hashed RPS detailed workbook or replication file, plus a verified variance procedure for detailed cells.
4. A new authorized IPUMS extract containing `EARNWEEK2` and required weights/design fields.
5. A verified public Hampole et al. occupation-score artifact.
6. The complete ten-journal search with journal-by-journal queries, dates, candidate disposition, and stable publisher URLs.

The sixth item matters for claim discipline: this audit supports targeted citation corrections, **not** a field-wide novelty statement or a claim that no prior paper exists.

## Mechanical check

Run:

```bash
python3 check_external_source_matrix.py
```

The check validates the matrix schema used here, requirement coverage, unique canonical URLs and source IDs, exact-claim and version-distinction fields, and the explicit `false` value for completion of the ten-journal search.
