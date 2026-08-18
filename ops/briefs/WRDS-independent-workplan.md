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

## Execution order for the **[NOW]** items — ALL SIX DONE 2026-08-18

Chosen by irreversibility first, then by what unblocks the most when access
arrives. Every one landed with tests; nothing consumed WRDS, network, or an owner
decision.

| # | item | landed |
|---|---|---|
| 1 | **W-06** licensing guard — the only item with an irreversible failure mode | `p1/t2_wrds/README.md` data policy, `.gitignore` rules for raw pulls, `p1/tests/test_wrds_data_policy.py` (allowlist + restricted-marker grep + a `git check-ignore` test proving the rules bite) |
| 2 | **W-07** the WRDS pipeline | rewritten from scaffold: all CRSP identifiers isolated in one UNVERIFIED `SCHEMA` dict (a test fails if one leaks out), batched fund lookup, per-permno as-of `shrout` within a lookback window, nulls instead of `""` in numeric contract columns, `pre_etf_ownership` left null rather than aliased to `conv_exp`, query-locator manifest, lineage |
| 3 | **W-08** day-one census | `coverage_census.py` — `--introspect` verifies `SCHEMA` against the live account via `information_schema`; the default mode censuses all 131 funds for a pre-conversion holdings report and its staleness |
| 4 | **W-17** reconciliation | `reconcile_convexp.py` with bands frozen before any number existed; verdict keys on the treated call against a pre-committed 95% floor; the 8-vs-9-character CUSIP trap handled explicitly; `NO_OVERLAP` never reads as `PASS` |
| 5 | **W-03b** R1b's schema-free half | `refraction/pipeline/surprises.py` (standardization, scheduled-window policy, five assertions) + `refraction/R1b_input_requirements.md`, which turns "paste the file heads" into eight specific items. `parse_usmpd()` raises `NeedInfo` rather than guessing |
| 6 | **W-05b** fund-level filter | `--exclude-asset-class` applied before aggregation — the only place a mixed wave can be split — so the sleeve decision is a flag, not a rewrite |
| — | **W-18** retirement note | audit item 3 (yfinance/Stooq recovery) marked superseded-pending-WRDS in both the memo and the module, deliberately not deleted |

Test count over the session: 252 passing, from 137 at the start. Selfcheck clean
throughout.

## What is left, and on whom

Nothing on this list is now blocked on this seat. The remaining items are
**[OWNER]** — W-03 (the paste-list), W-04, W-05, W-09, W-14, W-15, W-16 — and
**[LANE]** — W-01, W-02 (a web-capable session), W-10 (pre-dispatch), W-11, W-12,
W-13 (seat D). W-15 is the one to fix while waiting: a WRDS credential is useless
on a box that cannot run the job.
