# Y1b — Separate AI exposure from computerization

*Prepend `Y0_CONTEXT_PACK.md`. Runs before the freeze. Not optional.*

## Why

An AI-exposure gradient may be a computerization gradient wearing a new name.
AIOE is built by mapping AI capability benchmarks onto O\*NET **abilities** —
comprehension, deductive reasoning, information ordering — the same items that
load on routine-cognitive measures. It was not constructed to separate the two.

Three things follow, and the third is what makes this urgent:

1. Computerization-exposed occupations have been on differential employment
   trends for decades. A DiD switching at 2022-11 will attribute a continuing
   trend to ChatGPT.
2. `computerization_support.py` already measures the cross-sectional damage
   using teleworkability as a proxy. **AIOE's clean cell — high exposure, no
   computer-desk character — holds 1.61% of employment.** A horse-race
   regression is not identified off that.
3. The chapter's own central table adds computer occupations back (3.33% →
   97.7%). If the vintage repair moves the coefficient, the chapter currently
   cannot say whether that is AI exposure measured properly or the most
   computerized occupations in the economy being restored to the sample.

**A control added after outcomes are seen is specification search.** This must
enter the pre-specification before the tag or it cannot be done cleanly at all.

## The approach, in order of identification strength

### 1. Timing — primary

Computerization is a decades-long trend; generative AI is a dated shock. This
works **even under near-perfect cross-sectional collinearity**, which is what
item 2 above says we have, so it does not depend on a clean cell existing.

- Estimate the exposure gradient **year by year across the 66-month
  pre-period**, and on 2017–2019 separately.
- If AI exposure predicts young-worker employment decline in 2017–2019 —
  before any LLM existed — the measure is loading on computerization.
- Reframe the existing 2018-11 placebo: it is not a generic design check, it
  is *the* confound test. Report it as such.
- The post-2022 question then becomes whether there is a **break** on top of a
  trend, not whether a level gradient exists.

### 2. Webb (2020) — secondary

Webb reportedly constructs separate exposure measures for **software, robots
and AI** from patent text: same construction, same source, differing only in
patent class. That makes the software-vs-AI contrast interpretable in a way a
generic control is not.

**Verify the contents before relying on any of that** — it is second-hand and
this project has been wrong three times by exactly that route. Record the URL,
the file, and its sha256.

### 2b. Archived pre-2022 O\*NET "Working with Computers"

Work-activity descriptor **`4.A.3.b.1`**. The cleanest computerization measure
available: simple, independent, and containing no AI content whatsoever, so it
cannot smuggle the treatment into the control.

Use a **pre-2022 archived release** — current O\*NET ratings are collected after
LLM diffusion began and are not a clean measure of *prior* computerization.
Record the release version and its sha256.

### 3. Frey–Osborne and RTI — defensive rows

A routine-task-intensity index built by the Autor–Levy–Murnane /
Acemoglu–Autor recipe, and Frey–Osborne (2017) computerisation probability.

**Frey–Osborne is secondary only.** It bundles AI and robotics into an
"automation risk" score rather than measuring prior computerization cleanly, so
it partly contains the treatment. Report it, do not lean on it. RTI needs O\*NET
work-context and work-activity items that `onet_task_weights.parquet` does not
carry — it holds task-level importance and frequency only — so the required
O\*NET files must be obtained.

Expected by any labour economist. Cheap. Report as rows, not as identification.

### 4. Re-run the support check against the real measures

`computerization_support.py` currently uses teleworkability as a proxy and says
so loudly. Re-run it against Webb-software, Frey–Osborne and RTI. **Report the
verdict whatever it is.** If the clean cell stays below the 5% floor for every
computerization measure, the paper says the horse race is not identified and
leans on the timing test instead. That is a finding, not a failure.

## The crosswalk decomposition — build this table

Repairing the crosswalk corrects exposure values **and** re-admits dropped
occupations. Separate them, or a coefficient move cannot be interpreted:

| # | specification | isolates |
|---|---|---|
| 1 | original exposure, original matched support | published baseline |
| 2 | repaired exposure, **same** support as row 1 | measurement correction alone |
| 3 | repaired exposure, expanded support | what re-admitting occupations adds |
| 4 | expanded support, **excluding computer/math occupations** | whether row 3 is just software developers |

Row 1 → 2 is measurement; row 2 → 3 is composition; row 4 tests the
software-developer explanation directly. The support definitions for rows 1–4
must be fixed and committed **before** the freeze, since they determine the
estimation samples.

## Crosswalk note

Webb and Frey–Osborne are near-certainly SOC 2010 vintage, like AIOE and
Dingel–Neiman. The chapter's own vintage repair applies unchanged. Run them
through it and report coverage before and after, exactly as for AIOE.

## Definition of done

- Webb, Frey–Osborne and RTI obtained, crosswalked, merged, with receipts and
  source sha256s.
- `computerization_support.py` re-run against each; receipt committed.
- The year-by-year pre-period gradient specified in `DESIGN_FREEZE_v1.md` as a
  frozen table, with its own empty shell.
- A paragraph in the plan stating which approach the chapter leans on, decided
  **before** any post-period outcome is opened.
- `pytest -q` green.

## Do not

- Do not open a post-period file.
- Do not drop a computerization measure because it absorbs the AI coefficient.
  That absorption is the result.
- Do not report horse-race coefficients as a decomposition when the support
  check says the clean cell is empty.
