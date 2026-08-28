# GDPval active-human-completion-time annotation instructions

**Version:** `DAX-TD-v1-pilot40-bounce-amendment`

**Audience:** independently qualified real-human annotators only

**Response visibility:** private; annotators cannot see one another's answers

## Quantity to estimate

Estimate the active labor time required for **one competent professional** to
produce one rubric-compliant completion of the supplied task, assuming all
provided task inputs are ready and ordinary professional tools are available.
Estimate realistic work, not the fastest conceivable completion and not how
long an AI system would take.

Record three positive ordered estimates:

- lower plausible active minutes;
- median/best-estimate active minutes;
- upper plausible active minutes.

Also select the corresponding frozen bins: `5, 15, 30, 60, 120, 240, 480,
960, 1,920+` minutes. For `1,920+`, provide a numeric lower/median estimate and
do not invent a finite upper bound if the upper tail is genuinely open.

## Include as active work

- reading and understanding the supplied task and reference materials;
- task-specific preparation and planning;
- analysis, calculations, research permitted by the task, and professional
  judgment;
- drafting, coding, spreadsheet work, tool operation, or other production;
- revision, verification, formatting, and quality assurance needed to satisfy
  the supplied rubric;
- ordinary file opening, saving, and required mechanical operations when the
  professional must actively attend to them.

## Exclude

- queue time, scheduling delay, procurement, unrelated training, and general
  onboarding;
- passive waiting for downloads, renders, long computations, approvals, or
  third parties when the professional can do other work;
- abnormal software installation, hardware failure, or one-time environment
  setup not intrinsic to the task;
- optional coordination not required by the prompt;
- time to learn basic professional skills that the competent-professional
  assumption already supplies.

Include actively monitored mechanical delay only when the worker must remain
engaged and cannot perform other work. State this assumption in the rationale.

## Completion and familiarity assumptions

Completion means delivery of every required output at the quality level in the
private rubric—not merely a first draft. Assume normal professional familiarity
with the occupation, common tools, and task format, but no advance familiarity
with the specific supplied materials. Include the time needed to read those
materials. Do not assume reusable work from another GDPval task.

## Required response fields

1. lower, median, and upper active minutes;
2. selected lower, median, and upper frozen bins;
3. short rationale broken into reading/preparation, production, and QA stages;
4. direct-experience versus structured-professional-judgment basis;
5. included/excluded delay assumptions;
6. confidence level;
7. missing-input or cannot-complete-as-provided flag.

Do not communicate with another annotator about the task before submission.
Do not use an LLM to generate or revise the estimate. Ordinary calculators or
tools used to understand supplied materials are permitted if disclosed.

## Blinding

You will not receive AI model identity or performance, Mapping A results, W5
doses, treatment assignments, identification or power results, outcomes, API
prices, or the estimates of another annotator. Do not seek those data.
