# Batch069 fixed10k empirical essential QA

Status: **PASS for the bounded T1--T6 empirical release**, using analysis code SHA-256 `15c391cf66703d90d8329c5d2bd6eea5f7f6e4f85b2c7c7942da7c40448b6d58` and `results/RUN_RECEIPT_PUBLIC.json`. The output-only repair in `results/FINAL_RENDER_RECEIPT_PUBLIC.json` also passes; it changes no numeric analysis.

## Essential checks

- Input binding is fail-closed against the accepted Batch069 receipt: ledger, uncertainty register, and isolation-register hashes match; the frozen counts are 10,000 ads, 9,282 original eligible ads, 1,002 reviewed-uncertainty contexts, and 14 isolated contexts. The 14 isolated contexts expand to 16 advertisements, so context and ad denominators remain distinct.
- Each of the seven family-status panels conserves 10,000 and 9,282 ads. `known`/`not_applicable` are the only usable states; `unknown_or_conflict`, `partial`, and `candidate_only` are not silently recovered from another family or source.
- New fixed-frame panels use weight 1. Published Formal800 files are byte-identical copies of their existing sources and retain their published `w3` estimates and sampling intervals.
- The frozen technology contrast is preserved: GenAI work use, including traditional-software co-use, versus traditional-software work use without active AI. Technology-membership uncertainty is reported separately from recorded outcome-family unknown bounds.
- Q1 rate, count, lower-bound, upper-bound, and difference identities pass. Equal-major results reproduce the arithmetic mean of majors 11, 13, 15, and 17 at weight 0.25 each. Point and bound availability use separate fail-closed denominator checks; no major is dropped or renormalized.
- Q2 eligibility unknowns are excluded from conditional domains and reported separately. Marginal rate identities pass. Pairwise duty-by-experience partitions and four-experience-pattern by `duty_any` counts conserve each eligible domain. Current duty does not acquire a required/preferred label; duty conditionality and experience-clause strength are reported separately.
- Experience-clause strength indicators are overlapping ad indicators. Literal years retain object and literal relation and are not interpreted as a job minimum. Conditions and OR/AND branch summaries retain their family/object scope without publishing or pooling record-local alternative IDs. Use `T2_EXPERIENCE_CLAUSES_INTERPRETABLE.csv` for interpretation; it supersedes the ambiguous presentation of overlapping indicators in the original T2 export.
- T3 technology-by-experience combinations conserve each frame. T4 fixed10k results use only available `created_year`; exact-date cuts and same-company/similar-job first-seen analyses are explicit NA. Reused global T4 files remain labeled as global 204,774,035-row results and are not new fixed10k historical or causal evidence.
- Every file named in the main and final-render receipts is present with the recorded hash. The final figures are legible and label their intervals as recorded-family-unknown bounds, not confidence intervals. Use `FIG1_Q1_CORE_RECORDED_UNKNOWN_BOUNDS_FINAL.png` and `FIG2_Q2_CORE_RECORDED_UNKNOWN_BOUNDS_FINAL.png`; the original dense figures are superseded.

## Claim boundary

The structured reference labels are accepted historical Pro judgments, not human truth. These results are descriptive snapshots of existing reference coverage. They do not establish causal or historical text change, and the 27 TF-IDF presence targets cannot establish absence or replace the rich seven-family ledger.
