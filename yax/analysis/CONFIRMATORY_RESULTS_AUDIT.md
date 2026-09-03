# YAX v1.1 confirmatory-results completion audit

**Audit conclusion: PASS.** Every outcome result and measurement diagnostic
required by `DESIGN_FREEZE_v2.md` is present, authenticated, and verified. The
only missing frozen analysis found by this audit was the full outcome-free Test
A characteristic matrix. It was completed using public O*NET/OEWS measurement
inputs and frozen 2017-01–2022-11 employment weights. It did not read protected
post-period outcomes or estimate a new outcome specification.

This is a verification and archival record. It contains no exploratory or
rescue analysis and makes no change to the frozen estimator, sample, outcome,
exposures, support rules, timing, controls, or inference.

## 1. Authority and archive state

| object | verified value |
|---|---|
| design tag | `v1.1-design-freeze` |
| design tag peeled commit | `22fbf7924809b7a535e31ae0ab68f5b113ce8078` |
| previously reported result commit | `5596d18df329ed3266163ba979256ee52b04d37a` |
| confirmatory result tag | `v1.1-confirmatory-results` |
| first outcome access receipt | `yax/analysis/FIRST_OUTCOME_ACCESS_RECEIPT.json` |
| canonical result JSON SHA-256 | `4f7df33a530e499c5562dead9464b2a19b87a3e3c6454d52944bc5e00879a831` |
| canonical result ledger SHA-256 | `e900adb75510729be635eb7aea381bfe6e523b376b6f2723350cf47bdf09266b` |
| canonical result Markdown SHA-256 | `2a152018d0198bb106a01ae08e5eda7c2d4a0e2fe617d74cc7f4ad731c18666e` |

The remote branch resolved to the reported result commit before this audit.
The final annotated tag is accepted only after the branch and peeled tag are
pushed and checked again. The tag's peeled commit is the complete archive
commit containing this report and the audit artifacts.

## 2. Frozen completion matrix

The detailed completion matrix has **241 rows** in
`yax/analysis/audit/CONFIRMATORY_COMPLETION_MATRIX.csv`. It individually
enumerates 48 Test A construct relationships, six joint residual diagnostics,
30 Test B AI-by-computerization diagnostics, 12 headline models, three support
rules, all frozen exposure/computerization variants, the paired Test C object,
seven remote-work models, four mapping rows, the placebo, 109 event-study
months (including the normalized reference), the extension test, and every
rendered table/figure content shell. Every row is `PASS`.

Measurement-only Test A/B rows are authenticated by their pre-period receipts,
not inserted retrospectively into the outcome ledger. Every frozen outcome
target or diagnostic is covered by the unchanged 195-row result ledger; the
normalized event-study reference month is correctly not a stochastic ledger
row.

## 3. Test A — complete construct-divergence matrix

Test A now covers all six frozen AI measures and all eight pre-specified
occupational characteristics. The matrix contains 48 Pearson/Spearman pairs;
the employment-weighted Pearson results are:

| AI measure | cognitive | manual/physical | routine (RTI) | education | log wage | telework | STEM | computer use |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AIOE administrative equal | 0.653 | -0.936 | 0.161 | 0.688 | 0.611 | 0.741 | 0.249 | 0.849 |
| AIOE ability direct | 0.689 | -0.913 | 0.152 | 0.708 | 0.640 | 0.746 | 0.242 | 0.847 |
| AIOE OEWS source weighted | 0.660 | -0.939 | 0.148 | 0.700 | 0.617 | 0.754 | 0.249 | 0.854 |
| Eloundou alpha | -0.032 | -0.266 | 0.217 | -0.034 | 0.011 | 0.200 | 0.436 | 0.304 |
| Eloundou beta | 0.478 | -0.758 | 0.169 | 0.425 | 0.478 | 0.589 | 0.371 | 0.797 |
| Eloundou gamma | 0.598 | -0.810 | 0.108 | 0.530 | 0.600 | 0.618 | 0.253 | 0.833 |

The joint eight-characteristic residual audit uses 348 occupations on common
support:

| AI measure | weighted R2 on characteristics | residual SD | effective occupations | top-five residual share |
|---|---:|---:|---:|---:|
| AIOE administrative equal | 0.964 | 0.189 | 35.5 | 30.4% |
| AIOE ability direct | 0.954 | 0.214 | 37.8 | 29.0% |
| AIOE OEWS source weighted | 0.971 | 0.171 | 44.2 | 24.9% |
| Eloundou alpha | 0.368 | 0.795 | 31.5 | 33.7% |
| Eloundou beta | 0.743 | 0.507 | 36.9 | 28.0% |
| Eloundou gamma | 0.811 | 0.435 | 31.5 | 29.7% |

Full Spearman results, raw high/low rankings, 15 residual-correlation pairs,
30 Q1/Q5 overlap rows, and named residual contributors are stored under
`yax/measurement/test_a/`. The receipt pins the O*NET 26.1 archive and every
derived-file hash and records `post_period_outcomes_read: false`.

## 4. Test B — all frozen exposure definitions

The complete Test B table has 30 rows: six AI measures by five frozen
computerization controls. The prior alpha/beta examples were not selectively
chosen. Effective identifying occupations are:

| AI measure | Webb | O*NET importance | O*NET level | Autor-Dorn RTI | Frey-Osborne |
|---|---:|---:|---:|---:|---:|
| AIOE administrative equal | 72.2 | 73.0 | 77.3 | 62.8 | 63.8 |
| AIOE ability direct | 74.6 | 77.8 | 82.2 | 68.2 | 59.3 |
| AIOE OEWS source weighted | 72.1 | 65.4 | 70.3 | 62.1 | 62.8 |
| Eloundou alpha | 17.4 | 31.1 | 31.7 | 11.9 | 26.3 |
| Eloundou beta | 53.3 | 63.2 | 59.5 | 51.7 | 62.9 |
| Eloundou gamma | 84.5 | 44.4 | 72.2 | 77.5 | 74.0 |

Top-five residual-variance shares are:

| AI measure | Webb | O*NET importance | O*NET level | Autor-Dorn RTI | Frey-Osborne |
|---|---:|---:|---:|---:|---:|
| AIOE administrative equal | 18.4% | 17.9% | 16.6% | 20.5% | 20.0% |
| AIOE ability direct | 15.9% | 16.5% | 15.0% | 17.8% | 20.6% |
| AIOE OEWS source weighted | 18.1% | 19.5% | 18.3% | 20.6% | 20.2% |
| Eloundou alpha | 41.6% | 32.8% | 33.3% | 46.6% | 36.0% |
| Eloundou beta | 22.2% | 20.1% | 20.6% | 22.8% | 19.8% |
| Eloundou gamma | 15.8% | 25.2% | 18.0% | 17.3% | 17.1% |

The full machine-readable table also contains correlations, R2, partial
variance, VIF, SE inflation, residual SD, largest occupational-family share,
and the five named leading occupations for every row. Cross-measure residual
correlations and Q1/Q5 Jaccard overlaps are in
`yax/analysis/audit/TEST_B_MEASURE_OVERLAP.csv`.

## 5. Test C and headline estimates

All 12 frozen alpha/beta x Rule A/B/C x Webb/O*NET headline models converged.
All coefficient objects contain 999-draw bootstrap inference, and every target
coefficient matches the result ledger exactly. The target range is
`-0.2084809` to `-0.0970951` log points. The primary beta x Webb x Rule-A
estimate is:

> `-0.131074 [-0.217038, -0.045110], p=0.003`.

The paired beta-minus-alpha result is exactly:

| object | result |
|---|---:|
| beta | -0.131074 |
| alpha | -0.098678 |
| Delta | -0.032396 |
| paired SE(Delta) | 0.036968 |
| paired 95% CI | [-0.102345, 0.037553] |
| paired p-value | 0.403 |
| common bootstrap draws | 999 |
| frozen MDE80 | 0.032722 log points (about 3.27 percentage points) |

The stored paired distribution reproduces the paired SE. The same draws and
stored covariance preserve paired inference. Because the CI includes zero, the
binding interpretation is only that the design does not detect a difference.
It does not establish economic equivalence.

## 6. Computerization, remote work, mapping, and timing

The beta Q5-Q1 coefficient remains negative under every frozen
computerization control but moves materially: Webb `-0.13107`, O*NET
importance `-0.20848`, O*NET level `-0.15120`, Autor-Dorn RTI `-0.12771`, and
Frey-Osborne `-0.10011`.

All seven remote-work models and all 13 component coefficients match the
ledger. For beta, the AI coefficient is `-0.03814` alone, `-0.03795` with
remote exposure, and `-0.03718` with Webb and remote exposure. The remote
coefficient is `0.00469 [-0.02288, 0.03226]` in the AI-remote model and
`0.00606 [-0.02123, 0.03335]` in the full model. Remote-only is `-0.01884
[-0.04508, 0.00739]`. These are conditional coefficient comparisons, not a
causal claim that AI beats remote work.

The mapping/common-support sequence reproduces exactly:

`-0.018845 -> -0.019200 -> -0.031565`, with computer/math excluded
`-0.029404`.

The value correction on unchanged support is negligible; the larger movement
comes from occupation re-admission/composition. Excluding computer/math removes
little of that change. This is not evidence that a named benchmark paper used a
naive crosswalk.

The frozen placebo is `0.001421 [-0.020395, 0.023236], p=0.894`. The event
archive contains 109 rows: one normalized October-2022 reference, 65
non-reference pre-event coefficients, and 43 transition/post coefficients.
Zero pre-event intervals exclude zero. Six post intervals exclude zero:
November–December 2023 and April–July 2026. The post-2025 extension-change
test has `p=0.127`.

## 7. Post-outcome implementation audit

`yax/analysis/audit/POST_OUTCOME_CHANGE_LEDGER.csv` classifies every commit
after first outcome access. There is no substantive specification change.
The post-access code modifications were solver/existence implementation fixes,
the correction of a Rule-A-universe bug that prevented frozen Rules B/C from
being estimated, ledger completion, rendering, documentation, and this audit.
The first successful but defective output remains immutable. Every frozen
model was rerun after each implementation fix that could affect estimates.

The corrected cell build reproduces the frozen Rule-A cells to a maximum
absolute gap of `9.313225746154785e-10`.

The Test A completion occurred after confirmatory outcomes had been archived,
but its executable asserts that its employment-weight input ends in 2022-11;
its receipt records no protected outcome read. It changes no outcome model.

## 8. Reproducibility and integrity

From a detached, clean checkout of result commit `5596d18...`,
`render_frozen_outputs.py` regenerated 16 reporting artifacts. All 16 tables
and figures matched the canonical files byte-for-byte. The checkout remained
clean, and no untracked local input was required. Licensed microdata were not
read. The canonical hash manifest separately validates all reporting artifacts.

Authoritative SCC checks:

| check | exact result |
|---|---:|
| full repository test suite | 772 passed, 3 skipped, 13 warnings |
| immutable design-tag gates at `22fbf792...` | 12 PASS, 0 FAIL, 0 BLOCKED |
| confirmatory integrity checks | 47 PASS, 0 FAIL |
| completion-matrix rows | 241 PASS, 0 FAIL |
| result-ledger rows | 195 valid, 195 unique |
| canonical reporting reproduction | 16/16 byte-identical |

The three skips are the already disclosed optional dependency paths. The 13
warnings are deprecation warnings outside the YAX estimator. During this audit,
one stale test still assumed the repository contained no committed outcomes.
It was corrected to verify that the immutable `v1.1-design-freeze` exists
before the intentionally committed result archive; the seal gate itself was
unchanged.

## 9. Discrepancies found

1. The previous prose report printed the result-ledger SHA-256 with the final
   character `e`. Direct hashing and the audit show that the canonical ledger
   hash ends in `b`: `e900...266b`. The documentation typo is corrected here;
   the ledger itself is unchanged.
2. A stale SCC directory previously described as the freeze worktree was at an
   earlier pre-freeze commit and therefore showed two blocked gates. It was not
   used as evidence. A new detached checkout of the actual annotated tag peeled
   to `22fbf792...` and returned 12/12 PASS.
3. The original frozen-results prose summarized only the partial Test A
   evidence already in the repository. The full frozen cognitive, manual,
   routine, education, wage, telework, STEM, computer-use, residual, ranking,
   and overlap matrix is now complete and permanently recorded.

## 10. Final status

| Component | Status |
|---|---|
| Test A | PASS |
| Test B | PASS |
| Test C | PASS |
| Headline models | PASS |
| Mapping | PASS |
| Computerization | PASS |
| Remote work | PASS |
| Placebo | PASS |
| Event study | PASS |
| Extension | PASS |
| Result ledger | PASS |
| Reproducibility | PASS |
| Post-outcome change audit | PASS |
| Remote archival | PASS |

The annotated `v1.1-confirmatory-results` tag is the immutable confirmatory
archive boundary. No exploratory analysis is included. Manuscript drafting did
not begin during this task.
