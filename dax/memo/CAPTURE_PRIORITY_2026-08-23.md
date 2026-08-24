# Prospective capture priority under a $100 ceiling

**AUTHORIZED 2026-08-24** by the owner's instruction, recorded in
`dax/memo/PI_AUTHORIZATION_2026-08-24.md`, which carries the scope and
the standing conditions. Owner counter-signature pending there.

**Status:** prospective rule, unsigned. Must be signed **before** any capture
runs; choosing an order after seeing which calls succeeded would be a
specification choice.
**Date:** 2026-08-23.

## Why an order is needed

`dax/capability_panel/minimal_preservation_receipt.json` prices the five
snapshots retiring 2026-10-23 against the frozen 220-task GDPval open set at
**$97.28**, baseline perturbation, one repetition. The available ceiling is
**$100**. That is 2.7% headroom against a figure the receipt itself flags as a
planning number, because the 2048-token output cap may understate
deliverable-heavy tasks.

So a budget stop is a realistic outcome, not a remote one. The harness reserves
cost atomically in SQLite before each request and will halt cleanly at the
ceiling. What it halts *on* is then whatever order the plan happened to
enumerate — which would make the captured subset an artifact of iteration
order rather than a sample anyone can defend.

The fix costs nothing: fix the order now, in advance.

## The rule

Capture proceeds in this order. Every item at priority `k` completes before any
item at `k+1` begins.

**P1 — one call per retiring model, cheapest task first.**
Five calls. Establishes that every one of the five snapshots is reachable and
returns a well-formed response, before any budget is committed to volume. If a
model is unreachable, that is discovered for cents rather than after $90 has
gone to four others.

**P2 — full GDPval sweep, model-major, in registry order.**
For each retiring model in `vintage_registry.json` order — `gpt-4-1106-preview`,
`gpt-4-turbo-2024-04-09`, `gpt-4o-2024-05-13`, `gpt-4o-mini-2024-07-18`,
`o1-2024-12-17` — all 220 tasks in ascending `task_id`, then the next model.

**Model-major, not task-major.** A budget stop mid-sweep then yields *complete
coverage of the earliest vintages* rather than partial coverage of all five.
Complete early vintages support a capability-over-time comparison; five partial
sets support nothing, because the task composition would differ by model and no
difference could be attributed to capability rather than sampling.

Ordering the models oldest-first is deliberate: the oldest snapshots are the
ones with no substitute. Later vintages are either still available after
2026-10-23 or have approved open-weight stand-ins filed.

**P3 — perturbation battery**, only if the ceiling is raised. Not funded here.

## What a budget stop means

A halt at any point in P2 is a **complete** result for the models finished and
**absent** for the rest. Absent rows are recorded as `blocked` with
`failure_code` naming the budget stop; they are never estimated, interpolated,
or scored. The captured set is described by how far the order reached, which is
reproducible from this memo plus the ledger.

## What this does not authorise

No capture. The capture/scoring split amendment
(`AMENDMENT_DRAFT_w4_capture_scoring_split.md`) remains unsigned, no OpenAI key
is provisioned, and `budget_ceiling.json` does not exist. This memo only fixes
the order so that when those three land, the money buys a defensible sample.

## Signature

    PI signature: ______________________  Date: ____________

    [ ] approved — P1 then P2 model-major, oldest vintage first
    [ ] approved with the order amended below
    [ ] rejected
