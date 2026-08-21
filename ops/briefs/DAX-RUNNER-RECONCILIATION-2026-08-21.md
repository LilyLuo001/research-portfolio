# DAX runner/DAG reconciliation — 2026-08-21

## Determination

The old runner state treated every non-complete DAX task as fresh-ready,
dependency-blocked, or leased. That vocabulary hid executed scientific
failures and infrastructure-only completions. `state.json` now records audited
non-DONE statuses, and `runner.py --plan` prints them under
`RECONCILED HOLD` instead of reassigning them as fresh work.

| Task | Artifact reality | Reconciled state | Next gate |
|---|---|---|---|
| `DAX-W0.5-legwork` | Superseded by owner-run feasibility legwork and signed gate | `superseded` | None |
| `DAX-W1-memo` | A5 source/PDF reconciliation complete; scientific gates remain | `memo_reconciled_scientific_gates_open` | Mapping, duration, benchmark, real power, fresh review |
| `DAX-W1-power` | Person-level engine and fail-closed receipt exist; no real run | `engine_complete_real_run_blocked` | Real W5 panel and authorized benchmark |
| `DAX-W2-data` | CPS, crosswalk, price, and source receipts report execution | `execution_complete_receipts_present_contract_recheck_needed` | Re-run private directory contract on SCC before marking complete |
| `DAX-W3-mapA` | v1 executed deterministically but produced zero accepted mappings and 0.22461% wage-bill coverage | `execution_failed_scientific_gate` | PI-approved v2 method/thresholds plus blind labels |
| `DAX-W3-bulk` / `DAX-W3-audit` | Old-v1 annotation continuation would not validate proposed v2 | `not_runnable_mapping_v2_unapproved` | Approve v2, then label and audit |
| `DAX-W4-panel` | Contract/preflight/availability infrastructure exists; 0 captured rows and 0/220 durations | `infrastructure_complete_execution_blocked` | Mapping, duration, availability, and future budget gates |
| `DAX-W5-index` | Schema and blocker receipt exist; no real panel or identification result | `schema_complete_real_panel_blocked` | Qualified W3 and populated W4 |

Downstream Gate 1 and power work remain blocked. No dependency was weakened,
and no scientific task was marked complete merely because code exists.

## Lease safety defect found during this batch

Attempting the canonical `DAX-W1-memo` claim from the task branch produced a
failed push. The old failure handler unconditionally ran
`git reset --hard origin/main`, moving the branch pointer away from unpublished
task commits. The commits remained recoverable and this batch continued from
an exact recovered branch without rewriting published history.

`lease.py` now:

- refuses to claim from a dirty worktree/index;
- records the exact pre-claim HEAD;
- checks lease-commit success before pushing; and
- on push rejection, returns to that exact HEAD with a mixed reset rather than
  hard-resetting to `origin/main`.

Focused tests pin both the rejected-push recovery and dirty-tree refusal.

## Branch convention reconciliation

The initial local branch was `task/DAX-mapa-redesign-gates-20260821`, outside
the exact queue task-ID convention. The failed lease handler moved that branch
back to its base. Work was safely recovered at exact commit `5fc3cf2...` onto
`task/DAX-upstream-gates-20260821`. No published commit was amended or
reconstructed. This noncanonical but descriptive branch is retained for the
multi-gate batch rather than impersonating a single completed queue task.
