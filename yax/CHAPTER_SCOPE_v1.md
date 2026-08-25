# Chapter scope v1 — 2026-08-25

> **SUPERSEDED by `RESEARCH_PLAN_v1.md` (project YAX).** Retained for revision
> history: this file records the scope before the power result was measured and
> before the vintage gloss was corrected. Do not execute from it.

**Third dissertation chapter. Independently authored. Not the job-market paper.**

Supersedes `dax/memo/design_memo_v1.md` as the active research object. That
memo is archived, not retracted — see `dax/memo/DAX_ARCHIVE_2026-08-25.md`.

## 1. The question

> Does young employment deteriorate in AI-exposed occupations after the ChatGPT
> release? Tested on nationally representative data, under a specification and
> a coverage rule frozen before any post-period outcome was opened, and
> reported against a stated minimum detectable effect.

One bounded contribution: **a pre-registered, adequately powered, public-data
test of a contested claim.** Not a structural index, not a theory of
occupational adjustment, not a firm-level mechanism the data cannot observe.

The contribution is not the question — others ask it. It is the combination of
three things nobody in this literature currently offers together:

1. the specification fixed before the outcomes were visible, with the
   pre-period file built outcome-blind and the post-period file sealed;
2. a measured MDE from a 999-repetition simulation on the real panel, so a null
   can be distinguished from an underpowered null;
3. the exposure-coverage rule pre-specified in advance with all three variants
   reported — see `COVERAGE_RULE_PRESPEC_v1.md`.

The literature disagrees about magnitudes (ADP-based estimates large,
public-data estimates reportedly null) and every side ran its specification
after seeing its outcomes. That is the gap.

## 2. Why the question is worth asking

Four facts, all measured on real data, none taken on faith:

1. **The design is powered — this is the fact that decides the chapter.** On
   the real pre-period panel (490 occupation clusters, 66 months, 999
   repetitions), simulated power against a 19% relative decline is **100%**,
   and a **4.88%** relative decline still returns **98.6%** power. The MDE lies
   below the original grid. A null in this design would therefore be an
   informative null, not an underpowered one.

   **Read with the caveats in §2.5.** Simulated power on a fitted DGP is an
   upper bound, and the engine's own calibration is imperfect: the null rejects
   at 6.6% against a nominal 5%, and interval coverage is 93–94%.

2. **The exposure-coverage rule failed its own gate at 88.70%, and the failure
   is diagnosed.** The top 25 target codes carry 93.4% of the excluded mass;
   Janitors and Cooks alone are ~2.50% of eligible employment despite 99.38%
   and 99.27% component coverage, because the strict rule discards a whole
   occupation over a tiny unscored residual. All three candidate rules are
   pre-specified in `COVERAGE_RULE_PRESPEC_v1.md` and all three are reported.

3. **AI exposure and remote-work feasibility are entangled.** Employment-
   weighted R² against Dingel–Neiman teleworkability runs 0.09 (Eloundou α) to
   0.58 (AIOE). Emanuel, Harrington & Pallais attribute 64% of the rise in
   young college-graduate unemployment to remote work.

4. **The variation separating them is concentrated.** After removing
   teleworkability, 14 occupations carry half the employment-weighted residual
   variance of Eloundou α; its effective number of contributing occupations is
   28 out of 669. Dropping SOC major group 43 moves its R² from 0.0909 to
   0.0103. This bounds what any occupation-level decomposition can claim, and
   it is reported as a limit on the design rather than as a finding about AI.

Merging the measures onto the CPS taxonomy requires a crosswalk decision that
papers make silently. That decision is a **reported robustness dimension**, not
the contribution: AIOE and Dingel–Neiman cover the SOC 2010 taxonomy in full,
and the 96.7% group-15 figure measures the cost of an exact-code merge, not a
gap in the measures — see `CORRECTION_2026-08-25_vintage_gloss.md`.

Sources: `yax/measurement/AUDIT_RESULTS.md`, the coverage-failure audit,
and the power aggregate, each with receipt and lineage.

### 2.4 What is already crowded — VERIFY BEFORE THE FREEZE

The following are reported second-hand and **none has been verified from this
repo** (no network access at the time of writing). Each is cheap to check and
each would reshape the chapter. Treat them as claims to confirm, not facts.

| claim to verify | if true, consequence |
|---|---|
| Eckhardt & Goldschlag (EIG), *AI and Jobs: The Final Word (Until the Next One)* (2025), chose AIOE **because** ability-level exposure makes crosswalking more accurate, compared two crosswalk approaches, and published data on GitHub | the crosswalk *construction* is done. Reconcile against their file rather than rebuilding. §1's question survives only if they did not test the **coefficient's** sensitivity |
| EIG report findings "similar across all the available measures" | "is it robust across measures?" is answered in public. Do not re-ask it |
| Budget Lab SDID finds nulls | the estimate this chapter bounds may already be contested |
| Brynjolfsson, Chandar & Chen (Aug 2026 version) added interest-rate controls (Zens et al.) **and telework robustness** | fact 2 above is substantially pre-empted; the telework angle becomes a supporting appendix, not a contribution |

**Audit item 10 (novelty verification) is now a gate, not an open item.** It
runs before the design freeze in C2, not after estimation.

### 2.5 Reading the power result honestly — BINDING

The power number is the chapter's foundation, so it carries three standing
constraints. None is optional.

1. **Report bootstrap power, not normal-critical-value power.** The engine
   rejects at 6.6% under the null and covers at 93–94%. Inference is mildly
   oversized, so the headline power figure must be recomputed under a
   wild-cluster bootstrap before it appears in the manuscript.
2. **The fine grid must show a gradient.** A healthy design has power falling
   through 80% somewhere in the 1–3% range. If power is still near 100% at a
   1% relative decline, the simulation is too smooth and is understating real
   variance — treat that as an engine bug to be found, not a strong design, and
   do not proceed to the freeze until it is explained.
3. **Never write "100% power".** Write the MDE with its bootstrap interval and
   the assumptions the DGP makes. Simulated power on a fitted model cannot
   capture misspecification or unmodelled shocks, and the paper must say so.

## 3. The pre-commitment

Power is now measured, so the old "informative vs imprecise" split is settled:
the design is powered, and the branches are about **what the estimate shows**,
not about whether it can show anything. All three are written from the same
pre-specified tables and the first run is the reported run.

- **A material decline** → the public-data test corroborates the proprietary-
  data literature, with a magnitude and a stated MDE, under a frozen
  specification. That is worth reporting precisely because nobody has done it
  pre-registered.
- **A null** → an *informative* null, which is the rarer and more useful
  result. With an MDE below 5%, a null says the effect is smaller than the
  published estimates, not that the data could not see it. This is the branch
  that most needs the bootstrap in §2.5 to be airtight.
- **Rules A, B and C disagree** → the finding is about the fragility of
  occupation-level exposure measurement, reported as such, not resolved by
  choosing a rule.

**No branch is preferred and none is written before the run.** The chapter is
complete under all three because the pre-registration and the MDE are the
contribution; the sign of the coefficient is the content.

## 4. Data

| input | source | state |
|---|---|---|
| CPS analysis panel | IPUMS, SCC `dax-private/ipums/w5_analysis_extract_7/` | built, 242,474 person-months, 2021-11 → 2026-07 |
| CPS pre-event panel | IPUMS, SCC `w1_preperiod_extract_6/` | built, 71,322 rows |
| CPS wide panel (2017-01 →) | IPUMS extract 9 | **BUILT AND VALIDATED — 9,262,480 rows** |
| Pre-period file, outcome-blind | derived | **BUILT — 6,188,956 rows** |
| Post-ChatGPT outcomes | derived | **SEALED — not opened** |
| Occupation bridge + exposure lookup | Census 2010→2018 crosswalk, BLS SOC crosswalk | **BUILT** |
| Power engine (PPML-equivalent) | this repo | **BUILT — 999 reps on real panel** |
| AIOE | Felten, Raj & Seamans (2021) | vendored |
| Eloundou α/β/γ, GPT-4 + human | Eloundou et al. (2023) | vendored |
| Dingel–Neiman teleworkable | Dingel & Neiman (2020) | vendored |
| OEWS 2021 | BLS | built |
| OEWS 2019 + recent year | BLS | **not obtained** |
| SOC 2010 → 2018 crosswalk | BLS | **not obtained — blocks the repair** |
| Webb (2020), Frey–Osborne (2017) | public | not obtained, optional |

The wide extract is no longer a blocker — it is built and validated, and the
pre-period file was constructed **outcome-blind**, which is what makes the
pre-registration claim in §1 true rather than aspirational. Keep it that way:
the post-period file stays sealed until the tag.

**Operational risk, unresolved.** This work currently lives only on two SCC
working copies (`dax_design_power_20260825`, `dax-cps-sparse-20260825`) with
commits cherry-picked between them and no remote. The code and receipts are not
licensed data and belong on `origin`. Push before anything else.

## 5. Sample and variable definitions — frozen

- **Population.** Ages 16–75, matching Cavounidis, Chai, Lang & Malhotra.
  Young = 20–29 in the primary split; 16–24 and 22–27 reported as alternates,
  all three specified here in advance.
- **Outcome.** Employment, from `EMPSTAT` codes 10 and 12. Unconditional weekly
  hours (`UHRSWORKT`, 999 → missing) as the secondary outcome, zero-filled for
  the non-employed, with the zero-fill sensitivity reported both ways.
- **Weights.** `WTFINL` for employment. **`EARNWT` and outgoing rotation groups
  only (`MISH` ∈ {4, 8}) for any earnings outcome** — `EARNWEEK` and `HOURWAGE`
  are not asked of the full sample and `WTFINL` is the wrong weight for them.
- **Exposure.** Occupation-level, merged to CPS occupation via the repaired
  crosswalk. All measures standardised to mean 0, sd 1 over the *employment-
  weighted* occupation distribution, so coefficients are comparable across
  measures on different native scales.
- **Telework.** Occupation-level Dingel–Neiman share only. **Do not use a young
  worker's own `TELWRKHR`/`TELWRKPAY`** — those begin 2022-10 and are asked
  only of people employed and at work in the reference week, so they are
  post-treatment and conditioned on the outcome. The occupation-level measure
  avoids the individual-level mechanical conditioning but remains endogenous to
  employer return-to-office decisions and sectoral demand; it is not an
  exogenous measure of remote work and must not be described as one.

## 6. Specification — frozen before estimation

**Primary.** Two-way fixed effects on person-months, occupation × month:

    y_iot = β (Exposure_o × Young_i × Post_t) + γ (Exposure_o × Young_i)
            + δ (Exposure_o × Post_t) + α_o + λ_t + X_it + ε_iot

- `Post_t` = 1 from 2022-11 (ChatGPT public release).
- Standard errors clustered on **occupation**, which is the level of treatment.
  Report a two-way occupation × month cluster as a robustness row.
- **Wild-cluster bootstrap is the primary inference**, not a robustness row.
  The power engine rejects at 6.6% under a nominal 5% and covers at 93–94%, so
  normal critical values are known to be oversized in this design. Report
  bootstrap p-values and intervals in every main table.
- `X_it`: education, sex, race, state, and a state × month fixed effect in the
  saturated row.

**Event-time.** Same, with month-relative-to-2022-11 indicators, 2022-10
omitted. Pre-period coefficients are the pre-trend test — **reported whatever
they show**, never used to select a window.

**Every main table carries three coverage-rule columns** — A strict, B
sibling-imputed (primary), C renormalized — per
`COVERAGE_RULE_PRESPEC_v1.md`. Not one primary plus footnotes.

**The four robustness dimensions, each a pre-specified table:**

1. **Exposure measure** — all seven (AIOE, Eloundou α/β/γ × dv/human), each
   run identically. No measure is selected; disagreement is explained, not
   resolved by choice.
2. **Occupational-code vintage** — every measure run unrepaired and repaired,
   side by side. The gap is a result, not a diagnostic.
3. **Pre-existing trends** — event-time pre-period, plus a 2017-2019
   placebo-`Post` on the wide extract.
4. **Remote-work exposure** — add the Dingel–Neiman share interacted with
   `Young × Post`, and report the exposure coefficient with and without it,
   alongside the VIF.

**Anti-specification-search rules, binding.**

- The first run of each pre-specified table is the reported run.
- No outcome is inspected before §5 and §6 are committed to git.
- Any deviation is logged in a deviation table with its date and reason, in the
  manner of `design_memo_v1.md` §11.2.
- `dax/analysis/outcomes/` stays sealed until the `v1.0-preregistered` tag.

## 7. Deliverables

| item | target |
|---|---|
| manuscript | 25–35 pages |
| principal figures | 3–4 |
| main tables | 4–6 |
| measurement appendix | 1 — the exposure-gate audit, repaired |
| replication package | code + public inputs + receipts; no licensed microdata |

**Figures.** (1) event-time coefficients, primary measure; (2) exposure vs
teleworkability with employment weights, showing the common-support problem;
(3) coefficient across all seven measures, repaired vs unrepaired; (4) residual
variance concentration.

**Tables.** (1) summary statistics; (2) primary TWFE; (3) all seven measures;
(4) vintage repair contrast; (5) telework horse-race with VIFs; (6) pre-trend
and placebo.

## 8. Out of scope — recorded so it stays out

- Rescuing DAX or any part of the capability-price panel.
- A novel exposure index.
- BTOS × QWI firm-level work. **Optional**, and only if the public merge works
  immediately; it is not the mechanism this chapter must establish.
- Matching proprietary payroll precision. ADP-based results are a comparison
  point, not a target.
- Any claim about general-equilibrium employment effects.

## 9. Execution

Task briefs in `yax/briefs/`. `C0_CONTEXT_PACK.md` is the header pasted
at the top of every task prompt; C1–C4 are one task each, run in order, one per
session.

C1 and most of C2 are **done** — extract, bridge, exposure lookup, coverage
audit, and the power engine all exist and run on real data. What remains before
the freeze:

1. the fine power grid, checked for a gradient per §2.5
2. the wild-cluster bootstrap recomputation of the MDE
3. the novelty gate in §2.4
4. push everything to `origin`
5. commit `COVERAGE_RULE_PRESPEC_v1.md` and `DESIGN_FREEZE_v1.md`, then tag
   `v1.0-preregistered`

Only then may C3 open a post-period outcome. Plan three to five calendar weeks
from the freeze to a complete draft.
