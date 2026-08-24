# Amendment draft — separate W4 capture from W4 scoring

**AUTHORIZED 2026-08-24** by the owner's instruction, recorded in
`dax/memo/PI_AUTHORIZATION_2026-08-24.md`, which carries the scope and
the standing conditions. Owner counter-signature pending there.

**Status:** UNSIGNED DRAFT prepared 2026-08-23, corrected 2026-08-23 after audit for PI consideration. No code
change has been applied. The gate described here is still fail-closed in the
repository as of this commit.

**Amends:** `dax/capability_panel/README.md` hard gate 2; the signed
2026-07-10 feasibility decision insofar as it sequences W4.

**Does not amend:** meta-rule 1, the no-inference rule on duration, the budget
ceiling requirement, the GDPval licence guard, or the outcomes seal.

## 1. The problem this fixes

Task duration is at 0/220. The metadata request bounced; the three-qualified-
human fallback is a $2.6k–$7k pilot that has not started and may require BU
human-subjects review.

Duration currently blocks W4 capture through three independent points:

| Location | Nature | Effect |
|---|---|---|
| `dax/capability_panel/plan.py:148` | wiring | `blockers.append("blocked_missing_task_duration")` — sets `plan_status = "blocked"` on **every** plan item |
| `dax/capability_panel/harness.py:381` | wiring | `if item.get("plan_status") != "eligible"` — records the item blocked and returns at line 390, **before prompt load and transport** |
| `dax/capability_panel/preflight.py:147` | wiring | gate `task_duration_complete`; line 190 `full_capture_allowed = all(gates.values())` |
| `dax/capability_panel/contract.py:281` | **invariant** | `if duration_status == "blocked_missing" and failure != "blocked": raise` — with lines 229-236 this forces null pi and zero trials |
| `ops/contracts/dax_w4_capability_cost_panel.yaml:39` | **frozen schema** | `task_duration_status: verified \| blocked_missing` — a two-valued enum |

With duration at 0/220 the chain is airtight: every item is blocked, the
harness issues zero requests, and no capability measurement occurs at all.

The registry's deadline-bound rows are the 14 `direct` rows, every one
currently at `account_probe_required`. They retire on **2026-10-23 (61 days
from this draft)** and **2026-12-11 (110 days)**. The two
`approved_open_weight_standin` rows are not deadline-bound and can be measured
at any time.

**Consequence as the repository currently stands:** an unstarted, IRB-
contingent human-subjects pilot is the sole blocker on the only irreversible
deliverable in the project. Every other DAX work item is recoverable after its
nominal date. Retired model snapshots are not. If the duration pilot slips two
months — an ordinary outcome for anything touching human-subjects review — the
historical capability panel becomes permanently unrecoverable, and no
subsequent benchmark, mapping, or index work restores it.

## 2. Why the split is sound rather than a weakening

Duration is an input to **cost scoring**, not to **capability capture**.

The crossing rule of design memo §2 is
`A_tom = 1[c/pi_eff + f*(1-pi_eff)/pi_eff < w]`. Duration enters through the
wage comparison `w` — the human cost of doing the task. It does not enter the
measurement of `pi` (whether the model completed the task), nor token counts,
nor latency, nor price lineage. Nothing about issuing a request to a dated
snapshot and storing its completion depends on knowing how long a human takes.

**Correction to an earlier draft of this section.** A previous version claimed
the row schema already tolerates duration-free capture, and that only gate
wiring conflated the two stages. **That was wrong**, and it was the sentence the
whole amendment rested on. `contract.py:281` reads

    if duration_status == "blocked_missing" and failure != "blocked":
        raise ContractError("missing duration must block the row")

and the `failure != "none"` branch at lines 229-236 forces `pi_successes = 0`,
`pi_trials = 0`, null `pi` and CI bounds, and
`pi_uncertainty_method = "not_estimable"`. A **captured** row therefore cannot
carry `blocked_missing` duration. The contract forbids precisely the state this
amendment needs. What the schema tolerates is a duration-free *blocked* row —
the opposite of capture.

This is a deliberate fail-closed invariant, phrased in the same language as
`plan.py`'s `blocking_rule` string. It encodes the proposition **"a row without
duration is a row with no measurement."** This amendment breaks that
proposition, and the case for it must be made on those terms rather than as a
wiring fix.

**Why breaking it is nonetheless correct.** The invariant conflates two claims
that happen to coincide today: (a) a row without duration cannot be *scored*,
which is true and must be preserved; and (b) a row without duration cannot be
*measured*, which is false. Duration enters the design memo §2 crossing rule
`A_tom = 1[c/pi_eff + f*(1-pi_eff)/pi_eff < w]` only through the human wage
comparison `w`. It does not enter pi, token counts, latency, or price lineage.
Nothing about issuing a request to a dated snapshot and recording its
completion depends on how long a human takes.

**The amendment authorizes no spending.** Gate
`signed_repository_usd_ceiling` stays inside `full_capture_allowed` unchanged.
Capture still requires `budget_ceiling.json` at `status: PI_SIGNED` with a
positive ceiling. This amendment removes one gate from the capture set; it does
not release a dollar, and the smoke-mode USD 5 cap continues to apply until the
ceiling is signed separately.

**No crossing can be computed from a duration-blocked row.** The rows this
amendment permits carry `task_duration_status = "blocked_missing"` and cannot
enter the `A_tom` determination, the index, or W5. They are raw measurement
held in escrow against a deadline.

## 3. What changes

Five changes, to be applied **only after signature**. This is larger than the
three-line wiring fix an earlier draft described.

1. **`ops/contracts/dax_w4_capability_cost_panel.yaml:39`** — extend the enum to
   `verified | deferred_scoring | blocked_missing`. This amends a frozen
   contract and carries the same signature discipline as any schema change
   under portfolio rule 3. No column is renamed and no column is removed.
2. **`contract.py`** — admit `deferred_scoring` with its own invariant: value,
   unit, and source must be null or empty exactly as under `blocked_missing`,
   but `failure_status` may be `none`, so pi, tokens, cost, and the Wilson
   interval are permitted. Leave the `blocked_missing` rule at line 281
   **untouched** — a genuinely blocked row keeps its old meaning.
3. **`plan.py`** — emit `task_duration_status = "deferred_scoring"` rather than
   `"blocked_missing"` when duration is absent but the row is otherwise
   eligible, and move the duration test out of `blockers`.
4. **`harness.py`** — no change. It keys on `plan_status`.
5. **`preflight.py`** — move `task_duration_complete` into a new `scoring_gates`
   dict with `scoring_allowed = all(scoring_gates.values())`, leaving
   `full_capture_allowed` to govern capture. Retain the duration receipt block
   verbatim so coverage stays visible.

### The safety property being traded, and its replacement

Today the "no scoring without duration" guarantee is enforced *structurally*: a
duration-free row has null pi, so it cannot reach a crossing computation
because it carries nothing to compute with. After this amendment that guarantee
must be enforced *behaviourally*: a `deferred_scoring` row will carry a real pi
and must be refused by every cost, crossing, and index consumer.

**That enforcement point does not exist yet.** W5 index code is unwritten. The
amendment therefore relaxes an enforced invariant and defers its replacement to
code not yet written, which is the honest risk here and the strongest argument
against signing.

Mitigation, and it is a precondition rather than a follow-up: write the guard
and its test **before** any capture runs. A `deferred_scoring` row reaching
`metered_cost_usd`, any `A_tom` determination, the DAX index, or W5 must raise.
The test must fail against a stub if the guard is absent. The split is only as
safe as that test, and the test must exist first.

## 3a. The preservation path — added 2026-08-23, and it is why this matters now

The split above is necessary but **not sufficient** for the $100 preservation
capture priced in `minimal_preservation_receipt.json`. Enumerating what
`preflight.py` would evaluate for a GDPval-direct run today:

| Gate | Today | Why |
|---|---|---|
| `w3_exact_commit` | FAIL | Mapping A is `MAPA_EXECUTED_QUEUE_FROZEN_AUDIT_PENDING`, not `pushed_validated` — and the W3 reconciliation retires it as primary |
| `task_duration_complete` | FAIL | duration 0/220 — the only one section 3 fixes |
| `task_count > 0` | FAIL | `task_count` is read **from the duration receipt**, which does not exist |
| `account_availability_probed` | FAIL | clears when the key lands |
| `signed_repository_usd_ceiling` | FAIL | `budget_ceiling.json` does not exist |

Two of those block on inputs that are **irrelevant to a preservation capture**.
Such a run consumes no mapping — it sends the frozen public GDPval open set to
five retiring snapshots and stores the completions — so requiring a validated
W3 mapping gates it on work it does not use. And drawing the stimulus count
from the duration receipt means the universe is undefined precisely when
duration is what we are deferring.

Signing section 3 alone would leave the money unspendable. The amendment
therefore also defines:

**[PRESERVE-1] A named stimulus set.** A preservation run takes its task
universe from an explicitly named, pinned stimulus set — for this run the
GDPval open set, 220 tasks, parquet SHA-256
`f8422fab9b21d90c0ee5f0659842ab666d418cb8940842918f9f4b0df7ae0202`, referenced
by task ID under the standing licence condition. `task_count` comes from that
set, never from the duration receipt.

**[PRESERVE-2] The W3 gate is not applicable.** When a run declares the
preservation route and consumes no mapping, `w3_exact_commit` is recorded
`not_applicable` with the reason, rather than passed or waived. A run that
*does* consume a mapping keeps the gate unchanged and unweakened.

**[PRESERVE-3] Preservation rows cannot be scored.** Every row carries
`task_duration_status = "deferred_scoring"` and is refused by
`assert_scoreable`. A preservation capture can never reach an `A_tom`
determination, the index, or W5 without duration arriving first.

**[PRESERVE-4] What stays enforced.** The signed budget ceiling, the
availability probe, the atomic cost reservation, the encryption of prompts and
responses, and the capture order in `CAPTURE_PRIORITY_2026-08-23.md` are all
unchanged. This narrows two gates for one declared route; it removes none.

Without PRESERVE-1 and PRESERVE-2 the five snapshots retiring 2026-10-23 are
lost regardless of funding, because preflight will refuse a run whose
prerequisites do not apply to it.

## 4. Dependency this amendment does not resolve

Capture requires a frozen stimulus set. Given the S1 result and the open S3
design, the recommendation is to capture against a deliberately over-inclusive
set — the 24 constructible S1 instances, the GDPval open subset referenced by
task ID under the §7 licence guard, the perturbation battery, and any S3
Phase-2 instances ready before the cutoff. Raw completions are storable and
re-gradable indefinitely; a retired snapshot is not re-runnable. Grading and
rubric design then proceed after the deadline has passed, against whatever
benchmark S3 eventually freezes.

That stimulus-set freeze is a separate decision and is deliberately **not**
bundled into this amendment. Narrow amendments can be signed quickly, which is
the entire point under a 61-day deadline.

## 5. Prerequisite, and it is free

`python -m dax.capability_panel.availability` takes only `--registry`,
`--env-file`, and `--output`. It reads no duration receipt, hits the account-
scoped models endpoint rather than any inference endpoint, and costs USD 0. All
14 direct rows sit at `account_probe_required`, so it is not currently known
which historical snapshots this account can still reach.

Run it before signing. It determines whether this amendment is urgent for 14
rows or for 6, and whether the remaining effort belongs in capture or in filing
open-weight stand-ins for rows already lost. It requires the SCC key at
`/usr3/graduate/qluo/dax-private/w4/.env` and cannot be run from a session
without that path.

## 6. Signature

    PI signature: ______________________  Date: ____________

    [ ] approved as drafted
    [ ] approved with the modifications noted below
    [ ] rejected — duration remains a capture gate, and the historical
        capability panel is accepted as at risk of permanent loss

Rejection is a legitimate option and is listed explicitly so that accepting the
loss is a recorded decision rather than an outcome of inaction.
