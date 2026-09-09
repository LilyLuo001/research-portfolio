# Gate 4 RPS occupation-adoption extension specification

Date fixed: 2026-09-09 Asia/Shanghai

Status: **fixed before opening the downloaded workbook's adoption-rate cells**.

## Question and boundary

This extension asks whether the frozen YAX beta exposure measure is positively
associated with later, self-reported generative-AI use for work across detailed
occupations. It is an external descriptive validation of the exposure measure.
It is not a treatment effect, an instrument, an adoption-adjusted version of
the CPS estimate, or evidence that adoption caused the young-worker pattern.

The adoption measure pools four RPS waves (August 2025, November 2025,
February 2026, and May 2026). It is therefore a future, post-outcome
classification relative to much of the YAX CPS window. No pre-survey value will
be set to zero, and the pooled rate will not be presented as an occupation-by-
time panel.

## Authenticated inputs

1. Official author-linked RPS occupation workbook, downloaded from
   `https://docs.google.com/spreadsheets/d/1_JfNtZVoBi5W_jHEJ1UOs2rhHYRtLXGM/export?format=xlsx`:
   `inputs/rps_adoption_rates_by_occupation_20260806.xlsx`, SHA-256
   `2212465781179782c6f69750af21b00bd545edc21581d9577fbf7affc1bf0c43`.
2. Frozen YAX primary membership:
   `../../runs/gate1_baseline/results/REBUILT_TREATMENT_MEMBERSHIP.csv`,
   SHA-256
   `c76eb85956e4a413e130bab53fe8c50616cf6d7a02c81c266ec369879dd56bc1`.
3. The frozen broader-support file supplies the verified SOC major-family label
   for primary occupations:
   `../../runs/gate2_broader_support_authoritative_20260908/BROADER_SUPPORT_MEMBERSHIP.csv`,
   SHA-256
   `2fe1967db31dea51e007861867e01bd6fa872828a9d589bc0490212e534220fc`.

Only the workbook sheet `2018 Census Occupation Code` enters the analysis.
Workbook tabs, dimensions, and source documentation may be audited, but source
values and formatting will not be modified.

## Frozen sample and merge

- Standardize both occupation keys as four-digit strings and merge exactly on
  2018 Census occupation code.
- Start from all 468 frozen YAX primary occupations. Obtain family from the
  broader-support file only where `in_primary_468` is true; require one family
  per occupation and exact agreement of the beta score and primary quintile
  across the two frozen files.
- The analysis sample is the intersection with a nonsuppressed, finite RPS
  `adoption_rate` in [0,1] and a strictly positive reported
  `number_observations`.
- Do not impute suppressed or missing RPS values. Report matched and unmatched
  counts by YAX quintile and SOC major family, and name every unmatched YAX
  occupation in a retained coverage file.
- Refuse duplicate RPS occupation codes. Report any RPS code not present in the
  frozen 468, but do not expand the YAX support.

## Frozen descriptive quantities

The primary weighting is one occupation, one observation. Because the workbook
does not provide cell standard errors or replicate weights, no p-value or
confidence interval will be constructed.

Report:

1. the unweighted Pearson correlation and Spearman rank correlation between
   frozen continuous `rule_A_beta` and the RPS adoption rate;
2. the unweighted OLS slope from adoption rate on an intercept and
   `rule_A_beta`;
3. unweighted mean adoption by frozen beta quintile and the Q5-minus-Q1
   difference;
4. the fraction of the matched exposure sum of squares remaining after SOC
   major-family fixed effects, and the slope after residualizing both adoption
   and exposure on those family indicators;
5. descriptive sensitivity versions of the Pearson correlation, OLS slope,
   quintile means, and family-conditioned quantities weighted by the reported
   pooled `number_observations`. Spearman rank correlation remains an
   unweighted occupation-level quantity.

The reported observation count is not treated as a survey weight or as a
verified inverse-variance weight. Count-weighted results are a cell-reliability
sensitivity only. The family-conditioned slope is a within-family descriptive
association; it is not an answer to whether realized adoption moderates the CPS
post coefficient.

## Decision rule and presentation

This focused extension is informative if the exact-code merge leaves all five
quintiles represented and at least two matched occupations in at least ten SOC
major families. Otherwise B08 will be recorded as scientifically unsupported
on the released detailed cells, with the coverage audit retained.

If informative, one appendix table will report coverage, correlations, slopes,
quintile means, and within-family exposure-variation retention. Wording is
limited to whether later reported work use is descriptively aligned with the
constructed exposure measure. It must disclose suppression, the absence of
detailed-cell sampling uncertainty, the pooled future timing, and the lack of
causal interpretation.

No exposure-by-adoption CPS regression is authorized here. With only one pooled
detailed-occupation adoption rate, such a regression would use future adoption
as a fixed occupational classification, provide no adoption timing, and rely
on the same within-family exposure support already audited in the paper. The
quarterly public series is available only at broad occupational levels whose
main effects are absorbed by family-by-month controls; interacting it with
exposure asks a different question and is outside this focused extension.
