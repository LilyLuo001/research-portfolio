# PI decision packet — the missing-mass rule, before outcomes open

**Date:** 2026-08-24. **Status:** drafted for signature. **Not signed, and not
taken on delegated authority** — this fixes what the paper estimates, which is
not a seat's decision.

## Why this is urgent rather than tidy

The v3 packet §D is the only place in the repository that states a rule for
non-evaluable task mass:

```text
lower_om  = L_om
center_om = NOT IDENTIFIED
upper_om  = L_om + U_o
```

`design_memo_v1.md` — the pre-registration document — contains no partial-
identification treatment at all. So the rule that governs roughly **80% of
wage-weighted task mass** exists in one decision packet and in no
pre-registered specification.

**The 80% is not a detail of this design; it is the finding.** S1 classified
120 tasks and returned `directly_executable_digital: 0`. Not a small number —
zero. The non-evaluable were 57 requiring interpersonal interaction and 35
requiring physical-world action. Whatever rule governs that mass governs the
paper.

*(S1 is single-annotator, `formal_s1_gate_result: UNRESOLVED`; these counts are
diagnostics, and the qualifier travels with them. The rule still needs signing
whatever S1's replication returns, because the mass is large under any
plausible re-estimate.)*

## The problem, stated precisely

§D's bound is **correct as a bound**. It is the honest worst case: assume all
unidentified mass crosses. Nothing here says the arithmetic is wrong.

The problem is what the bound does when it is used as a **level**. Write
`B_o` for the evaluable share of occupation `o`'s mass and `E_om` for the
crossing rate among evaluable tasks. Then `L_om = B_o·E_om`, `U_o = 1 − B_o`,
and

```text
upper_om = B_o·E_om + (1 − B_o) = 1 − B_o(1 − E_om)
```

which is **decreasing in `B_o`**. At a fixed true crossing rate of 0.40:

| evaluable share `B_o` | `upper_om` |
|---:|---:|
| 0.05 | 0.970 |
| 0.30 | 0.820 |
| 0.80 | 0.520 |

An occupation we can barely measure scores 0.97; one we measure well scores
0.52, at the same underlying exposure. As a statement of ignorance that is
fine. As the input to a regressor it is a measurement artifact **with the
wrong sign**, and D1 made the primary specification a continuous cumulative
dose built from DAX levels. The occupations where evaluability is worst are
disproportionately the interpersonal and physical ones — that is what S1
found — so the artifact is not noise. It correlates with occupation type, and
therefore with the outcome.

This is the referee objection that ends the paper: *your exposure measure is
highest exactly where your measurement is weakest.*

## What §D already requires, and what is missing

§D says a model-based center "may be reported only after a separate,
prospective missing-mass model and validation rule are signed." That is
exactly right, and the model does not exist in any packet. It exists as
working code — `dax/memo/nonevaluable_bound_repair.py`, with tests — and is
referenced by no memo, no packet and no specification. An established result
sitting outside the spec is not part of the paper.

## The proposed rule

Index the missing-mass assumption explicitly by `κ ∈ [0,1]`, the fraction of
non-evaluable mass assumed to cross, and apply it as a multiplier on the
occupation's dose:

```text
ΔDAX_om(κ) = ΔE_om · [B_o + κ(1 − B_o)]
```

- `κ = 0` — no unidentified mass crosses. Reduces to the identified lower bound.
- `κ = 1` — all of it crosses. Recovers §D's worst case as a limiting case,
  so nothing is discarded.
- The multiplier `[B_o + κ(1 − B_o)]` is **weakly increasing in `B_o` for
  every κ in [0,1]**, verified over a κ grid in
  `test_nonevaluable_bound_repair.py`. Better-measured occupations can no
  longer score lower for being better measured.

The reported object is the **κ-path**, not a point. Report the identified
`lower_om` and the full `upper_om` unchanged — they remain the honest bracket
— and report the dose and the coefficient across the κ grid, so a reader sees
how much of the result is carried by the assumption rather than the data.

## What the PI must decide

| # | Decision | Options |
|---|---|---|
| MM-1 | Adopt the κ-family as the prospective missing-mass model | adopt / reject / amend |
| MM-2 | The reported κ grid, frozen before outcomes | `{0, 0.25, 0.50, 0.75, 1}` / other |
| MM-3 | Which κ, if any, is the headline | **recommended: none — the path is the result** / a named κ with prospective justification |
| MM-4 | Whether `B_o` itself is reported per occupation | **recommended: yes** — a reader cannot judge the κ-path without knowing coverage |
| MM-5 | Whether the rule enters `design_memo_v1.md` before the `v1.0-preregistered` tag | **recommended: yes** — see below |

**On MM-5.** If the missing-mass rule is not in the pre-registered memo, then
choosing it afterwards is a post-hoc identification choice over 80% of the
mass, and it will be read that way however it is documented. This is precisely
the specification-search the project's own meta-rules forbid. It costs nothing
to sign now and cannot be recovered later.

## What this does not decide

It does not set `p_star`, the crossing threshold, the sampling option, or
anything else in v3 forms 1–5. Those remain open and are not made easier by
this. It also does not make the bridge benchmark exist: `E_om` is unmeasured
until it does, and `B_o` is estimated from the evaluability classification,
whose own replication is outstanding.

## Signature

    PI signature: ______________________  Date: ____________

    [ ] MM-1 adopt   [ ] MM-1 reject   [ ] MM-1 amend as noted
    [ ] MM-5 the rule enters the pre-registered memo before the tag
