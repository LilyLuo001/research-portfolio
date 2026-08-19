# Refraction — four Gate-0 decisions made under delegation, 2026-08-19

**Standing: DECIDED UNDER DELEGATION, AWAITING PI COUNTER-SIGNATURE.** Same
footing as `dax/memo/PI_DECISION_D1_2026-08-18.md` — recorded, machine-enforced,
and binding only once the PI signs. The owner instructed "go ahead and make these
decisions for me" after the audit (`refraction/AUDIT-2026-08-19.md`) surfaced
them.

**Why deciding now is legitimate.** The anti-specification-search rule is that a
threshold must be fixed *before* the data it judges is seen. No Gate-0 diagnostic
has been run: R3 has not executed, there is no panel, no beta, no sweep output.
Fixing these now, in git, with reasons, is exactly what pre-registration means.
Deciding them a week from now, after a first diagnostic, would not be.

Two of the four rest on evidence computed from pre-period coverage counts only.
No outcome variable was touched to make any of them.

---

## D-A · `d_b_mass_share_min = 0.50` (Gate-0 line G4)

**Question.** Plan §9 requires "sufficient treatment mass with D_b ≥ 0.1". How
much is sufficient?

**Decision.** A **majority of treated ConvExp mass** — 50%, measured as
Σ ConvExp over treated names with D_b ≥ `d_b_min`, divided by Σ ConvExp over all
treated names. Mass-weighted, not name-counted, because the Plan says *mass* and
because a name carrying 0.02 ConvExp and one carrying 0.0006 do not contribute
equally to γ_tilt.

**Reasoning.** The asymmetry decides it. Failing G4 does not kill the chapter; it
binds the §10 framing gate, so claims become "wrapper-induced beta compression"
and basket-specific language is dropped repo-wide. Failing costs *language*;
passing wrongly costs *the claim's truth*. A strict line is therefore cheap
insurance. Below half, "basket-specific refraction" would describe a minority of
the treated mass while the headline speaks for the whole sample — precisely the
overclaim the framing gate exists to catch.

**Alternative considered and rejected:** 0.70, for consistency with G2's
SE-share line. Rejected because the two lines measure different kinds of thing —
G2's share is an *estimability* condition, G4's is a *mechanism-presence*
condition — and 0.70 would trip the framing gate on a design whose modal treated
name has a genuinely distinguishable basket. If the PI prefers uniform
conservatism, 0.70 is defensible and this is the line to change.

## D-B · `pretrend_joint_p_min = 0.10`, `pretrend_individual_lead_adjust = holm` (G6)

**Question.** Plan §9 says the pre-trend triple must be "all three flat/zero" and
gives no numeric criterion.

**Decision.** Adopt **DAX Decision 14 verbatim**: joint p ≥ 0.10 **and** no
individually significant lead after Holm adjustment.

**Reasoning.** House precedent beats an invented number, and it is already
PI-approved in a sibling project (`dax/memo/PI_DECISIONS_OPEN.md`, Decision 14).
Using one flatness standard across the portfolio also removes the appearance of
tuning per chapter. G6 was the most post-hoc-vulnerable line in the design:
"flat/zero" with no number means any pre-trend plot can be described as flat once
it has been seen.

**Caveat that must travel with this line.** It is a *failure to reject*, so low
power passes it trivially. R3 must report the pre-trend confidence intervals
beside the p-value, and the line is only meaningful read against G5's archived
power bar. A wide band is not evidence of flatness. This is recorded in the
config next to the key.

## D-C · The G2 joint-window conflict — resolved by observation, not by choice

**Question.** Plan §9 puts "median pre-period announcements ≥ 30" *inside* the
joint shrinkage window (it must hold at the same w_shrink as SD(L̂) ≥ 0.25,
|corr| ≤ 0.3, and the ≥70% SE share). 执行手册 §R3 sweeps only those three and
treats n_pre as a separate G3 line. Which governs?

**Decision.** Evaluate n_pre **once**, as the 执行手册 does. No arbitration was
needed, because the two texts are operationally equivalent:

> Median n_pre is **invariant in w_shrink**. Shrinkage changes β̂'s precision and
> its cross-sectional dispersion; it does not change how many pre-period
> announcements a stock has. The estimation sample is fixed by
> `beta.n_pre_min_for_estimation`, which does not depend on w either.

So the Plan's "inside the window" phrasing is satisfied automatically whenever
the line holds at all — and if it fails, it fails at *every* w, which is an empty
window, which triggers the Plan's own "stock-level design fails jointly;
portfolio-level becomes primary or kill" branch. Same consequence, either
reading. **R3 must still route a G3 failure into the empty-window branch**, not
report it as an isolated line, so the Plan's intent survives the 手册's split.

## D-D · Sample frame: `waves_end = 2025-06-30`, `post_quarters_required = 4`

**Question.** `waves_end` was 2025-12-31, predating the current P1 event set
(`p1/t2_wrds/waves.csv` now runs to 2026-11-20, three waves dated after today).
And what minimum post-period must a wave have? Assert A2 cannot answer this: it
compares the panel against a calendar itself truncated at `announcements_end`, so
a wave with two post-quarters passes green.

**Evidence** (pre-period coverage counts only, from the committed free-path
build):

| post-quarters required | implied waves_end | waves kept | waves with computed cells | treated names ≥0.5% |
|---|---|---|---|---|
| 0 | 2026-06-30 | 74 | 46 | 395 |
| 2 | 2025-12-30 | 67 | 43 | 395 |
| **4** | **2025-06-30** | **53** | **34** | **386** |
| 6 | 2024-12-30 | 45 | 30 | 386 |
| 8 | 2024-06-30 | 39 | 25 | 385 |

**Decision.** `post_quarters_required = 4`, and `waves_end` derived from it.

**Reasoning.** The treated set is dominated by the early large waves, so the
post-period rule is nearly free in treatment terms — a full symmetric 8 quarters
costs only 10 of 395 treated names. What it *does* cost is waves: 8Q drops 28 of
them (67 → 39), and waves are the clustering dimension
(`inference.cluster_dims`, with `effective_cluster_warning_below: 10`). Four
quarters is where the marginal wave stops buying post-period identification and
starts costing effective clusters: ~32 scheduled announcements per treated stock
after conversion, ample for the Post × ConvExp × β × S interaction, with a
quarter of runway left inside the announcement window for the +60d wedge horizon
and next-quarter SUE.

**The window is asymmetric on purpose** (8 pre, 4 post): the pre side carries β
estimation, which needs many announcements plus the Vasicek prior; the post side
carries the interaction and the longest horizon.

**Made structural, not clerical.** `waves_end` is no longer a hand-set date. It
is governed by the invariant

    waves_end + post_quarters_required <= announcements_end

enforced in `refraction/tests/test_gate0_config.py`, and `assert_panel.a2_treated_coverage`
now reads the post bound from config instead of mirroring the pre bound. The
original defect could not recur silently.

---

## What the PI is signing

1. G4 clears at a **majority of treated mass**, not a plurality (D-A).
2. Portfolio-wide flatness standard, inherited from DAX (D-B).
3. A G3 failure is an empty-window failure and routes to portfolio-level-or-kill (D-C).
4. The chapter's sample is **53 waves ending 2025-06-30**, buying every wave four
   post-quarters (D-D).

Items 1, 2 and 4 change what Gate-0 can conclude. Item 3 changes nothing
numerically and only fixes how R3 must report a failure. If any is wrong, now is
the free moment to say so: nothing downstream has run.
