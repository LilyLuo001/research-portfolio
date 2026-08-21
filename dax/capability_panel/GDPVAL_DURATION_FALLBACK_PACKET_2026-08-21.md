# GDPval qualified-human duration fallback packet — 2026-08-21

**Status:** prospectively approved by PI decision commit
`4577fecab7b4e142cb28d78d4aec0800637c7b05`; `NOT_YET_APPLICABLE` and
`NOT_LAUNCHED`. It becomes applicable only if validated author data remain
unavailable after 14 calendar days or an explicit author response activates
the route. It implements the source hierarchy in
`TASK_DURATION_PROTOCOL_2026-08-21.md`.

## 1. Estimand and task packet

For each GDPval task, estimate active human labor minutes for one competent
professional to produce one rubric-compliant completion with supplied inputs
ready. Include task-specific reading, analysis, drafting, tool operation, and
quality assurance. Exclude queue time, passive waiting, unrelated training,
procurement, and coordination not required by the prompt. Record elapsed time
separately if an annotator has direct timing evidence.

Every annotator sees the same versioned private packet: task ID, prompt,
provided inputs, required deliverables, rubric, competency assumption,
estimand, inclusion/exclusion rules, and the response form. They do not see AI
performance, prices, other annotators' estimates, Mapping A labels, W5 dose,
power, treatment effects, occupations' downstream exposure, or outcomes.

## 2. Annotator eligibility and independence

- Each task requires three independent round-1 annotators.
- An annotator must document current or recent professional experience in the
  GDPval occupation or experience directly supervising the relevant work.
- Record only a private eligibility code, experience band, conflict statement,
  and reviewer approval; do not commit identities or CVs.
- The three round-1 estimates must be completed without communication or access
  to one another's responses. The same person cannot fill two roles for a task.
- A fourth independently qualified reviewer adjudicates cases triggered below.
- An LLM may check form completeness but cannot supply, revise, or adjudicate a
  duration estimate.

## 3. Response form and scale

For one competent professional, the annotator records:

1. lower plausible active minutes;
2. best/median active minutes;
3. upper plausible active minutes;
4. selections from the log-spaced grid `5, 15, 30, 60, 120, 240, 480, 960,
   1,920+` minutes;
5. short private rationale by required work stage;
6. missing-input flag and whether the task can be completed as provided;
7. direct experience/timing basis versus structured expert judgment;
8. included/excluded time components and confidence.

Values must be positive and ordered `lower <= median <= upper`. The `1,920+`
bin requires a numeric lower bound and may retain an open upper tail rather
than inventing a finite maximum.

## 4. Frozen disagreement, outlier, aggregation, and missingness rules

- Trigger fourth-reviewer adjudication if any pair of round-1 median estimates
  differs by more than one adjacent grid bin, if inclusion/exclusion coding
  conflicts, or if any annotator flags missing required inputs.
- Preserve all original responses. The adjudicator may confirm a response,
  document an interpretation correction, or leave the task unresolved; they
  may not delete an inconvenient value.
- No automatic trimming or winsorization. A factual unit or transcription
  correction requires a reason code and retains the original value.
- Frozen task median: median of the three valid round-1 medians after any
  documented adjudication. Lower bound: minimum valid lower estimate. Upper
  bound: maximum valid upper estimate. If adjudication changes eligibility or
  interpretation, record both pre- and post-adjudication summaries.
- Fewer than three valid independent estimates, an unresolved missing-input
  flag, failed ordering/unit checks, or failed PI-approved agreement floor
  leaves the task missing. No occupation mean, cross-task average, constant,
  semantic match, or model-generated imputation is permitted.
- The gate requires all 220 task IDs exactly once and uses lower/median/upper
  bounds throughout cost and crossing sensitivity.

## 5. Assignment, blinding, and storage mechanics

- Freeze the eligible roster before assignments. Assign annotators to tasks by
  deterministic hash of protocol version, task ID, and private annotator code,
  subject to eligibility and conflicts; record the seed privately.
- Distribute the minimum task material required through BU-approved storage.
- Store identities, task text, rationales, assignments, and row-level estimates
  only under `/usr3/graduate/qluo/dax-private/task_duration/annotation_<date>/`
  with directory mode `700` and file mode `600`.
- Git may receive only protocol/version, aggregate counts, reliability metrics,
  hashes, failure reasons, and gate status. It must not receive task text,
  identities, or row-level durations.
- Keep Mapping A validation and duration annotation stores separate. Duration
  annotators never receive mapping retrieval scores or relation labels.

## 6. Launch checklist and stopping rules

The annotation may launch only after all boxes are signed:

- [ ] PI approves use of qualified-human estimates when exact author values are unavailable.
- [ ] PI approves the numeric adjacent-bin agreement floor.
- [ ] Roster eligibility and conflict review is complete.
- [ ] Compensation, consent, confidentiality, and any IRB determination are documented.
- [ ] Versioned task packet and deterministic assignment script pass dry-run checks.
- [ ] Private SCC directory and permissions are verified.
- [ ] No Mapping A labels, AI performance, outcomes, or downstream estimates appear in packets.
- [ ] Pilot size and a stop/revise rule are signed; pilot responses cannot be used to tune the rule that judges that same pilot.

Stop and return `NEED_HUMAN` for an unqualified annotator, confidentiality
failure, missing task input, fewer than three independent estimates, material
rubric ambiguity, or failure of the prospectively approved agreement rule.

For the authorized 40-task pilot, a task satisfies the adjacent-bin agreement
criterion only when the maximum minus minimum round-1 **median** bin index
across its three independent annotators is at most one, before adjudication.
The aggregate pilot rule therefore requires at least 32 of 40 tasks to satisfy
that criterion. Adjudication may explain disagreement but cannot retroactively
convert a round-1 pilot failure into agreement. The family-concentration rule
and stratified pilot-selection algorithm must be mechanically frozen before
any pilot estimate is collected; if they are not, the pilot may not launch.

## 7. Recorded PI decision — task-duration source/fallback

- Send the GDPval author request first: YES
- Minimum response period before fallback consideration: 14 calendar days
- Accept exact author task-level values under the stated validation rule: YES
- Approve three-independent-qualified-annotator fallback: YES, conditionally
- Pilot size: 40 stratified tasks
- Pilot pass rule: at least 80% of pilot tasks satisfy the adjacent-bin
  criterion and no systematic family-concentrated failure invalidates that
  family's use of the protocol
- Author data take precedence if later received and validated: YES
- Approved privacy/DUA/IRB conditions: ____
- Decision authority/date: PI/specification owner / 2026-08-21

Current status is `AUTHORIZED_CONDITION_NOT_MET_NOT_LAUNCHED`.
