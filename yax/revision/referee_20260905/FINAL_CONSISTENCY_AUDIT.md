# Final consistency and production audit

Date: 2026-09-05

Revision branch: `task/yax-referee-revision-20260905`

Status: **PASS, subject to the disclosed unresolved items below**

## Immutable baseline and chronology

- Annotated tag `v1.1-design-freeze` peels to commit `22fbf7924809b7a535e31ae0ab68f5b113ce8078`.
- Annotated tag `v1.1-confirmatory-results` peels to commit `b16109482c3bf5ca176f6f08976e120b04769945`.
- The frozen tags and their commits were not modified. Calendar repair, placebos, alternative comparison ages and eras, external architectures, family refits, mobility thresholds, and inference audits are labeled post-outcome exploratory.
- The master execution prompt has SHA-256 `d8ede8cb69cffab502604653344a042556194ac613c5ccc99593a7af7827c14a`.

## Claim-to-result audit

The executable audit `paper/scripts/audit_referee_revision.py` returned **PASS** for 9 substantive claim checks and hashed all 62 files in the revised result tree. Its receipt is `FINAL_NUMERIC_AUDIT.json` (SHA-256 `ab462c055e0605744e516d05aca49a4965f93a627bcfd1548001270501719cdf`). The receipt is the authoritative result-file hash inventory.

The working-paper abstract and synthesis were checked against the following machine-readable sources:

| Claim used in the paper | Verified source |
|---|---|
| 3.33 to 97.7 percent computer/mathematical coverage repair | frozen taxonomy receipts and the reproduced repair decomposition summarized in Appendix B |
| Six within-family common-support estimates remain negative | frozen result artifacts and `results/inference/INFERENCE_AUDIT.csv` |
| Webb AI and OECD contrasts attenuate or approach zero | `results/external/EXTERNAL_ARCHITECTURE_OUTCOMES.csv` |
| Q5 differs from Q1 and Q3, but not detectably from Q2 or Q4 | `results/core/REFERENCE_CONTRASTS.csv` |
| Broad-family permutation does not establish AI specificity | `results/permutation/WITHIN_SOC2_PERMUTATION_SUMMARY.json` |
| Zero-threshold, mass-weighted, and 0.5-SD opposition mobility statements | `results/mobility/MOBILITY_THRESHOLD_RESULTS.csv` |
| Age and era heterogeneity | `results/balanced_cells/AGE_COMPARISON_RESULTS.csv` and `TIME_HETEROGENEITY_RESULTS.csv` |
| No-alpha F/G result and leave-one-measure sensitivity | `results/core/FG_LEAVE_ONE_OUT_RESULTS.csv` |

No abstract or conclusion sentence treats exposure as adoption, asserts causal displacement, claims general AI specificity, calls a failed difference test equivalence, or relabels the new analyses confirmatory.

## Test and compilation audit

- Full SCC suite: **890 passed, 3 skipped, 13 warnings** in 240.38 seconds. Log: `logs/FULL_TEST_SUITE_SCC.log`, SHA-256 `0303f86f48c4ff8a149ca374b82b311bd7f10dcc8dd1d8a4a1711bc673231e0a`.
- Final LaTeX logs pass `paper/scripts/check_latex_log.sh`: no fatal errors, undefined references, undefined control sequences, or overfull boxes.
- The exact build command and SCC fallback are documented in `paper/revision/README.md`; the SCC build also writes the four-PDF hash receipt.
- All 50 PDF pages were rasterized and inspected in contact sheets, with dense tables and figures additionally inspected at page resolution. No clipping, overlapping boxes, blank pages, broken mathematics, or misleading panel labels were found. One orphaned appendix line was corrected before the final build.

## Final artifact manifest

| Artifact | Pages | SHA-256 |
|---|---:|---|
| `paper/build/YAX_WORKING_PAPER_REVISED.pdf` | 21 | `f050a8120c9bc8e4917b85da3a6dce2b630655d1d81e1f9c278c4e31924bc62b` |
| `paper/build/YAX_ONLINE_APPENDIX_REVISED.pdf` | 20 | `72d746df3bd5bf5563278e4814a0a3f9358a85408f05970cae1b9e630bff75f4` |
| `paper/build/YAX_REFEREE_RESPONSE.pdf` | 6 | `9bb88e8569e1c38878241961cbc0477fe0cc59a056ee7b387b43db7cd7aa6c2c` |
| `paper/build/YAX_REVISION_DIAGNOSIS.pdf` | 3 | `27578f2200d5ddfaf9827f932aadd0d2c2209e88218aa3d4b825c13096f5eb20` |

## Completion and unresolved items

The response matrix covers every scientific, editorial, and production request represented in the supplied master prompt. Its SHA-256 is `84be231d63b482b749da67849228d91345edca8f32d2c5a0d0df39624b9189dd`. The original full R1 and R2 files were not supplied, so exact unseen wording cannot be reconciled; this limitation is stated in both the matrix and response letter.

Two requested diagnostics failed and are reported rather than replaced: the occupation-specific age-season model did not converge, and the literal full residual-wild refit generated no admissible grouped-binomial pseudo-outcomes. Survey-design variance, unique attribution of the precision gap, entrant destinations, and the exact no-self rematching expectation remain unavailable for the documented reasons. Author affiliation, email, acknowledgments, funding, and disclosure text remain flagged for author completion. The full wording register is `UNRESOLVED_ITEMS.md` (SHA-256 `fb9985d80f92bb73c313c17c1ef0f70ade1b1bac0d239e2f3331f3964bbe8b98`).
