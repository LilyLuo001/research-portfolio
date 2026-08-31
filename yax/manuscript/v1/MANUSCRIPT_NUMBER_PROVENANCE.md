# YAX manuscript-number provenance

Every quantitative statement in the abstract, introduction, conclusion, publication tables, and figure captions is covered below. All outcome authorities resolve to the immutable tag `v1.1-confirmatory-results`, commit `b16109482c3bf5ca176f6f08976e120b04769945`. Measurement-only authorities were archived at the same commit and record that no protected post-period outcome was read.

| ID / scope | Manuscript location and quantitative content | Authoritative source artifact | Ledger row, result key, or frozen row rule |
|---|---|---|---|
| A01 | Abstract: 6 measures, 8 characteristics, 30 architectures, effective N 11.9–84.5, top-five share 15.0%–46.6% | `yax/analysis/CONFIRMATORY_RESULTS_AUDIT.md`; `yax/analysis/audit/TEST_B_IDENTIFYING_VARIATION_FULL.csv` | Test-A completion matrix; minimum/maximum of stored Test-B fields across all 30 frozen rows |
| A02 | Abstract: 12 alpha/beta models; coefficient range -0.097 to -0.208; all CIs exclude zero | `yax/analysis/outcomes/frozen_v11_corrected_run/reporting/table4a_headline_q5_q1.csv` | Ledger rows with specification IDs matching `dv_rating_{alpha,beta}__Rule{A,B,C}__{webb,onet}_...` |
| A03 | Abstract: primary -0.131, CI [-0.217,-0.045], p=.003, 12.3% | `yax/analysis/outcomes/frozen_v11_corrected_run/RESULT_LEDGER.jsonl`; `FROZEN_RESULTS_REPORT.md` | `dv_rating_beta__RuleA__webb_pct_software__q5_q1`; report's canonical exponential translation |
| A04 | Abstract: paired difference -0.032, CI [-0.102,0.038] | `yax/analysis/outcomes/frozen_v11_corrected_run/FROZEN_RESULTS.json` | `paired_test_c`: beta, alpha, delta, paired CI, p-value, 999 common draws |
| I01 | Introduction: all-30 Test-B range | `yax/analysis/audit/TEST_B_IDENTIFYING_VARIATION_FULL.csv` | All 30 rows; stored effective-N and top-five-share fields |
| I02 | Introduction: alpha/Webb 17.4 and 41.6%; beta/Webb 53.3 and 22.2% | `yax/analysis/audit/TEST_B_IDENTIFYING_VARIATION_FULL.csv` | Rows `dv_rating_alpha/webb_pct_software` and `dv_rating_beta/webb_pct_software` |
| I03 | Introduction: mapping sequence -0.01885, -0.01920, -0.03156, -0.02940 | `yax/analysis/audit/MAPPING_DECOMPOSITION_AUDIT.csv` | Frozen rows 1–4 |
| I04 | Introduction: 12 models, -0.0971 to -0.2085, -9.3% to -18.8%, all intervals exclude zero | `table4a_headline_q5_q1.csv`; `FROZEN_RESULTS_REPORT.md` | All 12 canonical headline rows; report's stored relative-magnitude translations |
| I05 | Introduction: primary coefficient, CI, p-value, 12.3%, January 2023 | `RESULT_LEDGER.jsonl`; `DESIGN_FREEZE_v2.md`; `FROZEN_RESULTS_REPORT.md` | Primary specification row; frozen static-post definition; report translation |
| I06 | Introduction: delta -0.0324, SE 0.0370, CI, p=.403 | `FROZEN_RESULTS.json`; `RESULT_LEDGER.jsonl` | `paired_test_c` and paired ledger row |
| I07 | Introduction: paired MDE 3.27 percentage points and 80% power | `yax/power/PAIRED_DIFFERENCE_PRECISION_v2.json`; `DESIGN_FREEZE_v2.md` | `MDE_Delta_80 = 0.032722`; frozen permitted precision statement |
| C01 | Conclusion: 30 cells; effective N and top-five ranges | `TEST_B_IDENTIFYING_VARIATION_FULL.csv` | All 30 frozen rows |
| C02 | Conclusion: composition rather than within-support value correction | `MAPPING_DECOMPOSITION_AUDIT.csv` | Frozen rows 1–4; row 1→2 versus row 2→3 comparison as interpreted in `FROZEN_RESULTS_REPORT.md` |
| C03 | Conclusion: all 12 negative, -0.097 to -0.208, all intervals exclude zero | `table4a_headline_q5_q1.csv` | All 12 frozen rows |
| C04 | Conclusion: primary -0.131, CI, p, 12.3% | `RESULT_LEDGER.jsonl`; `FROZEN_RESULTS_REPORT.md` | Primary specification row; canonical translation |
| C05 | Conclusion: paired result does not detect difference and does not establish equivalence | `FROZEN_RESULTS.json`; `FREEZE_AMENDMENT_2026-08-29_PAIRED_PRECISION.md` | Paired CI includes zero; binding interpretation rule |
| C06 | Conclusion: magnitude depends on 5 computerization definitions | `yax/analysis/audit/ALTERNATIVE_X_AUDIT.csv` | Beta Rule-A rows for Webb, O*NET importance, O*NET level, RTI, and Frey-Osborne |
| T1 | Table 1 source years and measure architecture | `yax/literature/NOVELTY_AUDIT_RECEIPT_2026-08-28.json`; `CPS_OCCUPATION_EXPOSURE_LOOKUP.md` | Verified source records `felten_raj_seamans_2018`, `felten_raj_seamans_2021`, `eloundou_et_al_2024`; notation record |
| T2A | Table 2A: every one of 48 Pearson correlations | `yax/measurement/test_a/TEST_A_CHARACTERISTIC_MATRIX.csv` | Unique key `(ai_measure, characteristic)`; field `weighted_pearson`; 6×8 complete |
| T2B | Table 2B: all 6 joint R², residual SD, effective-N, and top-five-share rows | `yax/measurement/test_a/TEST_A_RESIDUAL_DIAGNOSTICS.csv` | Unique key `ai_measure`; common support is stored as 348 in every row |
| T3 | Table 3: all numeric cells and named occupations for 30 architectures | `yax/analysis/audit/TEST_B_IDENTIFYING_VARIATION_FULL.csv` | Unique key `(ai_measure, computerization_measure)`; all 30 rows, no filtering |
| T4 | Table 4: all 4 mapping coefficients, SEs, CIs, p-values, and occupation counts | `yax/analysis/audit/MAPPING_DECOMPOSITION_AUDIT.csv` | Stored rows 1–4 |
| T5A | Table 5A: all 12 headline coefficients, SEs, CIs, p-values, and occupation counts | `yax/analysis/outcomes/frozen_v11_corrected_run/reporting/table4a_headline_q5_q1.csv` | All rows, matched to ledger by specification ID |
| T5B | Table 5B: all 6 alternative-X rows and paired row | `yax/analysis/audit/ALTERNATIVE_X_AUDIT.csv`; `FROZEN_RESULTS.json` | First six frozen Rule-A/Webb alternative-exposure rows; `paired_test_c` |
| T6 | Table 6: all 5 computerization rows and 11 presented remote rows | `yax/analysis/audit/ALTERNATIVE_X_AUDIT.csv`; `yax/analysis/audit/REMOTE_MODEL_AUDIT.csv` | Five beta/control rows; remote rows keyed by `(specification_id, coefficient_label)` |
| F02 | Figure 2 caption and every plotted value | `yax/analysis/audit/TEST_B_IDENTIFYING_VARIATION_FULL.csv` | All 30 frozen rows; plotted fields copied without estimation |
| F03 | Figure 3 caption: 65 pre coefficients, 43 post/reference-era coefficients, 6 excluding zero and named months | `yax/analysis/outcomes/frozen_v11_corrected_run/reporting/table6_dynamics_and_placebo.csv`; `RESULT_LEDGER.jsonl` | Event rows `event_2017-01` through `event_2026-07`; normalized 2022-10 reference; canonical count diagnostic |

## Presentation-transformation rule

The build script formats stored fields, pivots complete frozen matrices, and copies the canonical event-study image. It does not fit a model or construct a new diagnostic. Percent signs in the tables are decimal-to-percent display transformations of stored shares. Rounding is presentational and the underlying CSVs retain the frozen precision.
