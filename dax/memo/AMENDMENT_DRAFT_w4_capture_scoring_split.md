# Amendment draft — separate W4 capture from W4 scoring

**Status:** UNSIGNED DRAFT prepared 2026-08-23 for PI consideration. No code
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

| Location | Effect |
|---|---|
| `dax/capability_panel/plan.py:148` | `if not duration_verified: blockers.append("blocked_missing_task_duration")` — sets `plan_status = "blocked"` on **every** plan item |
| `dax/capability_panel/harness.py:381` | `if item.get("plan_status") != "eligible"` — records the item blocked and returns **before any API call** |
| `dax/capability_panel/preflight.py:147` | gate `task_duration_complete`; line 190 `full_capture_allowed = all(gates.values())` |

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

**The row schema already anticipates this.** `dax/capability_panel/
contract.py:248` already accepts `task_duration_status = "blocked_missing"`
with `task_duration_value`, `task_duration_unit`, and `task_duration_source`
all null or empty, and *raises* if a missing duration is imputed or claims a
source. Captured rows therefore validate today without duration. Only the gate
wiring conflates the two stages.

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

Three surgical changes, to be applied **only after signature**:

1. **`plan.py`** — move the duration test out of `blockers` into a separate
   `scoring_blockers` list. Add field `scoring_status` carrying
   `"blocked_missing_task_duration"`. `plan_status` is then governed by
   availability and provider status alone. `task_duration_status` continues to
   be emitted exactly as today.
2. **`harness.py`** — no change. It keys on `plan_status`, which now correctly
   reflects capture eligibility.
3. **`preflight.py`** — move `task_duration_complete` out of `gates` into a new
   `scoring_gates` dict. Add `scoring_allowed = all(scoring_gates.values())`
   alongside the existing `full_capture_allowed`. The duration receipt block in
   the emitted receipt is retained verbatim so coverage stays visible.

Add a contract test asserting that a row with
`task_duration_status = "blocked_missing"` can be captured but **cannot** reach
any cost, crossing, or index path. The split is only as safe as that test.

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
