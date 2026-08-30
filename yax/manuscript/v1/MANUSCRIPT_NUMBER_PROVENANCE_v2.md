# YAX Manuscript-Number Provenance v2

All outcome numbers resolve to `v1.1-confirmatory-results` at commit `b16109482c3bf5ca176f6f08976e120b04769945`. Measurement diagnostics were produced pre-outcome and archived at the same commit. Exact percentage translations use \(100(e^\beta-1)\).

| ID / scope | Quantitative content | Authoritative artifact | Exact key or row rule |
|---|---|---|---|
| A01 | Abstract: 30 architectures; effective N 11.9–84.5 | `yax/analysis/audit/TEST_B_IDENTIFYING_VARIATION_FULL.csv` | All 30 rows; min/max `effective_identifying_occupations` |
| A02 | Abstract: all headline estimates negative; about 9%–19%; primary about 12% | `table4a_headline_q5_q1.csv`; `RESULT_LEDGER.jsonl` | All 12 alpha/beta rows; primary `dv_rating_beta__RuleA__webb_pct_software__q5_q1`; exact transforms 9.253%, 18.818%, and 12.285% |
| I01 | Introduction: 6×8 characteristics; joint R² 36.8% and 95.4%–97.1% | `TEST_A_CHARACTERISTIC_MATRIX.csv`; `TEST_A_RESIDUAL_DIAGNOSTICS.csv` | Six measures × eight rows; `weighted_r_squared_on_all_characteristics` |
| I02 | Introduction: 30 architectures; effective N and top-five ranges | `TEST_B_IDENTIFYING_VARIATION_FULL.csv` | All 30 stored rows |
| I03 | Introduction: alpha/Webb 17.4 and 41.6%; beta/Webb 53.3 and 22.2% | `TEST_B_IDENTIFYING_VARIATION_FULL.csv` | Rows `(dv_rating_alpha, webb_pct_software)` and `(dv_rating_beta, webb_pct_software)` |
| I04 | Introduction: mapping sequence -0.01885, -0.01920, -0.03156, -0.02940 | `MAPPING_DECOMPOSITION_AUDIT.csv` | Stored rows 1–4 |
| I05 | Introduction: 12 headline rows; -0.0971 to -0.2085; exact 9.3%–18.8%; all CIs exclude zero | `table4a_headline_q5_q1.csv` | All 12 rows; exact transforms of stored extrema |
| I06 | Introduction: primary -0.1311, CI, p, 12.3% | `RESULT_LEDGER.jsonl` | Primary specification ID; exact transform 12.2847117% |
| I07 | Introduction: beta -0.1001 to -0.2085 across computerization controls | `ALTERNATIVE_X_AUDIT.csv` | Five Rule-A beta rows for Webb, O*NET importance, O*NET level, RTI, Frey-Osborne |
| I08 | Introduction: paired delta -0.0324, CI, p=.403 | `FROZEN_RESULTS.json` | `paired_test_c` |
| B01 | Section 6: AIOE within-family Q5 Jaccard 0.793–0.886 | `TEST_B_MEASURE_OVERLAP.csv` | Three AIOE-pair rows; min/max `Q5_jaccard` |
| B02 | Section 6: alpha-beta and beta-broad Q5 overlap and weighted residual correlation | `TEST_B_MEASURE_OVERLAP.csv` | Rows `(alpha,beta)` and `(beta,gamma)` |
| B03 | Section 6: cross-family AIOE-alpha and AIOE-beta Q5 ranges | `TEST_B_MEASURE_OVERLAP.csv` | Six AIOE-to-Eloundou rows |
| F02 | Figure 2 caption and plotted values | `TEST_B_IDENTIFYING_VARIATION_FULL.csv` | All 30 rows; stored effective N and top-five share |
| F03 | Figure 3 caption: 65 pre, 43 post/reference-era, 6 excluding zero and named months | `table6_dynamics_and_placebo.csv`; `RESULT_LEDGER.jsonl` | Event-study rows plus normalized October 2022 reference |
| C01 | Conclusion: construct/support divergence and mapping composition | Test A/B artifacts; `MAPPING_DECOMPOSITION_AUDIT.csv` | Interpretations authenticated in `FROZEN_RESULTS_REPORT.md` |
| C02 | Conclusion: computerization more than doubles beta point-estimate range | `ALTERNATIVE_X_AUDIT.csv` | Stored extrema -0.10011 and -0.20848 |
| C03 | Conclusion: every pre-specified architecture negative; roughly 9%–19% | `table4a_headline_q5_q1.csv`; `ALTERNATIVE_X_AUDIT.csv` | All required confirmatory headline/alternative exposure rows |
| C04 | Conclusion: no equivalence and no individual causal interpretation | `FROZEN_RESULTS.json`; `DESIGN_FREEZE_v2.md` | `paired_test_c`; binding interpretation limit |
| T1 | Table 1 architecture and source years | `NOVELTY_AUDIT_RECEIPT_2026-08-28.json` | Verified FRS and Eloundou source records |
| T2A | Every one of 48 Pearson correlations | `TEST_A_CHARACTERISTIC_MATRIX.csv` | Unique `(ai_measure, characteristic)`; `weighted_pearson` |
| T2B | Six joint residual-diagnostic rows | `TEST_A_RESIDUAL_DIAGNOSTICS.csv` | Unique `ai_measure`; all stored fields |
| T3A | Every numeric cell and named occupation in 30 architectures | `TEST_B_IDENTIFYING_VARIATION_FULL.csv` | Unique `(ai_measure, computerization_measure)` |
| T3B | All 15 weighted-residual-correlation and Q1/Q5-overlap rows | `TEST_B_MEASURE_OVERLAP.csv` | All rows copied without filtering |
| T4 | Four mapping rows | `MAPPING_DECOMPOSITION_AUDIT.csv` | Rows 1–4 |
| T5A | Twelve headline rows | `table4a_headline_q5_q1.csv` | All rows matched to ledger IDs |
| T5B | Six alternative-X rows plus paired row | `ALTERNATIVE_X_AUDIT.csv`; `FROZEN_RESULTS.json` | First six Rule-A/Webb exposure rows; `paired_test_c` |
| T6 | Five computerization and 11 presented remote rows | `ALTERNATIVE_X_AUDIT.csv`; `REMOTE_MODEL_AUDIT.csv` | Stored rows keyed by specification and coefficient label |

## Formula provenance

The continuous and quintile equations reproduce `prepare_model()` in `yax/analysis/run_frozen_v11.py`: Q1 is omitted, Q2–Q5 enter separately, and the target index is Q5. The effective-support formulas reproduce `weighted_projection()` and `analyse_pair()` in `yax/measurement/computerization_support.py`: contributions are exactly \(w_o\widetilde X_o^2\), normalized to shares before applying the inverse Herfindahl.

## Clean/auditable identity

`YAX_MANUSCRIPT_v2_CLEAN.md` is generated from `YAX_MANUSCRIPT_v2_AUDITABLE.md` by removing only `<!-- prov:... -->` comments. No prose, equation, table link, or quantitative content changes between versions.
