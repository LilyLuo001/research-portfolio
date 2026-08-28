# Correction to the AI/telework separability gate

**Date:** 2026-08-25, same day as the original run. The numbers in
`ai_telework_overlap_receipt.json` are unchanged and correct. **The reading
placed on them was overstated in four ways**, and this records the corrections
before anything is built on them.

## 1. "No specification rescues AIOE" is false

R² = 0.58 implies VIF = 1/(1−0.58) = **2.38**, which inflates standard errors
by about 1.54×. Costly, not disqualifying.

| measure | R² | implied VIF |
|---|---:|---:|
| Eloundou α | 0.09 | 1.10 |
| Eloundou β | 0.42 | 1.72 |
| Eloundou broad | 0.45 | 1.82 |
| Felten AIOE | 0.58 | 2.38 |

Multicollinearity at this level is a **precision** problem, not an
identification failure. The real threats to a design using AIOE are
measurement error, thin common support, influential occupations, and
correlated pre-trends — none of which this gate measured.

## 2. Choosing α because it has the lowest overlap would be specification search

The gate reports a property of the *design*, not of the world. Selecting the
exposure measure on that property is measure selection by another name, and it
is what meta-rule "never specification-search" forbids.

**The measure must be justified economically, and all measures reported.**

**Stated precisely, because the weaker claim is the true one:** measure roles
were fixed **after** examining treatment overlap and **before** examining any
labour-market outcome. That is acceptable and standard. Calling the choice
wholly prospective would be misleading, because the exposure-telework
correlations had already been seen when the roles were written down.

The justification, recorded before any employment result is examined:

- **α (E1)** — tasks a language model accelerates directly, with no
  complementary investment.
- **β, broad (E1 + E2)** — tasks requiring complementary software or
  organisational investment built on top of the model.
- **AIOE** — a broader occupational measure of AI applicability, not
  LLM-specific and predating the LLM era.

If a result appears only under α, that is *either* economically meaningful —
directly usable capability is what binds — *or* noise surfaced by measure
choice. The paper must report all four and explain the divergence rather than
select on it.

## 3. The off-diagonal share is not a common-support diagnostic

62.7% of SOC codes have a teleworkable share of exactly zero, so the telework
"median" split is `> 0` versus `= 0`. That is not comparable to a genuine
high-versus-low split on the AI side, and the 39.4%-versus-11.6% contrast does
not mean what the original summary implied.

Replace it with: residualised exposure distributions; quartiles **among
occupations with positive telework feasibility**; two-dimensional occupation
plots; residual standard deviations; effective employment mass by region; and
**a named list of the occupations supplying the identifying variation**. That
last item is decisive — if α's residual variation comes from a handful of
peculiar occupations, it is not usable regardless of the R².

## 4. Notation to verify against the source

The GPTs-are-GPTs repository README defines `_gamma = E1 + E2`. Eloundou et
al. denote the broad measure **ζ** in the paper. The repository appears to have
renamed it. Confirm against the published text before citing either symbol.

## What the gate does and does not establish

**Establishes:** AI exposure and remote-work feasibility are not inevitably
near-collinear; the narrow LLM-specific measure carries substantially more
variation independent of Dingel–Neiman than AIOE does.

**Does not establish:** that α identifies an AI effect; that AIOE is unusable;
that the residual variation has good common support; that the divergent
occupations are representative; or that any resulting CPS interaction is
adequately powered.

**The defensible statement today:**

> Narrow and broad AI-exposure measures differ substantially in their overlap
> with remote-work feasibility. Whether that difference supplies usable
> identifying variation depends on which occupations generate the divergence
> and whether their employment histories support the comparison.

## Consequence for sequencing

No memo and no measure selection until the robustness and common-support audit
runs. The audit is specified in `AUDIT_SPEC.md` alongside this file.
