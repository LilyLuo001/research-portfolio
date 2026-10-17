# Independent QA: frozen Formal800 research comparisons

Date: 2026-10-16
Verdict: **PASS — no material issue remains.**

## Scope

This review covered the frozen analyzer, scheduled wrapper, public scheduler receipts, aggregate outputs, and the claims in `RESULTS_DRAFT_ZH.md`. It did not reread advertisements, create labels, change the sample, or recompute research estimates locally. Figure appearance is reviewed separately by root.

## Execution and source binding

- Analyzer SHA-256: `602d509b9839484cfc3a1733a13d2d7a93561090be146275a135b1bca4b94a29`.
- Accepted wrapper SHA-256: `65f758312118bcf83f5e36ed278c215d069016d7ab5bb4983205d6e2f38cca26`.
- Wuzhen Slurm job `46700531` completed `0:0` in 13 seconds on `wzhdtest`, with 2 CPUs, 4 GiB requested memory, and 42,008 KiB batch maximum RSS. The required DCU was reserved by the partition; the analysis itself was CPU-only.
- The earlier 8-GiB submission was rejected before job creation because it exceeded `DefMemPerCPU`. The public submission receipt preserves that event; only the memory request changed before the successful job.
- The public analysis receipt binds the frozen 800-ad export SHA-256 `c3cfbc13db0186b209c7a5a18a33c743b17262c02f46899852e8927e8aaa4f8b` and the 719-record validated structured review SHA-256 `2939a5846cb6d40f42af94465e764fedcad51b86fc3d387d04d142c51ff63860`. Both match the accepted Formal800 receipt. The finite frame remains 9,282 ads and the main weight remains `1/pi3`; no parent-frame weight is used.
- Every output hash listed in `ANALYSIS_RECEIPT.json` matches the returned public file. The original Q1 table hash is preserved, and all 20 pooled/within-major Q1 rows reproduce the published table to the declared absolute tolerance of `1e-12`.

## Estimator and denominator checks

- Q1 compares frozen GenAI work use, including software co-use, with traditional-software work use without active AI. Majors 11, 13, 15, and 17 receive fixed weights of 0.25. The receipt and tables label this as a hypothetical equal-major composition, not an estimated population composition.
- The standardized contrast is a weighted sum of eight group-major ratios. Its unit influence is evaluated over all 800 sampled ads, including zero domain contributions, and the six original sampling strata are used jointly. This retains covariance across ratio terms and applies each stratum's finite-population correction.
- The production self-test verifies a zero point contrast with standard error exactly `sqrt(1/112)`, a nonconstant census-stratum influence with zero sampling variance, and fail-closed `NA` when a required group-major denominator is empty. Noncensus singleton variance also remains unavailable by contract.
- Q1 tables expose sampled, positive, known, and unknown counts and weighted masses. Recorded-outcome unknowns are excluded from defined denominators and included in the stated lower/upper bounds. A required empty cell is not selectively dropped or followed by weight renormalization.
- Q2's main domain is the fixed 33 explicit-new-graduate positives across all technology categories. The 54-ad waiver-or-graduate domain is clearly secondary and is not described as zero-total-experience eligibility. Unknown graduate membership is excluded from the positive domain and reported as both one sampled ad and weighted mass 11.8123.
- Q2 reports all four strict current-duty dimensions, any strict current duty, the four experience dimensions, identifiable experience combinations, and the permitted aggregate clause supplement. One masked or unrecognized clause stays excluded and counted. Numeric years, strength, conditionality, waiver status, and alternative group/branch indicators remain descriptive clause fields; no universal minimum or contradiction label is inferred.
- Zero-event or zero-linearized-SE rows carry an explicit flag that they do not prove population absence. Confidence intervals are described as sampling uncertainty conditional on frozen labels and support; they exclude semantic error, technology-group uncertainty, and support-selection uncertainty.

## Ad unit, privacy, and claims

The analysis retains 800 advertisement rows while binding them to 719 structured reviews, so byte-identical contexts remain advertisement-level observations with their original weights rather than being collapsed to contexts. Public results and receipts contain aggregate values and hashes only. A search found no advertisement keys, record IDs, context hashes, source row identifiers, quotes, or raw text in the public artifacts.

The Chinese results memo accurately transcribes the returned aggregates and keeps the required boundaries: descriptive delivered-text associations only; no causal, historical-change, employer, fine-occupation, global-accuracy, or full-corpus claim. Its Q1 differences and intervals match `Q1_EQUAL_MAJOR_STANDARDIZED.csv`; its Q2 known/unknown counts, rates, intervals, weighted domain mass, zero-event caveats, and 92-clause supplement count match the published tables and receipt.

## Acceptance

The frozen analyzer, successful scheduled execution, public aggregates, provenance receipts, and written claims satisfy the predeclared comparison contract. No repair or additional analysis is required for release.
