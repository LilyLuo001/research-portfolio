# Y1d — Construct validity, support reconciliation, then the joint power run

*Self-contained. One session. Run on the SCC. Requires Y1b (`113ff31`).*

---

## Who you are and what this is

You are the execution agent for **YAX**, a self-contained third dissertation
chapter — not the student's main paper. It asks: *among occupations with
comparable pre-existing computerization, did employment of workers aged 22–25
decline relative to 26–65 after ChatGPT, in occupations with greater LLM
exposure?*

Read `yax/RESEARCH_PLAN_v4.md`. §2, §3, §5, §6 and §13b are binding.

**The five rules.** (1) You are not a source of facts — every number comes from
code you ran or a document you opened, with a locator. (2) Schema contracts:
hand off through files, never rename a column another task reads. (3) Don't know
→ stop: `NEED_HUMAN`, never guess-fill. (4) Never specification-search: the
first run of a pre-specified table is the reported run. (5) Commit early, named
paths only.

**The one irreversible mistake.** Never open a post-ChatGPT outcome before
`v1.0-design-freeze` is tagged. This task touches no outcome data.

**Environment.** Verify the interpreter before assuming: SCC default Python is
3.6.8 with **no pandas**; a project venv carries 1.4.3. Prefer stdlib
`csv`/`json`. Never `git add -A`. Never echo a credential. No API key needed.

---

## Context: what Y1b established and what a reviewer got wrong

Y1b built five computerization measures and passed the `computerization` gate.
Review then found `webb_pct_software` correlates with nothing — −0.106 with
O\*NET computer importance, −0.003 with O\*NET level, −0.028 with RTI, +0.104
with Frey–Osborne — while O\*NET importance and level agree at +0.912 and RTI
and Frey–Osborne at +0.448.

**That was first called a broken merge. It is not.** The ranking is coherent:
highest are broadcast equipment operators, power plant operators, water and
sewage treatment operators, locomotive operators, elevator installers; lowest
are barbers, podiatrists, performers, mail carriers. Computer programmers sit at
98. That is what exposure to *software patents* looks like — process and machine
control — as opposed to O\*NET, which measures computer *use*.

**Different constructs.** So Y1b's conclusion stands: *"computerization" is not
one interchangeable control; report all five.* A `gate_convergent_validity`
FAIL on Webb is expected and is cleared by that evidence.

Your job is to make this defensible rather than asserted, reconcile the support,
and then run the power simulation that has been blocked behind it.

## Task 1 — Document construct validity for all five measures

For **each** of `webb_pct_software`, `onet_computers_importance`,
`onet_computers_level`, `rti_autor_dorn`, `frey_osborne_probability`:

- the **15 highest and 15 lowest ranked occupations, named**;
- the full 5 × 5 correlation matrix on common support, with pairwise n;
- one paragraph stating **what construct the measure captures** and how it
  differs from the others, argued from the ranking rather than from the source
  paper's abstract.

Write `yax/measurement/CONSTRUCT_VALIDITY.md` plus a receipt. This is what
converts "Webb is orthogonal" from a suspicious number into a documented
property, and a referee will ask for exactly this.

**If any measure's ranking is incoherent** — no interpretable pattern at either
end — say so and treat it as a merge failure. That is the distinction the
convergent-validity gate cannot make on its own.

## Task 2 — Reconcile the support and pin one

Three occupation counts are live across three artifacts and they must be
reconciled before anything is frozen:

| count | artifact |
|---|---|
| 490 | occupation clusters, unconditional power run |
| 445 | observed pre-period CPS `OCC2010` codes, Y1a |
| 442 | codes carrying a Webb score, Y1b |

Also: the Y1b diagnostics ran on a **13-month support, 2021-11 to 2022-11**,
while the frozen design's pre-period is **66 months, 2017-01 to 2022-11**.

- Explain each difference.
- **Re-run the Y1b diagnostics on the full 66-month pre-period support.**
  Report whether any partial variance, VIF or effective-N moves materially.
- State which support the design freeze will pin, and record its sha256.

## Task 3 — The joint-model power simulation

Blocked behind Task 2, and the design has **no MDE until it runs**. The 3.44%
figure is unconditional and does not apply; do not quote it.

Simulate plan §5's exact equation:

    E[N_oat] = exp[ α_oa + δ_ot + λ_at
                    + β_AI (AI_o × Young_a × Post_t)
                    + β_C  (Comp_o × Young_a × Post_t) ]

- Use the **observed joint distribution** of AI and computerization, preserving
  their correlation. Not independent marginals.
- Inject an AI-specific effect with **β_C held fixed** at a plausible non-zero
  value; report sensitivity to that value.
- Run it for **β and α** as AI measures, and for **O\*NET importance and Webb**
  as computerization — those two bracket the confounding range (VIF 2.80 versus
  1.00), so the conditional MDE will differ and both belong in the freeze.
- 999 repetitions, exact seed recorded. Grid wide enough that power crosses 80%
  **inside** it.
- **Wild-cluster bootstrap is primary inference** — Rademacher weights,
  clustered on occupation, ≥999 draws.

Report conditional MDE80 with bootstrap interval, realised type-I error at
nominal 5%, effective number of occupations identifying β_AI, and influence
concentration.

`yax/gates.py` FAILs if power sits at ceiling at the smallest tested effect —
an engine describing its own smoothness — and also if power never reaches 80%,
which is the opposite diagnosis and triggers plan §12.4.

---

## Definition of done

- `CONSTRUCT_VALIDITY.md` + receipt: 15 highest and lowest per measure, the
  5 × 5 matrix, and a construct paragraph each.
- Support reconciled; diagnostics re-run on the 66-month pre-period; the pinned
  support named with its sha256.
- Conditional power aggregate with a `bootstrap` key; `POWER_NOTE.md` giving the
  MDE, its interval, the assumed β_C, and what a simulation on a fitted DGP
  cannot capture.
- `python yax/gates.py --power-aggregate <path>`: `gradient`, `calibration` and
  `convergent_validity` all resolved — `convergent_validity` may pass, or FAIL
  with Task 1's evidence recorded as the explanation, but not be left silent.
- `pytest -q` green. Report counts, **the skip list with reasons, and which
  repository and branch you ran in.** Expect ~738 passed, 3 skipped on
  `claude/dax-research-direction-1ohi97`.

## Do not

- Do not open a post-period file.
- Do not quote the unconditional 3.44% MDE.
- Do not write "100% power".
- Do not drop Webb because it is orthogonal — that orthogonality is the finding,
  and §13b explains it.
- Do not switch the primary AI measure from β to α because α is less
  confounded. Plan §2 fixes β on conceptual grounds and bars selecting on
  separability statistics. Report both.
