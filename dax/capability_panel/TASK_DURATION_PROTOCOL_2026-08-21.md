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

1. **Preferred:** task-specific observed human completion times supplied by the
   GDPval authors or another documented benchmark run. Require at least three
   completions per task, the exact benchmark/task version, collection protocol,
   and a dated source locator.
2. **Fallback:** three independent domain-qualified annotators per task. An LLM
   may format or flag annotations, but an LLM-only estimate is prohibited.
3. If neither is available for a task, that task remains blocked. Do not fill
   it with an occupation mean or a constant.

## Annotation protocol

Annotators work independently in round 1 and estimate lower, median, and upper
active minutes on a log-spaced grid: 5, 15, 30, 60, 120, 240, 480, 960, and
1,920+. They receive the full private task materials and rubric, the estimand
above, and a competency assumption; they do not see W4 model outcomes, API
prices, or other annotators' answers.

Disagreement of more than one adjacent bin is adjudicated with the original
answers preserved. The frozen task row carries lower/median/upper minutes, the
number of annotators or observed completions, adjacent-bin agreement, source
type, a private-manifest/source locator, protocol version, and adjudication
status. Raw text and identities remain private.

## Acceptance gate

- all 220 task IDs appear exactly once;
- every task has positive ordered lower/median/upper bounds;
- observed timings have at least three completions, or expert estimates have
  at least three independent annotators;
- expert adjacent-bin agreement is at least 0.80 after adjudication;
- every row has `adjudication_status = PASS` and a source locator;
- sensitivity construction uses all three duration bounds, not only the median.

`task_duration_gate.py` enforces the row-level portion of this gate and rejects
LLM-only, constant, or occupation-average sources.

## Immediate next action

First request task-level human timing metadata from the GDPval authors. In
parallel, prepare the private three-annotator packet so the project does not
depend on receiving unpublished data. No OpenAI API capture is authorized by
this protocol.
