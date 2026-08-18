# W1 v2 adversarial PRE-review — 2026-08-18

```
STATUS: SELF_REVIEW_NOT_INDEPENDENT
SATISFIES_META_RULE_2: NO
COUNTS_AS_GATE1_RED_TEAM_EVIDENCE: NO
VERDICT: none issued — a self-review may not issue CONDITIONAL_GO
```

**Read this first.** This is the author of the v2 rewrite attacking their own
work. It is *not* the independent cross-vendor red team, it does not satisfy
meta-rule 2, and it must never be counted as the Gate-1 review item. The
corresponding checklist line in `PI_DECISIONS_OPEN.md` stays unchecked.

A genuine pass was attempted twice this session and is impossible here: no
vendor API key exists in the environment (`ops/box/.env` is box-only and the
box has been down since 2026-07-10), and `api.deepseek.com`,
`dashscope.aliyuncs.com` and `api.moonshot.cn` are all unreachable through the
sandbox egress policy. `run_deepseek_red_team.py` has been updated with the v2
packet and prompt and will fire unchanged once a key and egress exist.

Its value is narrow but real: the paid cross-vendor pass should not be spent
rediscovering things the author could find alone.

---

## M1 — The pre-trend diagnostic is not computable. **Blocker. FIXED 2026-08-18.**

`[PI-DECISION 14]` requires "a joint test of pre-event dose coefficients over
2021-11 to 2023-02". Under the continuous design the regressor is cumulative
`DAX_ot`, which is **identically zero for every occupation** across that entire
window — the first event is 2023-03. Verified:

```
pre-event window: 2021-11-01 -> 2023-02-01 (16 months)
dose variance across occupations in the pre-event window: 0.0
all-zero pre-event dose: True
```

A regressor with zero variance has no coefficient. The headline identification
check of the amended memo cannot be run as written, and §9.3 lists it as
required. This is the same class of error the 2026-08-14 audit found in the
original draft — a rule stated in prose that does not survive contact with the
data it governs — reintroduced by the rewrite that was fixing it.

**Required change.** The pre-trend test must be re-specified as a *placebo
lead*: regress pre-period outcome changes on each occupation's **eventual**
dose (for example cumulative DAX at 2024-12), with the same controls. That
regressor does vary in the pre-period because it is a fixed occupation
characteristic, and a non-zero coefficient is exactly the violation of interest
— occupations destined for high exposure already trending differently. §9.3 and
Decision 14 both need rewriting; the current text is unimplementable.

**Resolution.** Decision 14 now specifies a placebo lead on eventual exposure
`D_o = DAX_o,2024-12` interacted with time, restricted to pre-event months.
`placebo_lead_design` computes it and reports its variance rather than
asserting estimability: 0.058, 0.196 and 0.588 at the 2023-12 / 2024-12 /
2025-12 horizons, against exactly 0.0 for the superseded form. Horizons are
frozen in advance so `D_o` cannot be chosen after seeing a result. Three tests
pin both the defect and the fix.

## M2 — The D3 benchmark conflates payroll with employment. **Major.**

D3 sets `ceiling = 0.5 x 0.13 x baseline_employment_rate` and sources the 0.13
from "the young-worker employment/payroll decline in the proposal". §7.1 of the
amended memo separately describes it as a "13% **payroll** benchmark".

Payroll is employment x hours x wage. A 13% payroll decline is not a 13%
employment decline, and the three margins can move in opposite directions. The
frozen constant therefore rests on an ambiguity, and because it is *frozen*,
the ambiguity gets locked in at the moment the standard is filled.

**Required change.** Resolve which quantity the proposal's 0.13 refers to,
citing the page, before `freeze_power_standard.py` is run. If it is payroll,
either decompose it into an employment-margin equivalent with a stated
assumption, or define the standard against a payroll-equivalent outcome. Do
not freeze the constant until this is settled — freezing is one-way.

## M3 — The frozen entry mix is unlikely to be estimable. **Major.**

§7.2 freezes `pi_go`, the probability an entrant in cell `g` first appears in
occupation `o`, from 16 months of pre-event CPS. Order of magnitude: the monthly
CPS yields on the order of 5,000 persons aged 22-25; entrants are a minority of
those; across 16 months and then split across demographic-education cells and
several hundred occupations, the per-(cell, occupation) count plausibly falls to
single digits.

`pi_go` is then a multinomial proportion estimated on a handful of observations,
and `EDAX_gt = sum_o pi_go * DAX_ot` inherits that noise directly into the
regressor. §7.2 waves at this — "measured with error and bounded by the same
EIV machinery as the primary" — but §10.1's EIV module is calibrated for
*mapping* error from human-disagreement distributions, not for sampling error
in a sparse multinomial. The stated mitigation does not cover the stated
problem.

**Required change.** Compute the realised per-cell entrant counts from the
frozen extract *before* committing to the companion, and pre-register a minimum
cell count below which occupations are pooled into major groups. If pooling to
2-digit SOC is required for adequate counts, say so now, because it materially
weakens the companion's exposure variation and that should be visible before
the design is registered rather than discovered afterwards.

## M4 — The "entrant" sample is contaminated by linkage failure. **Major.**

§7.2 defines entrants as the complement of the primary sample: persons with no
valid occupation observation in the lookback window. That set contains at
least three distinct populations:

1. genuine labour-market entrants;
2. persons whose earlier interviews exist but failed to link on `CPSIDP`;
3. persons with a long non-employment spell exceeding the 15-month lookback.

Only (1) is the intended estimand. CPS longitudinal linkage failure is neither
rare nor random — it correlates with mobility, and mobility correlates with
local labour-market conditions, which is precisely the confound the design is
trying to avoid.

**Required change.** Separate the three groups observationally before the
companion is registered: use CPS month-in-sample to distinguish someone in
their first rotation (cannot have a prior observation by design) from someone
in a later rotation whose prior record failed to link. Restrict the companion to
the first group, report the linkage-failure rate, and pre-register a sensitivity
analysis bounding its effect. As written the companion estimates an effect on
a population that is partly a data artefact.

## M5 — The memo's unit and the engine's unit disagree. **Major.**

§3.1 and §7.1 state the analysis unit is **person-month**. `build_panel` in
`simulate_power_continuous.py` constructs an **occupation-month** panel from
pre-period cell moments, weights by `weight_sum`, and clusters on occupation.

These are not the same estimator. Person-level and cell-level weighting differ
whenever within-occupation composition shifts, and the degrees of freedom,
standard errors, and the interpretation of the person-level covariates `X_i` in
§9.1 all differ between them.

This is precisely the memo-versus-code divergence the 2026-08-14 audit
identified as this project's characteristic failure mode, and the rewrite
reproduced it in a new place.

**Required change.** State explicitly that the power calculation operates on
occupation-month cells as a computational approximation to the person-month
estimator, justify the approximation, and either drop `X_i` from §9.1 or
specify how person-level covariates enter a cell-level design. Better: run the
estimator itself at person level once the extract exists, and keep the cell
approximation only for simulation.

## M6 — The degeneracy trigger has no consequence. **Minor.**

§9.2 requires reporting the dose-matrix effective rank and leading share, and
says a leading share above 0.95 with rank 1 means "report it as such, interpret
beta as a single exposure contrast". It does not say what happens to the
paper's claims. On the synthetic fixture the leading share is already 0.909;
real dose paths driven by common model releases will plausibly be higher.

**Required change.** State the consequence in advance: if the design is
degenerate, does the paper still claim a dynamic exposure effect, or does it
retitle to a cross-sectional exposure result? Deciding after seeing the number
is a specification choice made with knowledge of the data.

## Minor issues

- **m1.** `dax_paths` sums all increments and `test_dax_path_...` asserts
  monotonicity, but §3.2's retired Decision 5 preserves a non-monotone
  diagnostic for capability regressions and price increases. A negative
  increment would silently violate the test's assumption. Specify whether the
  primary path is clipped at zero.
- **m2.** §7.3 gives the entrant companion its own multiplicity family. With
  one primary outcome in that family, Holm and unadjusted are identical; say so
  rather than implying a correction is being applied.
- **m3.** Decisions 1 and 3 now govern only descriptive reporting. They remain
  in the approved 17 and an implementer may reasonably mistake them for binding
  analysis parameters. Mark them clearly as non-binding in the checklist.
- **m4.** The PDF's text content was not verifiable in this environment (no
  poppler, broken `pypdf`, subsetted fonts without a ToUnicode map). Only page
  count and structure were checked. The PI should read the render, not just
  trust the source stamp.

## Assessment

Six major issues, one of them a blocker that makes a required diagnostic
uncomputable. M1, M2 and M5 are all instances of the same underlying failure:
prose written without executing it against the data or code it governs. That
this pre-review found them in a rewrite explicitly motivated by that failure is
the most useful thing in this document.

**No verdict is issued.** A self-review cannot clear a gate. The independent
cross-vendor pass remains required, and should be run against a v3 that has
addressed M1 through M5 — spending it on a draft with a known-uncomputable
diagnostic would waste it.
