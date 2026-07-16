# PROMPT — DAX-W1-memo (pre-registered design memo → GATE 1)
_Paste below the line into an Opus 4.8 session. This is the portfolio's ONE
irreplaceable frontier task (queue notes: "spread across several sessions
with PI iteration — don't rush it"). Expect 2–4 sessions; each session ends
by committing the draft and listing open [PI-DECISION] items. The PI signs
EVERY number before the `v1.0-preregistered` tag; the memo is a draft until
then. Cheap-model help is banned here (不省钱区)._

---

You are the Design Memo Agent for the DAX project (seat A, DAX-prime). Read,
in order: `CLAUDE.md`, `dax/CLAUDE.md`, `docs/DAX_ERE_Proposal_v3.md`,
`docs/DAX_Execution_Plan_with_AI_Agents.md` §W1,
`docs/DAX_Amendment_v1_1.md` (amendments 1–5), and
`dax/memo/feasibility_note.md` (**its three signed CONDITIONAL-GO conditions
are binding constraints on the memo**: W4 capture before the 2026-10-23 /
2026-12-11 OpenAI shutdown waves; retired vintages via cited open-weight
stand-ins inside the amendment-1 EIV bounds with gpt-4.5-preview excluded;
GDPval task-by-ID referencing only pending license clarification) and
`dax/memo/w05_legwork_2026-07-10.md` (verified price/vintage rows — use ONLY
rows with locators; UNKNOWN cells stay UNKNOWN in the memo).

## Protocol
`python ops/runner/lease.py claim DAX-W1-memo --account A` → branch
`task/DAX-W1-memo` → touch only `dax/`. **Never open `dax/analysis/outcomes/`
— the repo guard + CI enforce the prereg seal, and so do you.** No OpenAI NDA
usage aggregates anywhere in the repo (CI greps).

## Deliverable
`dax/memo/design_memo_v1.md` (PDF render is the owner's step), numbered and
auditable, no hedging in committed items. You draft; the PI decides: flag
every numeric commitment `[PI-DECISION]` with a defensible default + one-
paragraph justification + citations. Sections (execution plan §W1 verbatim,
plus amendment overlays):
1. Event registry: dated OpenAI capability/price events Nov 2021–present
   (GPT-4 2023-03; GPT-4o 2024-05 at half GPT-4-Turbo price = lead price
   event; o1 2024-09; and all subsequent releases/price changes). Compile
   from published API price histories; verify each date against two sources
   — meta-rule 1: **every date needs a locator; no date from memory**. Where
   the legwork memo already verified a row, cite it rather than re-deriving.
2. Stacking protocol: window length, minimum ΔDAX for event inclusion,
   dose-accumulation function, treatment of earlier crossers in later clean
   windows — with trade-offs stated for each choice.
3. The numbered strong parallel-trends identifying condition for continuous
   treatment (Callaway–Goodman-Bacon–Sant'Anna 2024), conditional on
   static-exposure decile, industry×month FE, and occupation-level
   interest-rate sensitivity.
4. Failure-cost grid f ∈ {0.25w, 1w, 4w} by O*NET consequence-of-error tier;
   halved/doubled grid + f=0; flip-rate diagnostic with the pre-registered
   >20% redesign trigger.
5. Mapping hierarchy (GDPval primary; Tolan-style benchmark→ability; Eloundou
   rescoring); define "survive all three" (consistent sign under all three,
   10% significance under ≥2); propose the tiebreaker.
6. Validation & first-stage thresholds: min rank correlation with the
   Felten/Eloundou/Webb static ensemble; min usage-share jump at crossings;
   the asymmetric interpretation of a first-stage null.
7. Power-analysis plan: CPS cells (dose bins × month, ages 22–25), clustering
   by occupation, employment-weighted many-to-many CPS→O*NET-SOC crosswalk
   doses with dispersion diagnostics, MDEs benchmarked against the 13%
   payroll decline. Write the simulation SPEC here; implementation is the
   separate DAX-W1-power task (allowed pre-gate: pre-event data only).
8. Primary/secondary outcome registry + multiple-testing corrections;
   education-split secondary analysis with its own power budget and an
   explicit no-headline-claims restriction.
9. OpenAI data handling: suppressed-cell rules, minimum estimability
   condition, only-named-team-runs-real-aggregates constraint.
10. (AMEND 1,2) EIV bounds module intent + cross-mapping IV + δ-calibration
    intent — state them as pre-registered commitments.

## Session end (every session)
Commit the draft + a `dax/memo/PI_DECISIONS_OPEN.md` checklist; if the memo
is complete, request the frontier-tier red-team pass (seat-C lane offered it)
BEFORE the PI reads it; do NOT `--complete DAX-W1-memo` until the PI-signed
version is in and DAX-GATE1-memo is the owner's next act. `make plan`, stop.
