# Independent P1 reconciliation delta review

Final status after one focused repair/re-review: **BLOCKED_RECONCILIATION/REVIEW**. Remaining corrections are identified in the final addendum below; initial findings are retained as history. Research verdict remains **HOLD_DESIGN + HOLD_DATA**. This review approves no extraction, outcome access, purchase, SCC job, empirical estimator, inference or power result.

Reviewer actual dispatched routing: **gpt-6-astra / high**; usage **NOT_OBSERVED**. The coordinator used supported specialist routing; no separate backend telemetry or token accounting is exposed to this reviewer. This is a separate fresh-context review, without an instruction to favor an architect/coordinator verdict. No nested specialist was launched.

## Scope and independent derivation order

I read both supplied prompts, the complete original DECISION.md, review.md including **Final bounded confirmation**, estimation_contract.yaml and NEXT_ACTION.md, and the architect's mathematical handoff. I derived the restrictions and numerical identities below before opening coordinator reconciliation YAML/code/tests. I then inspected only targeted original plan §§7.1–7.2, BOOTCLUSTER-DECISION.md and blueprint treatment/stack passages. I did not repeat the feasibility audit, inspect actual response values or raw earnings/quotes, access SCC/credentials, or reopen the final resolved iterator guard finding.

Repository checks: branch `task/p1-feasibility-adjudication-20260913`, HEAD `35361cc5a8c6360e1d48da9a2aa4fd40458b0e04`; status `?? p1/feasibility_adjudication/`. Repository `rg --files -g AGENTS.md` returned no match (exit 1); this is not a test failure. Writes by this role are restricted to this review. Historical files and existing uncommitted work are preserved.

### Identification

Suppress wave notation. Let `b^0_gph` be the conversion-absent standardized SUE slope and `b^1_g1h` the post slope under the actual conversion package, on fixed PRE group populations and an explicitly defined calendar/covariate standardization. With no pre-announcement treatment, define `tau_gh=b^1_g1h-b^0_g1h`. The observed slope DID satisfies

`delta_h = tau_Hh - tau_Lh + [(b^0_H1h-b^0_H0h)-(b^0_L1h-b^0_L0h)]`.

Thus parallel **counterfactual SUE-slope changes**, not mean-return trends, identify the difference between the group-specific package effects. This does not identify either group's effect separately, a common ownership-dose increment, an untreated comparison, or AP arbitrage. Binning positive doses cannot remove selection on gains. Comparable surprise measurement, overlap/standardization, no differential selection and the stipulated exposure/spillover mapping remain substantive assumptions. A shock proportional to SUE × Post × high exposure survives additive stock/fund effects. A conversion-induced change in analyst forecasts changes the measured-surprise slope even if latent-news price incorporation does not change.

For the supplementary normalized object let `F^a_gph=b^a_gph/b^a_gpT`, wherever the required denominators support that operation. Its observed DID equals the difference between causal normalized-shape changes only if

`F^0_H1h-F^0_H0h = F^0_L1h-F^0_L0h`.

Raw-slope parallel trends do not imply this ratio restriction. A stronger group-specific no-conversion stationarity/transport condition `b^0_g1h=b_g0h` would identify both group-specific changes, but is not supplied by low-dose observations. Relative shape can improve because low slows while high stays unchanged; high-group acceleration needs its own directional causal shape change.

### Equal-wave influence and economic-event reuse

For each wave write `Q_w=diag(sqrt(weight))`, `R_w=M_(Q_w X_w)Q_w Z_w`, and `B_w=(R_w'R_w)^-1 R_w'Q_w`. A contrast influence is `c'B_w`. Let `J_w` map unique economic earnings outcomes to rows in that stack. Then

`a_h = W^-1 sum_w c'B_wh J_w`, and `Cov(theta_h,theta_k)=a_h Omega_hk a_k'`.

This includes every cross-wave and cross-horizon term. A duplicated event receives the sum of its row influences; it is never a fresh shock. In a scalar pooled regression the weights are proportional to residualized information `R_w'R_w`, even when every wave has equal total row weight.

Independent exact-fraction/Python reproduction, without importing coordinator code: heterogeneous-baseline raw DID `(0.08,0)`, normalized DID `(0,0)`; pooled residual-dose coefficient `0.9`, equal-wave target and explicit separate-wave influence result `0.5`; reused event variance `1`, erroneous independent-row variance `0.5`. All assertions exited 0.

### Amplitude and estimated reference

The supplied high slopes `(0.8,1) -> (0.96,1.2)` and low slopes `(0.4,1) -> (0.48,1.2)` each undergo positive proportional amplitude growth. Each group's normalized curve is unchanged. Nevertheless raw DID is `(0.08,0)`, so any common-reference `delta_h-f_h delta_T` equals `0.08` early. It cannot establish timing. Group-specific normalization passes this algebraic counterexample but changes the estimand and requires the separate causal restriction above.

For an estimated common-reference contrast `q=beta_e-f beta_T`, the gradient with respect to `(beta_e,beta_T,f)` is `(1,-f,-beta_T)`. With `f=.5`, `beta_T=.2`, variances `(.01,.01,.04)`, the plug-in-reference variance is `.0125`; joint variance is `.0141`; adding `Cov(beta_e,f)=.005` changes it to `.0121`. These positive-semidefinite covariance examples were independently executed, exit 0. Reference uncertainty can increase or decrease total variance through covariance; it cannot be omitted. For a ratio `b_h/b_T`, the gradient is `(1/b_T,-b_h/b_T^2)` when a regular approximation is justified. Near zero, joint confidence-set inversion/projection is needed, with a zero-containing denominator set treated as a failure of the normalized interpretation. No weak-wave trimming or precisely known normalizer is justified. A confidently negative terminal slope also needs a distinct sign interpretation; it cannot silently be called a positive completion fraction.

The estimated margin `0.05 B*` requires joint inference for the terminal effects and PRE calibration defining `B*`. Freezing the translation algorithm is not the same as knowing its numerical value without uncertainty.

### Inference dependence

The relevant shock unit is the unique earnings event. Stock serial dependence, economic sponsor/wave shocks, overlap in every response-leg date, reused stack outcomes, and cross-horizon/reference dependence all matter. A graph connecting every event pair sharing one of the declared dependence sources, followed by connected-component score aggregation, contains all such dependence within components. One common multiplier per component then preserves these stipulated links. This is a coherent conservative **amendment** to the signed sponsor/stock method, conditional on independence across components; it is not proof of bootstrap coverage. All signed sponsor memberships and all response-leg dates, including +1d, must enter. Transitive connections may produce one component, in which case confirmatory inference remains blocked. No raw sponsor count, inverse-HHI cutoff, or generic phrase about sufficient information supplies a validity result.

## Recommendation assessment and required initial corrections

Initial coordinator YAML locators refer to SHA-256 `19953536d9f16455a87e1cf7146da9ecf2da5b8c67103f6deab1a46ca69c7403`. Architect locators refer to handoff hash `fcc00389eba24fcf2cdd75c62c269d26bc26adcdf7fab645e112908f60942788`.

| Recommendation | Independent assessment / exact correction |
|---|---|
| Positive PRE terciles and clock | Coherent differential package proposal, PI pending. Architect lines 7–11 correctly distinguish ownership as-of from publication, omit transition and require a complete competing-conversion calendar. Historical 8,801/30 support must not carry over. |
| RTH primary rule | Coherent PI amendment to original plan §7.1.1's metadata-driven scope decision. Architect line 15 specifies ≥60 minutes and no fallback; YAML 72–74 still refers to an undefined signed feasibility criterion. Specify open-inclusive/close-exclusive boundaries, common mask, group support and required identified design; otherwise NOT_ESTIMABLE. |
| SUE rule | Coherent proposed measured-news unit, PI pending; 90 days/median/≥2 analysts and fixed PRE price/unique-event SD are new choices. Exact licensed field semantics, calibration population and coverage/measurement invariance remain unverified. Stock-level unique scaling avoids changing SUE when an event is reused. It does not establish latent-news invariance. |
| Slope standardization | YAML 84–86 and architect line 13 need precision. PRE/POST calendar support is disjoint: define common high/low calendar weights **within each period**, fixed group-specific PRE stock weights, and any model extrapolation/support requirement. State which fitted common calendar slopes enter each `b_gph`; ratios depend on these levels. |
| Supplementary normalized DID | Coherent supplementary estimand with stronger assumptions, PI pending. YAML 99–109 should preserve architect line 19's precise early-direction rule and distinguish high acceleration from improvement relative to low. Weak or nonpositive required terminal references must block positive-completion timing language. |
| Pure timing | Correctly BLOCKED. Differential terminal equivalence alone is insufficient. Both group-specific terminal package effects and a directional shape claim need identification and joint equivalence; finite +1d never means fundamental value. |
| Shape/terminal margins | Coherent calibration-dependent proposal, economic magnitude PI pending. YAML 113 must explicitly propagate `B*` uncertainty/covariance. The five-point choice represents the recommended economic tolerance, not a sourced universal constant or an empirical power result. |
| Component inference | Coherent conservative amendment, PI pending, empirical inference BLOCKED. YAML 122–123 must include every sponsor membership and every response date, state across-component independence, and retain a block until a signed design-validity protocol resolves leverage/support; no undefined criterion may authorize inference. |
| Authority/extraction | Five initial YAML approval flags are actually false. However YAML 131 wrongly asks that **all** approvals be true for extraction, including SCC/purchase/outcome access. Require purpose-scoped approval and verified owner/hash/view authority instead. Draft status must deny extraction regardless of edited booleans. |

Initial deterministic suite: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider p1/feasibility_adjudication/20260913/reconciliation/tests/test_contract_counterexamples.py` exited 0, **5 passed**. That result did not meet all mandatory checks:

- Initial code lines 38–46 computed only PRE normalization and hardcoded a classification string; tests 16–22 did not compute POST normalized curves or normalized DID. Calculate and test them.
- Initial code lines 70–76 and tests 37–39 labeled reference states but did not calculate reference uncertainty/covariance. Add a deterministic joint-gradient variance check, including a covariance perturbation and weak/nonfinite failures.
- Initial code lines 79–84 and tests 42–44 did not read the actual YAML or evaluate extraction. `{}`, nested `approved: true`, and string `"true"` all returned `PASS_PENDING_PI_APPROVAL` in independent challenges. This is a draft lint label, not an authorization gate. Require nonempty exact-boolean approvals and test actual YAML; separately deny draft extraction unconditionally. The initial test name overstates its coverage.

Initial implementation hashes: code `4cfa163668a62ea4d73d2000b3952c588f44281beea3619b99dfea7df906a6c0`; tests `c5e7f7732e4e085ab522c4dd289698b19be943ad54775c969545796c29ca9a2a`. Coordinator received these corrections for one focused repair cycle. The original feasibility guards are not challenged by these new reconciliation-only findings.

## Source and execution receipts

Original source SHA-256: DECISION `ddf992a968168a7da0a60551430616db9b0565b2a13a58a5f3236e69a8bda908`; full review `ccef6fab1348efae406b6187b268b33f18c4a49ecc9d45b698964fb8fa0e2ac2`; original contract `6704be74ff67b72308b4e823892a493549ec5ea128a23caa82d4b8a2d189b6f5`; NEXT_ACTION `a4ed49a973db0fa43fd077157c45db4bb50276a268f5924451af70ce19dddc31`. `shasum -a 256` exited 0. Reads via `cat`, `sed`, `nl`, `wc` exited 0; an initially combined git/AGENTS inventory exited 1 solely for no AGENTS match. Initial tests and independent arithmetic/challenge commands each exited 0; deliberately demonstrated test inadequacies are recorded above rather than disguised as passes.

No empirical power, real estimator rank, signed economic grouping, protected-view content, sponsor bootstrap coverage, quote/earnings measurement or causal identification was verified. The original final bounded guard signoff remains intact. A repaired draft may become READY_FOR_PI_REVIEW without changing these research holds or authorizing the next extract.

## Final focused re-review — 2026-09-13

This is the **one permitted repair/re-review cycle**, confined to revised passages and the revised deterministic suite. Final reviewer routing remains **gpt-6-astra / high**, usage **NOT_OBSERVED**. Coordinator-supplied revised hashes independently matched, `shasum` exit 0:

| Artifact | Reviewed SHA-256 |
|---|---|
| Proposed YAML | `f1b4982ae5530a4cf0b6813264655a98ad12a8dfd5abf60a90f7f854da5cdb6d` |
| Deterministic code | `0494649d2eeca1f621f66ddffe74a12f1102a8ff262325fe5c0f9cf486b3ef9c` |
| Tests | `dad87e3013b7b7e6af073a51a4f3eaa7142d69540e464d706222c09bf2cc3171` |
| TIMING_COUNTEREXAMPLES.md | `5956a665863a1fe018a5ff9ac24f4279389f72e509a1614ebeebb4c33e7debe8` |

I reran the same focused pytest command: **exit 0, 6 passed**. The revised heterogeneous-baseline calculation now computes both POST normalized curves and `kappa`, and the test verifies its zero value (code 41–45; tests 20–23). The estimated-reference check now executes the ratio-gradient covariance calculation (code 86–94; tests 43–45): joint variances `.0464` with zero covariance and `.0344` with positive covariance. This passes the required deterministic demonstration that reference covariance matters; it is not a validated nonlinear-ratio inference engine. Independent A/B/C derivations above remain unchanged.

I parsed the actual YAML and independently asserted that **all five `pi_approval` values are exact booleans and false**. Its unchanged proposal status denies metadata extraction. The revised YAML correctly separates metadata approval from SCC, purchase and outcome permissions (132–134). RTH session bounds/support/rank are now explicit (74); estimated `B*` uncertainty is explicit (114–115); component membership includes all sponsor memberships and all response-leg dates (123–124); component validity, H3 and pure timing remain blocked; high-group acceleration now requires its own causal shape change (109–110). Those corrections are accepted within this review's scope.

The following concrete issues remain. They were reported to the coordinator; no further review cycle is claimed.

1. **An editable label still substitutes for authority in the helper.** Code 97–104 returns `PASS_METADATA_EXTRACT_ONLY` when a mapping contains `document_status: PI_APPROVED` and two true booleans. It verifies no owner record, signed contract hash or authorized view, although YAML 132 requires all three. In an independent in-memory challenge I copied the actual proposed YAML, changed only the status and these two booleans, and received `PASS_METADATA_EXTRACT_ONLY`. No source file was edited and no extraction was attempted. Tests 51–53 positively expect this inadequate pass. The actual unmodified proposal remains denied, but this function cannot establish that a draft cannot self-authorize by changing its own fields. **Exact correction:** keep every extraction result non-authorizing until separate owner/hash/view verification exists—e.g. return an explicit `AUTHORITY_VERIFICATION_REQUIRED` for the hypothetical approved mapping—or label this only a scope-lint fixture and remove authorization-pass claims. TIMING_COUNTEREXAMPLES.md:43 must reflect that limitation. An executable extraction gate is outside this bounded task; honest unimplemented status is sufficient, but a simulated approval must not masquerade as one.

2. **Standardized slope levels are not fully reproducible.** YAML 86 now correctly avoids identical PRE/POST calendar support, but still says “common high/low calendar-cell mix” and “fixed group-specific PRE stock weights” without assigning those weights or defining the fitted slope functional. Different pooled-event, equal-calendar-cell and equal-stock choices change `b_gph`, its ratio and the causal target. **Exact correction:** specify a numerical weighting formula and support rule for the joint PRE-stock × period-calendar reference distribution, state the derivative/linear contrast of the fitted response model used for `b_gph`, and include the applicable fitted period/calendar SUE slopes in that functional. This is a finite contract choice; it must be settled before signing the estimand, not selected using results. The proposed no-extrapolation restriction must remain explicit.

3. **The directional shape decision is still qualitative in the executable draft.** YAML 107 retains “A directional meaningful early relative-shape change is identified.” Architect handoff 19 is more precise. **Exact correction:** name the equal-wave early components at 5m/15m/30m/60m; require the declared joint confidence region to support nonnegative components and their equal-weight mean exceeding the approved `.05` margin, together with the stated group-terminal equivalence conditions. Keep this as an observed-horizon relative-timing statement; high-group acceleration additionally requires its own positive causal shape change. A PI should not have to infer the sign/averaging rule from a specialist handoff.

4. **One reference-uncertainty sentence is mathematically false.** TIMING_COUNTEREXAMPLES.md:39 says treating a fitted reference as fixed “understates uncertainty.” Its own revised example yields `.0344` versus fixed-reference `.04`, whereas zero covariance yields `.0464`. **Exact correction:** say it “misstates uncertainty; the direction depends on covariance.” My independent three-parameter example above likewise exhibits both directions.

Additional bounded limitation: the scalar reference-state fixture (code 77–83) does not reject nonfinite arguments; `reference_failure_state(NaN,.1)` returns the generic joint-propagation label. The ratio-variance helper also lacks general finite/PSD covariance validation. These functions demonstrate the stated finite synthetic examples only. They must not be represented or reused as production weak-reference eligibility/inference validators without appropriate checks. This does not reopen any previously repaired feasibility guard.

**Final disposition: BLOCKED_RECONCILIATION/REVIEW.** The recommended high/low package estimand, PRE-announcement clock, RTH target, SUE rule, equal-wave aggregation, supplementary group-normalized shape object, calibration-dependent margins and conservative component amendment are conditionally coherent **PI-pending proposals**, subject to the exact outstanding specification corrections above. There is no scientific disagreement requiring an empirical test to settle them. The numerical counterexamples now pass within their finite synthetic scope. The draft remains unsigned, and approval/extraction enforcement is not implemented. Signing would settle the chosen question and algorithms; it would not establish counterfactual restrictions, realized eligibility, H3, measurement validity, sponsor/component support, empirical inference/power, or permission to open treatment responses. No completed independent signoff is claimed for any later unreviewed edit.

**Subsequent coordinator report, not re-reviewed:** after this cycle, the coordinator reported mechanical corrections to the external-authority status, explicit standardization weights/slopes, explicit directional condition and covariance wording. I did not inspect or execute those later versions, honoring the one-cycle limit. Findings and line locators above apply to the exact reviewed hashes, not assertions about the later unreviewed contents. Final review status remains **BLOCKED_RECONCILIATION/REVIEW** because independent verification of that final delta is outside the permitted cycle; this is a review-completion limitation, not a claim that the coordinator's reported corrections failed.
