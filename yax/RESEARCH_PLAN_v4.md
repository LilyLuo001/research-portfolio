# YAX — research plan v4

**Young-worker AI Exposure.** Third dissertation chapter. Independently
authored. Not the job-market paper.

*Plan date 2026-08-26. Supersedes v3 after a third review round found six
internal contradictions and overclaims. v3 is retained for revision history.
**Nothing here is frozen.** §3 states what is unresolved and §13 is the order of
work that resolves it.*

---

## 1. The question

> Among occupations with comparable pre-existing computerization, did the
> employment of workers aged 22–25 decline relative to workers aged 26–65 after
> ChatGPT, in occupations with greater LLM exposure?

The contribution claim, one level up:

> Does the post-2022 young-worker employment gradient associated with AI
> exposure survive correction of occupational crosswalks, adjustment for
> pre-existing computerization and remote work, and tests for pre-existing
> differential trends?

The crosswalk repair, the coverage rule and the design-freeze machinery are
**infrastructure for answering that credibly**, not the contribution.

## 2. Three concepts, held apart

| concept | definition | measure |
|---|---|---|
| **AI exposure, broad** | tasks an LLM accelerates, **including those needing complementary LLM-powered software** | Eloundou **β** = E1 + ½E2 — *primary* |
| **AI exposure, direct** | tasks an LLM accelerates **on its own** | Eloundou **α** = E1 — *pre-specified contrast* |
| **Computerization** | prior exposure to conventional software and routine information processing | Webb **software** exposure |
| **Remote work** | location independence; correlated, distinct | Dingel–Neiman + constructed occupation-month telework |

**β is "broad LLM-plus-software exposure", not "LLM-specific".** Eloundou et al.
distinguish what an LLM does alone (E1) from the much larger set reachable with
complementary software built on top (E2). β bundles half of E2 in. In a chapter
asking whether AI exposure is really computerization, describing the
software-inclusive measure as LLM-specific would come close to assuming the
answer. β stays primary because it is the source paper's headline definition —
a conceptual choice, not a choice on any separability statistic — and **α is
reported alongside it in every main table** as the direct-LLM contrast. If the
gradient appears under β but not α, that is evidence about complementary
software, and it is reported as such.

Computerization robustness, in descending priority:

- **O\*NET *Interacting With Computers***, work-activity descriptor
  `4.A.3.b.1` (the official 24.3 element name).
  Contains no AI content, so it cannot smuggle the treatment into the control.
- **routine-task intensity** (Autor–Levy–Murnane / Acemoglu–Autor).
- **Frey–Osborne** — *secondary only*: it bundles AI and robotics into
  automation risk rather than measuring prior computerization cleanly.

**AIOE is an alternative AI measure and is barred from the computerization
role.** It is built from AI capability benchmarks mapped onto O\*NET abilities.

## 3. What is unresolved — read before §4

**The joint design is not yet established as feasible.** Proxy diagnostics
suggest it may be, and that is all they do.

`measurement/computerization_support.py` uses Dingel–Neiman teleworkability as a
stand-in for computerization. Teleworkability is not computerization: an
occupation can be computer-intensive and not teleworkable, and the reverse.
Every number it produces is provisional. **No conditional MDE and no headroom
figure from that script may be quoted** — v3 quoted them in §3.1 while §5
simultaneously forbade quoting any MDE, which was a contradiction and is
removed here.

Unresolved, in the order §13 resolves it:

1. Webb software exposure: file, checksum, native taxonomy, merge — **and see
   §6.1, which is a blocker.**
2. O\*NET 24.3 `4.A.3.b.1` obtained and constructed.
3. Partial-support diagnostics on the **real** computerization measures.
4. The exact joint-model power simulation. Until it runs, **no MDE exists** for
   this design.
5. Novelty locators and the registry search.

## 4. What is established

| fact | value |
|---|---|
| Wide CPS extract | 9,262,480 rows, 2017-01 → 2026-07 |
| Outcome-blind pre-period file | 6,188,956 rows |
| Occupation clusters / pre-months / planned post | 490 / 66 / 43 |
| **Unconditional** MDE80, AI alone | 3.439% — *does not apply to the joint model* |
| Null size / interval coverage | 6.8068% / 93.1932% |
| Computer/math coverage, exact-code vs repaired | 3.33% → 97.7% |
| Strict coverage rule | 88.70%, fails its 90% gate |
| Wide extract occupation variable | **`OCC2010` only — no `OCC1990`** |

## 5. The joint model

    E[N_oat] = exp[ α_oa + δ_ot + λ_at
                    + β_AI (AI_o × Young_a × Post_t)
                    + β_C  (Comp_o × Young_a × Post_t) ]

Occupation × age-group × month employment counts. Young = 22–25, comparison =
26–65, Post = 2022-12. Clustered on occupation; wild-cluster bootstrap primary.
Never assign a current occupation to a non-employed person.

**Power must be simulated for this exact equation** on the observed joint
distribution of AI and computerization, preserving their correlation, injecting
an AI-specific effect with β_C held fixed, and reporting conditional MDE,
realised type-I error, and the effective number of occupations identifying
β_AI. No post-period outcomes are needed. **Until it runs, no MDE may be
quoted anywhere.**

## 6. Operationalization — fixed here, before the freeze

### 6.1 Webb software exposure — BLOCKER

Webb (2020) constructs software, robot and AI exposure from a common
task–patent framework; the conceptual claim is verified from the paper.
`michaelwebb.co/webb_ai.pdf`.

**The data file is not verified**, and the merge path is not what the rest of
this project uses. Webb exposure is commonly distributed on **`occ1990dd`**, and
existing CPS implementations key it on IPUMS **`OCC90`** rather than treating it
as another SOC-2010 measure — see EIG's replication repository,
`github.com/EIG-Research/AI-unemployment`.

**The wide extract carries `OCC2010` and no `OCC1990`.** Verified against
`dax/memo/power_calcs/ipums_ai_telework_extract_v1.json`: 26 variables, one
occupation code, `OCC2010`. So Webb cannot be merged as things stand. Two ways
out, and the choice is fixed **before** the freeze:

- **Amend the extract** to add `OCC1990`, and re-derive. Cleanest; the amendment
  is outcome-blind today and impossible after the tag.
- **Bridge `OCC2010` → `occ1990dd`** with a documented, cited crosswalk,
  reporting coverage and the occupations lost.

Record file URL, sha256, native taxonomy, and merge coverage either way.
`IND1990` is already in the extract, which matters for §8.

### 6.2 O\*NET *Interacting With Computers* — frozen

| choice | value | why |
|---|---|---|
| release | **O\*NET 24.3, May 2020** | last release before the O\*NET-SOC 2019 transition; pre-dates LLM diffusion |
| descriptor | **`4.A.3.b.1`** | using computers and software to program, enter data, or process information |
| scale | **Importance primary**, Level as robustness | |

Release 25.1 introduced the new taxonomy, so 24.3 keeps the measure on one
vintage. Historical releases are downloadable from
`onetcenter.org/db_releases.html`. **Current O\*NET ratings must not be used** —
they are collected after LLM diffusion began and are not a measure of *prior*
computerization. Record the release and its sha256.

## 7. Where the effect comes from

### 7.1 The crosswalk decomposition — four rows, one fixed scale

Repairing the crosswalk corrects exposure values **and** re-admits occupations
the exact-code merge dropped. Reporting only the aggregate change conflates
them.

| # | specification | isolates |
|---|---|---|
| 1 | original exposure, original matched support | **naïve exact-code baseline** |
| 2 | repaired exposure, **same** support as row 1 | the measurement correction, sample fixed |
| 3 | repaired exposure, **expanded** support | what re-admitting occupations adds |
| 4 | expanded support, **excluding SOC major group 15** | dependence on the computer/mathematical major group |

Row 1 → 2 is measurement; row 2 → 3 is composition; row 4 is the group
dependence.

**Standardization uses one fixed reference distribution across all four rows** —
the employment-weighted mean and sd of the repaired measure on the expanded
support. Standardizing within each row would change what a one-sd increase
means as the support changes, and the coefficients would not be comparable.

Row 1 is a *naïve exact-code baseline*, not "the published baseline": no named
paper's procedure is reproduced here. Row 4 tests dependence on the whole
major group, which is more than software developers.

### 7.2 Where the effect sits

Estimates for computer/math, office/administrative, business/finance and other;
leave-one-major-group-out; each group's contribution to the overall
coefficient; a formal test of equality across groups.

## 8. Confounds: what is controlled and what is not

**Return to office — specified, or not claimed.** Occupation-month telework
rates constructed **from workers aged 26–65 only**, never from the young
worker's own `TELWRKHR`/`TELWRKPAY`, which begin 2022-10, are asked only of
people employed and at work, and are therefore post-treatment and conditioned
on the outcome. Fixed in advance: age range 26–65; minimum cell size 30
unweighted; 3-month centred moving average; one-month lag. Occupation-months
below the cell floor are missing, not imputed.

**Interest rates — an interpretation limitation, not a control.** A national
rate series is absorbed entirely by the age × month and occupation × month
fixed effects. It can only enter interacted with a *predetermined* occupation
or industry measure of rate sensitivity. `IND1990` is in the extract, so such a
measure is constructible; if a credible one is not built before the freeze,
interest rates are stated as a limitation and **not described as controlled**.

**Not modelled away, stated as limits:** the technology-sector correction,
post-pandemic normalization of a distorted 2021–22 labour market, and shifts in
CPS occupational composition.

**The chapter claims an association conditional on computerization, not
identification of an AI causal effect.**

## 9. Timing — supporting evidence

Separate monthly event-study gradients for AI and computerization; 2020–21
treated separately; the 2025–26 extension as a joint early-versus-extension
model and Wald test.

**The inference is asymmetric in both directions.** A pre-2022 gradient
demonstrates non-parallel trends or confounding; it does **not** establish what
the exposure measure represents. No pre-trend does **not** establish that the
post-2022 effect is AI — see §8 for what else a late-2022 break is consistent
with.

## 9a. Position in the literature — resolved

Every row was opened at the primary source named in it, not taken from a
secondary summary. Retrieved 2026-08-27.

| prior work | locator | design | outcome and unit |
|---|---|---|---|
| Tyler Atkinson and Shane Yamco, "Young workers' employment drops in occupations with high AI exposure", Federal Reserve Bank of Dallas, 2026-01-06 | `https://www.dallasfed.org/research/economics/2026/0106` | CPS, ages 20–24 against 25–55, by AI exposure | employment, occupation × month |
| Maxim Massenkoff and Peter McCrory, "Labor market impacts of AI: A new measure and early evidence", Anthropic, 2026-03-05 | `https://www.anthropic.com/research/labor-market-impacts` | CPS, ages 22–25, by a new exposure measure | unemployment and job-finding **flow**, not employment stock |
| Lee C. Tucker, "You're (not) hired: Artificial intelligence and early career hiring in the Quarterly Workforce Indicators", U.S. Census Bureau, CES working paper 26-27, April 2026 | `https://www2.census.gov/library/working-papers/2026/adrm/ces/CES-WP-26-27.pdf`, sha256 `bc4c7e6da652f79fd796aecc008ff1219138eff9c4a1cf44d3411160eec039c6` | ages 22–24 on ages 25–54, interacted with period × most-exposed quintile | **hiring**, QWI industry × state |
| Natalia Emanuel, Emma Harrington and Amanda Pallais, "The Power of Proximity to Coworkers: Training for Tomorrow or Productivity Today?", NBER working paper 31880, November 2023 | `http://www.nber.org/papers/w31880`, revision `w31880.rev0.pdf`, sha256 `48fdfa1c0c4c54c2c87784249245373c9dbadfec61ff3b0bf697e2749cf2746b` | young and junior against senior engineers at one Fortune 500 firm, standard errors clustered by team | online feedback and programming output, **within-firm** |
| Michael Webb, "The Impact of Artificial Intelligence on the Labor Market", 2020 | see §6.1 | separates software, robot and AI patent exposure | occupation, `occ1990dd` |

Three corrections this search forced, recorded rather than smoothed over:

- **EHP is farther from this design than §9a previously implied.** It is not an
  AI paper, does not use the CPS, and its outcome is not employment. Its age
  contrast is junior-versus-senior software engineers inside a single firm.
  It belongs here as a precedent for age-interaction *designs*, nothing more.
- **Anthropic's outcome is a flow, not a stock.** Verbatim: "we find no
  systematic increase in unemployment for highly exposed workers since late
  2022, though we find suggestive evidence that hiring of younger workers has
  slowed in exposed occupations". A slower hiring flow and a lower employment
  stock are different claims; this chapter measures the stock.
- **The "roughly 14%" figure carried in the earlier internal audit
  (`dax/paper/research/NOVELTY_GATE_2026-08-25.md`) could not be confirmed** on
  the Anthropic page as published. It is not repeated here.

### Has anyone run a pre-registered, power-stated test of this claim on public data?

**No such registration was found.** §12.2 does not trigger. Absence found in a
bounded search is not proof of absence, so the search itself is recorded:

- **AEA RCT Registry.** Site search requires sign-in; queries were run
  site-scoped instead. The registry is by construction for *randomized* trials,
  so an observational CPS difference-in-differences would not be registrable
  there. The one adjacent entry, trial #18261 "Adapting to AI: How Information
  on Occupational AI Exposure Affects Educational Decisions", is an
  information-provision experiment on educational choice, not an employment test.
- **OSF Registries.** There is no general search endpoint; `filter[title]` is
  exact-match, so `filter[title][icontains]` was enumerated term by term.
  Counts returned: "generative AI" 384 (fully paged), "early career" 31,
  "occupational exposure" 21, "AI exposure" 7 (each description read), "AI
  labor" 1, and zero for "artificial intelligence employment", "labor market
  artificial intelligence", "young workers employment", "ChatGPT labor", "AI and
  jobs", "AI employment" and "automation employment".
- **Closest candidates, all rejected on inspection:** two Thai Labour Force
  Survey studies (`osf.io/wrgmj`, `osf.io/jv6wn`), a Russian occupational
  measurement project (`osf.io/mgjby`), and a postsecondary-enrollment study.
  None is a United States CPS young-versus-older employment test.

The chapter does not claim to discover the young-versus-older pattern — the
first two rows above establish that it is already reported. What no prior work
identified here addresses is whether that pattern survives conditioning on
pre-existing computerization, which is the question §2 poses. The tag this
search supports is `design-freeze`; nothing above makes this chapter
preregistered.

## 10. Main tables

1. AI versus computerization: measurement and identifying support.
2. **Joint AI–computerization employment estimates — the central table**, with
   β and α columns.
3. Event study and pre-period placebos.
4. Alternative AI and computerization measures on common support.
5. Crosswalk decomposition, §7.1's four rows on one fixed scale.
6. Entrant hiring versus separations, and the post-2025 extension.

## 11. Interpretation, fixed in advance

- **AI remains, computerization does not** → an AI-specific post-2022 component.
- **AI collapses after conditioning** → existing AI estimates substantially
  proxy for older computerization.
- **Both remain** → two distinct labour-market gradients.
- **Neither precise** → public occupational data cannot distinguish them.
- **β but not α** → the gradient runs through complementary software, not
  direct LLM capability.
- **Only in particular families** → a narrower mechanism, not a general effect.

All six are reportable. The first run of each frozen table is the reported run.

## 12. Kill conditions

1. **A material 2017–2019 AI gradient**, conditional on computerization. This
   rejects the simple parallel-trends interpretation. Report it, and either
   estimate a pre-specified differential-trend model or restrict the chapter to
   a descriptive decomposition. It does **not** by itself establish that the
   measure is a computerization index.
2. **A pre-registered, power-stated public-data test already exists.**
3. **The seal breaks before the tag.** The chapter can be written but must be
   labelled post-hoc.
4. **The §5 conditional MDE approaches the contested magnitude.**

## 13. Order of work

1. Verify and vendor Webb software exposure; resolve the §6.1 `OCC1990` blocker.
2. Obtain O\*NET 24.3, construct `4.A.3.b.1`, freeze it.
3. Run partial-support diagnostics on the **real** measures.
4. Run the exact joint-model power simulation.
5. Novelty locators and registry search.
6. Push everything to `origin`.
7. Commit `DESIGN_FREEZE_v1.md` with the panel sha256 and empty shells.
8. Tag **`v1.0-design-freeze`**.
9. Only then may a post-period outcome be opened.

**The tag is `v1.0-design-freeze`, not `v1.0-preregistered`.** Nothing has been
deposited in an external registry, and "pre-registered" claims a public,
timestamped, third-party record that a git tag is not. If the design is
deposited with the AEA RCT Registry or OSF, the deposit id goes in
`DESIGN_FREEZE_v1.md` and the stronger word becomes available.

Machine-checked: `python yax/gates.py --power-aggregate <aggregate>.json`.

## 13a. Why the design changed after work began

The computerization dimension was added 2026-08-26, after the extract, bridge,
exposure lookup and unconditional power run were complete. It is a legitimate
amendment, not specification search, because **no post-period outcome has been
opened** — the pre-period file was built outcome-blind and post rows were
rejected before protected fields were decoded — and because it arose from a
substantive question from the student's advisor rather than from an unfavourable
estimate, of which there are none. Every superseded plan version and the failed
90% coverage receipt are preserved; the ordering is checkable in git history.

## 13b. Webb software exposure is a different construct — CORRECTED

**An earlier version of this section claimed the Webb `occ1990dd` merge was
broken. That claim was wrong and is withdrawn.**

The evidence that prompted it stands: `webb_pct_software` correlates with
essentially nothing else.

| pair | r |
|---|---:|
| Webb × O\*NET computers importance | −0.106 |
| Webb × O\*NET computers level | −0.003 |
| Webb × RTI | −0.028 |
| Webb × Frey–Osborne | +0.104 |
| *O\*NET importance × O\*NET level* | *+0.912* |
| *RTI × Frey–Osborne* | *+0.448* |

But the ranking is coherent, not scrambled. Highest: broadcast equipment
operators, power plant operators, water and sewage treatment operators,
locomotive operators, elevator installers, chemical engineers. Lowest: barbers,
podiatrists, performers, mail carriers, hotel clerks. Those are **process- and
machine-control occupations at the top and no-patentable-task occupations at
the bottom** — which is what exposure to *software patents* should look like.
Computer programmers sit at 98, which a misaligned join would not produce.

**Webb measures whether software patents describe your tasks. O\*NET
`4.A.3.b.1` measures whether you use a computer.** Those are different
constructs, and near-zero correlation between them is a property of the
measures, not a defect.

So the Y1b conclusion — *"computerization" is not one interchangeable control;
all frozen measures should be reported* — was **correct**, and withdrawing it
was my error. It is reinstated. The chapter reports all five and does not treat
them as substitutes.

`gate_convergent_validity` still earns its place, but as a **flag demanding an
explanation, not a verdict of breakage**. A measure agreeing with nothing is
either a merge failure or a distinct construct, and only inspecting the ranking
distinguishes them. Its FAIL on Webb is now expected and is cleared by the
construct-validity evidence recorded here.

**Two items from the same run still stand:**

- The diagnostics ran on a **13-month support, 2021-11 to 2022-11**, not the
  66-month pre-period the frozen design uses. Occupation counts read 442, 445
  and 490 across three artifacts. The freeze must state which support it pins.
- A discarded run used occupation weights from 2022-12 through 2023-02. No
  outcome field was accessed, the output was overwritten before commit, and the
  committed receipt rejects `month >= 2022-12-01` before any weight enters. The
  seal held and the near-miss was handled correctly.

## 14. Standing rules

- LLM output is not a source of facts.
- Don't know → stop. `NEED_HUMAN`, never guess-fill.
- Never specification-search. First run of a frozen table is the reported run.
- Licensed microdata never enters the git work tree. Never `git add -A`.
- A sentence describing a computed number must be checkable against the
  artifact that produced it.
- State which statistic answers the question before computing one.
- **A measure agreeing with no other is a question, not a verdict.** It is
  either a merge failure or a distinct construct, and only inspecting the
  ranking tells you which. Check convergent validity — a control that failed to
  join looks exactly like one that is cleanly orthogonal, and both flatter every
  identification statistic — but do not call it broken before looking at what it
  ranks highest and lowest. Added after Y1b, then corrected: I called Webb
  broken on the correlations alone and the ranking showed it was not.
- **A plan may not assert as settled anything its own later sections list as
  pending.** Added after v3 declared the joint design identified in §3.1 while
  §5–6 said the measures and the simulation were outstanding.
