# YAX v1.1 frozen-results report

**Confirmatory status:** complete. **Substantive classification:** State C —
measurement differences are real, while direct downstream measure differences
remain inconclusive. The negative young-relative employment-stock gradient is
nevertheless robust across every frozen exposure and computerization variant.

This report interprets only the confirmatory analysis frozen at
`v1.1-design-freeze`. It adds no specification and initiates no exploratory
analysis.

## A. Execution integrity

The design was frozen at commit
`22fbf7924809b7a535e31ae0ab68f5b113ce8078`, annotated tag
`v1.1-design-freeze`. The original `v1.0-design-freeze` remains preserved.

The permanent first-access record is
[`FIRST_OUTCOME_ACCESS_RECEIPT.json`](FIRST_OUTCOME_ACCESS_RECEIPT.json). It
records the first authorized command, timestamp, private data path, input
hashes, frozen commit and tag before protected post-period outcomes were read.

The authenticated private inputs were:

| input | SHA-256 |
|---|---|
| IPUMS CPS microdata | `3fe42477e6f2ce401e85123f0e278e758595c1c4071a8743f243a92752db38c9` |
| frozen pre-period cells | `4b8c8b96caeebc4121ad4914adbadf7ebfa98d677a80b32b78a9f905956ea800` |
| exposure lookup | `c6eb70623ea598bfc41f2352391add7a342a8809a4e57b02f2af0e75dd0223f8` |
| computerization measures | `352cb40834ec83225f747d316eb3e03fce1d1c5c65d80720c558177f85801fdd` |
| Rule-B values | `8092f0eef57aaf4271a7dc563a4820e2f9a6d13519bcac9372837bc7a2c991e6` |
| Census 2010→2018 bridge | `0bd2f63c72e24bed2cc1cb414395c3cbddf7c00011e47ec1c1de6ae534fd1dcc` |

Before outcomes, the tagged suite returned **769 passed, 3 skipped** and all
12 gates passed. After implementation and the documented fixes below, the SCC
suite returned **772 passed, 3 skipped, 13 warnings**. A clean tagged-state
rerun again returned **PASS on all 12 gates**, including novelty, calibrated
power, paired-difference precision, and the outcome seal as it existed at the
freeze.

Five implementation fixes were required and recorded, in order, in
[`POST_OUTCOME_IMPLEMENTATION_FIXES.md`](POST_OUTCOME_IMPLEMENTATION_FIXES.md):

1. two solver-ceiling increases for the frozen placebo;
2. the mechanical removal of one occupation with no finite fixed-effect MLE in
   the placebo window;
3. reconstruction of the full occupation-cell universe so frozen Rules B and C
   could actually re-admit occupations rather than inheriting Rule-A support;
4. completion of the result ledger.

The first successful output was never overwritten and remains at
[`frozen_v11_first_run`](outcomes/frozen_v11_first_run). It exposed the Rule-A
universe defect. The authoritative corrected output is
[`frozen_v11_corrected_run`](outcomes/frozen_v11_corrected_run). Its rebuilt
Rule-A slice reproduces the frozen pre-period cells with a maximum numerical
gap of `9.31e-10`. This is an implementation correction, not a design change.

Corrected core-output hashes are:

| artifact | SHA-256 |
|---|---|
| `FROZEN_RESULTS.json` | `4f7df33a530e499c5562dead9464b2a19b87a3e3c6454d52944bc5e00879a831` |
| `RESULT_LEDGER.jsonl` | `e900adb75510729be635eb7aea381bfe6e523b376b6f2723350cf47bdf09266e` |
| `FROZEN_RESULTS.md` | `2a152018d0198bb106a01ae08e5eda7c2d4a0e2fe617d74cc7f4ad731c18666e` |

The ledger contains 195 rows. Table, figure and reporting hashes are in
[`ARTIFACT_HASHES.sha256`](outcomes/frozen_v11_corrected_run/reporting/ARTIFACT_HASHES.sha256).

## B. Main empirical results

### Test A — construct divergence

The frozen measurement evidence rejects the convenient interpretation that the
major indices are noisy versions of one transparently common occupational
construct.

- Employment-weighted overlap with teleworkability ranges from **R² = 0.091**
  for Eloundou α to **0.579** for AIOE; β and γ lie at 0.421 and 0.454.
- The five computerization controls themselves are not interchangeable. Webb
  software-patent exposure correlates `-0.106` with O*NET computer-use
  importance and `-0.003` with O*NET computer-use level, whereas the two O*NET
  measures correlate `0.912`. RTI and Frey–Osborne correlate `0.448`.
- The named occupation rankings make these differences interpretable rather
  than indicating a broken join: Webb's upper tail emphasizes process and
  machine-control work; O*NET emphasizes computing, engineering and analytical
  work; RTI emphasizes routine clerical work; Frey–Osborne measures broader
  automation susceptibility.
- The three AIOE mapping variants are highly correlated on common support, but
  they remain separate constructions because aggregation and support rules are
  part of the measurement object.

These diagnostics establish construct divergence, not a unique latent “true AI
exposure.” The frozen in-repository audit is strongest on rankings,
teleworkability, and computerization; it does not justify a new factor-based
master index.

See
[`table1_construct_and_identifying_support.md`](outcomes/frozen_v11_corrected_run/reporting/table1_construct_and_identifying_support.md),
[`figure2_measurement_divergence.png`](outcomes/frozen_v11_corrected_run/reporting/figure2_measurement_divergence.png),
and the pre-outcome [`CONSTRUCT_VALIDITY.md`](../measurement/CONSTRUCT_VALIDITY.md).

### Test B — identifying-variation divergence

The occupations identifying an exposure coefficient change materially with
both the AI measure and the computerization control.

- Conditional on Webb, α has only **17.4 effective occupations** and its top
  five contributors carry **41.6%** of residual variance. Software Developers
  alone carry 19.6%.
- Under the same Webb control, β has **53.3 effective occupations** and a 22.2%
  top-five share. Its leading comparisons include software developers,
  construction laborers, maids, bookkeeping clerks and freight laborers.
- Conditional on O*NET computer use, α has 31.1 effective occupations; β has
  63.2. β's leading comparisons shift toward retail supervisors, automotive
  technicians, bookkeeping clerks, wholesale sales representatives and truck
  drivers.
- In the separate telework residualization, α's apparent low overlap is fragile:
  14 occupations carry half the residual variation, and dropping major group
  43 moves its R² from 0.091 to 0.010.

Thus “the AI-exposure coefficient” is not generated by a stable common set of
occupational comparisons. The full frozen names and shares are in
[`table2_identifying_variation.md`](outcomes/frozen_v11_corrected_run/reporting/table2_identifying_variation.md).

### Mapping and common support

The four-row crosswalk decomposition separates value correction from sample
composition. All coefficients below are per fixed SD of AIOE and condition on
Webb:

| step | coefficient | 95% CI | p | occupations |
|---|---:|---:|---:|---:|
| original exposure, original support | -0.01885 | [-0.04133, 0.00364] | 0.106 | 410 |
| repaired exposure, same support | -0.01920 | [-0.04213, 0.00373] | 0.119 | 410 |
| repaired exposure, expanded support | -0.03156 | [-0.05616, -0.00697] | 0.008 | 495 |
| expanded support, excluding computer/math | -0.02940 | [-0.05396, -0.00485] | 0.017 | 480 |

Correcting exposure values on unchanged support has essentially no effect.
Re-admitting occupations strengthens the coefficient by about 0.0124 log
points. Excluding computer/math reduces it by only 0.0022 log points. The
mapping consequence is therefore mainly composition, but not mainly a
software-developer story. See
[`table3_mapping_and_common_support.md`](outcomes/frozen_v11_corrected_run/reporting/table3_mapping_and_common_support.md).

### Test C — same design, different X

Every frozen Rule A/B/C headline Q5–Q1 estimate is negative and its wild-
bootstrap confidence interval excludes zero. Across α/β, Webb/O*NET and the
three support rules, coefficients range from **-0.0971 to -0.2085 log points**,
equivalent to approximately **-9.3% to -18.8%**. The primary β × Webb × Rule-A
estimate is **-0.1311** [95% CI `-0.2170, -0.0451`; p = 0.003], approximately a
12.3% relative difference in young-worker employment stock between Q5 and Q1.

All six alternative exposure constructions under the Rule-A/Webb design are
also negative with confidence intervals excluding zero:

- AIOE variants: `-0.0977` to `-0.1176`;
- Eloundou α: `-0.0987`;
- Eloundou β: `-0.1311`;
- Eloundou γ: `-0.1570`.

Alternative computerization controls leave the β estimate negative and
statistically detected, but materially change magnitude: `-0.1001` with
Frey–Osborne, `-0.1277` with RTI, `-0.1512` with O*NET level, and `-0.2085`
with O*NET importance.

The direct frozen paired β-minus-α contrast on common Rule-A/Webb support is:

| object | result |
|---|---:|
| β | -0.13107 |
| α | -0.09868 |
| Δ = β − α | -0.03240 |
| paired SE(Δ) | 0.03697 |
| paired 95% CI | [-0.10235, 0.03755] |
| p | 0.403 |
| common bootstrap draws | 999 |

The CI includes zero. Under the binding rule, the result is: **the frozen
design does not detect a difference between β and α.** It does not establish
economic equivalence. See
[`table4_same_design_different_x.md`](outcomes/frozen_v11_corrected_run/reporting/table4_same_design_different_x.md)
and
[`table4a_headline_q5_q1.md`](outcomes/frozen_v11_corrected_run/reporting/table4a_headline_q5_q1.md).

### Remote work as the core rival mechanism

For β, the per-SD AI coefficient is `-0.03814` alone and `-0.03795` after
adding remotability. In the full AI + Webb + remotability model it is
`-0.03718`. This is negligible attenuation. Remotability is `0.00469` in the
AI-remote model and `0.00606` in the full model; both confidence intervals
include zero.

For α, the AI coefficient moves from `-0.02795` alone to `-0.02376` with
remotability and `-0.02410` in the full model. Those α confidence intervals
include zero. The remotability coefficient changes sign across β and α
specifications and is never precisely estimated. Remote-only is `-0.01884`
[95% CI `-0.04508, 0.00739`; p = 0.154].

The correct inference is coefficient movement: β retains nearly all its
gradient conditional on remotability, while α is less precise and modestly
attenuated. Significance comparisons do not establish that one mechanism
“wins.” See
[`table5_ai_remote_and_post2025_extension.md`](outcomes/frozen_v11_corrected_run/reporting/table5_ai_remote_and_post2025_extension.md).

### Dynamics and falsification

The frozen 2017–2019 placebo is flat: `0.00142` [95% CI `-0.02040, 0.02324`;
p = 0.894]. None of 65 non-reference pre-event monthly coefficients excludes
zero. Six of 43 event/post coefficients exclude zero, in November–December
2023 and April–July 2026. The post-2025 β coefficient is more negative than the
2023–2024 coefficient (`-0.04755` versus `-0.03032` per SD), but the frozen
joint test does not detect the change (difference `-0.01722`; p = 0.127).

The frozen pretrend and timing checks are acceptable; they do not establish a
causal AI shock. The full window is shown in
[`figure1_event_study.png`](outcomes/frozen_v11_corrected_run/reporting/figure1_event_study.png)
and summarized in
[`table6_dynamics_and_placebo.md`](outcomes/frozen_v11_corrected_run/reporting/table6_dynamics_and_placebo.md).

## C. Precision

The outcome-blind headline MDE80 values were 4.53% for α × O*NET, 4.00% for α
× Webb, 5.97% for β × O*NET, and 4.06% for β × Webb. Observed headline
magnitudes are roughly 9%–19%, exceed the relevant 4%–6% MDEs, and have
confidence intervals excluding zero. The CPS design therefore meaningfully
detects the reported employment-stock gradient; these are not underpowered
nulls.

For the paired contrast, the frozen design had 80% power to detect coefficient
differences of approximately **3.27 percentage points** (`0.032722` log points;
3.326% relative magnitude). The observed Δ is `-0.03240`, nearly the ex-ante
log-point MDE, but the realized paired SE is `0.03697` and the 95% CI spans
`-0.10235` to `0.03755`. That interval includes zero and also economically
large differences. The paired result is therefore informative about failure to
detect a difference, but not sufficiently precise for equivalence or strong
downstream-invariance claims.

## D. Interpretation

**State C best describes the evidence.** Test A shows different construct
loadings. Test B shows different, sometimes highly concentrated identifying
occupations. Test C produces a robustly negative employment-stock gradient
under all frozen exposure definitions, but the one direct paired contrast has
a wide realized confidence interval.

What the paper can claim:

- public CPS data show a relative decline in young-worker employment stock in
  more AI-exposed occupations after the frozen January-2023 start;
- the sign and detection of that gradient survive all frozen exposure,
  computerization, support and remotability specifications;
- index construction changes occupational meaning and identifying support;
- naive occupation-code merging changes the estimation sample, and that
  composition change matters more here than repaired values on fixed support;
- the frozen β–α paired design does not detect a coefficient difference.

What it cannot claim:

- AI causally made individual young workers unemployed;
- the stock change is entry rather than exit or occupational switching;
- β and α are economically equivalent;
- remote work or prior computerization has been causally ruled out;
- one exposure index is the uniquely correct measure of AI.

The intended field-boundary contribution is strengthened on the full
measurement chain—construct, identifying occupations, mapping/support and
downstream robustness—but weakened relative to a State-A paper because direct
paired consequence divergence is not detected.

## E. Publication assessment

This is a **strong, defensible third dissertation chapter**. It has a complete
public-data empirical laboratory, credible pre-outcome discipline, a real
mapping/composition result, transparent influence diagnostics, and a robust
negative employment-stock pattern. It is more than a generic robustness note
because it connects how X is built to which occupations identify X and then to
same-design economic estimates.

Its realistic current ceiling is a solid labor/applied-methods field journal.
`Labour Economics`, `ILR Review`, `Economic Inquiry`, or a strong methods/data
outlet are realistic targets after a polished manuscript. `JHR`, `JLE`, or
`Review of Economics and Statistics` are defensible stretch submissions if the
construct and influence audit becomes exceptionally clear. `AEJ: Applied` or
an `AER: Insights`-type claim is not supported by the present State-C paired
result.

The main weakness is not lack of a young-worker pattern; it is that the chapter
remains descriptive and the paired consequence test is much less precise in
realized data than the pre-outcome diagnostic suggested. The strongest
contribution is the integrated chain and the concrete finding that taxonomy
repair matters through re-admitted occupations, while the negative employment-
stock conclusion survives every frozen measurement choice.

Per the handoff, confirmatory work stops here. No exploratory rescue analysis
has been started.
