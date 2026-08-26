# YAX — research plan v3

**Young-worker AI Exposure.** Third dissertation chapter. Independently
authored. Not the job-market paper.

*Plan date 2026-08-26; **amended the same day** (§8 timing asymmetry, §9.1
crosswalk decomposition, §2 O\*NET descriptor, §13a amendment rationale) after a
second review round. Supersedes v2, which is retained for revision history.
v3 re-centres the chapter on an economic question rather than a measurement
audit, after external review established that a joint AI-plus-computerization
model is identified — see `CORRECTION_2026-08-26_separability_verdict.md`.*

---

## 1. The question

> Among occupations with comparable pre-existing computerization, did the
> employment of workers aged 22–25 decline relative to workers aged 26–65 after
> ChatGPT, in occupations with greater LLM-specific exposure?

That is the estimand. The contribution claim is one level up:

> Does the post-2022 young-worker employment gradient associated with AI
> exposure survive correction of occupational crosswalks, adjustment for
> pre-existing computerization and remote work, and tests for pre-existing
> differential trends?

The crosswalk repair, the coverage rule and the pre-registration machinery are
**infrastructure for answering that credibly**, not the contribution. v2 had it
backwards.

## 2. Three concepts, held apart

| concept | definition | primary measure |
|---|---|---|
| **AI exposure** | can an LLM accelerate the occupation's tasks | **Eloundou GPT-4 β** (E1 + ½E2) |
| **Computerization** | prior exposure to conventional software and routine information processing | **Webb software exposure** |
| **Remote work** | location independence; correlated, distinct | Dingel–Neiman, robustness only |

Computerization robustness, in descending priority:

- **archived pre-2022 O\*NET *Working with Computers*** (work-activity descriptor
  `4.A.3.b.1`) — a simple, independent measure with no AI content at all;
- **routine-task intensity** (Autor–Levy–Murnane / Acemoglu–Autor);
- **Frey–Osborne** computerisation probability — *secondary only*, because it
  partly overlaps AI and robotics rather than measuring prior computerization
  cleanly.

**AIOE is an alternative AI measure, never the computerization control.** It is
built from AI capability benchmarks mapped onto O\*NET abilities, so using it as
a computerization proxy would confuse the two constructs it is being asked to
distinguish.

β is chosen as Eloundou's headline definition, on conceptual grounds. It is
**not** chosen because it scores well on any separability statistic — selecting
a measure on a design property is the specification search that
`measurement/CORRECTION_2026-08-25.md` §2 forbids.

*Webb (2020), michaelwebb.co/webb_ai.pdf, constructs software, robot and AI
exposure separately from patent text. **Verify the file contents and record its
sha256 before relying on this** — it is second-hand, and this project has been
wrong four times by that route.*

## 3. Identification

The joint model, on occupation × age-group × month employment counts:

    E[N_oat] = exp[ α_oa + δ_ot + λ_at
                    + β_AI (AI_o × Young_a × Post_t)
                    + β_C  (Comp_o × Young_a × Post_t) ]

`β_AI` answers the advisor's question directly: does LLM exposure predict an
additional young-worker decline **after conditioning on prior computerization**?

Fixed effects absorb occupation-specific levels and trends (α_oa, δ_ot) and
economy-wide age-group shocks (λ_at). Clustered on occupation; wild-cluster
bootstrap primary.

**Young = 22–25, comparison = 26–65, Post = 2022-12 onward.** This matches the
implemented SCC code and the literature being tested. Never assign a current
occupation to a non-employed person.

### 3.1 Is it identified? — measured, not assumed

| measure | R² vs computer proxy | partial variance | VIF | SE inflation | est. conditional MDE | headroom vs 19% |
|---|---:|---:|---:|---:|---:|---:|
| **Eloundou β** | 0.4208 | **57.9%** | 1.73 | 1.31× | 4.82% | **3.9×** |
| Eloundou α | 0.0909 | 90.9% | 1.10 | 1.05× | 3.87% | 4.9× |
| Eloundou γ | 0.4537 | 54.6% | 1.83 | 1.35× | 4.96% | 3.8× |
| AIOE | 0.5792 | 42.1% | 2.38 | 1.54× | 5.63% | 3.4× |

Yes. Even AIOE, the worst case, retains 3.4× headroom. Source:
`measurement/computerization_support.py`, using teleworkability as a stand-in
for computer-based work pending Webb.

**The conditional MDE above is an estimate** — the unconditional 3.44% inflated
by √VIF and the null-size correction. It is not a substitute for §5.

## 4. What is established

| fact | value |
|---|---|
| Wide CPS extract | 9,262,480 rows, 2017-01 → 2026-07 |
| Outcome-blind pre-period file | 6,188,956 rows |
| Occupation clusters / pre-months / planned post | 490 / 66 / 43 |
| Unconditional MDE80 | 3.439% (999 reps, exact seed) |
| Null size / interval coverage | 6.8068% / 93.1932% |
| Computer/math coverage, exact-code vs repaired | 3.33% → 97.7% |
| Strict coverage rule | 88.70%, fails its 90% gate |

## 5. Power must be recomputed for the joint model — BINDING

**The 3.44% MDE does not apply.** It was simulated for an unconditional AI
contrast; adding a collinear regressor changes the sampling distribution. v2
carried the unconditional figure forward and was wrong to.

The new simulation must:

- use the **observed joint distribution** of AI and computerization, preserving
  their correlation;
- inject an AI-specific effect while holding β_C fixed;
- use the exact joint estimating equation above;
- report conditional MDE, realised type-I error, and the effective number of
  occupations identifying β_AI;
- use wild-cluster bootstrap inference.

No post-period outcomes are needed. Until this runs, no MDE may be quoted.

## 6. The outcome-blind separability gate

Before any post-period employment is opened, report — not conceal:

1. Employment-weighted correlation between AI and computerization.
2. Partial variance of AI after controlling for computerization.
3. VIF and expected SE inflation.
4. Effective number of occupations identifying β_AI.
5. Share of residual variation supplied by each major occupational family.
6. Named occupations where AI and computerization diverge.
7. Common-support employment coverage.

**If conditional support turns out extremely weak**, the chapter's conclusion
becomes: *occupation-level public data cannot separately attribute the
young-employment pattern to LLM exposure rather than prior computerization.*
That is informative and it is a smaller chapter. Current numbers do not point
there, but the gate decides, not the plan.

## 7. Three complementary tests

**Joint horse race — primary.** §3's equation, both terms simultaneously.

**Residualized AI.** Regress AI on flexible computerization controls at the
occupation level, `AI_o = f(Comp_o) + AI⊥_o`, then estimate `AI⊥ × Young ×
Post`. Shows what the component of AI exposure unpredictable from
computerization is associated with.

**Divergence occupations — presentation.** The 2×2 of high/low AI against
high/low computerization. The off-diagonal cells are the interesting ones and
they carry the named occupations. **The continuous model stays primary**; the
four-group version discards information and must not be read as the
identification.

## 8. Timing — supporting evidence

Separate monthly event-study gradients for AI and computerization. Evidence
consistent with an AI-specific channel:

- no differential AI trend in 2017–2019;
- 2020–21 pandemic treated separately;
- no AI-specific divergence before late 2022;
- divergence appearing later, conditional on computerization;
- persistence or strengthening through the 2025–26 extension.

Descriptive, not causal — but far more discriminating than a single post
interaction. v2 made this primary on a mistaken premise; it is supporting
evidence, and the 2017–2019 placebo remains a kill condition (§12.1).

**The inference is asymmetric, and the paper must say so in both directions.**

*A pre-2022 gradient* demonstrates non-parallel trends or confounding. It does
**not** prove the exposure measure "is a computerization index" — v2's §8a
language claimed more than the test delivers.

*No pre-trend* does **not** establish that the post-2022 effect is AI. A break
at the end of 2022 is consistent with at least five other stories, and none is
excluded by a flat pre-period:

- the technology-sector correction and layoff wave;
- interest-rate changes, which bind hardest on long-horizon hiring;
- return-to-office mandates;
- post-pandemic normalization of a distorted 2021–22 labour market;
- shifts in occupational composition within the CPS sample.

Interest rates and return-to-office enter as controls (Tables 2 and 4). The
others are stated as limits on interpretation, not modelled away. **The chapter
claims an association conditional on computerization, not identification of an
AI causal effect**, and every branch of §11 is written to that standard.

## 9. Where the effect comes from

**Do not infer mechanism from whether the crosswalk repair moves the aggregate
coefficient.** v2 did, and it cannot distinguish "AI-specific" from
"software-developer-specific".

### 9.1 The crosswalk decomposition — four rows, in this order

Repairing the crosswalk does two things at once: it corrects the exposure value
and it re-admits occupations the exact-code merge dropped. Those must be
separated, because the second alone would move the coefficient by restoring the
most computerized occupations in the economy.

| # | specification | isolates |
|---|---|---|
| 1 | original exposure, original matched support | the published baseline |
| 2 | **repaired** exposure, **same** support as row 1 | the measurement correction, holding the sample fixed |
| 3 | repaired exposure, **expanded** support | what re-admitting dropped occupations adds |
| 4 | expanded support, **excluding computer and mathematical occupations** | whether row 3 is just software developers |

Row 1 → 2 is the measurement effect. Row 2 → 3 is the composition effect.
Row 4 is the direct test of the software-developer explanation. Reporting only
the aggregate change conflates all three.

### 9.2 Where the effect sits

- estimates for computer/math, office/administrative, business/finance, other;
- leave-one-major-group-out;
- each group's contribution to the overall coefficient;
- a formal test of equality across groups.

## 9a. Position in the literature — VERIFY BEFORE THE FREEZE

| finding | status |
|---|---|
| Dallas Fed and Anthropic publish related CPS young-vs-older patterns | reported; **locators outstanding** |
| EHP and Tucker use adjacent age-interaction designs | reported; **locators outstanding** |
| Broad novelty ("nobody has looked at young vs older") | **FAILS.** Not claimed here |
| Webb (2020) separates software, robot and AI exposure | second-hand; **not yet verified**, file and sha256 required |
| A pre-registered, power-stated public-data test of this claim | **not yet searched** — pre-analysis registries |
| A joint AI-versus-computerization test on young-worker employment | no prior work identified |

The chapter does not claim to discover the young-versus-older pattern. What no
prior work addresses is whether it survives conditioning on prior
computerization. That claim stands or falls on the last two rows, and both are
outstanding.

## 10. Main tables

1. AI versus computerization: measurement and identifying support.
2. **Joint AI–computerization employment estimates — the central table.**
3. Event study and pre-period placebos.
4. Alternative AI and computerization measures on common support.
5. Crosswalk and coverage decomposition.
6. Entrant hiring versus separations, and the post-2025 extension.

Telework enters as a control in Tables 2 and 4.

## 11. Interpretation, fixed in advance

- **AI remains, computerization does not** → an AI-specific post-2022 component.
- **AI collapses after conditioning** → existing AI estimates substantially
  proxy for older computerization.
- **Both remain** → two distinct labour-market gradients.
- **Neither precise** → public occupational data cannot distinguish them.
- **AI appears only in particular families** → a narrower mechanism, not a
  general AI effect.

All five are reportable. The first run of each frozen table is the reported run.

## 12. Kill conditions

1. **The AI gradient is present in 2017–2019**, conditional on computerization.
   The measure is then a computerization index and that is a different paper.
2. **A pre-registered, power-stated public-data test already exists.**
3. **The seal breaks before the tag.** The chapter can be written but must be
   labelled post-hoc.
4. **The conditional MDE from §5 approaches the contested magnitude.** Nothing
   in the estimates suggests this — headroom is 3.4–4.9× — but §5 decides.

## 13. Seal protocol

1. Coverage-rule pre-specification reflecting the §6 ruling. *(pending)*
2. Webb, Frey–Osborne, RTI, archived O\*NET obtained and crosswalked. *(pending)*
3. §6 separability gate run and reported. *(pending)*
4. §5 joint-model power simulation. *(pending)*
5. Novelty locators and registry search. *(pending)*
6. Everything pushed to `origin`. *(pending)*
7. `DESIGN_FREEZE_v1.md` committed with the panel sha256 and empty shells.
8. `v1.0-preregistered` tagged.
9. **Only then** may a post-period outcome be opened.

Machine-checked: `python yax/gates.py --power-aggregate <aggregate>.json`.

## 13a. Why the design changed after work began

Recorded so it can be checked rather than asserted.

The computerization dimension was added on 2026-08-26, after the extract, the
bridge, the exposure lookup and the unconditional power run were complete. Two
facts make it a legitimate pre-registration amendment rather than specification
search:

1. **No post-period outcome has been opened.** The pre-period file was built
   outcome-blind and post rows were rejected before protected fields were
   decoded. Nothing about the design was chosen in light of a result.
2. **It arose from a substantive question from the student's advisor**, not from
   an unfavourable estimate — there is no estimate.

The failed 90% coverage rule and its receipt are preserved permanently, as is
every superseded plan version. A reader can reconstruct the order of events from
git history; `yax/gates.py::gate_prespec_precedes_tag` checks the part that
matters mechanically.

## 14. Standing rules

- LLM output is not a source of facts.
- Don't know → stop. `NEED_HUMAN`, never guess-fill.
- Never specification-search. First run of a frozen table is the reported run.
- Licensed microdata never enters the git work tree. Never `git add -A`.
- A sentence describing a computed number must be checkable against the
  artifact that produced it.
- **State which statistic answers the question before computing one.** A
  diagnostic must be justified by the estimator it informs — for a continuous
  conditional model that is partial variance and VIF, never a discretized cell
  share. Added after the fourth instance of the same failure mode; see
  `CORRECTION_2026-08-26_separability_verdict.md`.
