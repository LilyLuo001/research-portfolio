# GDPval task-duration protocol — 2026-08-21

## Estimand

For each of the 220 GDPval tasks, measure **active human labor minutes for one
competent professional to produce one rubric-compliant completion**, with the
provided inputs ready. Include task-specific reading, analysis, drafting,
tool use, and quality assurance. Exclude queue time, procurement, unrelated
training, and passive waiting. Record elapsed time separately if observed.

This is the duration required by the human-cost side of the adoption
inequality. O*NET importance/frequency, ATUS activity time, occupation-average
hours, and a single constant for all tasks are not substitutes.

## Source hierarchy

1. **Preferred:** the task-specific validated self-reported professional
   completion times used by the GDPval authors. The public GDPval paper defines
   this quantity in Appendix A.2.4 (printed pp. 12--13), but the public 220-row
   parquet does not release the task-level values. A supplied value is usable
   only when it is joined by exact GDPval task ID and benchmark version and has
   a dated source locator. A semantically similar task is not an admissible
   substitute.
2. **Alternative observed source:** task-specific observed human completion
   times from another documented benchmark run. Require at least three
   completions per exact task/version, a collection protocol, units, and a
   dated source locator.
3. **Fallback:** three independent domain-qualified annotators per task. An LLM
   may format or flag annotations, but an LLM-only estimate is prohibited.
4. If neither is available for a task, that task remains blocked. Do not fill
   it with an occupation mean or a constant.

## Annotation protocol

An annotator must have professional experience in the task's GDPval occupation
or documented experience supervising that work. Annotators work independently
in round 1 and estimate lower, median, and upper
active minutes on a log-spaced grid: 5, 15, 30, 60, 120, 240, 480, 960, and
1,920+. They receive the full private task materials and rubric, the estimand
above, and a competency assumption; they do not see W4 model outcomes, API
prices, or other annotators' answers.

Annotators include hands-on reading, analysis, drafting, tool operation, and
quality assurance. They exclude queue time, passive waiting, unrelated
training, procurement, and coordination not required by the prompt. Each gives
a short rationale and flags missing inputs. Disagreement of more than one
adjacent bin is adjudicated by a fourth qualified reviewer, with original
answers preserved. The frozen row uses the median of adjudicated medians and
the minimum lower/maximum upper bounds. Missing annotations remain missing;
there is no mean, occupation, or constant imputation. Extreme values are not
discarded automatically and require a reason-coded adjudication.

The frozen task row carries lower/median/upper minutes, unit (`minutes`), exact
match status, observed-versus-estimated basis, number of annotators or observed
completions, adjacent-bin agreement, source type, a private-manifest/source
locator, protocol version, imputation field, and adjudication status. Raw text,
rationales, and identities remain private.

## Matching and transformation rules

- GDPval author data must match the public gold subset by exact task ID and
  dataset revision. Near/semantic matching is not accepted for a primary
  duration value.
- Another observed run must use the exact task materials and version. A related
  occupation or task is not a match.
- Direct expert annotations are marked
  `not_applicable_direct_annotation`; they are not represented as source-data
  matches.
- Source hours are converted once as `minutes = hours * 60`; source minutes are
  retained. The original value and unit remain in the private audit.
- No winsorization, averaging across tasks, occupation-level inheritance, or
  silent imputation is permitted.

## Acceptance gate

- all 220 task IDs appear exactly once;
- every task has positive ordered lower/median/upper bounds;
- GDPval-author task values retain the paper's validated-self-report basis and
  document at least two independent occupational validators; alternative
  observed timings have at least three completions; or fallback estimates have
  at least three independent qualified annotators;
- expert adjacent-bin agreement is tested against a prospectively
  PI-approved floor after adjudication; **the numeric floor is NEED_HUMAN and
  is not approved by this document**;
- every row has `adjudication_status = PASS` and a source locator;
- sensitivity construction uses all three duration bounds, not only the median.

`task_duration_gate.py` enforces the row-level portion of this gate and rejects
LLM-only, constant, occupation-average, unsupported-match, invalid-unit, and
silent-imputation sources. It has no default agreement floor: an explicitly
approved value must be supplied.

## Immediate next action

First request task-level human timing metadata from the GDPval authors. In
parallel, prepare the private three-annotator packet so the project does not
depend on receiving unpublished data. No OpenAI API capture is authorized by
this protocol.
