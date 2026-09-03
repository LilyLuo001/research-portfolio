# The WRDS-independent register — everything WRDS will NOT fix

Companion to `ops/briefs/WRDS-access-assessment.md`. WRDS has been purchased and
is not yet delivered. This is the full list of problems that survive its
arrival, triaged by who can move them, so the waiting period is not idle and so
nothing is deferred to WRDS that WRDS was never going to solve.

**Method note.** WRDS supplies *data*. It does not supply code, decisions,
licences, first-hand documents, or infrastructure. Every item below fails at
least one of those, which is why it is here.

Status key: **[NOW]** this seat can execute it without access to anything ·
**[OWNER]** needs a decision or a credential only the owner has ·
**[LANE]** needs a different execution lane (web-capable session, box, seat D).

---

## A. Refraction retrieval leg — WRDS carries none of this

| id | item | why WRDS does not touch it | status |
|---|---|---|---|
| W-01 | `REFR-R0-collide` channel A — literature collision + Marta–Riva priority | SSRN/journals/arXiv are not in WRDS; the 40% hair trigger protects positioning, not measurement | **[LANE]** web |
| W-02 | `REFR-R1a-verify` — USMPD structure, FOMC/BLS calendars, consensus registry | SF Fed USMPD is not a WRDS product; official calendar pages are first-hand documents | **[LANE]** web |
| W-03 | `REFR-R1b` **parse** stage (USMPD file → `S_raw`) | needs the real file's columns; the manual forbids guessing them | **[OWNER]** paste heads |
| W-03b | `REFR-R1b` **transform + assert** stage (`S_std`, `is_scheduled`, the three assertions) | defined entirely by the frozen contracts + `frozen_config`, so it needs no external schema at all | **[NOW]** |
| W-04 | CPI/NFP consensus source | R1a item 3 asks whether a WRDS-internal substitute exists — that is a question to *answer with access*, never to assume. FOMC-only is non-blocking meanwhile | **[OWNER]** + verify |

## B. Decisions — no data resolves a judgement call

| id | item | why WRDS does not touch it | status |
|---|---|---|---|
| W-05 | international sleeve: Option A / A-strict / fund-level rebuild | CRSP is US-listed; the foreign holdings stay undenominated either way. Costed in `p1/output/convexp_coverage_audit/international_sleeve_options.md` | **[OWNER]** |
| W-05b | fund-level asset-class filter in the pipeline | whichever option is chosen should be one flag, not a rewrite | **[NOW]** |
| W-09 | `holdings_weights` weight-basis alignment with P1-T2 (refraction R2 pre-dispatch) | a definitional agreement that must exist *in writing* before R2 is dispatched | **[OWNER]**, options draftable **[NOW]** |
| W-14 | queue bookkeeping: `P1-T1-events(+B)` never marked complete, so the runner still shows `P1-T1-arb` blocked | a gate call | **[OWNER]** |
| W-16 | prereg sequencing — refraction GATE-PREREG/OSF; recording the P1 sample definition before T5 | a timestamp and a signature | **[OWNER]** |

## C. Problems WRDS *creates*

| id | item | status |
|---|---|---|
| W-06 | **CRSP licensing / redistribution.** The free path's premise was "every number carries a public locator, zero paid data", so derived artifacts could be committed freely. CRSP-derived data cannot be treated that way, and `ops/COMPLIANCE.md` is currently silent on it. The rule must exist *before* the first pull lands, not after | **[NOW]** guard + policy; **[LANE]** seat D to fold into COMPLIANCE.md |
| W-17 | **Reconciliation design.** Two independent constructions of ConvExp (EDGAR N-PORT vs CRSP) is the portfolio's own dual-channel pattern and the strongest available validation — but it needs a cusip↔permno join and agreed tolerances, designed before the numbers exist so the comparison cannot be tuned after seeing them | **[NOW]** |

## D. Code and readiness — WRDS ships data, never code

| id | item | status |
|---|---|---|
| W-07 | `p1/t2_wrds/holdings_pipeline.py` is a 186-line scaffold. Completing it against the frozen `conv_exposure.yaml` contract, with an injected connection so it is testable with zero credentials | **[NOW]** |
| W-08 | **Day-one coverage census.** The first thing to run when access lands is not the pipeline but a census of the holdings tables against the 131 conversion funds — MF holdings coverage has known lags, and that is a fact to establish with code on real data, not assume | **[NOW]** |
| W-10 | `REFR-R2` panel builder | **[OWNER]** pre-dispatch (W-03/W-09) |
| W-18 | retire audit item 3 (yfinance/Stooq denominator recovery): CRSP `shrout` supersedes it. Mark retired-pending-WRDS, do not delete — it stays the fallback if access slips | **[NOW]** |

## E. Infrastructure and other lanes

| id | item | status |
|---|---|---|
| W-15 | box infra: SCC SSH auth and the broken venv (`ops/decisions.md`, 2026-07-09/10). **This gates the WRDS pull too** — a credential is useless on a machine that cannot run the job | **[OWNER]** |
| W-13 | seat-D cron line for `refraction/scan.py` (monthly) | **[LANE]** seat D |
| W-11 | `REFR-R13-triage` needs an L1 vendor lane (kimi is benched) | **[LANE]** |
| W-12 | `REFR-R14-metaqa` is cheap-tier-only by design | **[LANE]** |

---

## Execution order for the **[NOW]** items

Chosen by irreversibility first, then by what unblocks the most when access
arrives:

1. **W-06** licensing guard — the only item on this list with an irreversible
   failure mode (paid data committed to a repo cannot be un-published).
2. **W-07 + W-08** the WRDS pipeline and its day-one census — the difference
   between "access arrives and we start writing code" and "access arrives and we
   run one command".
3. **W-17** reconciliation design — must be fixed before numbers exist.
4. **W-03b** the R1b transform/assert layer + the exact paste-list the owner
   needs to supply for W-03.
5. **W-05b** fund-level filter.
6. **W-18** retirement note.

Each lands as its own commit with tests. Nothing here consumes WRDS, network, or
an owner decision; every item is inert-but-ready the day access is delivered.
