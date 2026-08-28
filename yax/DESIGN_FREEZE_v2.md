# Design freeze v1.1

**Written 2026-08-29 before any protected post-period YAX outcome was opened.**

This document consolidates the live YAX design defined by
`RESEARCH_PLAN_v5.md`, `FREEZE_AMENDMENT_2026-08-27.md`, and
`FREEZE_AMENDMENT_2026-08-29_PAIRED_PRECISION.md`. The tag it supports is
`v1.1-design-freeze`. The original `v1.0-design-freeze` tag and
`DESIGN_FREEZE_v1.md` remain unchanged.

This is a git-verifiable design freeze, not a registration in an external
registry. The chapter must not call it a preregistration.

**Question.** Holding the CPS sample, support, estimator and inference fixed,
do alternative definitions of occupational AI exposure identify different
occupations and produce distinguishable young-relative employment estimates
after conditioning on pre-existing computerization?

## 1. Estimand and estimating equation

The primary outcome is the employment stock `N_oat` in occupation `o`, age group
`a`, and month `t`. Young workers are ages 22–25; the comparison group is pooled
ages 26–65.

    E[N_oat] = exp[gamma_oa + delta_ot + lambda_at
                    + beta_AI (AI_o x Young_a x Post_t)
                    + beta_C  (Comp_o x Young_a x Post_t)]

The model is PPML on occupation × age-group × month counts, with occupation ×
age-group, occupation × month, and age-group × month fixed effects. The primary
unit is the cell, not the individual. A non-employed person is never assigned an
occupation or exposure.

- **Static post:** 2023-01 through 2026-07.
- **Transition:** 2022-12 is excluded from the static post coefficient and is
  retained only as the first event-study exposure month.
- **Known gap:** 2025-10 is excluded.
- **Clustering:** occupation.
- **Primary inference:** occupation-cluster Rademacher wild bootstrap with at
  least 999 draws. Analytic cluster-robust standard errors are secondary.
- **Interpretive limit:** a cell-stock decline can represent reduced entry,
  employment exit, or occupational switching. It is not automatically an
  individual employment-probability effect.

## 2. Exposure, computerization and coverage

Eloundou GPT-4 β (`E1 + 0.5 E2`) is the primary AI exposure. Eloundou GPT-4 α
(`E1`) is the frozen contrast and is not promoted based on its correlation or
precision.

Webb software-patent exposure is the primary computerization control. O*NET
*Interacting With Computers* importance is the first robustness control. O*NET
level, Autor–Dorn RTI, and Frey–Osborne automation probability remain required
reported alternatives; AIOE is never used as a computerization control.

The live coverage decision is `COVERAGE_RULE_PRESPEC_v2.md`:

- **Rule A — strict, PRIMARY:** every component must be exposure-scored;
  88.70% of eligible employment.
- **Rule B — sibling-imputed:** `s_c >= 0.95`.
- **Rule C — scored-component renormalized:** `s_c >= 0.95`.

Rules B and C remain reported columns. The failed 90% gate and Rule B primary in
v1 are preserved and disclosed; neither is rewritten as if it had not occurred.

## 3. Measurement tests

- **Test A — construct divergence:** compare rankings and conceptual content
  across exposure measures.
- **Test B — identifying-variation divergence:** report residual variance,
  effective occupations, occupational-family concentration, and named
  occupations that identify each coefficient.
- **Test C — consequence divergence:** estimate the direct paired difference
  `Delta_(m,m') = beta_m - beta_m'` on pairwise common support, changing only
  the exposure definition.

For Test C, the same bootstrap draw is applied to β and α and `Delta` is formed
within draw. This preserves

    Var(Delta) = Var(beta_m) + Var(beta_m') - 2 Cov(beta_m, beta_m').

The paired 95% CI uses the originally specified percentile-t
occupation-cluster bootstrap with at least 999 common draws. The 0.023430
outcome-blind null critical half-width belongs to the power calculation and is
not substituted for the eventual outcome CI.

Binding interpretation:

- CI excludes zero: the downstream estimates are statistically distinguishable
  across the frozen exposure definitions; report the magnitude.
- CI includes zero: the design does not detect a difference.
- Under neither branch may the paper claim economic equivalence.

The originally signed SESOI rule could not be instantiated because no verified
published estimate matches the YAX age groups, employment-stock estimand,
Q5–Q1 contrast and scale. Numerical SESOI, equivalence interval and equivalence
power are retired rather than replaced. The sign-off, benchmark audit and
blocked v1 paired artifact remain permanent pre-outcome records.

## 4. Outcome-blind precision

All simulations use only the sealed 2017-01–2022-11 cells and create synthetic
post months from pre-period donors. Every retained artifact records
`post_outcomes_read: false`.

### 4.1 Joint AI–computerization Q5–Q1 power

`Q5–Q1` is defined by employment-weighted exposure quintiles on each scenario's
estimation support, with tied scores kept together and Q2–Q4 separately
absorbed. The computerization effect is fixed at `log(0.95)` per weighted SD as
an outcome-blind design stress parameter.

| AI exposure | computerization control | clusters | partial variance | effective occupations | null size | MDE80 | 95% MC interval |
|---|---|---:|---:|---:|---:|---:|---:|
| α | O*NET computer importance | 465 | 0.908 | 31.1 | 0.038 | 4.53% | 4.44%–4.61% |
| α | Webb software | 468 | 0.983 | 17.4 | 0.038 | 4.00% | 3.91%–4.09% |
| β | O*NET computer importance | 465 | 0.365 | 63.2 | 0.049 | 5.97% | 5.78%–6.12% |
| β | Webb software | 468 | 0.997 | 53.3 | 0.038 | 4.06% | 3.98%–4.14% |

The four scenarios must pass both the gradient and calibration gates. These
Q5–Q1 results supersede the January-window per-SD artifacts for the binding MDE
comparison; the per-SD artifacts remain preserved as a distinct diagnostic and
must not be relabelled Q5–Q1.

### 4.2 Paired-difference precision

The frozen β-versus-α common-support run used 468 occupations and 999 common
draws with zero failures:

| quantity | result |
|---|---:|
| paired `SE(Delta)` | 0.011672 log points |
| paired β/α covariance | 0.00009467 |
| outcome-blind 95% null critical half-width for power | 0.023430 log points |
| `MDE_(Delta,80)` | 0.032722 log points |
| relative magnitude | 3.326% |

The permitted ex-ante statement is:

> The frozen paired design had 80% power to detect coefficient differences of
> approximately 3.27 percentage points.

This is a difference-detection precision statement, not evidence of economic
equivalence.

## 5. Frozen data and artifact hashes

### 5.1 Private sealed input

| artifact | SHA-256 |
|---|---|
| pre-period occupation × age-group × month cells | `4b8c8b96caeebc4121ad4914adbadf7ebfa98d677a80b32b78a9f905956ea800` |
| private cells receipt | `60ef90f11186fd0e6e8159099bcbd2d31c41d72652ecf54484884cd4c24dce70` |

The cells contain 490 balanced Census-2018 occupation clusters × 66 months,
2017-01 through 2022-11. Licensed person-level microdata remain outside git.

    4b8c8b96caeebc4121ad4914adbadf7ebfa98d677a80b32b78a9f905956ea800

### 5.2 Measurement inputs and receipts

| artifact | SHA-256 |
|---|---|
| `CPS_OCCUPATION_EXPOSURE_LOOKUP.csv` | `c6eb70623ea598bfc41f2352391add7a342a8809a4e57b02f2af0e75dd0223f8` |
| exposure-lookup receipt | `a06f5618cf1e9a6872913818faad911145a76b1fcb143b1ca4a5d939ebd73e8a` |
| `COMPUTERIZATION_MEASURES_CENSUS2018.csv` | `352cb40834ec83225f747d316eb3e03fce1d1c5c65d80720c558177f85801fdd` |
| computerization-measures receipt | `f7b34814bc78e3626218c0db213871c303667421d8764f1d49aff817f15615da` |
| 66-month computerization-support receipt | `196de768f28dc4c2f9637a06633de218e8fd0a18c059107a145cfdb58d144c33` |
| construct-validity receipt | `3efaf00ae9c8305d4098cf71aa59c4ec765102732501bdfe96b81e668fb06ec1` |
| crosswalk-gate receipt | `86ccc16ff370805868d2d7e993ea38de12ee94ecb466d702c2614d1082d5c985` |
| Census-2018 exposure variants | `3c8c1d26b73414cf1c173a264bcc0446e8b8ffca5c412f5f63edc5fe2eb2552a` |
| Census 2010→2018 bridge | `0bd2f63c72e24bed2cc1cb414395c3cbddf7c00011e47ec1c1de6ae534fd1dcc` |

### 5.3 Power artifacts

| Q5–Q1 artifact | SHA-256 |
|---|---|
| joint aggregate v3 | `198ba9203019dfe69e9fd117e295ff4b9ab2be663ed90e63e641ba53e0c1eb28` |
| α × O*NET scenario | `6aec07d9e3c87133ee8aa265d428d69e540fe02d1bb5175430a5f3d9d17807bc` |
| α × Webb scenario | `78adfc86c213b7a7926d27f6895e5a7b67ef9c1946213c047cb1e661cf5da930` |
| β × O*NET scenario | `e0a1632738c385f36d97ea48b0209d9ad4c81ad9a57f800058b79a86f1fb5cec` |
| β × Webb scenario | `0444277942d1b4db1d54a11d4df1a3317797eab663307a1870e890066db596de` |
| Q5–Q1 power note | `8d72c6d684cd5997115c4517ffa4ffa36f362d02cd797dd5fae19dea96b9f344` |
| SCC log, α × O*NET (job 7348589) | `b5e6d31a815e31194aea0e142798e1b75848bc61d05917345d8c01ad16024419` |
| SCC log, α × Webb (job 7348591) | `2465412607b92ea1dc78d9e00784d13f145fd75955cb64e867391d613b88b2ce` |
| SCC log, β × O*NET (job 7348586) | `77f67b7bf4de1b574d7eec2613deaef621769a0c94363e4aa78145b82cd03a61` |
| SCC log, β × Webb (job 7348587) | `cdb1bd83e142b04d70188ec23cd42c18d2768483c746ba823be19243d1d7b82d` |

| artifact | SHA-256 |
|---|---|
| original blocked paired-equivalence artifact | `4898f452f1368796d141f142ecbc88e6963b2ec273ed47446adaa0934908df5e` |
| amended paired-difference precision receipt | `2a756a8ea8e09fc515f64aee7a3ab57f020eb0cb1a0451ce38242b73c5aae7aa` |

### 5.4 Literature and amendment record

| artifact | SHA-256 |
|---|---|
| novelty audit | `40394475d72af95f288da04d3c17244d41bf7cc0f99cd34a0d461e742f3c0b8c` |
| novelty audit receipt | `c6f71afbd56761129778df40b1fb135e0ff311c7c19b4534fc3dd2d748c59a27` |
| published-measurement audit | `93d7eac6b3a2a53f6dc69a9ebab1720bdcdbd9bea4d265864dcc7deaea849c6a` |
| benchmark-alignment audit | `86aa9fc84eae1c1050f1522f128f35a9377269847c885247fa46455fe44b0b6f` |
| benchmark-alignment receipt | `4cbf5fe771a089574d0081289e7e0625baa05c1a96f095b9e4e5a067315c9c90` |
| coverage-rule v2 record | `d2323f6e35d85a2647111f27cd52d9ec5fe1bdadb00ad17e2b60d158ea78b1d8` |
| 2026-08-27 amendment | `4a7822b3b7e6f2a4ddf2205ab1babcdb791a6f3743ddd59bcc3d891bf15b3289` |
| 2026-08-29 paired-precision amendment | `173ddbbcf8c35ef9886d116467822a1a7898c94db800c76f9d3974f8c5f71e4a` |
| original SESOI owner sign-off | `c081faa81c631365ac756007ac517d19d25bab9064183d6bbb066a071ad59c89` |
| research plan v5 | `ec6478bf1e85a431501dca54e78bd160a5330890dd0e02c235e52601422eab93` |

## 6. Novelty boundary

The verified novelty audit remains PASS. YAX does not claim novelty for
comparing exposure measures, harmonising occupation codes, documenting
measurement error, or finding young-worker CPS patterns. The retained claim is
the joint construct → identifying-occupation → mapping/common-support → paired
downstream chain under one frozen public-data design. The closest predecessors
and retired claims remain named in the audit.

## 7. Differences from `DESIGN_FREEZE_v1.md`

| element | v1.0 | v1.1 |
|---|---|---|
| static post start | 2022-12 | 2023-01; 2022-12 transition excluded |
| coverage primary | Rule B sibling-imputed | Rule A strict, 88.70% support |
| headline power contrast | per weighted SD | binding literature-comparable Q5–Q1 also computed |
| Test C feasibility | binding equivalence rule awaiting SESOI | paired-difference precision; equivalence inference retired |
| Test C interpretation | equivalence possible only under SESOI rule | CI excludes zero = distinguishable; CI includes zero = no detected difference; never equivalence |
| novelty claim | earlier broader boundary | narrowed after latest-version audit |

No other estimator, age group, outcome, exposure ordering, computerization
control, fixed effect, clustering rule or table family changes.

## 8. Empty table shells

The first protected-outcome execution after the tag fills these shells. No cell
below contains an outcome estimate at freeze time.

### Table 1 — Construct and identifying-support diagnostics

| exposure | computerization control | correlation | VIF | partial variance | effective occupations | named top contributors |
|---|---|---:|---:|---:|---:|---|
|  |  |  |  |  |  |  |

### Table 2 — Joint AI–computerization employment estimates

| | β Rule A | β Rule B | β Rule C | α Rule A | α Rule B | α Rule C |
|---|---:|---:|---:|---:|---:|---:|
| AI × Young × Post |  |  |  |  |  |  |
| Computerization × Young × Post |  |  |  |  |  |  |
| wild-bootstrap p-value |  |  |  |  |  |  |
| occupations |  |  |  |  |  |  |

### Table 3 — Event study and pre-period placebos

| event month | coefficient | 95% CI | placebo indicator |
|---|---:|---:|---|
|  |  |  |  |

### Table 4 — Alternative exposure definitions on common support

| exposure pair | coefficient under m | coefficient under m' | paired Delta | paired 95% CI | detected difference? |
|---|---:|---:|---:|---:|---|
|  |  |  |  |  |  |

### Table 5 — Crosswalk decomposition

| row | exposure mapping | support | computer/math included? | coefficient | 95% CI |
|---|---|---|---|---:|---:|
| 1 | original | original | as published |  |  |
| 2 | repaired | original | as published |  |  |
| 3 | repaired | expanded | yes |  |  |
| 4 | repaired | expanded | no |  |  |

### Table 6 — Remote-work and post-2025 robustness

| specification | AI coefficient | computerization coefficient | remote-work coefficient | post-2025 Wald test |
|---|---:|---:|---:|---:|
|  |  |  |  |  |

## 9. Environment, tests and seal

- SCC worktree: `/projectnb/econdept/qluo/yax-freeze-v11-20260829`
- Python 3.13.8; pytest 9.1.1; pandas 3.0.3; NumPy 2.5.1.
- Full-suite freeze-candidate result: 769 passed, 3 skipped, 13 warnings.
- The tag is accepted only after the same full suite and every gate are rerun
  from the tagged state.
- The three skips are optional non-YAX dependency paths already disclosed in
  v1: PyTorch, scikit-learn and cryptography dependent modules.
- Joint Q5–Q1 simulation seed: 20260829; 999 repetitions per effect, 999
  calibration draws and 999 MDE interval draws per scenario.
- Paired simulation seed: 20260828; 999 common draws, zero failures.
- `git ls-files yax/analysis/outcomes dax/analysis/outcomes` returned no files.

The freeze is valid only when every gate passes from the tagged state and the
remote branch and annotated `v1.1-design-freeze` tag resolve to the same commit.
Protected post-period outcomes remain unopened until then.
