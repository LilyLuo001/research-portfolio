# Is there a replacement for the GDPval human-time source?

**Date:** 2026-08-24. **Answer: no, and the reason is structural rather than
bad luck.** This memo records why, so the search is not repeated, and names
the one candidate that still deserves a seat's time.

## What was already established

`gdpval_duration_source_audit_receipt.json` settles the preferred source:

- `exact_task_level_durations_available: 0` of 220.
- The public parquet's schema was enumerated and carries no duration field.
- The paper defines the measure (Appendix A.2.4, pp. 12--13) and publishes
  set-level aggregates only, and those aggregates disagree with each other:
  404 minutes on p. 13 against 9.49 hours in Table 3, for the same 220 tasks.
- Author outreach **bounced**; `AUTHOR_DATA_ROUTE_UNAVAILABLE`.

So the question is whether some *other* source can fill slot 2 of the
protocol's hierarchy: "task-specific observed human completion times from
another documented benchmark run."

## Why no external dataset can fill that slot

The protocol requires a value to be "joined by exact GDPval task ID and
benchmark version," and states that "a semantically similar task is not an
admissible substitute."

That requirement is not bureaucratic. The estimand is active human labor
minutes to produce **one rubric-compliant completion of one specific GDPval
task**, with that task's provided inputs ready. A duration measured against a
different task boundary is a measurement of a different quantity, and joining
it in would reproduce exactly the failure that retired DWA transport as the
primary mapping: the unit mismatch is not solved by moving it one level up.

No dataset outside the GDPval authors' own files is indexed on GDPval task
IDs. That is why this is structural. The three families people reach for are
each ruled out in the protocol itself, and each for the same reason:

| Candidate | Why it is not a replacement |
|---|---|
| O*NET importance / frequency | No duration exists anywhere in 26.1. The one "% Time" scale occurs in zero data tables and its nine items measure body position. Confirmed by the 2026-08-24 input inventory. |
| BLS ATUS activity time | Measured per *activity category* over a diary day, not per task, and never per GDPval task. Wrong grain and wrong universe. |
| Occupation-average hours, or one constant | Explicitly prohibited: it would erase the between-task variation the adoption inequality turns on. The protocol says an unfillable task stays blocked rather than take a mean. |

## The one candidate worth checking, recorded as unverified

**Hatgis-Kessell, Aguirre, Wan and Bommasani (2026), _Estimating time spent on
work tasks_.** Already cited in `dax/memo/W2_DECISION_task_weight_2026-08-24.md`
for its finding that existing time shares rest on "coarse O*NET data not
intended for this purpose."

It is the only known work whose stated subject is the missing quantity. **No
claim is made here about what it contains** — this session has no egress, the
paper has not been read, and under meta-rule 1 an unread paper supports
nothing. It is recorded as a candidate, not as a source.

A seat that can read it should answer three questions, in order, and stop at
the first "no":

1. Does it publish **per-task** time values, or only a method and aggregates?
   A method is not a source.
2. Are those values **observed**, or model-estimated? The protocol permits an
   LLM to format or flag annotations and prohibits an LLM-only estimate. An
   estimated duration is not an observed completion time and cannot enter at
   slot 2.
3. Are they indexed on **GDPval task IDs**? If they are O*NET-task-indexed —
   which the title suggests — then even a perfect answer to 1 and 2 fails the
   join requirement, and the most it can be is an external validity check on
   the pilot's outputs.

The realistic outcome is that it fails at 3, and its value to this project is
as a comparator for the pilot rather than a substitute for it. That is still
worth having, and it costs one seat a few minutes.

## The actual replacement

There is no dataset to find. The replacement is the **human duration pilot**,
which already exists as a frozen design:

- 40 tasks, sample frozen (`gdpval_duration_pilot_sampling_receipt_20260821.json`).
- Three independent domain-qualified annotators per task; LLM-only estimates
  prohibited.
- **Expected cost `$3,900`; requested cap `$7,000`**
  (`gdpval_duration_bounce_fallback_execution_receipt_20260821.json`).
- Status: `HUMAN_FALLBACK_ACTIVE_PILOT_40_FROZEN_RECRUITMENT_AND_BUDGET_PENDING`.

What it needs is a capped budget, governance and real annotator recruitment —
not more searching. Validated exact-version author data would still take
precedence for matching tasks if that route ever reopens.

## What this changes today

Nothing about the `$100` preservation run, which defers scoring and therefore
needs no duration at all. That separation is the whole point of the
capture/scoring split: a retiring snapshot can be captured now and graded when
duration exists. This memo only closes the question of whether a cheaper
duration source was missed.
