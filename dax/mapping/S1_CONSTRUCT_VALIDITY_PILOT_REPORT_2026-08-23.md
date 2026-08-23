# DAX v3 S1 construct-validity pilot report

**Status:** `COMPLETE_THRESHOLD_UNSIGNED_NO_DOWNSTREAM_RUN`

## A. Repository state

The pilot continues from `5d33c61c5a2adf8f432ae092ec8e76b580a30670`
on `task/DAX-upstream-gates-20260821`. The final result commit is recorded in
the handoff after verification because a commit cannot contain its own hash.

The protocol was frozen at `23ba7d5932ad3a84cb8301e528abd38474ad9034`;
the pre-draw ambiguous-token correction was frozen at
`f483c2eb93a4013990a2b1c86b991470fabf62c6`. No selected task statement had
been inspected before either commit.

### Provenance disclosure

The base repository and SCC private storage contained the proposed S1 size but
no persisted 120-row draw. The prompt was therefore implemented as one
deterministic first realization, not misrepresented as a prior sample. The
seed, frame, algorithm, and hashes are in `s1_draw_receipt_20260823.json`.
There was no redraw, replacement, or difficulty/model-performance filtering.

## B. Evaluability breakdown for all 120 frozen tasks

| Primary class | Tasks | Pilot task-mass share |
|---|---:|---:|
| Directly digitally executable without supplied context | 0 | 0.0000% |
| Executable with supplied files/data | 10 | 10.8613% |
| Executable with construct-valid simulated inputs | 14 | 14.8575% |
| Requires unavailable proprietary system | 2 | 1.8455% |
| Requires physical-world action | 35 | 22.8430% |
| Requires interpersonal interaction | 57 | 47.5527% |
| Otherwise not currently evaluable | 2 | 2.0400% |
| **Total non-evaluable** | **96** | **74.2812%** |

Every selected task is retained. Non-evaluable items have null instance/model
fields and were never scored as failures.

## C. Construct-validity results

The preliminary single-Codex audit applied the seven frozen axes before any
model evaluation.

| Status | Tasks | Unweighted share | Pilot task-mass share | Equal-family share |
|---|---:|---:|---:|---:|
| `PASS` | 13 | 10.8333% | 12.7861% | 10.7576% |
| `REVISE` | 11 | 9.1667% | 12.9327% | 8.7879% |
| `NON_EVALUABLE` | 96 | 80.0000% | 74.2812% | 80.4545% |

Passing instances preserve task boundary, work product, domain, and tools/input
under the pilot rule, carry low distortion/added/omitted-content risk, and have
complete owner-only synthetic fixtures where required. This is not independent
domain-expert certification.

## D. Benchmark-instance construction

- Same-boundary prospective instances constructed: 24/120 (20.0%).
- Passing and ready for independent review: 13/120 (10.8333%).
- Constructed but requiring prospective repair: 11/120 (9.1667%).
- Construction failure/non-evaluable without changing task meaning: 96/120
  (80.0%).
- Private input assets: 13 owner-only fixtures; no row-level instance or task
  identifier is committed.

## E. Scoring feasibility

| Scoring class | Constructed items | Pass items | Pilot task-mass share |
|---|---:|---:|---:|
| Fully objective/mechanical | 7 | 7 | 4.7720% |
| Partially objective with limited rubric | 13 | 6 | 16.3242% |
| Primarily expert-rubric | 4 | 0 | 4.6226% |
| Not currently scoreable | 0 constructed / 96 non-evaluable | 0 | 74.2812% |

Among passing mass, 37.3216% is fully mechanical; across the full 120-task
pilot, only 4.7720% of task mass both passes construct validity and needs no
human judgment. Legal, clinical documentation, commercial contracts, municipal
compliance, operations budgeting, security governance, emergency
documentation, and other named families require at least limited qualified
review. The 11 revisions additionally require legal, CAD/set design,
sustainability, climate risk, technical writing/communication, proposal,
security, and quality-validation expertise.

## F. Task-mass and family coverage

- Passing pilot task mass: 12.7861%; benchmarkable including revision: 25.7188%.
- Passing equal-family share: 10.7576%; benchmarkable including revision:
  19.5455%.
- Families with at least one pass: 12/22.
- All 22 major families remain in the denominator; families and tasks are not
  renormalized away when non-evaluable.

These are descriptive within-pilot weights from frozen 2021 annual task-wage
allocations and equal-family averaging. S1 is a balanced construct pilot, not a
design-weighted population estimator.

## G. Main failure modes

| Failure mode | Tasks | Interpretation |
|---|---:|---|
| Live interpersonal/supervisory interaction | 57 | Reciprocal communication, care, supervision, negotiation, instruction, authority, or stakeholder behavior is integral. |
| Physical-world action | 35 | Complete success requires manipulation, inspection, transport, treatment, cooking, equipment operation, or other embodied execution. |
| Unavailable proprietary system | 2 | An organization-specific claims/security/operating environment is indispensable. |
| No bounded observable work product | 2 | Ongoing knowledge maintenance or observation cannot be scored as a completed task under the current unit. |
| Repairable domain/input/rubric/CAD/role-boundary defect | 11 | A same-boundary artifact is plausible, but the domain packet, tool fixture, difficulty anchor, or expert rubric is incomplete. |

The dominant result is task heterogeneity, not poor AI performance—no AI was
evaluated.

## H. Prospective threshold still required

No aggregate S1 numerical threshold was signed. The item-level rule was applied
exactly, but the formal gate remains `UNRESOLVED`. The separate PI packet asks
for pass, task-mass, family, revision, non-evaluable-mass, objective-scoring,
expert-validation, and historical-executability decisions. V2 thresholds and
the W2 90% mapping gate are not reused.

## I. Historical-model capture readiness and urgency

For the 13 passing items, the existing planning design of two equivalent
instances × three repetitions implies:

- 78 calls per model vintage;
- 1,248 calls across the 16 direct-but-unprobed or approved-stand-in-but-
  unconfigured registry rows; and
- illustrative direct-API sensitivity of about USD 1.68–262.08 under the
  already documented 5k-input/1k-output low/high price assumptions, excluding
  hosting, tools, retries, human scoring, and future price changes.

Ten pass items are text/JSON native; two may use spreadsheet/code execution;
one audio item needs binary attachment or base64 serialization. These are
technical planning classifications, not account-availability proof. Current
project evidence still has 14 direct rows unprobed, two stand-in providers
unconfigured, five aliases blocked, and GPT-4.5 excluded. The first documented
retirement deadline remains 2026-10-23. No API metadata or inference call was
made in S1.

## J. Scientific recommendation

**`PARTIAL_IDENTIFICATION_ONLY`**

The pilot supports the conclusion that O*NET-aligned benchmark construction is
scientifically viable for a bounded subset—especially documentation,
structured recording, calculation, compilation, and constrained artifact
production. It does not support a single digitally executable benchmark frame
for most sampled task mass: physical and interpersonal activity dominates the
non-evaluable set.

This recommendation is not an aggregate threshold signature. Do not launch S3
until the PI decides whether a partial-identification central design is
acceptable and approves independent expert construct review and revision rules.
If the desired estimand must cover embodied/interpersonal task mass centrally,
the v3 methodology requires a separate measurement design rather than
zero-filling or silently redefining those tasks.

## K. Safeguards and spend

- AI/model evaluations: 0.
- API/model-availability calls: 0.
- W4/W5/identification/power/outcome operations: 0.
- Human recruitment or paid review: 0.
- Realized incremental spend: USD 0.
- V1/v2 and the locked test: unchanged and unopened.
- Private task IDs/text, instances, fixtures, and judgments: owner-only SCC;
  only code, protocol, hashes, and aggregates enter Git.
