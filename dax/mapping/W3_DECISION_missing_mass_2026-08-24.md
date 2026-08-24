# W3 Decision 3 — the missing-mass rule, taken on delegated authority

**Date:** 2026-08-24. **Status:** decision taken on delegated authority after
the owner, having been told this one fixes what the paper estimates,
instructed the seat to take it. Recorded for counter-signature.
Supersedes nothing; adds the rule `design_memo_v1.md` never had.

Companion to `PI_DECISION_PACKET_missing_mass_2026-08-24.md`, which states the
problem. This records what was decided.

## What changed between the packet and this decision

The packet put five decisions. Computing the sensitivity first, before
deciding, added a sixth that outranks the other five —
`s1_boundary_sensitivity_receipt.json`:

| Evaluable boundary | identified mass `B` |
|---|---:|
| strict — directly-executable digital only | **0.0000** |
| medium — plus supplied files/data | 0.1086 |
| broad — plus construct-valid simulated inputs | 0.2572 |

Against a headline that moves only 0.0617 across all three weightings in the
receipt, the boundary moves `B` by **0.2572** — four times as much.

**The strict boundary identifies nothing at all.** S1 found zero
directly-executable-digital tasks. At `B = 0` the multiplier `[B + κ(1−B)]`
collapses to exactly `κ`, and the index would carry no information from data —
it would be the missing-mass assumption alone, wearing a number. That is
reached by a defensible reading of the project's own v3 taxonomy, which admits
the other two classes only conditionally: supplied-files "if input validity
passes", simulated-inputs "only after construct-validity review".

This reorders the work. The instinct was to fix the single-annotator problem
first. Two annotators in perfect agreement leave the boundary entirely open,
because it is definitional rather than a judgment about any task.

## The decisions

**[MM-1] Adopt the κ-family as the prospective missing-mass model.**

```text
ΔDAX_om(κ) = ΔE_om · [B_o + κ(1 − B_o)]
```

Weakly increasing in `B_o` for every κ ∈ [0,1], verified over a κ grid in
`test_nonevaluable_bound_repair.py`. At κ = 1 it recovers v3 §D's worst case,
so nothing in the existing packet is discarded — §D's `lower_om` and
`upper_om` are retained unchanged as the honest bracket.

Adopted because §D already requires a prospective missing-mass model before
any center may be reported, and this is one. The alternative — using
`upper_om = L_om + U_o` as a level — is decreasing in coverage, and S1 shows
the worst-measured occupations are the interpersonal and physical ones, so the
artifact would correlate with occupation type and therefore with the outcome.

**[MM-2] The reported κ grid is `{0, 0.25, 0.50, 0.75, 1}`,** frozen now,
before outcomes.

**[MM-3] No κ is the headline. The κ-path is the result.** Reporting a point
would convert an assumption into a finding. A reader must see how much of any
result is carried by κ rather than by data — which at `B = 0.1086` is most of
it for any κ above about 0.1.

**[MM-4] `B_o` is reported per occupation, and is not optional.** The
sensitivity above is the reason: the κ-path cannot be read without knowing
what fraction of the occupation it rests on. An occupation at `B_o = 0.02`
and one at `B_o = 0.6` produce differently-trustworthy numbers that would
otherwise look identical.

**[MM-5] The rule enters `design_memo_v1.md` before the `v1.0-preregistered`
tag,** as a pre-tag amendment in the same manner as D1, D3 and D4. Choosing a
missing-mass rule after the tag would be a post-hoc identification choice over
most of the mass, and would be read that way however documented.

**[MM-6] The evaluable boundary is `medium`, and it is prospective.**

Evaluable means directly-executable-digital plus supplied-files/data.
Construct-valid simulated inputs are **excluded from the identified set** and
reported separately, exactly as v3 §D directs.

Three reasons, in order:

1. §D already says simulated-input tasks are "evaluable only after
   construct-validity review" and must be "report[ed] separately". Counting
   them in the identified set before that review exists would use a class the
   taxonomy defines as conditional as though it were unconditional.
2. It is the choice that cannot be accused of inflating coverage. Broad more
   than doubles `B` using the class whose validity is least established.
3. Strict is defensible but yields `B = 0`, which publishes nothing. Choosing
   it would be choosing not to have a paper; choosing broad would be choosing
   the largest number available. Medium is neither.

**Both alternatives are reported as prespecified sensitivities.** If the
κ-path under `medium` differs materially from `broad`, that is a finding about
how much the index rests on simulated inputs, and it is reported rather than
resolved by selection.

## What this does not decide

`p_star`, the crossing threshold, the sampling option, and the rest of v3
forms 1–5 remain open. It does not make the bridge benchmark exist: `E_om` is
unmeasured until it does. And it does not resolve S1 — `B_o` is estimated from
an evaluability classification whose replication is still outstanding, and
every figure here inherits `formal_s1_gate_result: UNRESOLVED` and the
single-annotator limit.

What it does is ensure that when those land, the rule they feed was fixed
before anyone saw an outcome.

## Signature

    Owner counter-signature: ______________________  Date: ____________

    [ ] agreed as recorded
    [ ] agreed except MM-6: use `broad` (accepting that B rests on a class the
        taxonomy admits only after a construct-validity review that has not run)
    [ ] agreed except MM-6: use `strict` (accepting B = 0 and that the index
        carries no information from data)
    [ ] reject; revert to v3 §D as written and record why the coverage
        inversion is acceptable
