# Chapter scope v1 — 2026-08-25

**Third dissertation chapter. Independently authored. Not the job-market paper.**

Supersedes `dax/memo/design_memo_v1.md` as the active research object. That
memo is archived, not retracted — see `dax/memo/DAX_ARCHIVE_2026-08-25.md`.

## 1. The question

> Does the occupational-code crosswalk decision — which every paper in this
> literature makes and none reports — change the estimated young-worker AI
> exposure gradient, and what magnitudes can nationally representative data
> detect at all?

One bounded contribution: the sensitivity of a headline labour-market finding
to an unglamorous measurement decision, plus the detectable range in public
data. Not a structural index, not a theory of occupational adjustment, not a
firm-level mechanism the data cannot observe.

**Deliberately NOT "is the deterioration robust across measures?"** That
question is crowded — see §2.4 — and arriving at a crowded question with a
smaller sample is a bad position.

## 2. Why the question is worth asking

Three facts, all measured in this repo, none taken on faith:

1. **Merging the standard measures requires a crosswalk decision that papers
   make silently.** AIOE (Felten, Raj & Seamans) and Dingel–Neiman publish on
   an identical list of 774 SOC 2010 codes with full coverage. SOC 2018
   renumbered essentially all of major group 15, so an **exact-code merge**
   onto a 2018-vintage target drops **19.65% of employment** and **96.7%** of
   major group 15.

   This is a property of the merge, not of the measures. AIOE covers Software
   Developers at 15-1132 (+1.20) and 15-1133 (+1.28); OEWS 2021 calls them
   15-1252. Nothing is missing from AIOE. What is unresolved is whether the
   crosswalk choice — and every paper in this literature makes one — moves the
   estimated coefficient.
2. **AI exposure and remote-work feasibility are entangled.** Employment-
   weighted R² against Dingel–Neiman teleworkability runs 0.09 (Eloundou α) to
   0.58 (AIOE). Emanuel, Harrington & Pallais attribute 64% of the rise in
   young college-graduate unemployment to remote work; the young-worker AI
   literature does not generally control for it.
3. **The variation that would separate them is thin.** After removing
   teleworkability, 14 occupations carry half the employment-weighted residual
   variance of Eloundou α; its effective number of contributing occupations is
   28 out of 669. Dropping SOC major group 43 moves its R² from 0.0909 to
   0.0103.

Source: `dax/w2/exposure_gate/AUDIT_RESULTS.md`, receipt and lineage alongside.

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

## 3. The pre-commitment that makes this chapter completable

**The chapter's claim is about what nationally representative data can and
cannot establish.** It is therefore complete under either branch of the
central estimate, using identical tables and figures:

- **Estimates informative** → a sensitivity paper. Whether and how far the
  crosswalk decision moves the young-worker gradient, and which measures the
  movement is largest for.
- **Estimates imprecise** → a bounds paper, and it must be the *strong* version
  of that. "Nationally representative data cannot adjudicate this" is a
  footnote in someone else's paper, not a chapter. The chapter version is:
  **state the minimum effect CPS can detect at conventional power, then report
  whether the published proprietary-data estimate falls inside or outside that
  interval.** If it falls inside, public data is simply silent and that is a
  quantified statement about the evidence base. If it falls outside, the
  proprietary estimate is larger than anything CPS could have missed, which is
  a substantive finding about the two data sources.

  This distinction is the difference between a chapter and a note. Do not write
  the weak version.

This is recorded *before* any estimate is produced. It is not a licence to
report whichever branch looks better — **both branches are written from the
same pre-specified tables, and the first run is the reported run.** Section 6
freezes the specification precisely so that this pre-commitment cannot decay
into specification search.

## 4. Data

| input | source | state |
|---|---|---|
| CPS analysis panel | IPUMS, SCC `dax-private/ipums/w5_analysis_extract_7/` | built, 242,474 person-months, 2021-11 → 2026-07 |
| CPS pre-event panel | IPUMS, SCC `w1_preperiod_extract_6/` | built, 71,322 rows |
| CPS wide panel (2017-01 →) | IPUMS, spec at `dax/memo/power_calcs/ipums_ai_telework_extract_v1.json` | **NOT SUBMITTED — critical path** |
| AIOE | Felten, Raj & Seamans (2021) | vendored |
| Eloundou α/β/γ, GPT-4 + human | Eloundou et al. (2023) | vendored |
| Dingel–Neiman teleworkable | Dingel & Neiman (2020) | vendored |
| OEWS 2021 | BLS | built |
| OEWS 2019 + recent year | BLS | **not obtained** |
| SOC 2010 → 2018 crosswalk | BLS | **not obtained — blocks the repair** |
| Webb (2020), Frey–Osborne (2017) | public | not obtained, optional |

**The wide extract is on the critical path.** The existing panel begins
2021-11, giving roughly twelve months of pre-period before the ChatGPT launch
and placing the 2020 remote-work shock entirely outside the window. Pre-trends
and remote work are two of the four robustness dimensions; neither can be
addressed on the 2021-11 panel. Submit it first.

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
- `X_it`: education, sex, race, state, and a state × month fixed effect in the
  saturated row.

**Event-time.** Same, with month-relative-to-2022-11 indicators, 2022-10
omitted. Pre-period coefficients are the pre-trend test — **reported whatever
they show**, never used to select a window.

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

Task briefs in `dax/paper/briefs/`. `C0_CONTEXT_PACK.md` is the header pasted
at the top of every task prompt; C1–C4 are one task each, run in order, one per
session.

Four weeks of work. Plan seven to nine calendar weeks: the IPUMS extract has
queue time, the crosswalk repair has never been run against the official file,
and there is no second person to unblock a failure.
