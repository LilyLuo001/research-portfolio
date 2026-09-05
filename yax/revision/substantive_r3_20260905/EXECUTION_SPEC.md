# YAX substantive revision R3: execution specification

Status: **post-outcome, referee-led revision specification written before the new R3 analyses**  
Branch: `task/yax-substantive-revision-r3-20260905`  
Parent commit: `6b8d85e79ee9e5b7f410776c73969f0a0bf5d897`  
Specification date: 2026-09-05 (Asia/Shanghai)

## Governing rule

This round investigates the referee diagnoses; it does not insert them as findings. Existing frozen and post-outcome results remain immutable comparison artifacts. Every new result must be labeled post-outcome exploratory, report its exact support and conditioning estimand, retain failures, and enter `RESULTS_LEDGER.csv` whether favorable, unfavorable, or inconclusive. No main-text conclusion may be finalized before its registered result and audit exist.

## Authenticated inputs

| Input | SHA-256 | Status |
|---|---|---|
| Integrated R3 execution prompt (`00f593.../pasted-text.txt`) | `8e4dc7e60a5ac9fc70799b669fb140b2dfa44c2a67589bdd87f31afdead8851c` | read in full |
| Uploaded referee report (`7095d3.../pasted-text.txt`) | `f5af3adc0774002fe3f0f76f7959ba336b47ff6a03b55aab6c49bf7141b73c67` | read in full; 12 major comments |
| Uploaded referee report (`f4872e.../pasted-text.txt`) | `78dd89b842934e10842e202b6578b655a4afb4bd1efb2a20a47cf2c05bda5146` | read in full; 9 major comments |
| Prior evidence-led master prompt (`0164c9.../pasted-text.txt`) | `d8ede8cb69cffab502604653344a042556194ac613c5ccc99593a7af7827c14a` | read in full; contains integrated numbered-R2 instructions |

The R3 prompt refers to another R2 whose headings are numbered 3.1--3.9, 4.1--4.9, and 5.1--5.11. A repository-wide and attachment-wide search has not located that exact source document. The integrated R3 prompt and the earlier master prompt preserve its requested analyses, but they are not substitutes for quoting or claiming to have read the missing report. The response matrix must mark this source limitation until the exact document is available.

## Compute and storage decision

The requested `/projectnb/econdept/...` tier is currently unwritable: SCC `pquota econdept` reports 30,100 GB used against a 30,000 GB quota, and a named 128 MB write probe failed with `Disk quota exceeded`. No existing files will be deleted to manufacture capacity. The verified compute root is:

`/project/econdept/qluo/yax-substantive-revision-20260905`

SCC reports 74.71 GB used against a 200 GB quota on this tier; a real 128 MB write-and-fsync probe succeeded and was removed. Private inputs may be read from their authenticated existing locations, but all new code copies, logs, temporary artifacts, draws, and results must be written beneath the verified compute root. No secrets may be stored in code, logs, receipts, or Git.

## Execution order

1. Inventory sources, reports, code, inputs, previous outputs, environment, and hashes.
2. Reproduce the frozen and corrected baselines without changing the estimator.
3. Rebuild the corrected data pipeline and distinguish historical treatment assignments from fully recomputed assignments.
4. Audit calendar, crosswalk, support, weighting, population-control eras, and late-2025/2026 coverage.
5. Run family-support and within-family estimands, including direct-tail and continuous designs.
6. Run characteristic-conditioning and matched-support placebo comparisons.
7. Audit sampling/dependence inference, then run the feasible SOC2, household/sample-unit, time-HAC, and finite-sample procedures.
8. Replace restricted dynamics with an estimand-aligned dynamic specification; only run Rambachan--Roth-style sensitivity if its requirements are verified.
9. Verify and implement BCC-comparable groupings/outcomes to the extent public data permit.
10. Run valid stock/flow and secondary-outcome extensions, retaining infeasible requests as explicit blockers.
11. Retain useful architecture diagnostics; demote coordinate rotations and mobility material unless directly needed.
12. Let the verified evidence determine the title, framing, and section allocation; shorten the scientific article and focused appendix.
13. Run numerical, citation, implementation, reproducibility, LaTeX, and rendered-PDF audits.

## Binding interpretation rules

- A SOC2-conditioned coefficient changes the conditioning estimand; it is not an additive causal decomposition of the baseline.
- A paired confidence interval containing zero means the design does not detect a difference. It does not establish equivalence.
- Smaller information and wider intervals must be reported with within-family estimates. Failure to reject zero cannot be called disappearance.
- No comparison of “significant” and “insignificant” coefficients substitutes for a direct paired test.
- Placebo occupational characteristics are benchmark comparisons, not automatically a calibrated null distribution.
- Outcome-ranked deletions are influence diagnostics, not conventional robustness or causal attribution.
- BCC public-CPS exercises are grouping/stock bridges unless their proprietary outcomes and mappings are actually reproduced.
- Teleworkability is not computerization. Any proxy use must be labeled; preferred computerization inputs must predate widespread LLM diffusion where feasible.
- The static grouped-binomial coefficient is not presumed to equal a simple average of event-time coefficients.
- No unavailable outcome, survey-design variable, crosswalk field, or permission may be invented.

## Registered branching rules

1. If direct within-family tail support is narrow, the changed population and support are the result; do not recover a headline by changing thresholds after seeing estimates.
2. If within-family estimates are imprecise, report their MDEs and the exact residual-information loss; do not write that detailed exposure is irrelevant.
3. If AI and generic occupational-characteristic contrasts are statistically indistinguishable on identical support, narrow AI-specific language.
4. If corrected dynamics do not support a coherent onset or if plausible pretrend deviations overturn the post functional, frame the employment exercise as descriptive.
5. If public CPS outcomes cannot reproduce a proprietary BCC estimand, stop at a transparent bridge rather than describing it as a replication.
6. If household/sample-unit identifiers or replicate weights are unavailable, report that design-based inference is incomplete and do not relabel model-based covariance sensitivities.
7. Failed or singular models remain in the failure registry with the attempted specification and reason.

## Required terminal artifacts

- Revised main paper source and PDF.
- Focused online appendix source and PDF.
- Change-marked or machine-readable manuscript diff.
- Concise editor response and separate point-by-point response.
- Machine-readable response matrix covering all located comments and every integrated R3 requirement.
- Specification registry, results ledger, failure registry, input/output hash manifest, environment lock, master build command, seeds/draws/covariances where disclosure permits, and automated audits.
- Numerical-consistency audit and unresolved-items register.
- Rendered-page visual-QA record for every delivered PDF.

