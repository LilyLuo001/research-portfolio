# YAX — research plan v2

**Young-worker AI Exposure.** Third dissertation chapter. Independently
authored. Not the job-market paper.

*Plan date 2026-08-26. Supersedes `RESEARCH_PLAN_v1.md`, which is retained for
its revision history. v1 was written before power was located and before the
novelty gate ran; both results change the question.*

---

## 1. The question

> Published estimates of a young-worker employment decline in AI-exposed
> occupations rest on exposure measures merged onto CPS through crosswalk,
> measure and coverage decisions that papers make silently. **Do those
> decisions change the estimated decline — and does the identifying variation
> sit where the assumed mechanism says it should?**

Two things v1 asked are now settled and enter as premises rather than
questions:

- **Can nationally representative data adjudicate the magnitudes at issue?**
  Yes. The empirical 80% MDE is 3.44% (normal theory) on 490 occupation
  clusters and 66 pre-period months; the contested magnitude is ~19%. The
  disagreement between proprietary-data estimates and public-data nulls is not
  a power problem, and that is worth stating because it has been assumed
  otherwise.
- **Is the young-versus-older CPS pattern itself novel?** No. Dallas Fed and
  Anthropic publish closely related patterns; EHP and Tucker use adjacent
  age-interaction designs. This chapter does not claim to discover it.

## 2. The contribution

Not the pattern. Others report it. The contribution is that **the measurement
decisions underneath it have never been tested against the coefficient**, and
this chapter tests them under a specification frozen before any post-period
outcome was opened, against a stated MDE.

The reason to expect it matters is measured, not speculative: on the OEWS 2021
taxonomy an exact-code merge of AIOE covers **3.33%** of computer and
mathematical employment. The official vintage repair raises that to **97.7%**.
Published work using off-the-shelf AIOE on post-2018 data is therefore
estimating an AI-exposure effect with software developers, systems analysts and
user-support specialists almost entirely absent from the sample.

**Both branches of the test are substantive**, which is what makes this a
chapter rather than a robustness note:

- **The repair moves the coefficient** → published estimates are shaped by a
  fixable merge artifact.
- **The repair does not move it** → the estimated effect is not driven by
  computer occupations, which cuts against the mechanism the literature
  assumes. A null here is a statement about mechanism, not an absence.

Three supporting properties, none of them the headline: the specification was
frozen outcome-blind, the MDE is measured rather than asserted, and the
coverage rule is pre-specified with its variants reported.

## 3. What is established

| fact | value | source |
|---|---|---|
| Wide CPS extract | 9,262,480 rows, 2017-01 → 2026-07 | IPUMS extract 9 |
| Outcome-blind pre-period file | 6,188,956 rows | derived; post rows rejected before protected fields decoded |
| Occupation clusters | 490 | pre-period panel |
| Pre-period months / planned post | 66 / 43 | pre-period panel |
| **Empirical MDE80** | **-0.035 log = 3.439% relative decline** | exact-seed 999-rep run |
| Power vs 19% benchmark | 1.000 (z ≈ 16.9) | same |
| Null rejection at nominal 5% | **6.8068%** | same |
| Null 95% interval coverage | **93.1932%** | same |
| Convergence failures | 0 of 999 | same |
| Effective Q1-vs-Q5 occupation concentration | 58.42 of 490 | same |
| Computer/math coverage, exact-code merge | **3.33%** | vintage bridge |
| Computer/math coverage, repaired | **97.7%** | vintage bridge |
| Strict coverage rule | **88.70%** — fails its 90% gate | coverage receipt |
| Exposure–telework R² range | 0.09 (Eloundou α) → 0.58 (AIOE) | `measurement/AUDIT_RESULTS.md` |

**The power curve is internally coherent.** Checked independently: the z
implied at 80% power (2.8016) and at 98.6% (4.1573) scale by 1.4839, while the
effects scale by 1.4295 — a 3.67% discrepancy, within simulation noise at 999
repetitions. The engine is not producing ceiling power across an order of
magnitude, which was v1 §5.2's falsification condition. **That condition did
not trigger.**

## 4. What is not established

1. **The size-corrected MDE.** The null rejects at 6.8068%, so reported SEs are
   understated by ~7% and 3.44% is optimistic. A back-of-envelope correction
   gives ~3.69%; the wild-cluster bootstrap is what the manuscript reports.
2. **Whether a pre-registered, power-stated test of this claim already exists
   on public data.** The novelty gate answered the broader question, not this
   one. Pre-analysis registries have not been searched.
3. **Locators for the four prior-work citations.** Dallas Fed, Anthropic, EHP
   and Tucker are named without URL, author, date or version.
4. **Any post-period result.** The seal holds.

## 5. Power and inference — BINDING

1. **Wild-cluster bootstrap is primary inference**, not a robustness row.
   Rademacher weights, clustered on occupation, ≥999 draws. Two-way
   occupation × month clustering as a reported row.
2. **Never write 3.44% as the MDE**, and never write "100% power". Report the
   bootstrap MDE with its interval, the 6.8% nominal size, and what a
   simulation on a fitted DGP cannot capture.
3. The Q1-vs-Q5 effective concentration of 58.42 out of 490 occupations is
   reported alongside every headline coefficient. It bounds how much of the
   estimate rests on how few occupations, and it is consistent with the
   measurement audit's finding that Eloundou α's residual variation sits in
   ~28 effective occupations.

## 6. The coverage decision — PENDING OWNER SIGN-OFF

The strict rule returned 88.70% against its own 90% gate and **failed**. No
freeze was created. Two ways forward, and this changes the estimand, so it is
not an agent's call.

**Recommended — redefine the population.** Keep the strict rule as primary and
state the estimand as the **full-component published-exposure support**,
88.70% of eligible employment. Report the excluded employment and the named
excluded occupations in every main table. Sibling imputation becomes a
sensitivity row only.

**Rejected — impute to pass.** `COVERAGE_RULE_PRESPEC_v1.md` v1 named the
sibling-imputed rule primary. That designation should change. The threshold was
justified ex ante on the structure of the missingness, and that is still not
enough: the *sequence* a reader sees is gate failed → imputation rule adopted →
gate passes. Ex-ante reasoning does not repair how that reads.

Either way the failed rule and its receipt are preserved permanently, and all
three rules appear as columns. The amendment is legitimate as a pre-registration
amendment only because no outcome has been opened; it must be committed before
the freeze.

## 7. Design

Unchanged from v1 §6 except where noted.

**Population.** Ages 16–75; young = 20–29 primary, 16–24 and 22–27
pre-specified alternates. Restricted to the exposure support fixed in §6.

**Outcome.** Employment (`EMPSTAT` ∈ {10, 12}); unconditional weekly hours
secondary. Occupation-month stock PPML is the estimator.

**Weights.** `WTFINL` for employment; `EARNWT` with `MISH` ∈ {4, 8} for any
earnings outcome.

**Treatment.** Occupation-level exposure standardised to mean 0 / sd 1 over the
employment-weighted occupation distribution. `Post` = 1 from 2022-11.

**Telework.** Occupation-level Dingel–Neiman share only. **Never a person's own
`TELWRKHR`/`TELWRKPAY`** — post-treatment and conditioned on the outcome.

**Estimating equation.** As v1 §6, clustered on occupation, bootstrap primary.
Event-time version relative to 2022-11, 2022-10 omitted.

## 8. The five frozen tables

1. **Primary** — the decline, with MDE and effective concentration alongside.
2. **Crosswalk vintage** — exact-code vs repaired, every measure. *The chapter's
   central table.*
3. **Exposure measure** — all seven, run identically. Disagreement explained,
   not resolved by choice.
4. **Coverage rule** — A / B / C as columns, with excluded occupations named.
5. **Pre-trends and placebo** — event-time pre-period, reported whatever it
   shows, plus a 2018-11 placebo on 2017–2019.

Plus the post-2025 extension as a frozen early-versus-extension joint model and
Wald test.

Telework enters as a reported robustness row rather than a dimension of its
own: Brynjolfsson et al.'s August 2026 version reportedly adds telework
robustness, which is to be confirmed under §4.3.

## 9. Position in the literature

| finding | status |
|---|---|
| Dallas Fed, Anthropic publish related CPS young-vs-older patterns | reported; **locators outstanding** |
| EHP, Tucker use adjacent age-interaction designs | reported; **locators outstanding** |
| Broad novelty claim ("nobody has looked") | **FAILS.** Not claimed by this chapter |
| Coefficient-level crosswalk/exposure sensitivity | no prior work identified |
| A pre-registered, power-stated public-data test | **not yet searched** |

## 10. Seal protocol

1. `COVERAGE_RULE_PRESPEC_v2.md` committed, reflecting the §6 ruling. *(pending)*
2. Bootstrap MDE computed and recorded. *(pending)*
3. §9 locators supplied and the registry search done. *(pending)*
4. Everything pushed to `origin`. *(pending)*
5. `DESIGN_FREEZE_v1.md` committed with the panel sha256 and empty shells.
6. `v1.0-preregistered` tagged.
7. **Only then** may a post-period outcome be opened.

Machine-checked: `python yax/gates.py --power-aggregate <aggregate>.json`.
Seven gates, non-zero exit unless all pass. `gradient` now PASSES;
`calibration` FAILS until a bootstrap field exists.

## 11. Deliverables

25–35 pages, 3–4 figures, 5 main tables plus the extension test, the
measurement appendix in `measurement/`, and a replication package carrying code,
public inputs and receipts but **no licensed microdata**.

## 12. Kill conditions

v1's first condition — the power gradient — **is retired: it passed.** The live
ones:

1. **A pre-registered, power-stated public-data test already exists.** Then the
   process contribution is gone and only the measurement test remains, which is
   a note rather than a chapter.
2. **The seal breaks before step 6.** The chapter can be written but must be
   labelled post-hoc, and its central claim is lost.
3. **The bootstrap MDE exceeds the contested magnitude.** If size correction
   pushes the MDE anywhere near 19%, the premise in §1 fails. Nothing in the
   current numbers suggests this — the gap is a factor of five — but it is
   checked, not assumed.

## 13. Standing rules

- LLM output is not a source of facts.
- Don't know → stop. `NEED_HUMAN`, never guess-fill.
- Never specification-search. The first run of a frozen table is the reported run.
- Licensed microdata never enters the git work tree. Never `git add -A`.
- **A sentence describing a computed number must be checkable against the same
  artifact that produced the number.** See
  `CORRECTION_2026-08-25_vintage_gloss.md`.
